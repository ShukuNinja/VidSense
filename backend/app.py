from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
from backend import models  # noqa: F401 — ensure models are registered before create_all
from backend.routers import chats, messages


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

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

    app.include_router(chats.router, prefix="/api", tags=["chats"])
    app.include_router(messages.router, prefix="/api", tags=["messages"])

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
