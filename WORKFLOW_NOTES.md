# Workflow Explainer Notes — AskUs AI (Hybrid RAG)

A practical walkthrough of how a request travels through the codebase: which
file calls which, what functions run, what credentials are needed, and where
the system still needs work.

> TL;DR stack: **React frontend → FastAPI backend → (Pinecone dense + BM25 sparse)
> → RRF fusion → cross-encoder rerank → OpenAI answer**. Each browser tab is its
> own "session"; its files/vectors are deleted on tab close or after a TTL.

---

## 0. The big picture (one diagram)

```text
Browser (frontend/src/App.js)
   │  X-Session-ID header on every call
   │
   ├── GET  /            → home()        → stats from Pinecone
   ├── POST /upload      → upload_file() → ingest_documents()
   ├── POST /query       → ask_question()→ query_documents()
   └── DELETE /session   → end_session() → cleanup_session()
                                   │
   backend/app/api/routes.py ──────┘
                                   │
            ┌──────────────────────┼───────────────────────┐
            ▼                      ▼                       ▼
   services/ingestion.py   services/retriever.py   services/session_cleanup.py
```

---

## 1. Entry points & wiring (where the app boots)

| File | Role | Key functions |
|------|------|---------------|
| `frontend/src/App.js` | Whole UI (upload, chat, sources, session) | `getOrCreateSessionId()`, `uploadFile()`, `handleSend()`, `clearSession()` |
| `backend/app/main.py` | FastAPI app, CORS, background sweep loop | `lifespan()`, `_session_sweep_loop()` |
| `backend/app/api/routes.py` | All HTTP routes | `home()`, `upload_file()`, `ask_question()`, `end_session()` |
| `backend/core/config.py` | Reads `.env`, holds all tunables | `_get_int()`, `_get_float()` |

**Boot flow:** `main.py` builds `app`, adds CORS from `CORS_ORIGINS`, mounts
`routes.py` via `app.include_router(router)`, and on startup launches
`_session_sweep_loop()` which calls `sweep_stale_sessions()` every
`SESSION_SWEEP_INTERVAL_MINUTES`.

**Session identity:** the frontend mints a UUID once (`getOrCreateSessionId`,
stored in `localStorage`) and sends it as the `X-Session-ID` header. The backend
reads it via `_get_session_id()` → `sanitize_session_id()`. This id becomes the
**Pinecone namespace** and the **on-disk folder name**, so everything is scoped
per tab/user.

---

## 2. UPLOAD / INGESTION flow (PDF → searchable index)

**Trigger:** user drops a PDF → `App.js: uploadFile()` → `POST /upload`.

```text
App.js uploadFile()
  → routes.py upload_file()                      [size check, read bytes]
      → ingestion.py ingest_documents()
          ├── calculate_content_hash()           → stable document_id (md5)
          ├── _write_temp_file() + load_document()
          │       PyPDFLoader / TextLoader / _load_docx()
          ├── local_storage.save_document()      → saves raw file on disk
          ├── _prepare_chunks()
          │       RecursiveCharacterTextSplitter.split_documents()
          ├── embeddings.get_embeddings().embed_documents()   [MiniLM, 384-dim]
          ├── pinecone_store.upsert_chunks()      → dense vectors (namespace=session)
          └── bm25.get_bm25_indexer().extend_and_rebuild()    → sparse index (.pkl on disk)
  → routes.py touch_session()                    → updates .last_active marker
```

**File-by-file:**

| Step | File · function | What happens |
|------|-----------------|--------------|
| HTTP | `routes.py: upload_file()` | Rejects empty/oversized files (`MAX_UPLOAD_MB`), reads bytes |
| Orchestrate | `ingestion.py: ingest_documents()` | The whole ingest pipeline below |
| ID | `ingestion.py: calculate_content_hash()` | `doc_<md5[:16]>` so re-uploads overwrite, not duplicate |
| Parse | `ingestion.py: load_document()` | PDF→`PyPDFLoader`, txt→`TextLoader`, docx→`python-docx` |
| Persist raw | `local_storage.py: save_document()` | Writes file under `storage/sessions/<id>/uploads/<doc_id>/` |
| Chunk | `ingestion.py: _prepare_chunks()` | 500-char chunks, 100 overlap; tags metadata (`chunk_id`, `semantic_section`, etc.) |
| Embed | `embeddings.py: get_embeddings()` | Lazy-loaded `all-MiniLM-L6-v2`, normalized |
| Dense store | `pinecone_store.py: upsert_chunks()` | `ensure_index()` (auto-creates), batched upsert by namespace |
| Sparse store | `bm25.py: extend_and_rebuild()` | Merges chunks, rebuilds `BM25Okapi`, pickles to disk |

