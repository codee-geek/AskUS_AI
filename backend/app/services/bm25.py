import pickle
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.services.local_storage import sanitize_session_id

# BM25 parameters (tuned for retrieval)
BM25_PARAMS = {
    "k1": 1.5,
    "b": 0.75,
}

SESSIONS_ROOT = Path(__file__).resolve().parent.parent / "storage" / "sessions"


def get_session_bm25_path(session_id: str) -> Path:
    """Return the on-disk BM25 storage path for a session."""
    session_key = sanitize_session_id(session_id)
    return SESSIONS_ROOT / session_key / "bm25"


class BM25Indexer:
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_path / "bm25_index.pkl"
        self.corpus_path = self.storage_path / "bm25_corpus.pkl"
        self._index: Optional[BM25Okapi] = None
        self._corpus: List[Document] = []

    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace + lowercase tokenization."""
        return text.lower().split()

    def _get_texts(self, docs: List[Document]) -> List[str]:
        """Extract texts from documents for BM25 indexing."""
        return [doc.page_content for doc in docs]

    @staticmethod
    def _doc_key(doc: Document) -> str:
        chunk_id = doc.metadata.get("chunk_id")
        if chunk_id:
            return str(chunk_id)
        return doc.page_content[:200]

    def build(self, documents: List[Document]) -> None:
        """Build BM25 index from documents."""
        self._corpus = documents
        if not documents:
            self._index = None
            self._save()
            return

        texts = self._get_texts(documents)
        tokenized_corpus = [self._tokenize(text) for text in texts]
        self._index = BM25Okapi(tokenized_corpus, **BM25_PARAMS)
        self._save()

    def extend_and_rebuild(self, new_documents: List[Document]) -> None:
        """Merge new chunks into the session corpus and rebuild the BM25 index."""
        if not new_documents:
            return

        self.load()
        merged: dict[str, Document] = {self._doc_key(doc): doc for doc in self._corpus}
        for doc in new_documents:
            merged[self._doc_key(doc)] = doc
        self.build(list(merged.values()))

    def remove_document(self, document_id: str) -> int:
        """Drop all chunks belonging to a document and rebuild. Returns removed count."""
        self.load()
        if not self._corpus:
            return 0

        remaining = [
            doc
            for doc in self._corpus
            if str(doc.metadata.get("document_id")) != str(document_id)
        ]
        removed = len(self._corpus) - len(remaining)
        if removed:
            self.build(remaining)
        return removed

    def _save(self) -> None:
        """Persist index and corpus to disk."""
        with open(self.corpus_path, "wb") as f:
            pickle.dump(self._corpus, f)
        with open(self.index_path, "wb") as f:
            pickle.dump(self._index, f)

    def load(self) -> bool:
        """Load index from disk. Returns True if successful."""
        if not self.index_path.exists() or not self.corpus_path.exists():
            return False
        try:
            with open(self.corpus_path, "rb") as f:
                self._corpus = pickle.load(f)
            with open(self.index_path, "rb") as f:
                self._index = pickle.load(f)
            return self._index is not None
        except Exception:
            self._index = None
            self._corpus = []
            return False

    def search(self, query: str, k: int = 5) -> List[tuple[Document, float]]:
        """
        Search BM25 index.
        Returns list of (Document, score) tuples sorted by relevance.
        """
        if self._index is None:
            if not self.load():
                return []

        tokenized_query = self._tokenize(query)
        scores = self._index.get_scores(tokenized_query)

        doc_scores = list(zip(self._corpus, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        return doc_scores[:k]

    @property
    def is_loaded(self) -> bool:
        return self._index is not None

    @property
    def corpus(self) -> List[Document]:
        return list(self._corpus)

    @property
    def document_count(self) -> int:
        return len(self._corpus)


def get_bm25_indexer(storage_path: Path) -> BM25Indexer:
    """Factory to get or create a BM25 indexer."""
    return BM25Indexer(storage_path)
