from functools import lru_cache

from django.conf import settings
from langchain_huggingface import HuggingFaceEmbeddings

BGE_QUERY_PROMPT = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
        query_encode_kwargs={
            "prompt": BGE_QUERY_PROMPT,
            "normalize_embeddings": True,
        },
    )
