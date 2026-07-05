from src.context_builder import render_compressed_context
from src.constants import NO_EVIDENCE_RESPONSE


def build_system_prompt():

    return f"""
You are a YouTube Knowledge Assistant.

Your knowledge is limited to the evidence provided.

Rules:

1. Use only information explicitly supported by the evidence.

2. Do not use outside knowledge.

3. Do not infer, assume, or speculate beyond what the evidence states.
4. If the evidence does not contain enough information to answer the question, state:

"{NO_EVIDENCE_RESPONSE}"

Do not use outside knowledge to complete the answer.
5. Answer clearly and concisely.
6. Answer short and precise answers. Provide elaborate long answers only if the question explicitly asks for it.
7. When answering, prioritize information from the most relevant evidence regions.
"""

def build_user_prompt(query, rendered_context):
    return f"""
    Evidence: {rendered_context}

    Question: {query}
    """

def build_prompt(query, compressed_evidence):
    rendered_context = render_compressed_context(compressed_evidence)
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
                query, 
                rendered_context)
    prompt = {"system": system_prompt,
            "user": user_prompt}

    return prompt
