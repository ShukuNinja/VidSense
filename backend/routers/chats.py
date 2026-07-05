import os
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src import validators

from backend.database import SessionLocal, get_db
from backend.models import Chat, User
from backend.schemas import ChatCreate, ChatRename
from backend.serialize import chat_to_dict, chat_detail
from backend.services import schedule_ingestion, registry, cache
from backend.auth import get_current_user
from backend.ratelimit import ingest_rate_limit
from backend.sse import sse

router = APIRouter()


def _owned_chat(chat_id, user, db):
    """Fetch a chat that belongs to `user`, or 404 (don't leak existence)."""
    chat = db.get(Chat, chat_id)
    if chat is None or chat.user_id != user.id:
        raise HTTPException(404, "Chat not found.")
    return chat


@router.post("/chats")
def create_chat(
    body: ChatCreate,
    user: User = Depends(ingest_rate_limit),
    db: Session = Depends(get_db),
):
    # Cheap, offline validation up front; network resolution happens in the job.
    if not validators.validate_url(body.url):
        raise HTTPException(400, "Invalid YouTube URL.")
    if not validators.validate_timestamp(body.start_time):
        raise HTTPException(400, "Invalid start time. Use HH:MM:SS.")
    if not validators.validate_timestamp(body.end_time):
        raise HTTPException(400, "Invalid end time. Use HH:MM:SS.")
    if not validators.validate_timerange(body.start_time, body.end_time):
        raise HTTPException(400, "Start time must be before end time.")

    chat = Chat(
        user_id=user.id,
        title=body.title or "New chat",
        source_url=body.url,
        start_time=body.start_time,
        end_time=body.end_time,
        status="pending",
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)

    schedule_ingestion(chat.id, body.url, body.start_time, body.end_time)

    return chat_to_dict(chat)


@router.get("/chats")
def list_chats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == user.id)
        .order_by(desc(Chat.created_at))
        .all()
    )
    return [chat_to_dict(c) for c in chats]


@router.get("/chats/{chat_id}")
def get_chat(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return chat_detail(_owned_chat(chat_id, user, db))


@router.patch("/chats/{chat_id}")
def rename_chat(
    chat_id: int,
    body: ChatRename,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = _owned_chat(chat_id, user, db)
    chat.title = body.title
    db.commit()
    return chat_to_dict(chat)


@router.delete("/chats/{chat_id}")
def delete_chat(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = _owned_chat(chat_id, user, db)

    for path in (chat.index_path, chat.chunk_path):
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

    cache.invalidate(chat_id)
    db.delete(chat)
    db.commit()
    return {"deleted": chat_id}


@router.get("/chats/{chat_id}/ingest/stream")
def ingest_stream(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _owned_chat(chat_id, user, db)  # authorize before streaming

    def event_stream():
        last = None
        while True:
            state = registry.get(chat_id)
            if state is None:
                s = SessionLocal()
                try:
                    chat = s.get(Chat, chat_id)
                    if chat is None:
                        yield sse({"status": "failed", "error": "Chat not found."})
                        return
                    state = {
                        "status": chat.status,
                        "stage": None,
                        "stages_done": [],
                        "error": chat.error,
                    }
                finally:
                    s.close()

            if state != last:
                yield sse(state)
                last = dict(state)

            if state.get("status") in ("ready", "failed"):
                return

            time.sleep(0.4)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
