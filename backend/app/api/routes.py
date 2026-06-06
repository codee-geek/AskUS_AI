from fastapi import APIRouter, UploadFile, File
from app.services.ingestion import save_uploaded_file, ingest_documents
from app.services.retriever import run_query

router = APIRouter()


@router.get("/")
def home():
    return {"message": "RAG Backend Running"}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    file_path = await save_uploaded_file(file)

    return {
        "filename": file.filename,
        "saved_at": file_path
    }


@router.post("/ingest")
def ingest():

    result = ingest_documents()

    return {
        "message": "Documents ingested",
        "details": result
    }


@router.post("/ask")
def run_query(query: str):

    response = run_query(query)

    return {
        "query": query,
        "answer": response
    }