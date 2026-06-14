# Bug Report & Fixes Log

A quick-glance record of problems we hit and how we solved them.
Newest / biggest issue first.

---

## At a glance

| # | Problem | Status |
|---|---------|--------|
| 1 | CI pipeline too slow (Docker build 12+ min) | Fixed |
| 2 | Backend tests failed in CI: `No module named 'app'` | Fixed |
| 3 | Frontend test failed (stale default test) | Fixed |
| 4 | Backend import crashed CI with HuggingFace `429` | Fixed |
| 5 | Feature code & artifacts not committed / leaking into git | Fixed |
| 6 | Risk of AWS S3 cost going over free tier | Fixed |
| 7 | Answer model hardcoded + expensive | Fixed |

---

## 1. CI pipeline was too slow  ⭐ (main issue)

**Problem**
The GitHub Actions pipeline took ~16 minutes. The backend Docker image
alone took 12+ minutes to build.

**Effects**
- Every push wasted 10+ minutes before we knew if things worked.
- Slow feedback, slow deploys, frustrating to iterate.

**Reasons**
- `sentence-transformers` pulls in **PyTorch**, and on Linux pip installed
  the **CUDA (GPU) version** by default — ~2.5–3 GB of NVIDIA libraries we
  never use (we run CPU-only).
- We were also installing heavy deps the app doesn't need at runtime:
  `faiss-cpu` (unused), `ragas` + `datasets` (eval only), `unstructured`
  (only for .docx, pulled in `numba`, `llvmlite`, `spacy`).
- The Docker build waited for the test jobs to finish first (2 min gate).
- The same images were built twice (build job + publish job).

**Solution**
- Install **CPU-only torch** (`--index-url .../whl/cpu`).
- Trim runtime deps; move eval deps to `requirements-eval.txt`; load .docx
  with the lightweight `python-docx` instead of `unstructured`.
- Multi-stage Dockerfile + pip cache mount (build tools stay out of the image).
- One matrixed Docker job (backend + frontend in parallel), pushes only on master.
- Removed the test gate so Docker builds in parallel with tests.

**Result**
- Backend image build: **12m 15s → 5m 28s (cold) → ~17s (warm cache)**.
- Whole pipeline: **~16.5 min → ~2 min**.
- Image size: **~4.5 GB → ~1.5 GB**.

---

## 2. Backend tests failed in CI: `No module named 'app'`

**Problem** Tests passed locally but failed on CI during import.

**Effect** Backend CI job red, blocked the pipeline.

**Reason** CI ran bare `pytest`, which (unlike local `python -m pytest`)
does not add the `backend/` folder to the import path.

**Solution** Added `backend/pytest.ini` with `pythonpath = .` so imports
work no matter how pytest is started.

---

## 3. Frontend test failed (stale default test)

**Problem** The default Create-React-App test looked for a "learn react"
link that no longer exists in our UI.

**Effect** Frontend CI job red.

**Reason** Leftover boilerplate test never updated after the UI was built.

**Solution** Replaced it with a real smoke test that renders the app and
checks the welcome message (mocking `fetch` and `scrollIntoView`, which
jsdom doesn't provide).

---

## 4. Backend import crashed CI with HuggingFace `429`

**Problem** The "verify imports" step failed with HTTP 429 (rate limited).

**Effect** Flaky backend CI failures, unrelated to our code.

**Reason** Importing the app loaded the ML models at import time, which
hit HuggingFace over the network — GitHub runners get rate-limited.

**Solution** Made the embedding model and cross-encoder **lazy-loaded**
(load on first real use, not at import). Importing the app no longer
touches the network. Bonus: faster startup.

---

## 5. Feature code & artifacts not committed / leaking into git

**Problem** The whole hybrid retrieval layer (BM25, Qdrant, cloud storage,
tests) was never committed; generated files (DB, uploads, `.pkl`) showed
up as untracked.

**Effect** Risk of losing work; noisy, bloated git status.

**Reason** Missing `.gitignore` rules; commits had only touched config/CI.

**Solution** Extended `.gitignore` (storage, sessions, `*.pkl`, `*.faiss`),
untracked legacy binaries, and committed the real source in clean,
logical commits.

---

## 6. Risk of AWS S3 cost going over free tier

**Problem** Planned to use S3 in production but worried about cost.

**Effect** Could exceed the AWS free tier (storage + request limits).

**Reasons**
- Re-uploading the same file created duplicate objects (random IDs).
- The home/stats endpoint did an S3 `LIST` on every request (billable).

**Solution**
- Content-hash document IDs + a `HEAD` check to skip re-uploading
  identical files (no duplicate storage, fewer PUTs).
- Stats now count from Qdrant instead of calling S3 `LIST`.
- Default stays on local disk (zero AWS cost in dev).
- Added moto-based tests for both local and S3 paths.

---

## 7. Answer model hardcoded + expensive

**Problem** The answer model was hardcoded (`gpt-4o-mini`) and ignored config.

**Effect** No easy way to switch models; higher cost than needed.

**Solution** Made it config/env driven, defaulting to the cheapest
**`gpt-4.1-nano`**, with a capped `max_tokens` to bound API cost.

---

_Tip: warm CI runs are fast because of the Docker layer cache. A run is
"cold" (slower) only when `requirements.txt` or the `Dockerfile` changes._
