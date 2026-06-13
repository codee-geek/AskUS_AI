from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from typing import Any
from uuid import uuid4

from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http import models

from core.config import (
    QDRANT_API_KEY,
    QDRANT_COLLECTION_NAME,
    QDRANT_LOCAL_PATH,
    QDRANT_TIMEOUT_SECONDS,
    QDRANT_URL,
)


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Create a reusable Qdrant client (remote server or local on-disk mode)."""
    if QDRANT_URL:
        return QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=QDRANT_TIMEOUT_SECONDS,
        )

    return QdrantClient(path=QDRANT_LOCAL_PATH)


def _session_filter(session_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="session_id",
                match=models.MatchValue(value=session_id),
            )
        ]
    )


def ensure_collection(vector_size: int) -> None:
    """Create the target collection if it does not already exist."""
    client = get_qdrant_client()
    collections = client.get_collections().collections
    existing = {collection.name for collection in collections}
    if QDRANT_COLLECTION_NAME in existing:
        return

    client.create_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )

    client.create_payload_index(
        collection_name=QDRANT_COLLECTION_NAME,
        field_name="session_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=QDRANT_COLLECTION_NAME,
        field_name="document_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


def upsert_chunks(chunks: list[Document], vectors: list[list[float]]) -> None:
    """Upsert chunk vectors and payloads into Qdrant."""
    if not chunks:
        return

    ensure_collection(len(vectors[0]))
    client = get_qdrant_client()
    points = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        payload = dict(chunk.metadata)
        payload["text"] = chunk.page_content
        points.append(
            models.PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload=payload,
            )
        )

    client.upsert(
        collection_name=QDRANT_COLLECTION_NAME,
        points=points,
        wait=True,
    )


def search_chunks(
    *,
    query_vector: list[float],
    session_id: str,
    limit: int,
) -> list[Document]:
    """Search the shared Qdrant collection with a session metadata filter."""
    client = get_qdrant_client()
    response = client.query_points(
        collection_name=QDRANT_COLLECTION_NAME,
        query=query_vector,
        query_filter=_session_filter(session_id),
        limit=limit,
        with_payload=True,
    )

    documents: list[Document] = []
    for result in response.points:
        payload = dict(result.payload or {})
        text = str(payload.pop("text", ""))
        payload["qdrant_score"] = float(result.score)
        documents.append(Document(page_content=text, metadata=payload))

    return documents


def count_session_chunks(session_id: str) -> int:
    """Count indexed chunks for the provided session."""
    count_result = get_qdrant_client().count(
        collection_name=QDRANT_COLLECTION_NAME,
        count_filter=_session_filter(session_id),
        exact=True,
    )
    return int(count_result.count)


def count_session_documents(session_id: str) -> int:
    """Count unique documents for the provided session."""
    client = get_qdrant_client()
    seen_document_ids: set[str] = set()
    offset: Any = None

    while True:
        points, offset = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=_session_filter(session_id),
            with_payload=["document_id"],
            with_vectors=False,
            limit=256,
            offset=offset,
        )
        for point in points:
            document_id = (point.payload or {}).get("document_id")
            if document_id:
                seen_document_ids.add(str(document_id))
        if offset is None:
            break

    return len(seen_document_ids)


def iter_session_sources(session_id: str) -> Iterable[str]:
    """Yield source filenames stored for a session."""
    client = get_qdrant_client()
    seen_sources: set[str] = set()
    offset: Any = None

    while True:
        points, offset = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=_session_filter(session_id),
            with_payload=["source"],
            with_vectors=False,
            limit=256,
            offset=offset,
        )
        for point in points:
            source = (point.payload or {}).get("source")
            if source and source not in seen_sources:
                seen_sources.add(str(source))
                yield str(source)
        if offset is None:
            break
