"""
Application configuration.

This module is the single source of truth for all environment-driven
configuration. No other module should call os.getenv().
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# LLM Configuration
# ==========================================================

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "Missing GROQ_API_KEY in .env"
    )

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

LLM_TEMPERATURE = float(
    os.getenv("LLM_TEMPERATURE", "0.2")
)

LLM_MAX_TOKENS = int(
    os.getenv("LLM_MAX_TOKENS", "1024")
)