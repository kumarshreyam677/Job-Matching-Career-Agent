import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import agent, db, retrieval
from .config import S
from .schemas import ChatRequest, FeedbackRequest


@asynccontextmanager
async def lifespan(app):
    db.init()
    retrieval.model()  # Warm BAAI/bge-small-en-v1.5 ONNX model on startup
    yield


app = FastAPI(title="Career Agent API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=S.cors_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    with db.conn() as c:
        n = c.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"]
    return {"status": "ok", "jobs_indexed": n, "embed_model": S.embed_model, "llm_model": S.llm_model}


@app.get("/search")
def search(q: str, k: int = 10):
    rows = retrieval.hybrid_search(q, k=min(k, 50))
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "company": r["company"],
            "location": r["location"],
            "url": r["url"],
            "score": round(float(r["score"]), 4),
        }
        for r in rows
    ]


@app.post("/chat")
def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())
    try:
        res = agent.run(sid, req.message)
    except Exception as e:
        raise HTTPException(500, f"agent error: {type(e).__name__}: {e}")
    if not res.get("ok"):
        raise HTTPException(502, res["error"])
    return res


@app.post("/feedback")
def feedback(f: FeedbackRequest):
    with db.conn() as c:
        c.execute(
            "INSERT INTO feedback(session_id, job_id, rating) VALUES (%s,%s,%s)",
            (f.session_id, f.job_id, f.rating),
        )
    return {"ok": True}


@app.get("/metrics/summary")
def metrics():
    """Live production telemetry directly from PostgreSQL for GitHub evaluation reports."""
    with db.conn() as c:
        q = c.execute(
            """SELECT count(*) AS queries,
                      count(DISTINCT session_id) AS sessions,
                      round(coalesce(percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms), 0)::numeric, 1) AS p50_ms,
                      round(coalesce(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms), 0)::numeric, 1) AS p95_ms,
                      round(coalesce(avg(valid_json::int), 0)::numeric, 4) AS valid_json_rate,
                      round(coalesce(avg(grounded::int), 0)::numeric, 4) AS grounded_rate
               FROM query_log"""
        ).fetchone()
        f = c.execute(
            """SELECT count(*) AS total_ratings,
                      round(coalesce(avg((rating > 0)::int), 0)::numeric, 4) AS up_rate
               FROM feedback"""
        ).fetchone()
    return {
        "queries": {k: float(v) if hasattr(v, "is_finite") else v for k, v in q.items()},
        "feedback": {k: float(v) if hasattr(v, "is_finite") else v for k, v in f.items()},
    }
