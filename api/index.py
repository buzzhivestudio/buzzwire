from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
TASK_DIR = Path(__file__).resolve().parent
for candidate in (TASK_DIR, TASK_DIR / "api", ROOT_DIR, ROOT_DIR / "api"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from buzzwire.main import app
except Exception as exc:  # pragma: no cover - only used by remote deployment diagnostics.
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="BuzzWire Deployment Debug")

    @app.get("/{path:path}")
    def deployment_error(path: str = "") -> JSONResponse:
        return JSONResponse(
            {
                "status": "import_failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "hint": "Check Vercel build logs, project root, requirements, and environment variables.",
            },
            status_code=500,
        )