**Important:** dense (Pinecone) needs a key; sparse (BM25) does not. If
`PINECONE_API_KEY` is missing, `upsert_chunks()` raises
`PineconeNotConfiguredError` and the whole upload 500s (see Gaps §6).

---

## 3. QUERY flow (question → grounded answer)

**Trigger:** user sends a message → `App.js: handleSend()` → `POST /query`.

```text
App.js handleSend()
  → routes.py ask_question()
      → retriever.py query_documents()
          → run_query()
              ├── _bm25_search()    → bm25.py search()        [sparse top-k]
              ├── _dense_search()   → embeddings.embed_query()
              │                       pinecone_store.search_chunks()  [dense top-k]
              ├── hybrid.py reciprocal_rank_fusion()           [RRF merge]
              └── reranker.py cross_encoder_rerank()           [ms-marco cross-encoder]
          → _build_answer()                                    [OpenAI or fallback]
          → _format_sources()                                  [doc/page/snippet]
  → routes.py touch_session()
```

**File-by-file:**

| Step | File · function | What happens |
|------|-----------------|--------------|
| HTTP | `routes.py: ask_question()` | Validates `question` (1–4000 chars) |
| Orchestrate | `retriever.py: query_documents()` → `run_query()` | Runs hybrid retrieval |
| Sparse | `retriever.py: _bm25_search()` → `bm25.py: search()` | Whitespace tokenize, BM25 scores |
| Dense | `retriever.py: _dense_search()` → `pinecone_store.py: search_chunks()` | Embed query, query namespace |
| Fuse | `hybrid.py: reciprocal_rank_fusion()` | Combine both ranked lists (`RRF_K`) |
| Rerank | `reranker.py: cross_encoder_rerank()` | `ms-marco-MiniLM-L-6-v2`, gap cutoff, `TOP_K` |
| Answer | `retriever.py: _build_answer()` | If `OPENAI_API_KEY`: `ChatOpenAI(LLM_MODEL)`; else returns top chunk text |
| Sources | `retriever.py: _format_sources()` | `{doc, page, document_id, snippet}` for the UI chips |

**Fallback logic (graceful degradation):**
- Both BM25 + dense present → RRF fusion.
- Only one present → use it directly.
- Neither → "I could not find relevant information…".
- No `OPENAI_API_KEY` → returns the best chunk verbatim instead of a generated answer.

---

## 4. SESSION CLEANUP flow (privacy / cost control)

**Two triggers:**
1. Explicit: tab close → `App.js` `beforeunload` → `navigator.sendBeacon` /
   `DELETE /session` → `routes.py: end_session()`.
2. Automatic: `main.py: _session_sweep_loop()` every hour.

```text
end_session() / sweep_stale_sessions()
  → session_cleanup.py cleanup_session()
      ├── local_storage.delete_session_files()   → rm storage/sessions/<id>/ (raw + BM25 .pkl)
      └── pinecone_store.delete_session()         → delete_all in that namespace
```

`iter_stale_sessions()` compares each session's `.last_active` marker against
`SESSION_TTL_HOURS` to decide what to sweep.

---

## 5. Credentials & API keys (what's needed vs. optional)

Configured in `.env` (copy from `.env.example`). Read in `core/config.py`.

| Key | Required? | Used by | If missing |
|-----|-----------|---------|------------|
| `PINECONE_API_KEY` | **Needed for dense search** | `pinecone_store.get_pinecone_client()` | `PineconeNotConfiguredError`; **upload currently 500s** (see §6.1) |
| `PINECONE_INDEX_NAME` | No (`rag-chunks`) | `pinecone_store` | default used |
| `PINECONE_CLOUD` / `PINECONE_REGION` | No (`aws`/`us-east-1`) | `ensure_index()` | default serverless location |
| `OPENAI_API_KEY` | Optional | `retriever._build_answer()` | No GPT answer; returns top chunk text |
| `LLM_MODEL` | No (`gpt-4.1-nano`) | `_build_answer()` | cheapest model |
| `ANSWER_TEMPERATURE` / `ANSWER_MAX_TOKENS` | No | `_build_answer()` | `0.2` / `512` |
| `CORS_ORIGINS` | No (localhost) | `main.py` CORS | only localhost allowed |
| `HYBRID_FETCH_K` / `RRF_K` | No (`10`/`60`) | `retriever` / `hybrid` | retrieval tuning |
| `MAX_UPLOAD_MB` | No (`20`) | `routes.upload_file()` | 20 MB cap |
| `SESSION_TTL_HOURS` / `SESSION_SWEEP_INTERVAL_MINUTES` | No (`24`/`60`) | cleanup loop | defaults |
| `REACT_APP_API_URL` | No (`localhost:8000`) | `App.js` (build-time) | points at localhost |

