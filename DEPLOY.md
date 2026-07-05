# Deploying VidSense (containerized)

VidSense runs as two containers via `docker compose`:

- **`ollama`** — runs the LLM on the **GPU** (the latency-critical part).
- **`app`** — FastAPI serving the **API + built frontend** in one process, on port
  `8000`. Whisper transcription and embeddings run on **CPU** here (ingestion is a
  one-time step per clip), which keeps this image small — only Ollama needs the GPU.

It stays **single-user** (no login; everyone who can reach it shares one workspace).
Only expose it on a trusted network / behind a VPN, or add auth first.

## Prerequisites

- **Docker** + **Docker Compose** on the host.
- A machine with an **NVIDIA GPU** and the **[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)**
  installed (so the `ollama` container can use the GPU). Linux is the smoothest host.
- Enough VRAM for your model (default `llama3.2:3b` needs ~2–3 GB).

## Run it

```bash
cp .env.example .env        # then edit: set VIDSENSE_SECRET (and DOMAIN for a real host)
docker compose up -d --build
```

Three services come up: `ollama` (LLM/GPU), `app` (API + SPA), and `caddy`
(reverse proxy + automatic HTTPS). On first boot `app` waits for Ollama, pulls the
model, then serves. Open:

- **Local test:** `https://localhost` (Caddy uses a local CA, so accept the browser
  warning once).
- **Real host:** set `DOMAIN=your.domain` in `.env`, point its DNS A-record at the
  host, open ports 80/443 → `https://your.domain` gets an automatic Let's Encrypt cert.

The `app` container isn't published to the host directly — all traffic goes through
Caddy on 80/443.

Follow logs / check status:

```bash
docker compose logs -f app
docker compose ps
```

Stop / update:

```bash
docker compose down                 # stop
docker compose up -d --build        # rebuild after code changes
```

## Configuration (env vars on the `app` service)

| Variable | Default | Meaning |
|---|---|---|
| `VIDSENSE_MODEL` | `llama3.2:3b` | Ollama model for generation + the follow-up gate |
| `OLLAMA_HOST` | `http://ollama:11434` | where the app reaches Ollama |
| `FRONTEND_DIST` | `/app/frontend/dist` | built SPA served by the backend |
| `VIDSENSE_SECRET` | dev placeholder | **JWT signing secret — set a long random value in production** (`openssl rand -hex 32`). Changing it signs everyone out. |
| `DOMAIN` | `localhost` | Caddy's site address. A real domain → automatic Let's Encrypt HTTPS; `localhost` → local self-signed cert. |

The app is **multi-user**: each visitor registers/logs in and only sees their own
chats. Set a strong `VIDSENSE_SECRET` (e.g. via a `.env` file next to
`docker-compose.yml`) before exposing it.

Pick a model to match your GPU: a small **instruct** model (llama3.2:3b,
qwen2.5:3b-instruct) is fastest; on a big GPU (16 GB+) you can use `qwen3:8b` — but
qwen3 is a *reasoning* model and answers slower/more verbosely (see `OLLAMA_THINK`
in `src/constants.py`).

## Data persistence

Two named volumes:

- `vidsense-data` → `/app/data` — clips, audio, transcripts, chunks, FAISS indexes,
  and the SQLite DB (`vidsense.db`).
- `ollama-models` → pulled models.

Both survive `docker compose down`. Use `docker compose down -v` to wipe them.

## Notes / gotchas

- **CPU-only host:** delete the `deploy:` block from the `ollama` service in
  `docker-compose.yml`. It will run, but generation will be slow.
- **torch version:** the Dockerfile installs `torch==2.12.0` from the CPU wheel
  index. If that exact version isn't published there, drop the `==2.12.0` pin (or the
  `--index-url` line) in the Dockerfile.
- **Whisper on CPU:** transcription of a clip is slower than on GPU but fine for short
  clips. For GPU transcription you'd need a CUDA base image for the `app` service.
- **Windows/macOS hosts:** GPU passthrough to containers is limited; a Linux host with
  the NVIDIA Container Toolkit is recommended for production.
- **HTTPS:** handled by the built-in `caddy` service (automatic certs). No extra proxy
  needed. There's still no rate-limiting — add abuse protection before public exposure,
  since ingestion is compute-heavy.
