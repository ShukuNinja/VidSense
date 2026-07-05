# VidSense

A local, fully-offline **YouTube RAG assistant**. The user supplies a YouTube URL and a
time range; the app clips that segment, transcribes it, indexes it, and then answers
questions about it in a conversational loop — with answers **strictly grounded** to the
transcript (no outside knowledge).

## Running the app

```bash
# from the repository root (imports use the `src.` package prefix — do NOT run from src/)
python main.py
```

### External requirements (not pip-installable)
- **ffmpeg** on `PATH` — used to cut the clip and extract audio.
- **Ollama** server running with the generation model pulled: `ollama pull qwen3:8b`
  (`ollama serve` must be up). The app calls `check_ollama_health()` before the Q&A
  loop and aborts with guidance if the server/model is missing.
- **GPU is optional** — `faster-whisper` tries CUDA (`float16`) and falls back to CPU
  (`int8`) automatically.

Python deps are in `requirements.txt` (faster-whisper, sentence-transformers, faiss-cpu,
yt-dlp, ollama, srt, numpy, …). First run downloads the Whisper `medium` model and the
`BAAI/bge-small-en-v1.5` embedding model.

## Architecture

The core logic lives in **`src/pipeline.py`** as a stdout-free, importable service layer
(`ingest_video()`, `answer_question()`); `main.py` is a thin CLI wrapper over it, and the
web backend calls the same functions. The app is **two pipelines run back-to-back**.

### Pipeline A — Ingestion (`ingest_clip()` → returns `(chunk_data, index)` in memory)
```
get_user_input()      validate URL + timestamps, resolve stream URL (yt_dlp)
  → download_clip()   ffmpeg cuts [start,end] segment            → data/videos/*.mp4
  → extract_audio()   ffmpeg strips audio                        → data/audio/*.wav
  → transcribe_audio()faster-whisper (CUDA→CPU) → .txt + .srt, detected language
  → parse_srt → create_chunks → save_chunks   ≤400-word chunks   → data/chunks/*.json
  → extract_texts → generate_embeddings        BAAI/bge-small-en-v1.5, normalized
  → build_faiss_index → save_*                 IndexFlatIP (cosine) → data/vector_store/
```

### Gate — `check_ollama_health()` (`src/ollama_manager.py`)
Confirms Ollama is reachable and `MODEL_NAME` is available. On failure the built index is
preserved and the app exits cleanly instead of crashing at generation time.

### Pipeline B — Conversational Q&A (`answer_question()` in `src/pipeline.py`)
Per question:
```
contextualize_query()   LLM decides FOLLOW-UP vs NEW topic (src/conversation.py):
                        - follow-up → rewrite into a standalone search query + replay history
                        - new topic → reset history, answer self-contained
  → embed_query → search_index (top-20) → filter_results     RETRIEVAL
      (relative α·max threshold, floored at ABSOLUTE_SCORE_THRESHOLD)
  → build_context                                            EXPANSION (group adjacent hits into regions)
  → text_extraction → process_regions → compress_evidence    COMPRESSION (per-sentence relevance)
  → generate_answer → build_prompt → call_llm                GENERATION (qwen3:8b, evidence-only)
```
Loop repeats until the user types `exit`/`quit`.

## Module map (`src/`)

| Module | Responsibility |
|---|---|
| `pipeline.py` | **Service layer**: `ingest_video()`, `answer_question()`, `ProgressReporter`/`ConsoleReporter`, `IngestResult` — stdout-free, called by both CLI and web backend |
| `youtube_utils.py` | `prepare_source()` (non-interactive validate+resolve), `get_user_input` (CLI), video info, `download_clip` |
| `ffmpeg_utils.py` | `create_clip` (returns success bool from ffmpeg exit code) |
| `audio_utils.py` | `extract_audio` (format from `DEFAULT_AUDIO_FORMAT`) |
| `transcriber.py` | faster-whisper transcription; **lazy** `get_model()` cache |
| `chunker.py` | `parse_srt`, `create_chunks` (≤400 words), `save_chunks` |
| `embedder.py` | `get_model()` (lazy), `generate_embeddings`, chunk I/O |
| `indexer.py` | build / save / load FAISS `IndexFlatIP` |
| `retriever.py` | `embed_query`, `search_index`, `filter_results`, `retrieve_chunks` |
| `context_builder.py` | `build_context` (region growing), `render_compressed_context` |
| `context_compressor.py` | sentence split/score, density-based region compression |
| `prompt_builder.py` | system + user prompt (grounding rules; injects `NO_EVIDENCE_RESPONSE`) |
| `generator.py` | `call_llm` / `generate_answer` (Ollama), optional `history` |
| `conversation.py` | `contextualize_query` — follow-up vs new-topic gate + query rewrite |
| `ollama_manager.py` | `check_ollama_health` |
| `validators.py` | input validation; `fail()` raises `PipelineError` |
| `errors.py` | `PipelineError` (shared operational-failure exception) |
| `console_utils.py`, `file_utils.py`, `time_utils.py`, `constants.py` | helpers / config |

