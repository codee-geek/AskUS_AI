from pathlib import Path

from langchain_core.documents import Document

from app.services.bm25 import BM25Indexer


def _make_doc(chunk_id: str, text: str) -> Document:
    return Document(page_content=text, metadata={"chunk_id": chunk_id})


def test_extend_and_rebuild_appends_without_duplicates(tmp_path: Path):
    indexer = BM25Indexer(tmp_path)
    first_batch = [
        _make_doc("c1", "retrieval augmented generation overview"),
        _make_doc("c2", "vector database indexing details"),
    ]
    second_batch = [
        _make_doc("c2", "vector database indexing details"),
        _make_doc("c3", "bm25 sparse retrieval keywords"),
    ]

    indexer.extend_and_rebuild(first_batch)
    assert indexer.document_count == 2

    indexer.extend_and_rebuild(second_batch)
    assert indexer.document_count == 3
    assert {doc.metadata["chunk_id"] for doc in indexer.corpus} == {"c1", "c2", "c3"}


def test_search_returns_scored_documents(tmp_path: Path):
    indexer = BM25Indexer(tmp_path)
    docs = [
        _make_doc("c1", "python fastapi backend service"),
        _make_doc("c2", "react frontend user interface"),
        _make_doc("c3", "fastapi python api routing"),
    ]
    indexer.build(docs)

    results = indexer.search("fastapi python", k=2)

    assert len(results) == 2
    doc, score = results[0]
    assert score >= results[1][1]
    assert "fastapi" in doc.page_content.lower() or "python" in doc.page_content.lower()
