from langchain_core.documents import Document

from app.services import retriever


def _doc(chunk_id, text="text"):
    return Document(page_content=text, metadata={"chunk_id": chunk_id})


def _identity_rerank(query, docs, top_n):
    return docs[:top_n]


def test_run_query_fuses_both_sources(monkeypatch):
    monkeypatch.setattr(retriever, "_bm25_search", lambda q, s, k: [_doc("a")])
    monkeypatch.setattr(retriever, "_dense_search", lambda q, s, k: [_doc("b")])
    monkeypatch.setattr(retriever, "cross_encoder_rerank", _identity_rerank)

    out = retriever.run_query("q", session_id="s1")
    assert {d.metadata["chunk_id"] for d in out} == {"a", "b"}


def test_run_query_dense_only(monkeypatch):
    monkeypatch.setattr(retriever, "_bm25_search", lambda q, s, k: [])
    monkeypatch.setattr(retriever, "_dense_search", lambda q, s, k: [_doc("b")])
    monkeypatch.setattr(retriever, "cross_encoder_rerank", _identity_rerank)

    out = retriever.run_query("q", session_id="s1")
    assert [d.metadata["chunk_id"] for d in out] == ["b"]


def test_run_query_bm25_only(monkeypatch):
    monkeypatch.setattr(retriever, "_bm25_search", lambda q, s, k: [_doc("a")])
    monkeypatch.setattr(retriever, "_dense_search", lambda q, s, k: [])
    monkeypatch.setattr(retriever, "cross_encoder_rerank", _identity_rerank)

    out = retriever.run_query("q", session_id="s1")
    assert [d.metadata["chunk_id"] for d in out] == ["a"]


def test_run_query_empty_returns_empty(monkeypatch):
    monkeypatch.setattr(retriever, "_bm25_search", lambda q, s, k: [])
    monkeypatch.setattr(retriever, "_dense_search", lambda q, s, k: [])

    assert retriever.run_query("q", session_id="s1") == []


def test_build_answer_fallback_without_llm(monkeypatch):
    monkeypatch.setattr(retriever, "OPENAI_API_KEY", None)
    docs = [Document(page_content="the relevant content", metadata={})]
    answer = retriever._build_answer("q", docs)
    assert "the relevant content" in answer


def test_build_answer_no_docs():
    assert "could not find" in retriever._build_answer("q", []).lower()


def test_query_documents_formats_sources(monkeypatch):
    docs = [Document(page_content="snippet text", metadata={"source": "f.pdf", "page": 0})]
    monkeypatch.setattr(retriever, "run_query", lambda q, session_id="default": docs)
    monkeypatch.setattr(retriever, "OPENAI_API_KEY", None)

    answer, sources = retriever.query_documents("q", session_id="s1")
    assert sources[0]["doc"] == "f.pdf"
    assert sources[0]["page"] == 1
    assert answer
