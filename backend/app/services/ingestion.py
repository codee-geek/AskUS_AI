import os
import hashlib
from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader
)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


STAGING_PATH = BASE_DIR / "storage" / "uploads"

PROCESSED_PATH = BASE_DIR / "storage" / "processed"

FAILED_PATH = BASE_DIR / "storage" / "failed"

VECTOR_DB_PATH = BASE_DIR / "storage" / "vectorstore"

SUPPORTED_EXTENSIONS = [".pdf", ".txt", ".docx"]
skipped_files = []
failed_files = []

# =========================
# INITIALIZE DIRECTORIES
# =========================

for path in [
    STAGING_PATH,
    PROCESSED_PATH,
    FAILED_PATH,
    VECTOR_DB_PATH
]:
    os.makedirs(path, exist_ok=True)
    
    
import os
from fastapi import UploadFile


#======================================================
#==uploaded file saved
#======================================================


async def save_uploaded_file(file: UploadFile):

    file_path = os.path.join(STAGING_PATH, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return file_path

# =========================
# EMBEDDING MODEL
# =========================

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# =========================
# TEXT SPLITTER
# =========================

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n", "\n", ".", " "]
)


# =========================
# FILE HASHING
# =========================

def calculate_file_hash(file_path):
    hasher = hashlib.md5()

    with open(file_path, "rb") as f:
        hasher.update(f.read())

    return hasher.hexdigest()


# =========================
# DOCUMENT LOADER
# =========================

def load_document(file_path):

    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)

    elif ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")

    elif ext == ".docx":
        loader = UnstructuredWordDocumentLoader(file_path)

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return loader.load()


# =========================
# MAIN INGESTION
# =========================

def ingest_documents():

    all_chunks = []

    processed_hashes = set()

    for file_name in os.listdir(STAGING_PATH):

        file_path = os.path.join(STAGING_PATH, file_name)

        if not os.path.isfile(file_path):
            continue

        ext = Path(file_path).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:                 #react 
            print(f"Skipping unsupported file: {file_name}")
            continue
        try:
            file_hash = calculate_file_hash(file_path)
            if file_hash in processed_hashes:
                print(f"Duplicate skipped: {file_name}")
                continue
            
            print(f"\nProcessing: {file_name}")
            documents = load_document(file_path)
            
            for doc in documents:
                doc.metadata["source"] = file_name
            chunks = text_splitter.split_documents(documents)
            
            all_chunks.extend(chunks)
            processed_hashes.add(file_hash)
            
            print(f"Chunks created: {len(chunks)}")
            
        except Exception as e:
            print(f"Error processing {file_name}: {e}") #react 
            
    if not all_chunks:
        print("No documents found")
        return {"chunks": 0, "pages": 0, "total_chunks": 0}

    print("\nCreating embeddings and FAISS index...")

    vectorstore = FAISS.from_documents(
        documents=all_chunks,
        embedding=embedding_model
    )

    vectorstore.save_local(str(VECTOR_DB_PATH))

    print("\nIngestion completed successfully")
    print(f"Total chunks stored: {len(all_chunks)}")

    pages = sum(doc.metadata.get("page", 0) + 1 for doc in all_chunks if "page" in doc.metadata)
    return {
        "chunks": len(all_chunks),
        "pages": pages or len(all_chunks),
        "total_chunks": len(all_chunks),
    }


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    ingest_documents()
    