# AskUs AI – Intelligent Multi-Document RAG System

AskUs AI is an enterprise-grade Retrieval-Augmented Generation (RAG) platform designed to answer questions across multiple documents with high accuracy and contextual understanding.

The system combines semantic search, vector databases, hybrid retrieval, reranking, and Large Language Models (LLMs) to provide reliable answers grounded in uploaded content.

## 🚀 Live Demo

**Deployed Application:** https://askus-ai.duckdns.org/

---

## 📌 Features

### Multi-Document Intelligence

* Upload and query multiple documents simultaneously
* Cross-document reasoning and information synthesis
* Document-specific and global search modes

### Advanced Retrieval Pipeline

* Semantic chunking
* Dense vector retrieval
* Hybrid search support
* Metadata filtering
* Context-aware ranking

### AI-Powered Question Answering

* Context-grounded responses
* Hallucination reduction through source retrieval
* Natural language querying
* Conversational document interaction

### Document Processing

* PDF ingestion
* Automatic text extraction
* Intelligent chunk generation
* Metadata preservation

### Modern User Interface

* Responsive React frontend
* Real-time query experience
* Clean document management workflow
* Source-aware answer presentation

---

## 🏗️ System Architecture

```text
User Query
    │
    ▼
Frontend (React)
    │
    ▼
FastAPI Backend
    │
    ├── Query Processing
    ├── Embedding Generation
    ├── Retrieval Pipeline
    └── Response Generation
    │
    ▼
Vector Database (Pinecone)
    │
    ▼
Relevant Chunks
    │
    ▼
LLM Response Generation
    │
    ▼
Final Answer + Sources
```

## 🛠️ Tech Stack

### Frontend

* React
* JavaScript
* Tailwind CSS

### Backend

* Python
* FastAPI
* Uvicorn

### AI & Retrieval

* Sentence Transformers
* Retrieval-Augmented Generation (RAG)
* Hybrid Search
* Vector Embeddings

### Database

* Pinecone Vector Database

### Infrastructure

* Docker
* Nginx
* AWS EC2
* GitHub Actions CI/CD

---

## 📂 Project Structure

```text
RAGRetrival2/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── retrieval/
│   ├── embeddings/
│   └── models/
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── components/
│
├── docker-compose.yml
├── .github/workflows/
└── README.md
```

---

## ⚡ Installation

### Clone Repository

```bash
git clone https://github.com/codee-geek/RAGRetrival2.git
cd RAGRetrival2
```

### Backend Setup

```bash
python -m venv venv

source venv/bin/activate
# Linux/Mac

venv\Scripts\activate
# Windows

pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend

npm install

npm start
```

---

## 🐳 Docker Deployment

### Build Containers

```bash
docker compose build
```

### Start Services

```bash
docker compose up -d
```

### View Logs

```bash
docker compose logs -f
```

---

## 🔍 Example Queries

* What methodologies are discussed in the uploaded documents?
* Summarize the key findings from all uploaded reports.
* Compare the approaches mentioned across documents.
* What risks and recommendations are highlighted?
* Generate an executive summary from multiple files.

---

## 📈 Future Enhancements

* Multi-modal document support
* Agentic workflows
* Knowledge graph integration
* Document comparison dashboard
* Citation-aware answer generation
* Enterprise authentication and access control

---

## 🤝 Contributions

Contributions, issues, and feature requests are welcome.

Feel free to fork the repository and submit a pull request.

---

## 👨‍💻 Author

**Atharva Wakade**

AI Engineer | Machine Learning | Generative AI | RAG Systems

GitHub: https://github.com/codee-geek
