import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DB_PATH = "vectorstore"
LLM_MODEL = "gpt-4.1-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOP_K = 5       
TEMPERATURE = 0.7
SOURCE_DIRECTORY = "data"
PERSIST_DIRECTORY = "vectorstore"
MAX_INPUT_SIZE = 4096
MAX_TOTAL_TOKENS = 8192

