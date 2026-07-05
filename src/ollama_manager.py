import time

import ollama

from src.constants import MODEL_NAME, OLLAMA_MAX_ATTEMPTS, OLLAMA_RETRY_DELAY


def chat_with_retry(**kwargs):
    """ollama.chat with a retry on transient server errors.

    The CUDA cold-load crash (llama-server dies with a 500 on the first request)
    reliably recovers on a second attempt, so retry it rather than surfacing the
    failure. Non-transient errors are re-raised once attempts are exhausted.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return ollama.chat(**kwargs)
        except ollama.ResponseError:
            if attempt >= OLLAMA_MAX_ATTEMPTS:
                raise
            time.sleep(OLLAMA_RETRY_DELAY)


def _model_names(response):
    """Extract model names from an ollama.list() response.

    Handles both the newer object-style response (ListResponse with .models)
    and the older dict-style response.
    """
    models = getattr(response, "models", None)
    if models is None and isinstance(response, dict):
        models = response.get("models", [])

    names = []
    for model in models or []:
        name = getattr(model, "model", None)
        if name is None and isinstance(model, dict):
            name = model.get("model") or model.get("name")
        if name:
            names.append(name)

    return names


def check_ollama_health():
    """Verify the Ollama server is reachable and MODEL_NAME is available.

    Returns True when generation can proceed, False otherwise (with a
    human-readable reason printed to the console).
    """
    try:
        response = ollama.list()
    except Exception as exc:
        print(f" ❌ Could not reach the Ollama server: {exc}")
        print("    Make sure Ollama is installed and running (`ollama serve`).")
        return False

    available = _model_names(response)

    target_base = MODEL_NAME.split(":")[0]
    is_available = any(
        name == MODEL_NAME or name.split(":")[0] == target_base
        for name in available
    )

    if not is_available:
        print(f" ❌ Model '{MODEL_NAME}' is not available in Ollama.")
        print(f"    Pull it first with: ollama pull {MODEL_NAME}")
        return False

    return True
