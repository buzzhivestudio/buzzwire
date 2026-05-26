from __future__ import annotations

import base64
import os
import re
import secrets
from threading import Lock
from pathlib import Path
from typing import Any, Generator
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from buzzwire import storage
from buzzwire.db import DatabaseIntegrityError, connect, initialize_database
from buzzwire.exporters import export_approved_markdown, export_board_json
from buzzwire.schemas import ApprovalNote, ManualTopic, PageProfilePayload, PostEdit, ToneChange
from buzzwire.services.llm import provider_status
from buzzwire.services.pipeline import fetch_and_process_rss, process_manual_topic, regenerate_post
from buzzwire.settings import DATABASE_URL, DB_PATH, STATIC_DIR


app = FastAPI(title="BuzzWire", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_database_lock = Lock()
_database_ready = False


def _masked_database_url() -> str:
    if not DATABASE_URL:
        return "not set"
    parsed = urlsplit(DATABASE_URL)
    if not parsed.scheme:
        return "set, but missing URL scheme"
    host = parsed.hostname or "unknown-host"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.username or 'user'}:***@{host}{port}{parsed.path or ''}"


def _safe_error_message(exc: Exception) -> str:
    message = str(exc) or exc.__class__.__name__
    if DATABASE_URL:
        message = message.replace(DATABASE_URL, "<DATABASE_URL>")
        parsed = urlsplit(DATABASE_URL)
        if parsed.password:
            message = message.replace(parsed.password, "***")
    message = re.sub(r"://([^:\s/@]+):([^@\s]+)@", r"://\1:***@", message)
    return message[:800]


def _database_error_detail(exc: Exception, phase: str) -> dict[str, str]:
    return {
        "message": f"BuzzWire database {phase} failed.",
        "error_type": exc.__class__.__name__,
        "error": _safe_error_message(exc),
        "database_url": _masked_database_url(),
        "hint": (
            "Check Vercel Production env vars, Supabase pooler connection string, "
            "URL-encoded password, and redeploy after every env var change."
        ),
    }


def _auth_credentials() -> tuple[str, str] | None:
    username = os.getenv("BUZZWIRE_AUTH_USERNAME", "").strip()
    password = os.getenv("BUZZWIRE_AUTH_PASSWORD", "").strip()
    if not username or not password:
        return None
    return username, password


def _unauthorized() -> Response:
    return Response(
        "Authentication required",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="BuzzWire"'},
    )


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    if request.url.path == "/api/health":
        return await call_next(request)

    credentials = _auth_credentials()
    if credentials is None:
        return await call_next(request)

    auth_header = request.headers.get("authorization", "")
    scheme, _, encoded = auth_header.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        return _unauthorized()

    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return _unauthorized()

    username, _, password = decoded.partition(":")
    expected_username, expected_password = credentials
    username_ok = secrets.compare_digest(username, expected_username)
    password_ok = secrets.compare_digest(password, expected_password)
    if not (username_ok and password_ok):
        return _unauthorized()

    return await call_next(request)


def ensure_database() -> None:
    global _database_ready
    if _database_ready:
        return
    with _database_lock:
        if not _database_ready:
            try:
                initialize_database()
            except Exception as exc:
                print(
                    "BuzzWire database initialization failed: "
                    f"{type(exc).__name__}: {_safe_error_message(exc)}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=_database_error_detail(exc, "setup"),
                ) from exc
            _database_ready = True


def get_conn() -> Generator[Any, None, None]:
    ensure_database()
    try:
        conn = connect(DB_PATH)
    except Exception as exc:
        print(
            "BuzzWire database connection failed: "
            f"{type(exc).__name__}: {_safe_error_message(exc)}"
        )
        raise HTTPException(
            status_code=500,
            detail=_database_error_detail(exc, "connection"),
        ) from exc
    try:
        yield conn
    finally:
        conn.close()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        Path(STATIC_DIR) / "index.html",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "BuzzWire"}


@app.get("/api/db-health")
def db_health() -> dict[str, Any]:
    ensure_database()
    conn = connect(DB_PATH)
    try:
        profiles = storage.get_profiles(conn)
    finally:
        conn.close()
    db_mode = "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite"
    return {
        "status": "ok",
        "database": db_mode,
        "database_url": _masked_database_url(),
        "profiles": len(profiles),
    }


@app.get("/api/provider")
def provider() -> dict:
    return provider_status()


@app.get("/api/profiles")
def profiles(conn: Any = Depends(get_conn)) -> list[dict]:
    return storage.get_profiles(conn)


