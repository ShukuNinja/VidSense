import ollama

from src.prompt_builder import build_prompt
from src.constants import MODEL_NAME, NO_EVIDENCE_RESPONSE

def no_evidence_response():
    return NO_EVIDENCE_RESPONSE

def call_llm(system_prompt, user_prompt):
    
    response = ollama.chat(
        model = MODEL_NAME,
        messages = [
            {
                "role" : "system",
                "content" : system_prompt
            },
            {
                "role" : "user",
                "content" : user_prompt
            }
        ]
    )

    return response["message"]["content"]
    

def generate_answer(query, evidence):
    if len(evidence["regions"]) == 0:
        result = {
        "query": query,
        "answer": NO_EVIDENCE_RESPONSE,
        "evidence": evidence,
        "model": MODEL_NAME
    }
        return result

    prompts = build_prompt(query, evidence)

    answer = call_llm(prompts["system"], prompts["user"])

    
    result = {
        "query": query,
        "answer": answer,
        "evidence": evidence,
        "model": MODEL_NAME
    }

    return result
