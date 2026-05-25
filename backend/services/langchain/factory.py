from functools import lru_cache

from django.conf import settings
from langchain_groq import ChatGroq


@lru_cache(maxsize=1)
def get_chat_model() -> ChatGroq:
    return ChatGroq(
        model=settings.GROQ_MODEL,
        groq_api_key=settings.GROQ_API_KEY or None,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_COMPLETION_TOKENS,
    )
