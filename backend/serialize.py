import json


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def chat_to_dict(chat):
    return {
        "id": chat.id,
        "title": chat.title,
        "source_url": chat.source_url,
        "start_time": chat.start_time,
        "end_time": chat.end_time,
        "video_title": chat.video_title,
        "status": chat.status,
        "error": chat.error,
        "created_at": _iso(chat.created_at),
        "updated_at": _iso(chat.updated_at),
    }


def message_to_dict(message):
    citations = None
    if message.evidence_json:
        try:
            citations = json.loads(message.evidence_json)
        except json.JSONDecodeError:
            citations = None
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "is_followup": message.is_followup,
        "citations": citations,
        "created_at": _iso(message.created_at),
    }


def chat_detail(chat):
    data = chat_to_dict(chat)
    data["messages"] = [message_to_dict(m) for m in chat.messages]
    return data
