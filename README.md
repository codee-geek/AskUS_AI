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
    ├── Embedding Generation (all-MiniLM-L6-v2)
    ├── Hybrid Retrieval
    │     ├── Dense  → Pinecone (per-session namespace)
    │     └── Sparse → BM25 (per-session, on disk)
    ├── Reciprocal Rank Fusion (RRF)
    ├── Cross-Encoder Reranking
    └── Answer Generation (OpenAI, optional)
    │
    ▼
Final Answer + Sources
```

Uploaded documents are stored on local disk only for the lifetime of a
session. When a session ends (an explicit `DELETE /session` call or after
`SESSION_TTL_HOURS` of inactivity), its raw files, Pinecone vectors and BM25
index are all deleted.

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

* Sentence Transformers (`all-MiniLM-L6-v2` embeddings)
* Hybrid retrieval: dense (Pinecone) + sparse (BM25)
* Reciprocal Rank Fusion + cross-encoder reranking
* OpenAI for optional grounded answer generation

### Database

* Pinecone (dense vectors, serverless free tier)
* BM25 sparse index (per-session, on disk)

### Infrastructure

* Docker
* Nginx
* AWS EC2
* GitHub Actions CI/CD (build + push to GHCR, auto-deploy to EC2)

---

## 📂 Project Structure

```text
RAGRetrival2/
│
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routes (upload, query, session, health)
│   │   ├── services/       # ingestion, pinecone_store, bm25, hybrid,
│   │   │                   # reranker, retriever, local_storage, session_cleanup
│   │   └── storage/        # ephemeral per-session files (gitignored)
│   ├── core/               # config / settings
│   ├── scripts/            # migrate_to_pinecone.py (one-off migration)
│   └── tests/              # pytest suite
│
├── frontend/
│   ├── src/                # React app + tests
│   └── nginx.conf
│
├── docker-compose.yml       # local dev (build images)
├── docker-compose.prod.yml  # production (pull GHCR images)
├── .github/workflows/ci.yml # CI + image publish + EC2 deploy
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

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in what you need. Everything has a
sensible default, so local development works with no keys at all (dense search
is disabled without a Pinecone key, but BM25 + reranking still answer).

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `PINECONE_API_KEY` | For dense search | – | Pinecone serverless project key. Without it, retrieval falls back to BM25-only. |
| `PINECONE_INDEX_NAME` | No | `rag-chunks` | Index name (auto-created on first upload). |
| `PINECONE_CLOUD` / `PINECONE_REGION` | No | `aws` / `us-east-1` | Serverless index location. |
| `OPENAI_API_KEY` | No | – | Enables GPT answer generation; otherwise the top chunk is returned. |
| `LLM_MODEL` | No | `gpt-4.1-nano` | Answer model. |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated allowed origins. |
| `HYBRID_FETCH_K` / `RRF_K` | No | `10` / `60` | Hybrid retrieval tuning. |
| `MAX_UPLOAD_MB` | No | `20` | Per-file upload size cap. |
| `SESSION_TTL_HOURS` | No | `24` | Inactivity window before a session's files + vectors are swept. |
| `REACT_APP_API_URL` | No | `http://localhost:8000` | Browser-facing API URL (baked into the frontend image). |

### Vector storage (Pinecone free tier)

Dense vectors live in **Pinecone** (serverless, free tier). Create a project at
[pinecone.io](https://www.pinecone.io/), copy the API key into `PINECONE_API_KEY`,
and the index is created automatically on first upload (384-dim, cosine). Each
session maps to its own Pinecone **namespace**, so deletes are scoped and cheap.

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

## 🔄 CI/CD

The pipeline lives in [.github/workflows/ci.yml](.github/workflows/ci.yml) and runs on every push/PR:

1. **frontend** – `npm ci`, Jest tests, production build.
2. **backend** – install deps, `ruff` lint, `pytest` with coverage, import smoke test.
3. **docker** – build both images; on `main`/`master`, push them to GitHub Container Registry (GHCR).
4. **deploy** – on `main`/`master` only: SSH into the EC2 host and run
   `docker compose -f docker-compose.prod.yml pull && up -d`, then a health-check
   against `/health`.

### Deploy secrets (GitHub → Settings → Secrets)

| Secret | Purpose |
|--------|---------|
| `EC2_HOST` | Public host/IP of the EC2 instance. |
| `EC2_USER` | SSH user (e.g. `ubuntu`). |
| `EC2_SSH_KEY` | Private key for SSH access. |
| `EC2_APP_DIR` | Directory on the server holding `docker-compose.prod.yml` + `.env`. |
| `DEPLOY_HEALTHCHECK_URL` | (Optional) URL to verify after deploy. Defaults to the live domain `/health`. |

On the server, keep a `.env` (Pinecone/OpenAI keys, `CORS_ORIGINS`, `GHCR_OWNER`)
next to `docker-compose.prod.yml`; the production compose file pulls the
`:latest` GHCR images instead of building.

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
