from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.schema import Document
from pinecone import Pinecone
import os


# ============================================================
# EMBEDDING MODEL
# ============================================================

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# ============================================================
# PINECONE INITIALIZATION
# ============================================================

pc = Pinecone(
    api_key=os.getenv("PINECONE_API_KEY")
)

index_name = "hybrid-rag-index"


# ============================================================
# VECTOR STORE
# ============================================================

vectorstore = PineconeVectorStore(
    index_name=index_name,
    embedding=embedding_model
)


# ============================================================
# LOAD CHUNKS
# chunks should come from your HybridChunker
# ============================================================

"""
Example chunk format:

chunks = [
    {
        "chunk_id": "...",
        "chunk_index": 0,
        "source": "sample.txt",
        "document_type": "article",
        "chunk_length": 120,
        "word_count": 20,
        "text": "Artificial Intelligence is transforming industries."
    }
]
"""

# ============================================================
# CONVERT TO LANGCHAIN DOCUMENTS
# ============================================================

documents = []

for chunk in chunks:

    doc = Document(
        page_content=chunk["text"],
        metadata={
            "chunk_id": chunk["chunk_id"],
            "chunk_index": chunk["chunk_index"],
            "source": chunk["source"],
            "document_type": chunk["document_type"],
            "chunk_length": chunk["chunk_length"],
            "word_count": chunk["word_count"]
        }
    )

    documents.append(doc)


# ============================================================
# STORE IN VECTOR DB
# ============================================================

vectorstore.add_documents(documents)


# ============================================================
# VECTOR RETRIEVER
# ============================================================

vector_retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={
        "k": 5
    }
)

# ============================================================
# BM25 RETRIEVER
# ============================================================

bm25_retriever = BM25Retriever.from_documents(documents)

bm25_retriever.k = 5


# ============================================================
# HYBRID RETRIEVER
# ============================================================

hybrid_retriever = EnsembleRetriever(
    retrievers=[
        bm25_retriever,
        vector_retriever
    ],
    weights=[0.4, 0.6]
)


# ============================================================
# QUERY FUNCTION
# ============================================================

def retrieve(query):

    results = hybrid_retriever.invoke(query)

    formatted_results = []

    for rank, doc in enumerate(results):

        formatted_results.append({
            "rank": rank + 1,
            "content": doc.page_content,
            "metadata": doc.metadata
        })

    return formatted_results


