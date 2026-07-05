import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from src.errors import PipelineError
from src.youtube_utils import prepare_source
from src.pipeline import ingest_video, ProgressReporter
from src.embedder import load_chunk_data
from src.indexer import load_faiss_index

from backend.database import SessionLocal
from backend.models import Chat


# ---------------------------------------------------------------------------
# Ingestion progress registry — bridges the worker thread to the SSE endpoint.
# ---------------------------------------------------------------------------
class JobRegistry:
    def __init__(self):
        self._state = {}
        self._lock = threading.Lock()

    def _slot(self, chat_id):
        return self._state.setdefault(
            chat_id,
            {"stage": None, "title": None, "stages_done": [], "status": "ingesting", "error": None},
        )

    def reset(self, chat_id):
        with self._lock:
            self._state[chat_id] = {
                "stage": None,
                "title": None,
                "stages_done": [],
                "status": "ingesting",
                "error": None,
            }

    def update(self, chat_id, **fields):
        with self._lock:
            self._slot(chat_id).update(fields)

    def add_done(self, chat_id, stage):
        with self._lock:
            slot = self._slot(chat_id)
            if stage and stage not in slot["stages_done"]:
                slot["stages_done"].append(stage)

    def get(self, chat_id):
        with self._lock:
            slot = self._state.get(chat_id)
            return dict(slot) if slot else None


registry = JobRegistry()


class RegistryReporter(ProgressReporter):
    """ProgressReporter that publishes ingestion stages to the JobRegistry."""

    def __init__(self, chat_id):
        self.chat_id = chat_id
        self._current = None

    def start(self, key, title):
        self._current = key
        registry.update(self.chat_id, stage=key, title=title, status="ingesting")

    def success(self):
        if self._current:
            registry.add_done(self.chat_id, self._current)


# One worker so GPU-heavy ingestions (Whisper) run one at a time; extras queue.
_executor = ThreadPoolExecutor(max_workers=1)


def schedule_ingestion(chat_id, url, start_time, end_time):
    registry.reset(chat_id)
    _executor.submit(_run_ingestion, chat_id, url, start_time, end_time)


def _run_ingestion(chat_id, url, start_time, end_time):
    db = SessionLocal()
    try:
        chat = db.get(Chat, chat_id)
        if chat is None:
            return
        chat.status = "ingesting"
        db.commit()

        info, start, end, stream_url = prepare_source(url, start_time, end_time)
        result = ingest_video(info, start, end, stream_url, RegistryReporter(chat_id))

        chat = db.get(Chat, chat_id)
        chat.video_title = result.video_title
        chat.index_path = result.index_path
        chat.chunk_path = result.chunk_json_path
        chat.status = "ready"
        if not chat.title or chat.title == "New chat":
            chat.title = result.video_title
        db.commit()

        registry.update(chat_id, status="ready", stage="ready")
    except PipelineError as exc:
        _fail(db, chat_id, str(exc))
    except Exception as exc:  # unexpected — record it so the UI isn't stuck ingesting
        _fail(db, chat_id, f"Unexpected error: {exc}")
    finally:
        db.close()


def _fail(db, chat_id, message):
    chat = db.get(Chat, chat_id)
    if chat is not None:
        chat.status = "failed"
        chat.error = message
        db.commit()
    registry.update(chat_id, status="failed", error=message)


# ---------------------------------------------------------------------------
# Chat-scoped index/chunk cache so we don't reload FAISS + JSON per message.
# ---------------------------------------------------------------------------
class ChatCache:
    def __init__(self, maxsize=8):
        self._items = OrderedDict()
        self._lock = threading.Lock()
        self.maxsize = maxsize

    def get(self, chat):
        with self._lock:
            if chat.id in self._items:
                self._items.move_to_end(chat.id)
                return self._items[chat.id]

        index = load_faiss_index(chat.index_path)
        chunk_data = load_chunk_data(chat.chunk_path)

        with self._lock:
            self._items[chat.id] = (index, chunk_data)
            self._items.move_to_end(chat.id)
            while len(self._items) > self.maxsize:
                self._items.popitem(last=False)
            return self._items[chat.id]

    def invalidate(self, chat_id):
        with self._lock:
            self._items.pop(chat_id, None)


cache = ChatCache()


# ---------------------------------------------------------------------------
# Segment-aware history reconstruction (mirrors the CLI's reset-on-new-topic).
# ---------------------------------------------------------------------------
def build_history(messages):
    """Turn prior chat messages into the [{query, answer}] history the pipeline
    expects, limited to the current conversation segment.

    A new segment begins at each assistant turn that was NOT a follow-up, so a
    fresh topic doesn't carry stale context — matching the CLI behaviour.
    """
    turns = []
    pending_user = None
    for m in messages:
        if m.role == "user":
            pending_user = m.content
        elif m.role == "assistant" and pending_user is not None:
            turns.append(
                {"query": pending_user, "answer": m.content, "is_followup": m.is_followup}
            )
            pending_user = None

    segment_start = 0
    for i, turn in enumerate(turns):
        if not turn["is_followup"]:
            segment_start = i

    return [
        {"query": t["query"], "answer": t["answer"]} for t in turns[segment_start:]
    ]
