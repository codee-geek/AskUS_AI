from app.services import session_cleanup as sc


def test_cleanup_session_combines_files_and_vectors(monkeypatch):
    monkeypatch.setattr(sc, "delete_session_files", lambda s: 3)
    monkeypatch.setattr(sc, "delete_session_vectors", lambda s: 7)

    out = sc.cleanup_session("s1")

    assert out["session_id"] == "s1"
    assert out["files_removed"] == 3
    assert out["vectors_removed"] == 7


def test_cleanup_session_survives_pinecone_error(monkeypatch):
    monkeypatch.setattr(sc, "delete_session_files", lambda s: 1)

    def boom(_session):
        raise RuntimeError("pinecone unavailable")

    monkeypatch.setattr(sc, "delete_session_vectors", boom)

    out = sc.cleanup_session("s1")
    assert out["files_removed"] == 1
    assert out["vectors_removed"] == 0


def test_sweep_cleans_each_stale_session(monkeypatch):
    monkeypatch.setattr(sc, "iter_stale_sessions", lambda ttl: ["a", "b"])
    cleaned: list[str] = []
    monkeypatch.setattr(
        sc,
        "cleanup_session",
        lambda s: cleaned.append(s)
        or {"session_id": s, "files_removed": 0, "vectors_removed": 0},
    )

    results = sc.sweep_stale_sessions(1)
    assert len(results) == 2
    assert cleaned == ["a", "b"]
