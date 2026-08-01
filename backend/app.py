import os
from pathlib import Path

# Development convenience: load .env into os.environ so running uvicorn from a
# shell picks up variables defined in a local .env file. This is safe for local
# dev only — production should set environment variables explicitly.
def _load_dotenv_file(path: str = ".env") -> None:
    p = Path(path)
    if not p.is_file():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        # Don't overwrite existing environment variables
        if key and key not in os.environ:
            os.environ[key] = val

# Load local .env early so other modules that call os.getenv get the values.
_load_dotenv_file()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import Base, engine, ensure_user_otp_columns
from backend import models  # noqa: F401 — ensure models are registered before create_all
from backend.routers import auth, chats, messages

# In production the built frontend is served by this backend (one process, one
# port). In dev it's empty/absent and the Vite dev server serves the UI instead.
FRONTEND_DIST = os.getenv("FRONTEND_DIST", "frontend/dist")


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    ensure_user_otp_columns()

    app = FastAPI(title="VidSense API")

    # Allow the Vite dev server (Phase 2 frontend).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(chats.router, prefix="/api", tags=["chats"])
    app.include_router(messages.router, prefix="/api", tags=["messages"])

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # Serve the built SPA at "/" when present (mounted last so /api wins).
    if os.path.isdir(FRONTEND_DIST):
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


app = create_app()
