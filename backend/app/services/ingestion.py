from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.bm25 import get_bm25_indexer, get_session_bm25_path
from app.services.cloud_storage import sanitize_session_id, upload_document
from app.services.embeddings import get_embeddings
from app.services.qdrant_store import upsert_chunks
from core.config import CHUNK_SIZE, CHUNK_OVERLAP

SUPPORTED_EXTENSIONS = [".pdf", ".txt", ".docx"]

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ".", " "],
)


def calculate_content_hash(file_bytes: bytes) -> str:
    """Calculate MD5 hash of uploaded bytes for stable document ids."""
    return hashlib.md5(file_bytes).hexdigest()


def load_document(file_path: str):
    """Load document based on file extension."""
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif ext == ".docx":
        loader = UnstructuredWordDocumentLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return loader.load()


async def save_uploaded_file(file: UploadFile, session_id: str = "default") -> str:
    """Kept for backward compatibility; uploads now go directly to S3 via ingest."""
    content = await file.read()
    document_id = f"doc_{calculate_content_hash(content)[:12]}"
    upload_result = upload_document(
        file_bytes=content,
        filename=file.filename,
        session_id=session_id,
        document_id=document_id,
        content_type=file.content_type,
    )
    return upload_result["uri"]


def _write_temp_file(filename: str, file_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(file_bytes)
        return tmp_file.name


def _prepare_chunks(
    *,
    documents,
    filename: str,
    session_id: str,
    document_id: str,
    s3_key: str,
    upload_time: str,
):
    for doc in documents:
        doc.metadata["source"] = filename
        doc.metadata["session_id"] = session_id
        doc.metadata["document_id"] = document_id
        doc.metadata["upload_time"] = upload_time
        doc.metadata["s3_key"] = s3_key

    chunks = text_splitter.split_documents(documents)
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{document_id}-chunk-{index:04d}"
        chunk.metadata["source"] = filename
        chunk.metadata["session_id"] = session_id
        chunk.metadata["document_id"] = document_id
        chunk.metadata["upload_time"] = upload_time
        chunk.metadata["s3_key"] = s3_key
    return chunks


def ingest_documents(
    *,
    file_bytes: bytes,
    filename: str,
    session_id: str = "default",
    content_type: str | None = None,
) -> dict:
    """
    Ingest a single uploaded document by storing it in S3 and indexing chunks in Qdrant.
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    session_key = sanitize_session_id(session_id)
    file_hash = calculate_content_hash(file_bytes)
    # Deterministic id from content so re-uploading the same file maps to a
    # stable S3 key and can be de-duplicated (keeps us within the free tier).
    document_id = f"doc_{file_hash[:16]}"
    upload_time = datetime.now(timezone.utc).isoformat()
    temp_path = _write_temp_file(filename, file_bytes)
    try:
        documents = load_document(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    if not documents:
        return {
            "chunks": 0,
            "pages": 0,
            "total_chunks": 0,
            "docs_indexed": 0,
            "session_id": session_key,
            "document_id": document_id,
            "indexed_files": [],
        }

    upload_result = upload_document(
        file_bytes=file_bytes,
        filename=filename,
        session_id=session_key,
        document_id=document_id,
        content_type=content_type,
    )

    chunks = _prepare_chunks(
        documents=documents,
        filename=filename,
        session_id=session_key,
        document_id=document_id,
        s3_key=upload_result["key"],
        upload_time=upload_time,
    )
    vectors = get_embeddings().embed_documents([chunk.page_content for chunk in chunks])
    upsert_chunks(chunks, vectors)

    bm25_indexer = get_bm25_indexer(get_session_bm25_path(session_key))
    bm25_indexer.extend_and_rebuild(chunks)

    return {
        "chunks": len(chunks),
        "pages": len(documents),
        "total_chunks": len(chunks),
        "docs_indexed": 1,
        "session_id": session_key,
        "document_id": document_id,
        "indexed_files": [filename],
        "s3_uri": upload_result["uri"],
        "s3_key": upload_result["key"],
        "upload_time": upload_time,
    }


if __name__ == "__main__":
    raise SystemExit("Run ingestion via the FastAPI upload route.")
