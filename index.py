from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from buzzwire.main import app
except Exception as exc:  # pragma: no cover - remote deployment diagnostics only.
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
                "hint": "Check Vercel logs, requirements.txt, and environment variables.",
            },
            status_code=500,
        )
