from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from core.config import VECTOR_DB_PATH, EMBEDDING_MODEL
from app.services.reranker import cross_encoder_rerank

# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    encode_kwargs={"normalize_embeddings": True}
)


# ============================================================
# QUERY FUNCTION
# ============================================================

def run_query(user_query):

    # Load FAISS
    vectorstore = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )

    # Similarity Search
    results = vectorstore.similarity_search_with_score(
        user_query,
        k=5
    )

    docs = []

    for doc, score in results:

        doc.metadata["faiss_score"] = float(score)

        docs.append(doc)

    # Rerank
    reranked_docs = cross_encoder_rerank(
        query=user_query,
        docs=docs,
        top_n=10
    )

    return reranked_docs


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    user_query = input("Enter your query: ")

    final_docs = run_query(user_query)

    for i, doc in enumerate(final_docs):

        print(f"\n--- Reranked Chunk {i + 1} ---")

        print(
            f"Rerank Score: "
            f"{doc.metadata.get('rerank_score')}"
        )

        print(doc.page_content)