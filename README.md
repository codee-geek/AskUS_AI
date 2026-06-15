# AskUs AI — Multi-Document Hybrid RAG

AskUs AI is a production-style Retrieval-Augmented Generation (RAG) app: upload PDFs (and other supported formats), ask questions in natural language, and get answers grounded in your documents with source citations.

**Live demo:** https://askus-ai.duckdns.org/

> Public demo — no authentication. Each browser session is isolated and expires after 24 hours of inactivity.

---

## Highlights

- **Hybrid retrieval** — BM25 sparse search + Pinecone dense vectors, fused with Reciprocal Rank Fusion (RRF)
- **Grounded answers** — OpenAI `gpt-4.1-nano` generates answers from retrieved context; falls back to top chunk if no API key
- **Session-scoped storage** — each user gets a Pinecone namespace + local BM25 index; data is deleted on session end or TTL
- **Deployed stack** — React frontend, FastAPI backend, Docker, GitHub Actions CI/CD, AWS EC2 (on-demand wake/stop)
- **Tested** — 38 automated backend tests; frontend smoke tests in CI

---

## Architecture

```text
User Query
    │
    ▼
Frontend (React + Nginx)
    │
    ▼
FastAPI Backend
    │
    ├── Chunk & ingest uploaded documents (PDF / TXT / DOCX)
    ├── Embeddings (OpenAI text-embedding-3-small, 1536-dim)
    ├── Hybrid retrieval
    │     ├── Dense  → Pinecone (per-session namespace)
    │     └── Sparse → BM25 (per-session, on disk)
    ├── Reciprocal Rank Fusion (RRF)
    └── Answer generation (OpenAI GPT, optional)
    │
    ▼
Answer + source snippets (doc name, page, excerpt)
```

Uploaded files live on disk only for the lifetime of a session. When a session ends (`DELETE /session`) or exceeds `SESSION_TTL_HOURS` without activity, local files, Pinecone vectors, and the BM25 index are all removed.

---

## Performance (live demo, Mar 2026)

Measured against https://askus-ai.duckdns.org/ on on-demand EC2:

| Operation | Typical latency |
|-----------|-----------------|
| Health check (`/health`) | ~250 ms |
| Document upload (small text file) | ~3 s |
| Query with indexed doc + GPT answer | ~4–5 s |
| Query on empty session (warm) | ~2.5 s |

Latency includes OpenAI embedding + LLM API calls and Pinecone query time. First request after idle can be slower while the instance wakes.

---

## Tech stack

| Layer | Tools |
|-------|-------|
| Frontend | React 19, custom CSS (inline styles) |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |
| Dense store | Pinecone serverless (per-session namespace) |
| Sparse store | BM25 (`rank_bm25`), persisted per session |
| Answer model | OpenAI `gpt-4.1-nano` (configurable) |
| Infra | Docker, Nginx, AWS EC2, GitHub Actions → GHCR |

---

## Project structure

```text
RAGRetrival2-1/
├── backend/
│   ├── app/
│   │   ├── api/            # Routes: upload, query, session, health
│   │   └── services/       # ingestion, retriever, bm25, pinecone_store,
│   │                       # hybrid, local_storage, session_cleanup
│   ├── core/               # Environment config
│   └── tests/              # pytest suite (38 tests)
├── frontend/
│   ├── src/                # React app
│   └── nginx.conf
├── deploy/ondemand/        # EC2 wake-on-visit + auto-stop scripts
├── docker-compose.yml      # Local dev (build images)
├── docker-compose.prod.yml # Production (pull GHCR images)
└── .github/workflows/ci.yml
```

---

## Quick start (local)

### 1. Clone and configure

```bash
git clone https://github.com/codee-geek/RAGRetrival2.git
cd RAGRetrival2
cp .env.example .env
```

Edit `.env` and set at minimum:

- `PINECONE_API_KEY` — required for upload (dense indexing)
- `OPENAI_API_KEY` — recommended for GPT answers and embeddings

### 2. Docker (recommended)

```bash
docker compose up -d --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Health: http://localhost:8000/health

### 3. Manual setup

**Backend**

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm start
```

### 4. Run tests

```bash
pip install -r requirements-dev.txt
cd backend && pytest tests/ -q
```

---

## Configuration

Copy `.env.example` to `.env`. Key variables:

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `PINECONE_API_KEY` | **Yes** (for upload) | — | Pinecone serverless key; index auto-created on first upload |
| `OPENAI_API_KEY` | Recommended | — | Embeddings + GPT answers; without it answers fall back to top chunk |
| `EMBEDDING_MODEL` | No | `text-embedding-3-small` | OpenAI embedding model |
| `EMBEDDING_DIM` | No | `1536` | Must match Pinecone index dimension |
| `PINECONE_INDEX_NAME` | No | `rag-chunks` | Pinecone index name |
| `LLM_MODEL` | No | `gpt-4.1-nano` | Answer generation model |
| `HYBRID_FETCH_K` / `RRF_K` | No | `10` / `60` | Hybrid retrieval tuning |
| `MAX_UPLOAD_MB` | No | `20` | Per-file upload limit |
| `SESSION_TTL_HOURS` | No | `24` | Inactivity before session cleanup |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Allowed browser origins |
| `REACT_APP_API_URL` | No | `http://localhost:8000` | API URL baked into frontend build |

---

## API overview

All routes accept an `X-Session-ID` header (the frontend generates a UUID per browser tab).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Session stats (docs indexed, chunk count) |
| `GET` | `/health` | Liveness probe |
| `POST` | `/upload` | Upload and ingest a document |
| `POST` | `/query` | Ask a question; returns answer + sources |
| `DELETE` | `/document/{document_id}` | Remove one document from the session |
| `DELETE` | `/session` | Clear session (files + vectors + BM25) |

**Example query**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: my-session" \
  -d '{"question": "What are the key terms in this contract?"}'
```

---

## CI/CD

Pipeline: [.github/workflows/ci.yml](.github/workflows/ci.yml)

On code changes (backend, frontend, Docker, dependencies):

1. **frontend** — install, Jest tests, production build
2. **backend** — ruff lint, pytest with coverage, import smoke test
3. **docker** — build images; on `main`/`master`, push to GitHub Container Registry
4. **deploy** — SSH to EC2, `docker compose pull && up -d`, health check

**Docs-only changes** (README, markdown files only) skip tests, Docker builds, and deploy — the workflow exits immediately with a success message.

### Deploy secrets (GitHub → Settings → Secrets)

| Secret | Purpose |
|--------|---------|
| `EC2_HOST` | EC2 public host/IP |
| `EC2_USER` | SSH user (e.g. `ubuntu`) |
| `EC2_SSH_KEY` | Private SSH key |
| `EC2_APP_DIR` | Server directory with `docker-compose.prod.yml` + `.env` |
| `DEPLOY_HEALTHCHECK_URL` | Optional post-deploy URL (defaults to live `/api/health`) |

---

## Example questions

- What methodologies are discussed in the uploaded documents?
- Summarize the key findings across all reports.
- Compare the approaches mentioned in different files.
- What risks and recommendations are highlighted?

---

## Known limitations

- No authentication or rate limiting on the public demo
- Frontend upload UI accepts PDFs only (backend also supports `.txt` and `.docx`)
- Session stats endpoint queries Pinecone and can be slow on large sessions
- BM25 index is fully rebuilt on each upload (fine for demo scale)

---

## Author

**Atharva Wakade** — AI Engineer | RAG Systems | Generative AI

GitHub: https://github.com/codee-geek