@app.post("/api/profiles")
def create_profile(payload: PageProfilePayload, conn: Any = Depends(get_conn)) -> dict:
    try:
        profile = storage.upsert_profile(conn, payload.model_dump())
    except DatabaseIntegrityError as exc:
        raise HTTPException(status_code=400, detail="A page with this name already exists.") from exc
    return {"ok": True, "profile": profile}


@app.put("/api/profiles/{profile_id}")
def update_profile(
    profile_id: int,
    payload: PageProfilePayload,
    conn: Any = Depends(get_conn),
) -> dict:
    try:
        profile = storage.upsert_profile(conn, payload.model_dump(), profile_id=profile_id)
    except DatabaseIntegrityError as exc:
        raise HTTPException(status_code=400, detail="A page with this name already exists.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "profile": profile}


@app.get("/api/sources")
def sources(conn: Any = Depends(get_conn)) -> list[dict]:
    return storage.get_sources(conn)


@app.get("/api/board")
def board(conn: Any = Depends(get_conn)) -> dict:
    return storage.get_board(conn)


@app.post("/api/manual-topic")
def manual_topic(payload: ManualTopic, conn: Any = Depends(get_conn)) -> dict:
    try:
        result = process_manual_topic(
            conn,
            title=payload.title,
            summary=payload.summary,
            source_url=payload.source_url,
            niche_hint=payload.niche_hint,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **result}


@app.post("/api/fetch/rss")
def fetch_rss(
    limit_per_source: int = Query(default=4, ge=1, le=20),
    conn: Any = Depends(get_conn),
) -> dict:
    result = fetch_and_process_rss(conn, limit_per_source=limit_per_source)
    return {"ok": True, **result}


@app.post("/api/posts/{post_id}/approve")
def approve_post(
    post_id: int,
    payload: ApprovalNote | None = None,
    conn: Any = Depends(get_conn),
) -> dict:
    storage.update_generated_post_fields(conn, post_id, {"status": "approved"})
    storage.insert_approval(conn, post_id, "approved", payload.notes if payload else "")
    return {"ok": True, "post_id": post_id, "status": "approved"}


@app.post("/api/posts/{post_id}/reject")
def reject_post(
    post_id: int,
    payload: ApprovalNote | None = None,
    conn: Any = Depends(get_conn),
) -> dict:
    storage.update_generated_post_fields(conn, post_id, {"status": "rejected"})
    storage.insert_approval(conn, post_id, "rejected", payload.notes if payload else "")
    return {"ok": True, "post_id": post_id, "status": "rejected"}


@app.post("/api/posts/{post_id}/used")
def mark_used(
    post_id: int,
    payload: ApprovalNote | None = None,
    conn: Any = Depends(get_conn),
) -> dict:
    storage.update_generated_post_fields(conn, post_id, {"status": "used"})
    storage.insert_approval(conn, post_id, "used", payload.notes if payload else "")
    return {"ok": True, "post_id": post_id, "status": "used"}


@app.post("/api/posts/{post_id}/regenerate-title")
def regenerate_title(post_id: int, conn: Any = Depends(get_conn)) -> dict:
    try:
        post = regenerate_post(conn, post_id, mode="title")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "post": post}


@app.post("/api/posts/{post_id}/regenerate-caption")
def regenerate_caption(post_id: int, conn: Any = Depends(get_conn)) -> dict:
    try:
        post = regenerate_post(conn, post_id, mode="caption")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "post": post}


@app.post("/api/posts/{post_id}/change-tone")
def change_tone(post_id: int, payload: ToneChange, conn: Any = Depends(get_conn)) -> dict:
    try:
        post = regenerate_post(conn, post_id, mode="all", tone_override=payload.tone)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "post": post}


@app.post("/api/posts/{post_id}/edit")
def edit_post(post_id: int, payload: PostEdit, conn: Any = Depends(get_conn)) -> dict:
    fields = {
        key: value.strip()
        for key, value in payload.model_dump(exclude_none=True).items()
        if isinstance(value, str) and value.strip()
    }
    if not fields:
        raise HTTPException(status_code=400, detail="No editable fields were provided.")
    try:
        storage.get_generated_post_detail(conn, post_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    storage.update_generated_post_fields(conn, post_id, fields)
    return {"ok": True, "post": storage.get_generated_post_detail(conn, post_id)}


@app.get("/api/export/json")
def export_json(conn: Any = Depends(get_conn)) -> Response:
    return Response(export_board_json(storage.get_board(conn)), media_type="application/json")


@app.get("/api/export/markdown")
def export_markdown(conn: Any = Depends(get_conn)) -> Response:
    return Response(
        export_approved_markdown(storage.get_approved_posts(conn)),
        media_type="text/markdown",
    )
