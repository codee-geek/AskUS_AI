from fastapi.testclient import TestClient

import app.api.routes as routes
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_returns_session_stats(monkeypatch):
    monkeypatch.setattr(routes, "count_session_documents", lambda s: 2)
    monkeypatch.setattr(routes, "count_session_chunks", lambda s: 9)

    response = client.get("/", headers={"X-Session-ID": "s1"})
    body = response.json()
    assert body["docs_indexed"] == 2
    assert body["total_chunks"] == 9
    assert body["session_id"] == "s1"


def test_query_rejects_empty_question():
    response = client.post("/query", json={"question": ""})
    assert response.status_code == 422


def test_query_success(monkeypatch):
    monkeypatch.setattr(
        routes,
        "query_documents",
        lambda q, session_id="default": ("the answer", [{"doc": "f.pdf"}]),
    )
    monkeypatch.setattr(routes, "touch_session", lambda s: None)

    response = client.post(
        "/query", json={"question": "hi"}, headers={"X-Session-ID": "s1"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "the answer"
    assert body["sources"][0]["doc"] == "f.pdf"


def test_query_handles_internal_error(monkeypatch):
    def boom(q, session_id="default"):
        raise RuntimeError("internal detail that must not leak")

    monkeypatch.setattr(routes, "query_documents", boom)
    monkeypatch.setattr(routes, "touch_session", lambda s: None)

    response = client.post("/query", json={"question": "hi"})
    assert response.status_code == 500
    assert "internal detail" not in response.json()["detail"]


def test_upload_rejects_empty_file():
    response = client.post(
        "/upload", files={"file": ("x.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400


def test_upload_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(routes, "_MAX_UPLOAD_BYTES", 4)
    response = client.post(
        "/upload", files={"file": ("x.pdf", b"way too big", "application/pdf")}
    )
    assert response.status_code == 413


def test_upload_bad_extension_returns_400(monkeypatch):
    def fake_ingest(**kwargs):
        raise ValueError("Unsupported file type: .png")

    monkeypatch.setattr(routes, "ingest_documents", fake_ingest)
    monkeypatch.setattr(routes, "touch_session", lambda s: None)

    response = client.post(
        "/upload", files={"file": ("x.png", b"data", "image/png")}
    )
    assert response.status_code == 400


def test_upload_success(monkeypatch):
    monkeypatch.setattr(
        routes,
        "ingest_documents",
        lambda **kwargs: {
            "chunks": 3,
            "pages": 1,
            "total_chunks": 3,
            "docs_indexed": 1,
            "document_id": "doc_x",
            "stored_uri": "file:///tmp/x.pdf",
        },
    )
    monkeypatch.setattr(routes, "touch_session", lambda s: None)

    response = client.post(
        "/upload",
        files={"file": ("x.pdf", b"data", "application/pdf")},
        headers={"X-Session-ID": "s1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chunks"] == 3
    assert body["document_id"] == "doc_x"


def test_ingest_is_deprecated():
    assert client.post("/ingest").status_code == 400


def test_delete_session(monkeypatch):
    monkeypatch.setattr(
        routes,
        "cleanup_session",
        lambda s: {"session_id": s, "files_removed": 2, "vectors_removed": 5},
    )

    response = client.delete("/session", headers={"X-Session-ID": "s1"})
    assert response.status_code == 200
    body = response.json()
    assert body["files_removed"] == 2
    assert body["vectors_removed"] == 5
