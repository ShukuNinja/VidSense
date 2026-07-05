# ---------- Stage 1: build the frontend ----------
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ---------- Stage 2: app runtime (CPU) ----------
# The GPU lives in the separate `ollama` service, so this image is CPU-only:
# ffmpeg + Whisper (CPU int8) + embeddings + FAISS + FastAPI serving the SPA.
FROM python:3.11-slim AS app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OLLAMA_HOST=http://ollama:11434 \
    VIDSENSE_MODEL=llama3.2:3b \
    FRONTEND_DIST=/app/frontend/dist

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the CPU build of torch first so the CUDA build isn't pulled in.
# If this exact version isn't on the CPU index, drop the "==2.12.0" pin (or the
# whole --index-url line to use the default wheel).
COPY requirements.txt requirements-backend.txt ./
RUN pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt -r requirements-backend.txt

COPY src/ ./src/
COPY backend/ ./backend/
COPY docker/entrypoint.sh ./docker/entrypoint.sh
COPY --from=frontend /app/frontend/dist ./frontend/dist
RUN chmod +x ./docker/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./docker/entrypoint.sh"]
