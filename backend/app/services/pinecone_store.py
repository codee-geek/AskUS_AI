from __future__ import annotations

import logging
import time
from collections import defaultdict
from functools import lru_cache
from typing import Any, Iterable, Iterator
from uuid import uuid4

from langchain_core.documents import Document

from core.config import (
    EMBEDDING_DIM,
    PINECONE_API_KEY,
    PINECONE_CLOUD,
    PINECONE_INDEX_NAME,
    PINECONE_REGION,
)

logger = logging.getLogger(__name__)

# Vector ids are the chunk ids (``doc_<hash>-chunk-0001``). Splitting on this
# separator recovers the owning document id without a metadata lookup.
_DOC_CHUNK_SEPARATOR = "-chunk-"
_UPSERT_BATCH_SIZE = 100
_METADATA_TEXT_KEY = "text"
# Pinecone serverless stats are eventually consistent and can momentarily
# report a negative vector_count as a wrapped unsigned int (e.g. 2**32 - 10)
# right after deletes. No realistic session will ever exceed this, so values
# at or above it are treated as a transient glitch and clamped to 0.
_IMPLAUSIBLE_VECTOR_COUNT = 2**31


class PineconeNotConfiguredError(RuntimeError):
    """Raised when Pinecone is required but no API key is configured."""


@lru_cache(maxsize=1)
def get_pinecone_client():
    """Create a reusable Pinecone client from the configured API key."""
    if not PINECONE_API_KEY:
        raise PineconeNotConfiguredError("PINECONE_API_KEY is not configured")
    from pinecone import Pinecone

    return Pinecone(api_key=PINECONE_API_KEY)


def _document_id_from_vector_id(vector_id: str) -> str:
    return vector_id.split(_DOC_CHUNK_SEPARATOR, 1)[0]


def _extract_id(item: Any) -> str | None:
    """Pull a vector id string out of whatever ``index.list`` yields.

    The Pinecone SDK returns ``ListResponse`` pages whose ``vectors`` are
    ``ListItem(id=...)`` objects, but tests/older SDKs yield plain id strings or
    dicts. Normalise all of these to a plain id string.
    """
    vid = getattr(item, "id", None)
    if vid is None and isinstance(item, dict):
        vid = item.get("id")
    if vid is None and isinstance(item, str):
        vid = item
    return str(vid) if vid is not None else None


