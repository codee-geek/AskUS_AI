import pytest
from langchain_core.documents import Document


@pytest.fixture
def sample_docs():
    return [
        Document(page_content="alpha document about retrieval", metadata={"chunk_id": "c1"}),
        Document(page_content="beta document about embeddings", metadata={"chunk_id": "c2"}),
        Document(page_content="gamma document about hybrid search", metadata={"chunk_id": "c3"}),
    ]
