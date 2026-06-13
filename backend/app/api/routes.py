from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel

from app.services.cloud_storage import list_session_documents, sanitize_session_id
from app.services.ingestion import ingest_documents
from app.services.qdrant_store import count_session_chunks
from app.services.retriever import query_documents

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


def _get_session_id(request: Request) -> str:
    """Read the frontend session id header and normalize it."""
    return sanitize_session_id(request.headers.get("x-session-id", "default"))


def _vectorstore_stats(session_id: str):
    try:
        docs_indexed = len(list_session_documents(session_id))
    except RuntimeError:
        docs_indexed = 0

    try:
        total_chunks = count_session_chunks(session_id)
    except RuntimeError:
        total_chunks = 0
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


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    session_id = _get_session_id(request)
    content = await file.read()

    try:
        result = ingest_documents(
            file_bytes=content,
            filename=file.filename,
            session_id=session_id,
            content_type=file.content_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "filename": file.filename,
        "saved_at": result.get("s3_uri"),
        "chunks": result.get("chunks", 0) if result else 0,
        "pages": result.get("pages", 0) if result else 0,
        "total_chunks": result.get("total_chunks", 0) if result else 0,
        "docs_indexed": result.get("docs_indexed", 0) if result else 0,
        "session_id": session_id,
        "document_id": result.get("document_id") if result else None,
        "s3_key": result.get("s3_key") if result else None,
    }


@router.post("/ingest")
def ingest(_: Request):
    raise HTTPException(
        status_code=400,
        detail="Direct /ingest is no longer supported. Upload a file to trigger S3 + Qdrant ingestion.",
    )


@router.post("/query")
def ask_question(request: Request, body: QueryRequest):
    session_id = _get_session_id(request)
    try:
        answer, sources = query_documents(body.question, session_id=session_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=400,
            detail="No documents indexed yet. Upload a PDF first.",
        ) from None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "question": body.question,
        "answer": answer,
        "sources": sources,
        "session_id": session_id,
    }
