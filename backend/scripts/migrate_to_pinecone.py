"""Thin one-off migration: copy vectors from a local on-disk Qdrant store
into Pinecone, preserving session namespaces and chunk ids.

Usage (from the backend/ directory):

    pip install qdrant-client            # only needed to run this migration
    export PINECONE_API_KEY=...          # target Pinecone project
    python scripts/migrate_to_pinecone.py [--qdrant-path PATH] [--collection NAME]

This is intentionally minimal. It reads every point from the old Qdrant
collection and upserts it into Pinecone using namespace = session_id and
id = chunk_id (falling back to the original point id).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as `python scripts/migrate_to_pinecone.py` from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pinecone_store import ensure_index  # noqa: E402

_DEFAULT_QDRANT_PATH = str(
    Path(__file__).resolve().parents[1] / "app" / "storage" / "qdrant"
)
_BATCH = 256


def migrate(qdrant_path: str, collection: str) -> int:
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        raise SystemExit(
            "qdrant-client is required to run this migration. "
            "Install it with: pip install qdrant-client"
        )

    client = QdrantClient(path=qdrant_path)
    index = ensure_index()

    migrated = 0
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            with_payload=True,
            with_vectors=True,
            limit=_BATCH,
            offset=offset,
        )
        if not points:
            break

        grouped: dict[str, list[dict]] = {}
        for point in points:
            payload = dict(point.payload or {})
            namespace = str(payload.get("session_id") or "default")
            vector_id = str(payload.get("chunk_id") or point.id)
            grouped.setdefault(namespace, []).append(
                {"id": vector_id, "values": point.vector, "metadata": payload}
            )

        for namespace, vectors in grouped.items():
            index.upsert(vectors=vectors, namespace=namespace)
            migrated += len(vectors)

        print(f"Migrated {migrated} vectors so far...")
        if offset is None:
            break

    print(f"Done. Migrated {migrated} vectors into Pinecone.")
    return migrated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qdrant-path", default=_DEFAULT_QDRANT_PATH)
    parser.add_argument("--collection", default="rag_chunks")
    args = parser.parse_args()
    migrate(args.qdrant_path, args.collection)


if __name__ == "__main__":
    main()
