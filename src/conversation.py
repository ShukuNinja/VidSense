import re

from src.llm import chat as llm_chat
from src.constants import MAX_HISTORY_TURNS

# Whole-clip / overview questions that similarity search can't retrieve (they
# aren't about any single chunk). Detected so they can be answered from the
# entire clip instead of returning no-evidence.
_SUMMARY_KEYWORDS = (
    "summar", "overview", "recap", "rundown", "the gist",
    "main point", "key point", "key takeaway", "main idea",
)
_SUMMARY_PATTERNS = (
    # "what ... discussed / topics / covered / about"
    re.compile(r"\bwhat.*\b(discuss\w*|topics?|cover\w*|about)\b", re.IGNORECASE),
    # "what ... (this) clip / video / section ..."
    re.compile(r"\bwhat.*\b(clip\w*|video|section|part|segment)\b", re.IGNORECASE),
    re.compile(r"\btell me about\b.*\b(this|the|it|clip|video)\b", re.IGNORECASE),
    re.compile(r"\bgive\b.*\b(summary|overview|rundown|gist|idea)\b", re.IGNORECASE),
)


def is_summary_question(query):
    """True if the question is about the clip as a whole (summary/overview)."""
    text = (query or "").lower()
    if any(keyword in text for keyword in _SUMMARY_KEYWORDS):
        return True
    return any(pattern.search(text) for pattern in _SUMMARY_PATTERNS)

CONTEXTUALIZE_SYSTEM = """You reformulate a user's latest question for a video Q&A system.

You are given the recent conversation and the user's latest question.

Decide which of these applies:
- FOLLOWUP: the latest question depends on the earlier conversation. It continues
  the same topic or uses references such as "it", "that", "they", "the second one",
  "more", "explain further", "why", etc. In this case, rewrite it into a fully
  self-contained question that carries over the needed context from the conversation.
- NEW: the latest question starts a different, unrelated topic and stands on its own.
  In this case, keep the question exactly as written.

Respond with EXACTLY one line, in one of these two formats, and nothing else:
FOLLOWUP: <standalone rewritten question>
NEW: <the original question unchanged>
"""


def _strip_think(text):
    """Remove <think>...</think> reasoning blocks emitted by thinking models."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _format_history(history):
    recent = history[-MAX_HISTORY_TURNS:]
    lines = []
    for turn in recent:
        lines.append(f"User: {turn['query']}")
        lines.append(f"Assistant: {turn['answer']}")
    return "\n".join(lines)


def contextualize_query(query, history):
    """Decide whether `query` is a follow-up to the conversation.

    Returns (search_query, is_followup):
    - search_query: the query to feed into the retrieval pipeline. For a follow-up
      this is a standalone rewrite; for a new topic it is the original query.
    - is_followup: True when prior turns should be shown to the model, False when
      the question should be answered self-contained.

    The first question of a session (empty history) is always self-contained, and
    costs no extra model call.
    """
    if not history:
        return query, False

    user_content = (
        f"Conversation so far:\n{_format_history(history)}\n\n"
        f"Latest question: {query}"
    )

    try:
        raw = _strip_think(
            llm_chat(
                [
                    {"role": "system", "content": CONTEXTUALIZE_SYSTEM},
                    {"role": "user", "content": user_content},
                ]
            )
        )
    except Exception:
        # If the reformulation step fails, fall back to a safe self-contained answer.
        return query, False

    if raw.upper().startswith("FOLLOWUP:"):
        rewritten = raw.split(":", 1)[1].strip()
        return (rewritten or query), True
    if raw.upper().startswith("NEW:"):
        original = raw.split(":", 1)[1].strip()
        return (original or query), False

    # Unparseable response -> default to self-contained, which never leaks stale context.
    return query, False
