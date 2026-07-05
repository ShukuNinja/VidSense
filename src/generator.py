from src.prompt_builder import build_prompt
from src.llm import chat, stream_chat, active_model
from src.constants import NO_EVIDENCE_RESPONSE, MAX_HISTORY_TURNS


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
    return chat(_build_messages(system_prompt, user_prompt, history))


def stream_llm(system_prompt, user_prompt, history=None):
    """Yield answer text deltas from the active LLM provider."""
    yield from stream_chat(_build_messages(system_prompt, user_prompt, history))


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
        return {
            "query": query,
            "answer": NO_EVIDENCE_RESPONSE,
            "evidence": evidence,
            "model": active_model(),
        }

    prompts = build_prompt(query, evidence)
    answer = call_llm(prompts["system"], prompts["user"], history=history)

    return {
        "query": query,
        "answer": answer,
        "evidence": evidence,
        "model": active_model(),
    }