**Deploy-only secrets** (GitHub → Settings → Secrets, used by `ci.yml` deploy job):
`EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`, `EC2_APP_DIR`, `DEPLOY_HEALTHCHECK_URL`
(optional). On the EC2 box, a `.env` next to `docker-compose.prod.yml` must hold
`PINECONE_API_KEY`, `OPENAI_API_KEY`, `CORS_ORIGINS`, `GHCR_OWNER`.

**To run locally end-to-end you need at minimum:** `PINECONE_API_KEY` (for
upload to succeed today). `OPENAI_API_KEY` is optional but recommended for real
answers.

---

## 6. Where you need to work more (gaps / risks / TODOs)

### 6.1 Upload hard-fails without Pinecone (highest priority)
The README claims "local development works with no keys… BM25 + reranking still
answer," but `ingestion.ingest_documents()` calls `upsert_chunks()`
unconditionally. With no `PINECONE_API_KEY`, `get_pinecone_client()` raises and
the upload returns 500 — so BM25-only mode is never reached on ingest.
**Fix:** wrap the Pinecone upsert in a try/except (or a "dense enabled" flag) so
ingestion can proceed BM25-only. Mirror the graceful handling already in
`cleanup_session()`.

### 6.2 Frontend is PDF-only, backend supports more
`App.js: addFiles()` filters to `.pdf` only, but `ingestion.SUPPORTED_EXTENSIONS`
allows `.txt` and `.docx`. **Decide:** either open the file input to txt/docx or
document the restriction.

### 6.3 Stats can be slow/expensive
`count_session_documents()` and `iter_session_sources()` call `index.list()` +
`fetch()` on Pinecone. `GET /` runs on every page load. For big namespaces this
is extra calls. **Consider:** caching counts or storing a lightweight per-session
manifest on disk.

### 6.4 BM25 rebuild cost grows with corpus
`extend_and_rebuild()` reloads the full corpus and rebuilds the entire
`BM25Okapi` on every upload. Fine for a few docs, O(n) per upload at scale.
**Consider:** incremental indexing or capping corpus size.

### 6.5 `pickle` for BM25 persistence
`bm25.py` pickles index/corpus to disk. Safe here (we write them ourselves) but
pickle is unsafe if a file is ever attacker-controlled. **Consider:** a safer
serialization (e.g. rebuild from stored chunks / JSON) if storage is shared.

### 6.6 Reranker is always loaded on first query
`cross_encoder_rerank()` is unconditional. First query pays the model
download/load latency. **Consider:** warmup on startup, or make rerank optional
via config.

### 6.7 Session cleanup on tab close is best-effort
`beforeunload` + `sendBeacon` is not guaranteed (crashes, mobile). The TTL sweep
is the real safety net — make sure `SESSION_TTL_HOURS` is set sensibly in prod.

### 6.8 Migration script needs an extra dep
`scripts/migrate_to_pinecone.py` requires `qdrant-client` (not in
`requirements.txt`). One-off only; install manually before running.

### 6.9 No auth / rate limiting
Any client can upload/query and consume Pinecone + OpenAI quota. **Add** auth,
per-session quotas, or rate limiting before exposing publicly.

### 6.10 Tests reference both old & new stores
Git status shows new `test_pinecone_store.py`, `test_local_storage.py`,
`test_retriever.py`, `test_reranker.py`, `test_session_cleanup.py` plus deleted
`cloud_storage`/`qdrant_store`. **Verify** the suite is green after the
Qdrant→Pinecone + S3→local migration (run `pytest` in `backend/`).

---

## 7. Quick "where do I change X?" cheat sheet

| I want to… | Edit |
|------------|------|
| Change chunk size / overlap | `core/config.py` (`CHUNK_SIZE`, `CHUNK_OVERLAP`) |
| Change embedding model | `core/config.py` (`EMBEDDING_MODEL`, `EMBEDDING_DIM`) |
| Change answer model / prompt | `core/config.py` (`LLM_MODEL`) + `retriever._build_answer()` |
| Tune hybrid retrieval | `core/config.py` (`TOP_K`, `HYBRID_FETCH_K`, `RRF_K`) |
| Change rerank behavior | `reranker.cross_encoder_rerank()` (`top_n`, `max_score_gap`) |
| Add a file type | `ingestion.SUPPORTED_EXTENSIONS` + `load_document()` + `App.js addFiles()` |
| Change upload limit | `MAX_UPLOAD_MB` (env) |
| Change session lifetime | `SESSION_TTL_HOURS` (env) |
| Add an API route | `backend/app/api/routes.py` |
| Change CORS / allowed origins | `CORS_ORIGINS` (env) consumed in `main.py` |
```
