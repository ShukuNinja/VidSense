import ollama

from src.prompt_builder import build_prompt
from src.constants import MODEL_NAME, NO_EVIDENCE_RESPONSE, MAX_HISTORY_TURNS

def call_llm(system_prompt, user_prompt, history=None):

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

    response = ollama.chat(
        model = MODEL_NAME,
        messages = messages
    )

    return response["message"]["content"]
    

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
