import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.services.ingestion import ingest_documents
from app.services.local_storage import sanitize_session_id, touch_session
from app.services.pinecone_store import count_session_chunks, count_session_documents
from app.services.retriever import query_documents
from app.services.session_cleanup import cleanup_session, delete_document
from core.config import MAX_UPLOAD_MB

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)


def _get_session_id(request: Request) -> str:
    """Read the frontend session id header and normalize it."""
    return sanitize_session_id(request.headers.get("x-session-id", "default"))


def _vectorstore_stats(session_id: str):
    # Derive counts from Pinecone so stats never touch local raw files.
    try:
        docs_indexed = count_session_documents(session_id)
    except Exception:
        docs_indexed = 0

    try:
        total_chunks = count_session_chunks(session_id)
    except Exception:
        total_chunks = 0

    return {
        "docs_indexed": docs_indexed,
        "total_chunks": total_chunks,
        "session_id": session_id,
    }


@router.get("/")
def home(request: Request):
    session_id = _get_session_id(request)
    stats = _vectorstore_stats(session_id)
    return {
        "message": "RAG Backend Running",
        "docs_indexed": stats["docs_indexed"],
        "total_chunks": stats["total_chunks"],
        "session_id": stats["session_id"],
    }


@router.get("/health")
def health():
    """Lightweight liveness probe that does no I/O."""
    return {"status": "ok"}


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    session_id = _get_session_id(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_UPLOAD_MB} MB upload limit.",
        )

    try:
        result = ingest_documents(
            file_bytes=content,
            filename=file.filename,
            session_id=session_id,
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Ingestion failed for session %s", session_id)
        raise HTTPException(
            status_code=500, detail="Failed to process the uploaded document."
        ) from None

    touch_session(session_id)
    return {
        "filename": file.filename,
        "saved_at": result.get("stored_uri"),
        "chunks": result.get("chunks", 0),
        "pages": result.get("pages", 0),
        "total_chunks": result.get("total_chunks", 0),
        "docs_indexed": result.get("docs_indexed", 0),
        "session_id": session_id,
        "document_id": result.get("document_id"),
    }


@router.post("/ingest")
def ingest(_: Request):
    raise HTTPException(
        status_code=400,
        detail="Direct /ingest is no longer supported. Upload a file to trigger ingestion.",
    )


@router.post("/query")
def ask_question(request: Request, body: QueryRequest):
    session_id = _get_session_id(request)
    try:
        answer, sources = query_documents(body.question, session_id=session_id)
    except Exception:
        logger.exception("Query failed for session %s", session_id)
        raise HTTPException(
            status_code=500, detail="Failed to answer the question."
        ) from None

    touch_session(session_id)
    return {
        "question": body.question,
        "answer": answer,
        "sources": sources,
        "session_id": session_id,
    }


@router.delete("/document/{document_id}")
def remove_document(request: Request, document_id: str):
    """Delete one document's local file, Pinecone vectors and BM25 chunks."""
    session_id = _get_session_id(request)
    try:
        summary = delete_document(session_id, document_id)
    except Exception:
        logger.exception(
            "Failed to delete document %s for session %s", document_id, session_id
        )
        raise HTTPException(
            status_code=500, detail="Failed to delete the document."
        ) from None

    touch_session(session_id)
    stats = _vectorstore_stats(session_id)
    return {
        "message": "Document deleted",
        **summary,
        "docs_indexed": stats["docs_indexed"],
        "total_chunks": stats["total_chunks"],
    }


@router.delete("/session")
def end_session(request: Request):
    """End a session: delete its local files, Pinecone vectors and BM25 index."""
    session_id = _get_session_id(request)
    try:
        summary = cleanup_session(session_id)
    except Exception:
        logger.exception("Cleanup failed for session %s", session_id)
        raise HTTPException(
            status_code=500, detail="Failed to clean up the session."
        ) from None

    return {"message": "Session cleared", **summary}
