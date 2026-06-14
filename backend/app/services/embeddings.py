from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from core.config import EMBEDDING_DIM, EMBEDDING_MODEL, OPENAI_API_KEY


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    """Lazily build a shared OpenAI embeddings client.

    Uses the OpenAI embeddings API instead of a local sentence-transformers
    model, so the backend carries no torch dependency (smaller image, far less
    RAM, no cold-start model download).
    """
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIM,
        api_key=OPENAI_API_KEY,
    )
