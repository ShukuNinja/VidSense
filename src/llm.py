"""Provider-agnostic LLM access.

Toggle with LLM_PROVIDER:
  - "ollama" (default): local Ollama server (uses MODEL_NAME).
  - "openai": any OpenAI-compatible chat API (OpenAI, Groq, OpenRouter, Together,
    a local vLLM, ...). Configure LLM_API_BASE / LLM_API_KEY / LLM_MODEL.

Both paths take/return the same message format ([{role, content}, ...]) and
expose chat() (blocking) and stream_chat() (token generator), so the rest of the
app doesn't care which is active.
"""

import os
import time

import ollama

from src.constants import (
    MODEL_NAME,
    OLLAMA_MAX_ATTEMPTS,
    OLLAMA_RETRY_DELAY,
    OLLAMA_THINK,
)
from src.ollama_manager import chat_with_retry, check_ollama_health

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


def active_model() -> str:
    return LLM_MODEL if LLM_PROVIDER == "openai" else MODEL_NAME


# --------------------------------------------------------------------------
# Ollama (local)
# --------------------------------------------------------------------------
def _ollama_chat(messages) -> str:
    response = chat_with_retry(model=MODEL_NAME, messages=messages)
    return response["message"]["content"]


def _ollama_stream(messages):
    chat_kwargs = {"model": MODEL_NAME, "messages": messages, "stream": True}
    if OLLAMA_THINK is not None:
        chat_kwargs["think"] = OLLAMA_THINK

    attempt = 0
    while True:
        attempt += 1
        produced = False
        try:
            for chunk in ollama.chat(**chat_kwargs):
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    produced = True
                    yield piece
            return
        except ollama.ResponseError:
            # Retry the transient cold-load crash, but only before the first token.
            if produced or attempt >= OLLAMA_MAX_ATTEMPTS:
                raise
            time.sleep(OLLAMA_RETRY_DELAY)


# --------------------------------------------------------------------------
# OpenAI-compatible (hosted)
# --------------------------------------------------------------------------
def _openai_client():
    from openai import OpenAI  # lazy: only needed for the hosted provider

    return OpenAI(base_url=LLM_API_BASE, api_key=LLM_API_KEY)


def _openai_chat(messages) -> str:
    response = _openai_client().chat.completions.create(
        model=LLM_MODEL, messages=messages
    )
    return response.choices[0].message.content or ""


def _openai_stream(messages):
    stream = _openai_client().chat.completions.create(
        model=LLM_MODEL, messages=messages, stream=True
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# --------------------------------------------------------------------------
# Public interface
# --------------------------------------------------------------------------
def chat(messages) -> str:
    """Blocking completion; returns the assistant text."""
    if LLM_PROVIDER == "openai":
        return _openai_chat(messages)
    return _ollama_chat(messages)


def stream_chat(messages):
    """Yield assistant text deltas as they are generated."""
    if LLM_PROVIDER == "openai":
        yield from _openai_stream(messages)
    else:
        yield from _ollama_stream(messages)


def health_check():
    """Return (ok, message) for the active provider."""
    if LLM_PROVIDER == "openai":
        if not LLM_API_KEY:
            return False, "LLM_API_KEY is not set for the hosted LLM provider."
        try:
            _openai_client().models.list()
            return True, ""
        except Exception as exc:
            return False, f"Hosted LLM ({LLM_API_BASE}) not reachable: {exc}"
    return check_ollama_health(), ""
