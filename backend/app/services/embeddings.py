from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from core.config import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Lazily build a shared embeddings model.

    Instantiated on first use (not at import time) so importing the app does
    not trigger a model download / HuggingFace network call.
    """
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
