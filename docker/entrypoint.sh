#!/bin/sh
set -e

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
MODEL="${VIDSENSE_MODEL:-llama3.2:3b}"

echo "[entrypoint] Waiting for Ollama at ${OLLAMA_HOST} ..."
until curl -sf "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; do
  sleep 2
done

echo "[entrypoint] Ollama is up. Ensuring model '${MODEL}' is present ..."
if python -c "import ollama, os; ollama.pull(os.environ.get('VIDSENSE_MODEL', 'llama3.2:3b'))"; then
  echo "[entrypoint] Model '${MODEL}' ready."
else
  echo "[entrypoint] WARNING: model pull failed; it will be retried on first query."
fi

exec uvicorn backend.app:app --host 0.0.0.0 --port 8000
