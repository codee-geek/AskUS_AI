
from typing import List
from langchain_core.documents import Document
from unstructured.partition.auto import partition
from sentence_transformers import CrossEncoder

# Initialize the cross-encoder model ONCE (at module level)
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def cross_encoder_rerank(
    query: str,
    docs: List[Document],
    top_n: int = 10,
    max_score_gap: float = 2.0
) -> List[Document]:

    if not docs:
        return []

    pairs = []
    for doc in docs:
        section = doc.metadata.get("semantic_section", "Unknown")
        pairs.append(
            (query, f"[{section}]\n{doc.page_content}")
        )

    rerank_scores = cross_encoder.predict(pairs)

    for doc, score in zip(docs, rerank_scores):
        doc.metadata["rerank_score"] = float(score)

    # 1. Sort ONLY by cross-encoder
    docs.sort(
        key=lambda d: d.metadata["rerank_score"],
        reverse=True
    )

    # 2. Gap cutoff (on rerank score, not fused fantasy score)
    best = docs[0].metadata["rerank_score"]

    docs = [
        d for d in docs
        if best - d.metadata["rerank_score"] <= max_score_gap
    ]

    return docs[:top_n]
