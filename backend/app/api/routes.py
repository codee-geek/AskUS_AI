from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.services.ingestion import (
    save_uploaded_file,
    ingest_documents,
    VECTOR_DB_PATH,
    STAGING_PATH,
)
from app.services.retriever import query_documents

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


def _vectorstore_stats():
    index_file = Path(VECTOR_DB_PATH) / "index.faiss"
    if not index_file.exists():
        return {"docs_indexed": 0, "total_chunks": 0}
    return {"docs_indexed": len(list(STAGING_PATH.iterdir())), "total_chunks": 0}


@router.get("/")
def home():
    stats = _vectorstore_stats()
    return {
        "message": "RAG Backend Running",
        "docs_indexed": stats["docs_indexed"],
        "total_chunks": stats["total_chunks"],
    }


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = await save_uploaded_file(file)

    try:
        result = ingest_documents()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "filename": file.filename,
        "saved_at": file_path,
        "chunks": result.get("chunks", 0) if result else 0,
        "pages": result.get("pages", 0) if result else 0,
        "total_chunks": result.get("total_chunks", 0) if result else 0,
    }


@router.post("/ingest")
def ingest():
    result = ingest_documents()
    return {
        "message": "Documents ingested",
        "details": result,
    }


@router.post("/query")
def ask_question(body: QueryRequest):
    try:
        answer, sources = query_documents(body.question)
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
    }
