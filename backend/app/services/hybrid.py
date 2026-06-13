from __future__ import annotations

import hashlib
from typing import Iterable, List

from langchain_core.documents import Document


def _doc_key(doc: Document) -> str:
    chunk_id = doc.metadata.get("chunk_id")
    if chunk_id:
        return str(chunk_id)
    digest = hashlib.md5(doc.page_content.encode("utf-8")).hexdigest()
    return f"content-{digest}"


def reciprocal_rank_fusion(
    result_lists: Iterable[List[Document]],
    rrf_k: int = 60,
) -> List[Document]:
    """
    Merge multiple ranked document lists using Reciprocal Rank Fusion.
    Each list may contain Documents or (Document, score) tuples.
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for results in result_lists:
        for rank, item in enumerate(results):
            if isinstance(item, tuple):
                doc = item[0]
            else:
                doc = item

            key = _doc_key(doc)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
            doc_map[key] = doc

    ranked_keys = sorted(scores, key=lambda key: scores[key], reverse=True)
    fused: List[Document] = []
    for key in ranked_keys:
        doc = doc_map[key]
        doc.metadata["rrf_score"] = scores[key]
        fused.append(doc)

    return fused