## Conventions & gotchas

- **Run from the repo root.** Every module imports via the `src.` package prefix.
- **Error-handling split (intentional):**
  - *Operational* ingestion failures (bad input, failed download/audio) → raise
    `PipelineError`, caught **once** in `ingest_clip()` for a clean abort.
  - *Contract/invariant* violations in the query pipeline → `ValueError`, caught per
    question by `question_loop` so one bad query never kills the session.
- **Lazy model loading:** `embedder.get_model()` and `transcriber.get_model()` build their
  models on first use, not at import — importing `main` does not load Whisper or touch the GPU.
- **Retrieval query vs. display query:** `answer_query(query, search_query, …)` retrieves
  and sentence-scores on `search_query` (the standalone rewrite for follow-ups) but shows
  the model the user's original `query`.
- **`search_index` clamps `top_k` to `index.ntotal`** so FAISS never pads results with
  sentinel scores (which otherwise pollute `filter_results` and warn on tiny indexes).
- **Pipeline order matters:** `text_extraction` (creates `sentences`) must run **before**
  `process_regions` (adds `scored_sentences`), which must run before `compress_evidence`
  (needs both). `process_regions` takes the **1-D** vector `query_embedding[0]`, not the
  `(1, dim)` batch.
- **Conversation memory:** capped at `MAX_HISTORY_TURNS`. `contextualize_query` strips
  `<think>…</think>` blocks from the thinking model and falls back to self-contained on any
  parse/API error.
- **Grounding:** the no-evidence sentence lives in one place — `constants.NO_EVIDENCE_RESPONSE`
  — and is injected into the system prompt, so the code path and the LLM instruction stay in sync.
- **Unique artifact paths:** index, embeddings, **and chunks** all use `get_unique_filepath`,
  so multiple chats from the same video never overwrite each other's data.
- **Summary questions:** whole-clip/overview questions (`conversation.is_summary_question`)
  bypass similarity retrieval and answer from the **entire clip**
  (`pipeline.full_clip_evidence`) — similarity search can't match "what is this about?".
  Specific questions keep the normal retrieval + strict-refusal path.
- **Ollama resilience:** all chat calls go through `ollama_manager.chat_with_retry`
  (`OLLAMA_MAX_ATTEMPTS`), which retries the transient CUDA cold-load crash. Streaming
  (`stream_llm`) retries only **before the first token** so output is never duplicated.

## Key constants (`src/constants.py`)

| Constant | Value | Meaning |
|---|---|---|
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | sentence-transformer for chunks + queries |
| `MODEL_NAME` | `llama3.2:3b` | Ollama generation + follow-up gate. Small instruct model that fits a 4 GB GPU and answers directly. Reasoning models (qwen3) are far slower here — they narrate reasoning even with `think=False`. |
| `OLLAMA_THINK` | `None` | `think` request option: `None` = omit (instruct models), `False` = ask a reasoning model to skip thinking, `True` = full chain-of-thought |
| `DEFAULT_TOP_K` | `20` | candidates retrieved per query |
| `ALPHA` / `ABSOLUTE_SCORE_THRESHOLD` | `0.85` / `0.6` | relative + absolute retrieval filter |
| `SIMILARITY_THRESHOLD` / `DENSITY_THRESHOLD` | `0.60` / `0.5` | sentence-keep + full-vs-compressed region cutoff |
| `MAX_HISTORY_TURNS` | `6` | conversation turns remembered |
| `OLLAMA_MAX_ATTEMPTS` | `2` | chat-call attempts before surfacing a failure (CUDA-crash retry) |

## Data layout (all under `data/`, git-ignored)
`videos/` · `audio/` · `transcripts/` · `chunks/` · `vector_store/{embeddings,indexes}/` ·
`vidsense.db` (SQLite, web backend)

## Web backend (`backend/`, FastAPI — Phase 1)

Local single-user API over the `src/pipeline.py` service layer. A **chat = one ingested
clip + its messages**.

```bash
pip install -r requirements-backend.txt
uvicorn backend.app:app --reload      # from the repo root; needs Ollama running
```

- **Auth (multi-user):** email/password with a JWT bearer token (`backend/auth.py`,
  `bcrypt` + `PyJWT`, secret from `VIDSENSE_SECRET`). `get_current_user` guards every
  chat/message/ingest endpoint; each `Chat` has a `user_id` owner and all queries are
  scoped to it (cross-user access → 404). `POST /api/auth/register|login` → token;
  `GET /api/auth/me`. The frontend stores the token (`session.ts`) and attaches it to
  every request/stream; a 401 anywhere logs out.
