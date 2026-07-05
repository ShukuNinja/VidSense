import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.pipeline import stream_answer_question

from backend.database import SessionLocal
from backend.models import Chat, Message
from backend.schemas import MessageCreate
from backend.services import cache, build_history
from backend.sse import sse

router = APIRouter()


@router.post("/chats/{chat_id}/messages")
def create_message(chat_id: int, body: MessageCreate):
    """Persist the user turn, then stream the assistant's grounded answer (SSE).

    Emits: meta -> token* -> done -> saved. The assistant message (with
    citations) is persisted after the stream completes.
    """
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "Message cannot be empty.")

    db = SessionLocal()
    try:
        chat = db.get(Chat, chat_id)
        if chat is None:
            raise HTTPException(404, "Chat not found.")
        if chat.status != "ready":
            raise HTTPException(409, f"Chat is not ready (status: {chat.status}).")

        user_msg = Message(chat_id=chat_id, role="user", content=content)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        prior = [m for m in chat.messages if m.id != user_msg.id]
        history = build_history(prior)
        index, chunk_data = cache.get(chat)
    finally:
        db.close()

    def event_stream():
        parts = []
        done = None
        try:
            for event in stream_answer_question(content, history, index, chunk_data):
                if event["type"] == "token":
                    parts.append(event["text"])
                elif event["type"] == "done":
                    done = event
                yield sse(event)
        except Exception as exc:
            yield sse({"type": "error", "message": str(exc)})
            return

        answer = done["answer"] if done else "".join(parts)
        citations = done["citations"] if done else []
        is_followup = done["is_followup"] if done else None

        session = SessionLocal()
        try:
            assistant = Message(
                chat_id=chat_id,
                role="assistant",
                content=answer,
                is_followup=is_followup,
                evidence_json=json.dumps(citations),
            )
            session.add(assistant)
            session.commit()
            session.refresh(assistant)
            message_id = assistant.id
        finally:
            session.close()

        yield sse({"type": "saved", "message_id": message_id})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
