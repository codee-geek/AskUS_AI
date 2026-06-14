from langchain_core.documents import Document

from app.services import reranker


class FakeCrossEncoder:
    def __init__(self, scores):
        self._scores = scores

    def predict(self, pairs):
        return self._scores


def _docs(n):
    return [Document(page_content=f"chunk {i}", metadata={}) for i in range(n)]


def test_rerank_orders_by_score_and_applies_gap_cutoff(monkeypatch):
    docs = _docs(3)
    # Scores: doc0=1.0, doc1=9.0, doc2=0.5. Best is doc1; gap cutoff (2.0) drops the rest.
    monkeypatch.setattr(reranker, "get_cross_encoder", lambda: FakeCrossEncoder([1.0, 9.0, 0.5]))

    out = reranker.cross_encoder_rerank("q", docs, top_n=3, max_score_gap=2.0)
    assert len(out) == 1
    assert out[0].page_content == "chunk 1"
    assert out[0].metadata["rerank_score"] == 9.0


def test_rerank_respects_top_n(monkeypatch):
    docs = _docs(3)
    monkeypatch.setattr(reranker, "get_cross_encoder", lambda: FakeCrossEncoder([3.0, 2.5, 2.0]))

    out = reranker.cross_encoder_rerank("q", docs, top_n=2, max_score_gap=5.0)
    assert len(out) == 2
    assert [d.metadata["rerank_score"] for d in out] == [3.0, 2.5]


def test_rerank_empty():
    assert reranker.cross_encoder_rerank("q", [], top_n=5) == []
