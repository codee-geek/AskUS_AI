from collections import defaultdict

from langchain_core.documents import Document

from app.services import pinecone_store


class FakeIndex:
    def __init__(self):
        self.store: dict[str, dict[str, dict]] = defaultdict(dict)

    def upsert(self, vectors, namespace):
        for vector in vectors:
            self.store[namespace][vector["id"]] = {
                "values": vector["values"],
                "metadata": vector["metadata"],
            }

    def query(self, vector, top_k, namespace, include_metadata):
        items = list(self.store.get(namespace, {}).items())[:top_k]
        return {
            "matches": [
                {"id": vid, "score": 0.9, "metadata": data["metadata"]}
                for vid, data in items
            ]
        }

    def describe_index_stats(self):
        return {
            "namespaces": {
                ns: {"vector_count": len(items)} for ns, items in self.store.items()
            }
        }

    def list(self, namespace):
        ids = list(self.store.get(namespace, {}).keys())
        if ids:
            yield ids

    def delete(self, delete_all=False, namespace=None, ids=None):
        if ids is not None:
            for vid in ids:
                self.store.get(namespace, {}).pop(vid, None)
            return
        self.store.pop(namespace, None)


class FakeClient:
    def __init__(self):
        self.index = FakeIndex()
        self._indexes: set[str] = set()

    def has_index(self, name):
        return name in self._indexes

    def create_index(self, name, dimension, metric, spec):
        self._indexes.add(name)

    def Index(self, name):
        return self.index


def _make_doc(chunk_id, session_id, text):
    return Document(
        page_content=text,
        metadata={
            "chunk_id": chunk_id,
            "session_id": session_id,
            "document_id": chunk_id.split("-chunk-", 1)[0],
        },
    )


def test_upsert_search_count_delete(monkeypatch):
    fake = FakeClient()
    fake._indexes.add(pinecone_store.PINECONE_INDEX_NAME)
    monkeypatch.setattr(pinecone_store, "get_pinecone_client", lambda: fake)

    docs = [
        _make_doc("doc_a-chunk-0000", "s1", "alpha text"),
        _make_doc("doc_a-chunk-0001", "s1", "beta text"),
        _make_doc("doc_b-chunk-0000", "s1", "gamma text"),
    ]
    pinecone_store.upsert_chunks(docs, [[0.1, 0.2, 0.3]] * 3)

    assert pinecone_store.count_session_chunks("s1") == 3
    assert pinecone_store.count_session_documents("s1") == 2

    results = pinecone_store.search_chunks(
        query_vector=[0.1, 0.2, 0.3], session_id="s1", limit=2
    )
    assert len(results) == 2
    assert "dense_score" in results[0].metadata
    assert results[0].page_content in {"alpha text", "beta text", "gamma text"}

    removed = pinecone_store.delete_session("s1")
    assert removed == 3
    assert pinecone_store.count_session_chunks("s1") == 0


def test_delete_document_removes_only_that_document(monkeypatch):
    fake = FakeClient()
    fake._indexes.add(pinecone_store.PINECONE_INDEX_NAME)
    monkeypatch.setattr(pinecone_store, "get_pinecone_client", lambda: fake)

    docs = [
        _make_doc("doc_a-chunk-0000", "s1", "alpha text"),
        _make_doc("doc_a-chunk-0001", "s1", "beta text"),
        _make_doc("doc_b-chunk-0000", "s1", "gamma text"),
    ]
    pinecone_store.upsert_chunks(docs, [[0.1, 0.2, 0.3]] * 3)
    assert pinecone_store.count_session_chunks("s1") == 3

    removed = pinecone_store.delete_document("s1", "doc_a")
    assert removed == 2
    assert pinecone_store.count_session_chunks("s1") == 1
    assert pinecone_store.count_session_documents("s1") == 1

    # Deleting a document that no longer exists is a no-op.
    assert pinecone_store.delete_document("s1", "doc_a") == 0


def test_search_returns_empty_when_index_missing(monkeypatch):
    fake = FakeClient()  # no index registered
    monkeypatch.setattr(pinecone_store, "get_pinecone_client", lambda: fake)

    assert pinecone_store.search_chunks(
        query_vector=[0.0], session_id="s1", limit=5
    ) == []
    assert pinecone_store.count_session_chunks("s1") == 0


def test_count_chunks_clamps_wrapped_negative(monkeypatch):
    class WrappedStatsIndex:
        def describe_index_stats(self):
            # Pinecone can transiently report -10 as a wrapped uint32.
            return {"namespaces": {"s1": {"vector_count": 2**32 - 10}}}

    class WrappedClient:
        def has_index(self, name):
            return True

        def Index(self, name):
            return WrappedStatsIndex()

    monkeypatch.setattr(pinecone_store, "get_pinecone_client", lambda: WrappedClient())
    assert pinecone_store.count_session_chunks("s1") == 0


def test_clean_metadata_drops_none():
    cleaned = pinecone_store._clean_metadata(
        {"a": None, "b": 1, "c": "x", "d": ["e", 2]}
    )
    assert "a" not in cleaned
    assert cleaned["b"] == 1
    assert cleaned["c"] == "x"
    assert cleaned["d"] == ["e", "2"]
