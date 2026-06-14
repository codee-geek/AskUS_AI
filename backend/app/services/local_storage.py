from __future__ import annotations

import time
from pathlib import Path

SESSIONS_ROOT = Path(__file__).resolve().parent.parent / "storage" / "sessions"
_ACTIVITY_MARKER = ".last_active"


def sanitize_session_id(session_id: str) -> str:
    """Normalize an incoming session id for safe on-disk paths."""
    cleaned = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in session_id.strip()
    )
    return cleaned or "default"


def get_session_dir(session_id: str) -> Path:
    return SESSIONS_ROOT / sanitize_session_id(session_id)


def get_session_uploads_dir(session_id: str, document_id: str | None = None) -> Path:
    base = get_session_dir(session_id) / "uploads"
    if document_id:
        return base / document_id
    return base


def touch_session(session_id: str) -> None:
    """Record activity so the TTL sweep keeps active sessions alive."""
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / _ACTIVITY_MARKER).write_text(str(time.time()), encoding="utf-8")


def _last_active(session_dir: Path) -> float:
    """Return the most recent activity timestamp for a session directory."""
    marker = session_dir / _ACTIVITY_MARKER
    if marker.exists():
        try:
            return float(marker.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass
    try:
        return session_dir.stat().st_mtime
    except OSError:
        return time.time()


def save_document(
    *,
    file_bytes: bytes,
    filename: str,
    session_id: str,
    document_id: str,
) -> dict[str, str]:
    """Persist an uploaded document to local session storage for the session."""
    doc_dir = get_session_uploads_dir(session_id, document_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / filename
    file_path.write_bytes(file_bytes)
    touch_session(session_id)

    relative_key = str(file_path.relative_to(SESSIONS_ROOT))
    return {
        "key": relative_key,
        "uri": f"file://{file_path}",
        "path": str(file_path),
    }


def list_session_documents(session_id: str) -> list[dict[str, str]]:
    """List uploaded documents currently on disk for a session."""
    uploads_dir = get_session_uploads_dir(session_id)
    if not uploads_dir.exists():
        return []

    documents: list[dict[str, str]] = []
    for doc_dir in uploads_dir.iterdir():
        if not doc_dir.is_dir():
            continue
        for file_path in doc_dir.iterdir():
            if file_path.is_file():
                documents.append(
                    {
                        "key": str(file_path.relative_to(SESSIONS_ROOT)),
                        "uri": f"file://{file_path}",
                    }
                )
    return documents


def delete_document_files(session_id: str, document_id: str) -> int:
    """Delete a single document's stored files for a session. Returns files removed."""
    import shutil

    doc_dir = get_session_uploads_dir(session_id, document_id)
    if not doc_dir.exists():
        return 0
    file_count = sum(1 for path in doc_dir.rglob("*") if path.is_file())
    shutil.rmtree(doc_dir, ignore_errors=True)
    return file_count


def delete_session_files(session_id: str) -> int:
    """Delete a session's local directory (uploads + BM25). Returns files removed."""
    import shutil

    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        return 0
    file_count = sum(1 for path in session_dir.rglob("*") if path.is_file())
    shutil.rmtree(session_dir, ignore_errors=True)
    return file_count


def iter_stale_sessions(ttl_hours: float) -> list[str]:
    """Return session ids whose last activity is older than ttl_hours."""
    if not SESSIONS_ROOT.exists():
        return []

    cutoff = time.time() - ttl_hours * 3600
    stale: list[str] = []
    for session_dir in SESSIONS_ROOT.iterdir():
        if not session_dir.is_dir():
            continue
        if _last_active(session_dir) < cutoff:
            stale.append(session_dir.name)
    return stale
