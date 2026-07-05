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

The app is **two pipelines run back-to-back**, orchestrated by `main.py`.

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

### Pipeline B — Conversational Q&A (`question_loop()` → `answer_query()`)
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
| `youtube_utils.py` | User input, video info, stream-URL resolution, `download_clip` |
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

## Key constants (`src/constants.py`)

| Constant | Value | Meaning |
|---|---|---|
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | sentence-transformer for chunks + queries |
| `MODEL_NAME` | `qwen3:8b` | Ollama generation (and follow-up gate) model |
| `DEFAULT_TOP_K` | `20` | candidates retrieved per query |
| `ALPHA` / `ABSOLUTE_SCORE_THRESHOLD` | `0.85` / `0.6` | relative + absolute retrieval filter |
| `SIMILARITY_THRESHOLD` / `DENSITY_THRESHOLD` | `0.60` / `0.5` | sentence-keep + full-vs-compressed region cutoff |
| `MAX_HISTORY_TURNS` | `6` | conversation turns remembered |

## Data layout (all under `data/`, git-ignored)
`videos/` · `audio/` · `transcripts/` · `chunks/` · `vector_store/{embeddings,indexes}/`

## Notes
- `test.py` is throwaway scratch (git-ignored) with hard-coded paths — **not** the app entry point. Use `main.py`.
