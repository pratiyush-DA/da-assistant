"""Backward-compatible LLM facade; implementation lives in services.langchain."""

from services.langchain.prompts import SYSTEM_PROMPT
from services.langchain.rag_chain import format_context_from_chunks as build_context_prompt
from services.langchain.streaming import stream_rag_tokens as stream_chat_completion

__all__ = ["SYSTEM_PROMPT", "build_context_prompt", "stream_chat_completion"]
