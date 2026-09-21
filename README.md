# Job-Matching Career Agent

> **Live Frontend (Vercel):** `<PASTE_YOUR_VERCEL_URL>`  
> **Live API Docs (Render Docker):** `<PASTE_YOUR_RENDER_URL>/docs`

An end-to-end **LLM Career Copilot** built with **FastAPI**, **PostgreSQL + `pgvector` + Full-Text Search**, **`BAAI/bge-small-en-v1.5` embeddings**, **Pydantic-validated Structured Outputs**, **Persistent Session Memory**, **Automated LLM Evals**, and **Synthetic Load Testing**.

## Architecture
- **Offline Ingestion (`backend/scripts/ingest.py`):** Embeds job postings into 384-d vectors (`BAAI/bge-small-en-v1.5` via `fastembed`) and stores them in PostgreSQL with an HNSW `pgvector` index + generated `tsvector` GIN index.
- **Online Agentic `/chat` Pipeline:**
  1. **Memory & Structured Profile Extraction:** Loads prior session profile from PostgreSQL `JSONB` and merges new user input into a Pydantic-validated `ProfileQuery`.
  2. **Personalized Hybrid Retrieval:** Combines dense `pgvector` cosine similarity and sparse Postgres FTS (`ts_rank_cd`) via **Reciprocal Rank Fusion (RRF)**, blending the query vector with the centroid of `👍` liked roles and excluding `👎` disliked roles.
  3. **Grounded Ranking & Guardrail:** Ranks top candidates with structured JSON output (`Recs`) and drops any `job_id` not present in the retrieved candidate set (`grounded = true`).
  4. **Production Telemetry:** Logs latency, JSON validity, groundedness, and user feedback to PostgreSQL (`query_log`, `feedback`) exposed via `GET /metrics/summary`.

## Quickstart & Deployment
1. **PostgreSQL + pgvector:** Create a free database at [neon.tech](https://neon.tech) and copy the connection string.
2. **Ingest Jobs:**
   ```bash
   cd backend
   pip install -r requirements-ingest.txt
   DATABASE_URL="<YOUR_NEON_URL>" python -m scripts.ingest --file data/sample_jobs.csv
   ```
3. **Deploy Backend (Docker on Render):** Connect this GitHub repo in Render (`render.yaml` auto-configures Docker in `backend/`) and set `DATABASE_URL` and `LLM_API_KEY` (from [console.groq.com](https://console.groq.com)).
4. **Deploy Frontend (Vercel):** Set `API` in `frontend/index.html` to your Render URL, then import `frontend/` into Vercel.
5. **Run Evals & 1,000-User Load Test:**
   ```bash
   python evals/run_evals.py --api https://<YOUR-API>.onrender.com
   python loadtest/run_1000_users.py --api https://<YOUR-API>.onrender.com --users 1000
   ```
