import time

import ollama

from src.prompt_builder import build_prompt
from src.ollama_manager import chat_with_retry
from src.constants import (
    MODEL_NAME,
    NO_EVIDENCE_RESPONSE,
    MAX_HISTORY_TURNS,
    OLLAMA_MAX_ATTEMPTS,
    OLLAMA_RETRY_DELAY,
)


def _build_messages(system_prompt, user_prompt, history=None):
    messages = [
        {
            "role" : "system",
            "content" : system_prompt
        }
    ]

    # Replay recent conversation turns so the model can resolve follow-up
    # references. Left empty for self-contained (new-topic) questions.
    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        messages.append({"role": "user", "content": turn["query"]})
        messages.append({"role": "assistant", "content": turn["answer"]})

    messages.append({
        "role" : "user",
        "content" : user_prompt
    })

    return messages


def call_llm(system_prompt, user_prompt, history=None):
    response = chat_with_retry(
        model = MODEL_NAME,
        messages = _build_messages(system_prompt, user_prompt, history)
    )

    return response["message"]["content"]


def stream_llm(system_prompt, user_prompt, history=None):
    """Yield answer text deltas as Ollama generates them.

    Retries the transient cold-load crash, but only before the first token is
    emitted, so streamed output is never duplicated.
    """
    messages = _build_messages(system_prompt, user_prompt, history)

    attempt = 0
    while True:
        attempt += 1
        produced = False
        try:
            for chunk in ollama.chat(model=MODEL_NAME, messages=messages, stream=True):
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    produced = True
                    yield piece
            return
        except ollama.ResponseError:
            if produced or attempt >= OLLAMA_MAX_ATTEMPTS:
                raise
            time.sleep(OLLAMA_RETRY_DELAY)


def stream_answer(query, evidence, history=None):
    """Stream a grounded answer token-by-token.

    Mirrors generate_answer: with no evidence it yields the canned no-evidence
    line (no model call); otherwise it streams the model's tokens.
    """
    if len(evidence["regions"]) == 0:
        yield NO_EVIDENCE_RESPONSE
        return

    prompts = build_prompt(query, evidence)
    yield from stream_llm(prompts["system"], prompts["user"], history=history)



def generate_answer(query, evidence, history=None):
    if len(evidence["regions"]) == 0:
        result = {
        "query": query,
        "answer": NO_EVIDENCE_RESPONSE,
        "evidence": evidence,
        "model": MODEL_NAME
    }
        return result

    prompts = build_prompt(query, evidence)

    answer = call_llm(prompts["system"], prompts["user"], history=history)

    
    result = {
        "query": query,
        "answer": answer,
        "evidence": evidence,
        "model": MODEL_NAME
    }

    return result
