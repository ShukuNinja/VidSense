import json


def sse(data: dict) -> str:
    """Format a dict as a Server-Sent Events `data:` frame."""
    return f"data: {json.dumps(data)}\n\n"
