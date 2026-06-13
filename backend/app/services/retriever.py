from typing import List, Tuple

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from core.config import (
    ANSWER_MAX_TOKENS,
    ANSWER_TEMPERATURE,
    EMBEDDING_MODEL,
    HYBRID_FETCH_K,
    LLM_MODEL,
    OPENAI_API_KEY,
    RRF_K,
    TOP_K,
)
from app.services.bm25 import get_bm25_indexer, get_session_bm25_path
from app.services.cloud_storage import sanitize_session_id
from app.services.hybrid import reciprocal_rank_fusion
from app.services.qdrant_store import search_chunks
from app.services.reranker import cross_encoder_rerank

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    encode_kwargs={"normalize_embeddings": True},
)


def _bm25_search(user_query: str, session_key: str, fetch_k: int) -> List[Document]:
    indexer = get_bm25_indexer(get_session_bm25_path(session_key))
    results = indexer.search(user_query, k=fetch_k)
    docs: List[Document] = []
    for doc, score in results:
        doc.metadata["bm25_score"] = float(score)
        docs.append(doc)
    return docs


def _dense_search(user_query: str, session_key: str, fetch_k: int) -> List[Document]:
    query_vector = embeddings.embed_query(user_query)
    return search_chunks(query_vector=query_vector, session_id=session_key, limit=fetch_k)


def run_query(user_query: str, session_id: str = "default", k: int | None = None) -> List[Document]:
    """
    Hybrid retrieval: BM25 sparse + Qdrant dense, fused with RRF, then reranked.
    Falls back to dense-only when no BM25 index exists for the session.
    """
    session_key = sanitize_session_id(session_id)
    top_k = k or TOP_K
    fetch_k = HYBRID_FETCH_K

    bm25_docs = _bm25_search(user_query, session_key, fetch_k)
    dense_docs = _dense_search(user_query, session_key, fetch_k)

    if bm25_docs and dense_docs:
        fused_docs = reciprocal_rank_fusion([bm25_docs, dense_docs], rrf_k=RRF_K)
    elif dense_docs:
        fused_docs = dense_docs
    elif bm25_docs:
        fused_docs = bm25_docs
    else:
        return []

    return cross_encoder_rerank(query=user_query, docs=fused_docs, top_n=top_k)


def _format_sources(docs: List[Document]) -> List[dict]:
    """Format documents as sources for the response."""
    sources = []
    for doc in docs:
        snippet = doc.page_content[:240].replace("\n", " ").strip()
        sources.append({
            "doc": doc.metadata.get("source", "unknown"),
            "page": doc.metadata.get("page", 0) + 1,
            "document_id": doc.metadata.get("document_id"),
            "snippet": snippet,
        })
    return sources


def _build_answer(question: str, docs: List[Document]) -> str:
    """Generate answer using LLM or fallback to best match."""
    if not docs:
        return "I could not find relevant information in the uploaded documents."

    if OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate

            context = "\n\n".join(doc.page_content for doc in docs[:3])
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Answer the question using only the provided context. If the answer is not in the context, say you don't know."),
                ("human", "Context:\n{context}\n\nQuestion: {question}"),
            ])
            llm = ChatOpenAI(
                model=LLM_MODEL,
                temperature=ANSWER_TEMPERATURE,
                max_tokens=ANSWER_MAX_TOKENS,
                api_key=OPENAI_API_KEY,
            )
            response = (prompt | llm).invoke({"context": context, "question": question})
            return response.content
        except Exception:
            pass

    top = docs[0].page_content.strip()
    return f"Based on the most relevant section in your documents:\n\n{top}"


def query_documents(question: str, session_id: str = "default") -> Tuple[str, List[dict]]:
    """
    Main entry point for querying documents.
    Returns (answer, sources) tuple.
    """
    docs = run_query(question, session_id=session_id)
    return _build_answer(question, docs), _format_sources(docs)
