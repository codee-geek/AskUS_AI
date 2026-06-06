from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from core.config import EMBEDDING_MODEL, OPENAI_API_KEY
from app.services.ingestion import VECTOR_DB_PATH
from app.services.reranker import cross_encoder_rerank

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    encode_kwargs={"normalize_embeddings": True},
)


def _load_vectorstore():
    index_file = Path(VECTOR_DB_PATH) / "index.faiss"
    if not index_file.exists():
        raise FileNotFoundError(f"Vector store not found at {VECTOR_DB_PATH}")

    return FAISS.load_local(
        str(VECTOR_DB_PATH),
        embeddings,
        allow_dangerous_deserialization=True,
    )


def run_query(user_query):
    vectorstore = _load_vectorstore()

    results = vectorstore.similarity_search_with_score(user_query, k=5)

    docs = []
    for doc, score in results:
        doc.metadata["faiss_score"] = float(score)
        docs.append(doc)

    return cross_encoder_rerank(query=user_query, docs=docs, top_n=5)


def _format_sources(docs):
    sources = []
    for doc in docs:
        snippet = doc.page_content[:240].replace("\n", " ").strip()
        sources.append({
            "doc": doc.metadata.get("source", "unknown"),
            "page": doc.metadata.get("page", 0) + 1,
            "snippet": snippet,
        })
    return sources


def _build_answer(question, docs):
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
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=OPENAI_API_KEY)
            response = (prompt | llm).invoke({"context": context, "question": question})
            return response.content
        except Exception:
            pass

    top = docs[0].page_content.strip()
    return f"Based on the most relevant section in your documents:\n\n{top}"


def query_documents(question):
    docs = run_query(question)
    return _build_answer(question, docs), _format_sources(docs)
