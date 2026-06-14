import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Also load .env from project root when running from backend/
_root_env = Path(__file__).resolve().parents[2] / ".env"
if _root_env.exists():
    load_dotenv(_root_env, override=False)


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# Chunking + embeddings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
# OpenAI embeddings (no local torch model). text-embedding-3-small supports a
# configurable output dimension; 1536 is its native size.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = _get_int("EMBEDDING_DIM", 1536)

# Answer generation
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-nano")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANSWER_TEMPERATURE = _get_float("ANSWER_TEMPERATURE", 0.2)
ANSWER_MAX_TOKENS = _get_int("ANSWER_MAX_TOKENS", 512)

# Retrieval tuning
TOP_K = 5
HYBRID_FETCH_K = _get_int("HYBRID_FETCH_K", 10)
RRF_K = _get_int("RRF_K", 60)

# Upload limits
MAX_UPLOAD_MB = _get_int("MAX_UPLOAD_MB", 20)

# Pinecone (dense vector store)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "rag-chunks")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

# Session lifecycle. Raw documents are ephemeral local files; abandoned
# sessions (no activity for this many hours) are swept and their files +
# Pinecone vectors + BM25 index are deleted.
SESSION_TTL_HOURS = _get_float("SESSION_TTL_HOURS", 24)
SESSION_SWEEP_INTERVAL_MINUTES = _get_float("SESSION_SWEEP_INTERVAL_MINUTES", 60)
