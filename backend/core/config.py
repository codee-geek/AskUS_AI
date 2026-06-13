import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Also load .env from project root when running from backend/
_root_env = Path(__file__).resolve().parents[2] / ".env"
if _root_env.exists():
    load_dotenv(_root_env, override=False)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-nano")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOP_K = 5
HYBRID_FETCH_K = int(os.getenv("HYBRID_FETCH_K", "10"))
RRF_K = int(os.getenv("RRF_K", "60"))
TEMPERATURE = 0.7
ANSWER_TEMPERATURE = float(os.getenv("ANSWER_TEMPERATURE", "0.2"))
ANSWER_MAX_TOKENS = int(os.getenv("ANSWER_MAX_TOKENS", "512"))
SOURCE_DIRECTORY = "data"
PERSIST_DIRECTORY = "vectorstore"
MAX_INPUT_SIZE = 4096
MAX_TOTAL_TOKENS = 8192

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
S3_PREFIX = os.getenv("S3_PREFIX", "rag-documents")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_LOCAL_PATH = os.getenv(
    "QDRANT_LOCAL_PATH",
    str(Path(__file__).resolve().parents[1] / "app" / "storage" / "qdrant"),
)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "rag_chunks")
QDRANT_TIMEOUT_SECONDS = float(os.getenv("QDRANT_TIMEOUT_SECONDS", "10"))
