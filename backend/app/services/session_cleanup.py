from __future__ import annotations

import logging

from app.services.bm25 import get_bm25_indexer, get_session_bm25_path
from app.services.local_storage import (
    delete_document_files,
    delete_session_files,
    iter_stale_sessions,
    sanitize_session_id,
)
from app.services.pinecone_store import delete_document as delete_document_vectors
from app.services.pinecone_store import delete_session as delete_session_vectors

logger = logging.getLogger(__name__)


def delete_document(session_id: str, document_id: str) -> dict[str, int | str]:
    """Remove a single document's local file, Pinecone vectors and BM25 chunks."""
    session_key = sanitize_session_id(session_id)

    files_removed = delete_document_files(session_key, document_id)

    try:
        vectors_removed = delete_document_vectors(session_key, document_id)
    except Exception as exc:  # Pinecone unavailable / not configured
        logger.warning(
            "Could not delete vectors for document %s in session %s: %s",
            document_id,
            session_key,
            exc,
        )
        vectors_removed = 0

    try:
        bm25_removed = get_bm25_indexer(
            get_session_bm25_path(session_key)
        ).remove_document(document_id)
    except Exception as exc:
        logger.warning(
            "Could not remove BM25 chunks for document %s in session %s: %s",
            document_id,
            session_key,
            exc,
        )
        bm25_removed = 0

    logger.info(
        "Deleted document %s from session %s: %d files, %d vectors, %d bm25 chunks",
        document_id,
        session_key,
        files_removed,
        vectors_removed,
        bm25_removed,
    )
    return {
        "session_id": session_key,
        "document_id": document_id,
        "files_removed": files_removed,
        "vectors_removed": vectors_removed,
        "bm25_removed": bm25_removed,
    }


def cleanup_session(session_id: str) -> dict[str, int | str]:
    """Remove a session's local files and its Pinecone vectors (and BM25).

    The BM25 pickle lives inside the session directory, so deleting the
    directory removes it alongside the raw uploads.
    """
    session_key = sanitize_session_id(session_id)

    files_removed = delete_session_files(session_key)

    try:
        vectors_removed = delete_session_vectors(session_key)
    except Exception as exc:  # Pinecone unavailable / not configured
        logger.warning("Could not delete vectors for session %s: %s", session_key, exc)
        vectors_removed = 0

    logger.info(
        "Cleaned up session %s: %d files, %d vectors",
        session_key,
        files_removed,
        vectors_removed,
    )
    return {
        "session_id": session_key,
        "files_removed": files_removed,
        "vectors_removed": vectors_removed,
    }


def sweep_stale_sessions(ttl_hours: float) -> list[dict[str, int | str]]:
    """Clean up every session with no activity within ttl_hours."""
    results: list[dict[str, int | str]] = []
    for session_id in iter_stale_sessions(ttl_hours):
        results.append(cleanup_session(session_id))
    if results:
        logger.info("Session sweep removed %d stale session(s)", len(results))
    return results