- **Persistence:** SQLite (`data/vidsense.db`) via SQLAlchemy — `users`, `chats`
  (owned by a user), `messages`. FAISS index / chunk JSON stay on disk; the chat row
  references their paths. (Schema changes need a fresh DB — no migrations.)
- **Ingestion:** `POST /api/chats` validates input, creates a `pending` chat, and runs
  ingestion on a single-worker `ThreadPoolExecutor` (serialized so only one Whisper job
  runs at a time). Progress is published to a `JobRegistry` and streamed via SSE at
  `GET /api/chats/{id}/ingest/stream` (`download → audio → transcribe → chunk → index`).
- **Messaging:** `POST /api/chats/{id}/messages` persists the user turn, then **streams**
  the answer as SSE events `meta → token* → done → saved`; the assistant message + citations
  are persisted after the stream. Token streaming uses `generator.stream_llm` /
  `pipeline.stream_answer_question` (`ollama.chat(stream=True)`). Citations are enriched
  (`backend/citations.py`) with absolute video timestamps + `watch?v=…&t=<secs>s`
  deep-links (clip-relative region time + the clip's start offset).
- **History:** rebuilt per turn from stored messages, segment-aware
  (`services.build_history`) so it mirrors the CLI's reset-on-new-topic.
- **Caches:** `services.cache` (LRU by `chat_id`) keeps loaded FAISS index + chunks warm.
- **Endpoints:** `GET/POST /api/chats`, `GET/PATCH/DELETE /api/chats/{id}`,
  `GET /api/chats/{id}/ingest/stream`, `POST /api/chats/{id}/messages`, `GET /api/health`.
- **Errors:** `PipelineError` → HTTP 400 (create) or `failed` chat status (ingestion);
  a mid-stream model failure emits an SSE `{"type":"error"}` frame instead of crashing.

Streaming routes are sync generators, so Starlette runs the blocking Ollama/embedding
calls in its threadpool (they don't block the event loop).

## Frontend (`frontend/`, React + Vite + TS — Phase 2)

ChatGPT-style SPA over the backend. No UI framework — plain CSS + a small
fetch-based SSE client.

```bash
cd frontend && npm install
npm run dev          # http://localhost:5173 ; proxies /api -> 127.0.0.1:8000
# run the backend separately: uvicorn backend.app:app  (from repo root)
```

- **`src/sse.ts`** — reads a fetch `ReadableStream` and parses `data:` frames.
  Used for both the ingest progress (GET) and message (POST) streams, since
  `EventSource` can't do POST.
- **`src/api.ts`** — typed client (`listChats`, `getChat`, `createChat`,
  `renameChat`, `deleteChat`, `streamIngest`, `streamMessage`).
- **Components:** `Sidebar` (chat list + status dots, rename/delete), `NewChatModal`
  (URL + time range, client-side validation mirroring `src/validators.py`),
  `IngestProgress` (SSE stepper: download → audio → transcribe → chunk → index),
  `ChatView` (loads detail; shows ingest progress until `ready`, then the chat),
  `MessageList` (bubbles + citations as clickable YouTube deep-links), `Composer`.
- **Streaming UX:** on send, an optimistic user bubble + an empty assistant bubble
  ("Searching the transcript…") are added; `token` events append text live, `done`
  finalizes content + citations. Vite dev-server proxy keeps it same-origin.
- Build/type-check: `npm run build` (`tsc --noEmit && vite build`).

## Deployment (`Dockerfile`, `docker-compose.yml`, `DEPLOY.md`)

Containerized as two services: **`ollama`** (LLM on GPU) and **`app`** (FastAPI serving
API + built SPA, CPU — Whisper/embeddings run on CPU there). One command:
`docker compose up -d --build` → open `http://<host>:8000`. Still single-user (no auth).

- The backend **serves the built frontend** when `FRONTEND_DIST` points at a real `dist/`
  (mounted at `/` after the `/api` routes); in dev that dir is absent and Vite serves it.
- Config via env: `VIDSENSE_MODEL` (→ `MODEL_NAME`), `OLLAMA_HOST` (read by the ollama
  client), `FRONTEND_DIST`. See `DEPLOY.md` for GPU prerequisites and caveats.
- `docker/entrypoint.sh` waits for Ollama, pulls the model, then starts uvicorn.

## Notes
- `test.py` is throwaway scratch (git-ignored) with hard-coded paths — **not** the app entry point. Use `main.py` (CLI), the FastAPI backend, or the frontend.
- `requirements.txt` is UTF-8 (was UTF-16, which breaks `pip`); it now also pins `ollama`.
