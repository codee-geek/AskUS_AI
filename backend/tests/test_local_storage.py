import time

from app.services import local_storage as ls


def test_sanitize_session_id():
    assert ls.sanitize_session_id("a b/c") == "a-b-c"
    assert ls.sanitize_session_id("  ") == "default"
    assert ls.sanitize_session_id("Keep_-1") == "Keep_-1"


def test_save_and_list(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "SESSIONS_ROOT", tmp_path)

    result = ls.save_document(
        file_bytes=b"hello world",
        filename="doc.pdf",
        session_id="session-alpha",
        document_id="doc_abc123",
    )
    assert result["uri"].startswith("file://")

    documents = ls.list_session_documents("session-alpha")
    assert len(documents) == 1
    assert documents[0]["key"].endswith("doc.pdf")


def test_delete_session_files(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "SESSIONS_ROOT", tmp_path)
    ls.save_document(
        file_bytes=b"hi",
        filename="a.pdf",
        session_id="s1",
        document_id="doc_1",
    )

    removed = ls.delete_session_files("s1")
    assert removed >= 1
    assert ls.list_session_documents("s1") == []
    # Deleting again is a no-op.
    assert ls.delete_session_files("s1") == 0


def test_iter_stale_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "SESSIONS_ROOT", tmp_path)
    ls.touch_session("fresh")
    ls.touch_session("old")

    stale_marker = ls.get_session_dir("old") / ls._ACTIVITY_MARKER
    stale_marker.write_text(str(time.time() - 100_000), encoding="utf-8")

    stale = ls.iter_stale_sessions(ttl_hours=1)
    assert "old" in stale
    assert "fresh" not in stale
