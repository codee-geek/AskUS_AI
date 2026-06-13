"""
RAG Retrieval Evaluation Module

Standard IR metrics for evaluating retrieval quality:
- Precision@K: Fraction of retrieved docs that are relevant
- Recall@K: Fraction of relevant docs that are retrieved
- MRR: Mean Reciprocal Rank - position of first relevant doc
- NDCG@K: Normalized Discounted Cumulative Gain
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from langchain_core.documents import Document


@dataclass
class EvalResult:
    query: str
    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    relevant_docs_retrieved: int
    total_relevant: int


def dcg_at_k(scores: List[float], k: int) -> float:
    """Discounted Cumulative Gain at k."""
    scores = scores[:k]
    dcg = 0.0
    for i, score in enumerate(scores):
        dcg += score / (i + 1)
    return dcg


def ndcg_at_k(retrieved_scores: List[float], ideal_scores: List[float], k: int) -> float:
    """Normalized DCG at k."""
    dcg_val = dcg_at_k(retrieved_scores, k)
    idcg_val = dcg_at_k(ideal_scores, k)
    if idcg_val == 0:
        return 0.0
    return dcg_val / idcg_val


def relevance_from_binary(relevant_docs: set, retrieved_docs: List[Document]) -> List[float]:
    """Convert relevant doc IDs to binary relevance scores."""
    scores = []
    for doc in retrieved_docs:
        doc_id = f"{doc.metadata.get('source', '')}:{doc.metadata.get('page', 0)}"
        scores.append(1.0 if doc_id in relevant_docs else 0.0)
    return scores


def precision_at_k(relevant_docs: set, retrieved_docs: List[Document], k: int) -> float:
    """Calculate Precision@K."""
    retrieved = retrieved_docs[:k]
    if not retrieved:
        return 0.0
    relevant_retrieved = sum(
        1 for doc in retrieved
        if f"{doc.metadata.get('source', '')}:{doc.metadata.get('page', 0)}" in relevant_docs
    )
    return relevant_retrieved / k


def recall_at_k(relevant_docs: set, retrieved_docs: List[Document], k: int) -> float:
    """Calculate Recall@K."""
    retrieved = retrieved_docs[:k]
    if not relevant_docs:
        return 0.0
    relevant_retrieved = sum(
        1 for doc in retrieved
        if f"{doc.metadata.get('source', '')}:{doc.metadata.get('page', 0)}" in relevant_docs
    )
    return relevant_retrieved / len(relevant_docs)


def mean_reciprocal_rank(relevant_docs: set, retrieved_docs: List[Document]) -> float:
    """Calculate MRR - reciprocal rank of first relevant document."""
    for i, doc in enumerate(retrieved_docs):
        doc_id = f"{doc.metadata.get('source', '')}:{doc.metadata.get('page', 0)}"
        if doc_id in relevant_docs:
            return 1.0 / (i + 1)
    return 0.0


def evaluate_query(
    query: str,
    retrieved_docs: List[Document],
    relevant_doc_ids: set,
    k: int = 5,
) -> EvalResult:
    """Run all metrics for a single query."""
    relevance_scores = relevance_from_binary(relevant_doc_ids, retrieved_docs[:k])

    ideal_scores = sorted(relevance_scores, reverse=True)

    return EvalResult(
        query=query,
        precision_at_k=precision_at_k(relevant_doc_ids, retrieved_docs, k),
        recall_at_k=recall_at_k(relevant_doc_ids, retrieved_docs, k),
        mrr=mean_reciprocal_rank(relevant_doc_ids, retrieved_docs),
        ndcg_at_k=ndcg_at_k(relevance_scores, ideal_scores, k),
        relevant_docs_retrieved=sum(1 for s in relevance_scores if s > 0),
        total_relevant=len(relevant_doc_ids),
    )


def evaluate_retriever(
    retriever_fn,
    eval_set: List[Dict[str, Any]],
    k: int = 5,
) -> Dict[str, float]:
    """
    Evaluate a retriever against an evaluation set.

    Args:
        retriever_fn: Function that takes a query string and returns List[Document]
        eval_set: List of dicts with 'query', 'relevant_docs' (set of doc IDs)
        k: Cutoff rank for metrics

    Returns:
        Dict with mean values of all metrics
    """
    results = []

    for item in eval_set:
        query = item["query"]
        relevant_docs = item["relevant_docs"]

        retrieved = retriever_fn(query)
        result = evaluate_query(query, retrieved, relevant_docs, k)
        results.append(result)

    # Aggregate metrics
    return {
        "precision_at_k": sum(r.precision_at_k for r in results) / len(results),
        "recall_at_k": sum(r.recall_at_k for r in results) / len(results),
        "mrr": sum(r.mrr for r in results) / len(results),
        "ndcg_at_k": sum(r.ndcg_at_k for r in results) / len(results),
        "total_queries": len(results),
    }


def print_eval_report(metrics: Dict[str, float], k: int = 5):
    """Print formatted evaluation report."""
    print(f"\n{'='*50}")
    print(f"RAG Retrieval Evaluation Report (K={k})")
    print(f"{'='*50}")
    print(f"Precision@{k:2d}: {metrics['precision_at_k']:.4f}")
    print(f"Recall@{k:2d}   : {metrics['recall_at_k']:.4f}")
    print(f"MRR           : {metrics['mrr']:.4f}")
    print(f"NDCG@{k:2d}    : {metrics['ndcg_at_k']:.4f}")
    print(f"{'='*50}")
    print(f"Evaluated on {metrics['total_queries']} queries")
    print(f"{'='*50}\n")