def _iter_vector_ids(index, namespace: str) -> Iterator[str]:
    """Yield every vector id in a namespace, handling SDK response shapes."""
    for page in index.list(namespace=namespace):
        vectors = getattr(page, "vectors", None)
        if vectors is None and isinstance(page, dict):
            vectors = page.get("vectors")
        if vectors is not None:
            items: Iterable[Any] = vectors
        elif isinstance(page, (list, tuple)):
            items = page
        else:
            items = [page]
        for item in items:
            vid = _extract_id(item)
            if vid is not None:
                yield vid


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Pinecone rejects null metadata values, so drop them and coerce types."""
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, bool, int, float)):
            cleaned[key] = value
        elif isinstance(value, (list, tuple)):
            cleaned[key] = [str(item) for item in value]
        else:
            cleaned[key] = str(value)
    return cleaned


def _batched(items: list[Any], size: int) -> Iterator[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def ensure_index(dimension: int = EMBEDDING_DIM):
    """Create the serverless index if needed and return a handle to it."""
    client = get_pinecone_client()
    if not client.has_index(PINECONE_INDEX_NAME):
        from pinecone import ServerlessSpec

        client.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
        )
        # Serverless index creation is asynchronous; wait until it is ready.
        for _ in range(60):
            if client.describe_index(PINECONE_INDEX_NAME).status.get("ready"):
                break
            time.sleep(1)

    return client.Index(PINECONE_INDEX_NAME)


def _get_index():
    """Return an index handle, or None when the index does not exist yet."""
    client = get_pinecone_client()
    if not client.has_index(PINECONE_INDEX_NAME):
        return None
    return client.Index(PINECONE_INDEX_NAME)


def upsert_chunks(chunks: list[Document], vectors: list[list[float]]) -> None:
    """Upsert chunk vectors + payloads into Pinecone, namespaced per session."""
    if not chunks:
        return

    index = ensure_index(len(vectors[0]))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk, vector in zip(chunks, vectors, strict=True):
        metadata = _clean_metadata(dict(chunk.metadata))
        metadata[_METADATA_TEXT_KEY] = chunk.page_content
        vector_id = str(chunk.metadata.get("chunk_id") or uuid4())
        namespace = str(chunk.metadata.get("session_id") or "default")
        grouped[namespace].append(
            {"id": vector_id, "values": list(vector), "metadata": metadata}
        )

    for namespace, items in grouped.items():
        for batch in _batched(items, _UPSERT_BATCH_SIZE):
            index.upsert(vectors=batch, namespace=namespace)


def search_chunks(
    *,
    query_vector: list[float],
    session_id: str,
    limit: int,
) -> list[Document]:
    """Query the session namespace and return matches as Documents."""
    index = _get_index()
    if index is None:
        return []

    response = index.query(
        vector=list(query_vector),
        top_k=limit,
        namespace=session_id,
        include_metadata=True,
    )

    documents: list[Document] = []
    for match in response.get("matches", []):
        metadata = dict(match.get("metadata") or {})
        text = str(metadata.pop(_METADATA_TEXT_KEY, ""))
        metadata["dense_score"] = float(match.get("score", 0.0))
        documents.append(Document(page_content=text, metadata=metadata))

    return documents


def count_session_chunks(session_id: str) -> int:
    """Count indexed chunks (vectors) for a session via index stats."""
    index = _get_index()
    if index is None:
        return 0
    stats = index.describe_index_stats()
    namespaces = stats.get("namespaces", {}) or {}
    namespace = namespaces.get(session_id)
    if not namespace:
        return 0
    count = int(namespace.get("vector_count", 0))
    if count < 0 or count >= _IMPLAUSIBLE_VECTOR_COUNT:
        return 0
    return count


def count_session_documents(session_id: str) -> int:
    """Count unique documents for a session by inspecting vector ids."""
    index = _get_index()
    if index is None:
        return 0

    document_ids: set[str] = set()
    try:
        for vid in _iter_vector_ids(index, session_id):
            document_ids.add(_document_id_from_vector_id(vid))
    except Exception as exc:  # pragma: no cover - network/SDK variance
        logger.warning("Failed to list vectors for session %s: %s", session_id, exc)
        return 0
    return len(document_ids)


def delete_document(session_id: str, document_id: str) -> int:
    """Delete every vector belonging to one document within a session namespace.

    Vector ids are ``<document_id>-chunk-<n>``, so we list the namespace and
    remove the ids that belong to this document. Returns chunks removed.
    """
    index = _get_index()
    if index is None:
        return 0

    prefix = f"{document_id}{_DOC_CHUNK_SEPARATOR}"
    ids_to_delete: list[str] = []
    try:
        for vid in _iter_vector_ids(index, session_id):
            if vid == document_id or vid.startswith(prefix):
                ids_to_delete.append(vid)
    except Exception as exc:  # pragma: no cover - network/SDK variance
        logger.warning(
            "Failed to list vectors for document %s in session %s: %s",
            document_id,
            session_id,
            exc,
        )
        return 0

    if not ids_to_delete:
        return 0

    removed = 0
    for batch in _batched(ids_to_delete, _UPSERT_BATCH_SIZE):
        try:
            index.delete(ids=batch, namespace=session_id)
            removed += len(batch)
        except Exception as exc:
            logger.warning(
                "Failed to delete vectors for document %s: %s", document_id, exc
            )
    return removed


def delete_session(session_id: str) -> int:
    """Delete all vectors for a session namespace. Returns chunks removed."""
    index = _get_index()
    if index is None:
        return 0

    removed = count_session_chunks(session_id)
    try:
        index.delete(delete_all=True, namespace=session_id)
    except Exception as exc:
        # Deleting a missing namespace raises a 404 on serverless; treat as no-op.
        logger.info("No Pinecone vectors deleted for session %s: %s", session_id, exc)
        return 0
    return removed


def iter_session_sources(session_id: str) -> Iterable[str]:
    """Yield unique source filenames stored for a session (best-effort)."""
    index = _get_index()
    if index is None:
        return
    seen: set[str] = set()
    try:
        all_ids = list(_iter_vector_ids(index, session_id))
        for batch in _batched(all_ids, _UPSERT_BATCH_SIZE):
            fetched = index.fetch(ids=batch, namespace=session_id)
            vectors = getattr(fetched, "vectors", None)
            if vectors is None and isinstance(fetched, dict):
                vectors = fetched.get("vectors", {})
            for vector in (vectors or {}).values():
                metadata = getattr(vector, "metadata", None)
                if metadata is None and isinstance(vector, dict):
                    metadata = vector.get("metadata")
                source = (metadata or {}).get("source")
                if source and source not in seen:
                    seen.add(str(source))
                    yield str(source)
    except Exception as exc:  # pragma: no cover - network/SDK variance
        logger.warning("Failed to iterate sources for session %s: %s", session_id, exc)
