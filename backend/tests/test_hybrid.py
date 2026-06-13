from langchain_core.documents import Document

from app.services.hybrid import reciprocal_rank_fusion


def test_rrf_promotes_docs_present_in_both_lists():
    doc_a = Document(page_content="shared chunk", metadata={"chunk_id": "shared"})
    doc_b = Document(page_content="bm25 only", metadata={"chunk_id": "bm25-only"})
    doc_c = Document(page_content="dense only", metadata={"chunk_id": "dense-only"})

    bm25_results = [doc_a, doc_b]
    dense_results = [doc_a, doc_c]

    fused = reciprocal_rank_fusion([bm25_results, dense_results], rrf_k=60)

    assert [doc.metadata["chunk_id"] for doc in fused[:3]] == ["shared", "bm25-only", "dense-only"]
    assert fused[0].metadata["rrf_score"] > fused[1].metadata["rrf_score"]


def test_rrf_deduplicates_by_chunk_id():
    doc = Document(page_content="duplicate chunk", metadata={"chunk_id": "dup"})
    fused = reciprocal_rank_fusion([[doc], [doc]], rrf_k=60)

    assert len(fused) == 1
    assert fused[0].metadata["chunk_id"] == "dup"
    assert fused[0].metadata["rrf_score"] > 0


def test_rrf_accepts_scored_tuples():
    doc_a = Document(page_content="first", metadata={"chunk_id": "a"})
    doc_b = Document(page_content="second", metadata={"chunk_id": "b"})

    fused = reciprocal_rank_fusion([[(doc_a, 1.0), (doc_b, 0.5)]], rrf_k=10)

    assert len(fused) == 2
    assert fused[0].metadata["chunk_id"] == "a"
