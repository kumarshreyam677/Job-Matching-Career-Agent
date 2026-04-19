import numpy as np
from fastembed import TextEmbedding

from . import db
from .config import S

_model = None


def model():
    global _model
    if _model is None:
        _model = TextEmbedding(S.embed_model)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    return np.array(list(model().embed(texts)), dtype=np.float32)


HYBRID_SQL = """
WITH dense AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(q)s) AS r
  FROM jobs WHERE id <> ALL(%(ex)s) ORDER BY embedding <=> %(q)s LIMIT 60),
sparse AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(tsv, tq) DESC) AS r
  FROM jobs, websearch_to_tsquery('english', %(t)s) tq
  WHERE tsv @@ tq AND id <> ALL(%(ex)s) ORDER BY ts_rank_cd(tsv, tq) DESC LIMIT 60)
SELECT j.id, j.title, j.company, j.location, j.url, left(j.description, 700) AS snippet,
       COALESCE(1.0/(60+d.r),0) + COALESCE(1.0/(60+s.r),0) AS score
FROM jobs j LEFT JOIN dense d ON d.id=j.id LEFT JOIN sparse s ON s.id=j.id
WHERE d.id IS NOT NULL OR s.id IS NOT NULL
ORDER BY score DESC LIMIT %(k)s
"""


def hybrid_search(
    query: str,
    keywords: list[str] | None = None,
    k: int | None = None,
    liked: list[str] | None = None,
    disliked: list[str] | None = None,
):
    """Dense (pgvector) + sparse (Postgres FTS) fused with Reciprocal Rank Fusion.
    Personalisation: blend query vector with L2-normalized centroid of liked jobs; exclude disliked."""
    k = k or S.top_k
    q = embed([query])[0]
    with db.conn() as c:
        if liked:
            row = c.execute("SELECT avg(embedding) AS v FROM jobs WHERE id = ANY(%s)", (liked,)).fetchone()
            if row and row["v"] is not None:
                centroid = np.array(row["v"], dtype=np.float32)
                blended = 0.8 * q + 0.2 * centroid
                norm = np.linalg.norm(blended)
                if norm > 0:
                    q = blended / norm
        text = " or ".join(keywords) if keywords else query
        rows = c.execute(HYBRID_SQL, {"q": q, "t": text, "k": k, "ex": disliked or []}).fetchall()
    return rows
