# VidSense — Chat with any slice of a YouTube video

VidSense is a **retrieval-augmented (RAG) assistant for YouTube videos**. You give it a
video URL and a time range; it clips that segment, transcribes it, indexes it, and then
lets you have a **conversation** grounded *strictly* in what was actually said in the clip
— with streaming answers and clickable citations that jump to the exact moment in the
video.

Everything — transcription, embeddings, retrieval, and the language model — runs on
**local models**, on a laptop GPU. That constraint shaped the whole project, and a lot of
this README is about what I learned because of it.

> **Live demo:** 
> *(Self-hosted from a personal machine over a tunnel — it's up when the host is online.)*

---

## Table of contents
1. [What it does](#what-it-does)
2. [The application flow](#the-application-flow)
3. [Retrieval architecture](#retrieval-architecture)
4. [Tech stack](#tech-stack)
5. [End-to-end: from a user's query to my laptop's GPU](#end-to-end-from-a-users-query-to-my-laptops-gpu)
6. [Deployment](#deployment)
7. [Constraints of running local models](#constraints-of-running-local-models)
8. [The ideal design (cost no object)](#the-ideal-design-cost-no-object)
9. [What I learned — and how it maps to how LLM providers work](#what-i-learned--and-how-it-maps-to-how-llm-providers-work)
10. [Running it locally](#running-it-locally)

---

## What it does

- **Clip → understand → chat.** Point it at a YouTube URL + a `[start, end]` range.
- **Grounded answers only.** The model may use *only* the transcript of that clip. If the
  clip doesn't answer your question, it says so instead of hallucinating.
- **Conversational.** Follow-up questions remember context ("and how do you check the
  *compiler* version?"); unrelated questions start fresh.
- **Summaries too.** "What is this clip about?" is answered from the whole clip (similarity
  search alone can't handle whole-clip questions).
- **Citations.** Each answer links back to the timestamp in the original video.
- **Multi-user.** Email/password accounts; every user only sees their own chats.
- **Streaming UI.** Answers stream in token-by-token, like ChatGPT.

---

## The application flow

The app is **two pipelines back-to-back**.

### A. Ingestion (once per clip)
```
YouTube URL + [start,end]
   → yt-dlp resolves the stream          → ffmpeg cuts the clip          (data/videos)
   → ffmpeg extracts audio               → faster-whisper transcribes    (.txt + .srt)
   → subtitles grouped into ≤400-word chunks (with timestamps)           (data/chunks)
   → bge embeddings per chunk            → FAISS index (cosine)          (data/vector_store)
```

### B. Conversational Q&A (per question)
```
question → follow-up gate → retrieve → expand → compress → generate (grounded) → stream
```
Details below.

---

## Retrieval architecture

This is the heart of the project — turning "a question" into "the right few sentences of
transcript to feed the model."

```
                         ┌─────────────────────────────────────────────┐
  user question ───────▶ │ 1. CONTEXTUALISE (follow-up vs new topic)     │
                         │    LLM rewrites follow-ups into standalone    │
                         │    queries; detects summary/overview intent   │
                         └───────────────┬─────────────────────────────┘
                                         │ (standalone query)
                         ┌───────────────▼─────────────────────────────┐
  summary question? ────▶│    → use the WHOLE clip as evidence           │
                         │      (similarity can't match "what's this     │
                         │       about?")                                │
                         └───────────────┬─────────────────────────────┘
                                         │ (specific question)
                         ┌───────────────▼─────────────────────────────┐
                         │ 2. RETRIEVE                                   │
                         │    embed query (bge-small, instruction-tuned) │
                         │    → FAISS IndexFlatIP, top-20                 │
                         │    → filter: keep scores ≥ max(α·top, 0.60)    │
                         └───────────────┬─────────────────────────────┘
                         ┌───────────────▼─────────────────────────────┐
                         │ 3. EXPAND (region growing)                    │
                         │    adjacent retrieved chunks are merged into  │
                         │    contiguous "regions" so context isn't torn │
                         └───────────────┬─────────────────────────────┘
                         ┌───────────────▼─────────────────────────────┐
                         │ 4. COMPRESS (density-based)                   │
                         │    embed each sentence, score vs the query;   │
                         │    dense regions kept whole, sparse regions   │
                         │    keep only the ≥0.60-similarity sentences   │
                         │    → cuts noise + tokens sent to the model    │
                         └───────────────┬─────────────────────────────┘
                         ┌───────────────▼─────────────────────────────┐
                         │ 5. GENERATE                                   │
                         │    strict "use only this evidence" prompt +   │
                         │    compressed evidence + question → LLM        │
                         │    → stream tokens; attach timestamp citations│
                         └─────────────────────────────────────────────┘
```

**Why each stage exists**
- **Contextualise** — RAG breaks on follow-ups ("explain that more"); a small LLM step
  rewrites them into self-contained queries so retrieval still works.
- **Retrieve + threshold** — a *relative* threshold (`α · best score`) with an *absolute*
  floor (`0.60`) means genuinely irrelevant questions retrieve **nothing** → the model
  correctly refuses instead of grasping at weak matches.
- **Expand** — a single retrieved chunk often starts mid-thought; merging adjacent hits
  restores coherent context.
- **Compress** — instead of dumping whole chunks at the model, keep only sentences that
  actually match the question. Less noise, fewer tokens, better answers.
- **Generate** — the prompt forbids outside knowledge; the "no evidence" sentence lives in
  one place and is injected into the prompt so the code and the model always agree.

Key parameters (`src/constants.py`): `top_k=20`, `ALPHA=0.85`, `ABSOLUTE_SCORE_THRESHOLD=0.6`,
`SIMILARITY_THRESHOLD=0.60`, `DENSITY_THRESHOLD=0.5`, chunk size `≤400 words`,
history window `6 turns`.

---

## Tech stack

| Layer | Technology | Purpose |
|---|---|---|
| **LLM** | Ollama running `llama3.2:3b` | grounded generation + follow-up/summary reasoning |
| **Transcription** | `faster-whisper` (medium) | audio → text + SRT timestamps |
| **Embeddings** | `sentence-transformers` `BAAI/bge-small-en-v1.5` | query + chunk + sentence vectors |
| **Vector search** | FAISS (`IndexFlatIP`, cosine) | nearest-chunk retrieval |
| **Media** | `yt-dlp` + `ffmpeg` | resolve stream, cut clip, extract audio |
| **Backend** | FastAPI + Uvicorn | REST + Server-Sent-Events streaming |
| **Auth** | JWT (`PyJWT`) + `bcrypt` | multi-user login, per-user isolation |
| **DB** | SQLite + SQLAlchemy | users, chats, messages |
| **Frontend** | React + Vite + TypeScript | ChatGPT-style SPA, token streaming |
| **Proxy / TLS** | Caddy | reverse proxy + automatic HTTPS |
| **Packaging** | Docker + docker-compose | one-command deploy |
| **Tunnel (current)** | ngrok | permanent public URL to the self-hosted app |

The Python core (`src/`) is UI-agnostic: the same functions power a CLI (`main.py`) and the
web backend (`backend/`).

---

## End-to-end: from a user's query to my laptop's GPU

This is the exact path a single question travels — and where my hardware becomes the
bottleneck.

```
 1. Browser: user types a question, clicks Send (SSE POST).
 2. Internet: browser ──▶ ngrok edge ──▶ encrypted tunnel ──▶ localhost:8000
                                                              (FastAPI, on MY laptop)
 3. Backend: verify JWT, check per-user rate limit.
 4. Load the chat's FAISS index + chunk JSON from disk (cached in RAM).
 5. Follow-up gate  ── LLM call ──▶ Ollama ──▶ llama3.2:3b on the RTX 3050 GPU   [GPU]
       (rewrites the query / classifies summary vs specific)
 6. Embed the query  ─────────────▶ bge-small-en-v1.5                            [GPU/CPU]
 7. FAISS cosine search (top-20) → threshold filter                              [CPU]
 8. Region growing (merge adjacent chunks)                                       [CPU]
 9. Compress: embed + score each sentence vs the query                          [GPU/CPU]
10. Build the grounded prompt (system rules + evidence + question)
11. GENERATE  ── the heavy step ──▶ Ollama ──▶ llama3.2:3b on the RTX 3050 GPU   [GPU ★]
       decodes the answer token-by-token
12. Stream: each token ──▶ backend ──▶ ngrok ──▶ browser (renders live)
13. Persist the final answer + citations to SQLite.
```

**Step 11 is where everything converges on a single 4 GB GPU.** That one GPU, decoding one
token at a time for one request, is the whole performance story of this project — and the
reason the next two sections exist.

---

## Deployment

**Packaged** (`Dockerfile`, `docker-compose.yml`, `Caddyfile`, `DEPLOY.md`) as three
containers — `ollama` (GPU), `app` (FastAPI + built SPA, CPU), `caddy` (HTTPS) — so a GPU
host can run the whole thing with:
```bash
cp .env.example .env      # set VIDSENSE_SECRET, DOMAIN
docker compose up -d --build
```

**Currently running** as a self-hosted app: the backend + Ollama run on my laptop, exposed
to the internet through an **ngrok tunnel** with a reserved domain. This is free and needs
no cloud GPU — but the app is only reachable while my machine is on. It's the pragmatic
choice for a portfolio demo; the "proper" alternative is a cloud GPU VM (see below).

---

## Constraints of running local models

Running the LLM myself, on a **laptop RTX 3050 with 4 GB of VRAM**, is where the real
lessons came from.

- **VRAM is the hard ceiling.** My first model, `qwen3:8b`, is ~6 GB — it *doesn't fit* in
  4 GB. Ollama split it **61% CPU / 39% GPU**, and a one-sentence answer took **~90
  seconds** (CPU-speed token generation). Switching to `llama3.2:3b` (~2 GB, fits on the
  GPU) dropped that to **~5 seconds**.
- **Model behaviour matters as much as size.** `qwen3` is a *reasoning* model — even with
  "thinking" disabled it narrates its reasoning into the answer, staying slow and verbose.
  A small **instruct** model answers directly. Picking the model was as important as the
  hardware.
- **One request at a time.** Ollama serves a single generation per model instance, so
  concurrent users **queue**. Fine for a few people; it does not scale.
- **Cold starts are real.** Loading ~2–6 GB of weights into VRAM takes seconds, and I even
  hit a transient CUDA "cold-load" crash (handled now with a retry). The first question of
  a session pays this cost.
- **Everything competes for the same GPU.** Whisper (transcription), the embedding model,
  and the LLM all want VRAM at once — on 4 GB they step on each other.
- **You can't host it cheaply.** Because it needs a GPU, a normal $5/month web host (or
  serverless platforms like Vercel/Netlify) simply can't run it — which is why it's on a
  tunnel to my own machine instead of "just deployed to the cloud."

None of these are bugs. They're the physics of running large models on small, shared,
single hardware — and they're exactly the problems large providers engineer around.

---

## The ideal design (cost no object)

If deployment cost weren't a concern, VidSense would look like a real production RAG
service:

```
        ┌──────────┐    ┌──────────────┐    ┌───────────────────────────┐
 users─▶│  CDN +    │──▶ │ API gateway  │──▶ │ stateless app servers      │
        │  SPA      │    │ + auth/OAuth │    │ (autoscaled)               │
        └──────────┘    └──────────────┘    └───┬───────────────┬───────┘
                                                 │               │
                       ┌─────────────────────────▼───┐   ┌───────▼──────────┐
                       │ ingestion queue (Redis/Celery)│   │ managed Postgres │
                       │ → GPU transcription workers   │   │ + object storage │
                       └─────────────────────────┬─────┘   │   (S3) for media │
                                                 │         └──────────────────┘
                       ┌─────────────────────────▼─────┐   ┌──────────────────┐
                       │ managed vector DB             │   │ LLM inference     │
                       │ (pgvector / Pinecone / Milvus)│   │ fleet: many GPUs, │
                       └───────────────────────────────┘   │ continuous batch  │
                                                           │ (vLLM/TGI) + LB   │
                                                           └──────────────────┘
```

- **LLM inference** on a fleet of datacenter GPUs (A100/H100, 40–80 GB each), using
  **continuous batching** so one GPU serves *many* concurrent users, behind a load
  balancer with autoscaling — instead of one laptop GPU serving one request at a time.
- **Transcription** as its own autoscaled GPU worker pool fed by a **job queue**, so
  ingestions run in parallel instead of one-at-a-time.
- **Managed vector DB** (pgvector/Pinecone/Milvus) instead of a local FAISS file, so
  retrieval scales and persists independently.
- **Postgres + object storage (S3)** instead of SQLite + local disk, so many app servers
  can be stateless and horizontally scaled.
- **API gateway, OAuth, observability, CDN** for the frontend.

The interesting part: **the RAG logic barely changes.** What changes is the *infrastructure
around the models* — which is precisely the expensive, hard part that this project taught me
to appreciate.

---

## What I learned — and how it maps to how LLM providers work

Building this on one small GPU turned abstract "LLM infra" ideas into things I actually felt.
Every constraint above is something companies like OpenAI/Anthropic/Google engineer around:

1. **VRAM is the currency of LLM serving.** A model's weights (plus its KV cache and
   activations) must live in GPU memory. I couldn't fit a 6 GB model in 4 GB → CPU offload →
   ~15× slowdown. Providers run **80 GB GPUs** and split enormous models across **many GPUs**
   (tensor/pipeline parallelism) to hold 70B–400B+ parameter models. My 4 GB wall is their
   80 GB × N-GPUs wall — same problem, different scale.

2. **Quantization buys headroom.** I ran 4-bit quantized models to make them fit at all;
   providers quantize too — it's a core lever for fitting bigger models and serving more
   users per GPU.

3. **The real magic is batching, and it's why one GPU can serve thousands.** My setup
   decodes **one request at a time**, leaving the GPU idle between tokens. Production
   inference servers (vLLM, TGI, TensorRT-LLM) use **continuous batching** — interleaving
   many users' requests through the GPU at once, keeping it saturated. This is *the* reason
   "one GPU = one user" for me but "one GPU = hundreds of users" for a provider. It reframed
   how I think about GPU utilization entirely.

4. **Keeping models warm is a feature.** My cold-start (and CUDA crash) come from loading
   weights per session. Providers keep models **resident and pooled** so there's no
   per-request load cost — model loading is amortized, not paid on your request.

5. **Concurrency needs a queue and a fleet, not just a bigger GPU.** My single instance
   serializes; scaling means **multiple GPU workers behind a load balancer with a request
   queue and autoscaling** — the shape of any real inference platform.

6. **This is why LLM APIs are metered per token.** GPUs are the dominant cost, and they're
   kept busy via batching. When you pay per token, you're renting a **carefully-scheduled
   slice of very expensive GPU time**. It also explains why you *can't* run an LLM on a cheap
   CPU host — the same reason my app lives on a tunnel to a GPU instead of on Vercel.

7. **Local vs hosted is a genuine tradeoff, not just convenience.** Local = private, free,
   fully in my control, but bounded by my hardware. Hosted = effectively unlimited scale and
   speed, but data leaves the machine and you pay per use. I built the app to run locally by
   choice, and *understanding why the hosted option exists* — batching, fleets, warm pools,
   VRAM economics — was the most valuable outcome of doing it the hard way.

In short: I set out to build a RAG app, and ended up understanding **why LLM inference is a
hard, expensive, specialized systems problem** — because I ran into every one of those walls
on a 4 GB laptop GPU.

---

## Running it locally

```bash
# prerequisites: Python 3.11, Node 20+, ffmpeg, and Ollama (https://ollama.com)
ollama pull llama3.2:3b

# backend
python -m venv venv && venv/Scripts/pip install -r requirements.txt -r requirements-backend.txt
venv/Scripts/python -m uvicorn backend.app:app --port 8000

# frontend (separate terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173

# or the CLI version
venv/Scripts/python main.py
```

For containerized / production deployment (Docker + Caddy + HTTPS), see **[DEPLOY.md](DEPLOY.md)**.
For a deeper architecture reference, see **[CLAUDE.md](CLAUDE.md)**.

---

*Built as a learning project exploring RAG, local LLM inference, and the systems realities
of serving AI models.*
