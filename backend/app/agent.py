import json
import time
import urllib.error
import urllib.request

from pydantic import BaseModel, ValidationError

from . import db, retrieval
from .config import S
from .schemas import ProfileQuery, Recs


def _chat_completion(messages: list[dict], temperature: float = 0.2) -> str:
    """Call OpenAI-compatible Chat Completions endpoint using stdlib urllib (avoids httpx Py3.13 decompression bugs)."""
    url = S.llm_base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {
            "model": S.llm_model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {S.llm_api_key}",
            "Accept-Encoding": "identity",
            "User-Agent": "CareerPilot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"].get("content") or ""
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LLM API HTTP {e.code}: {err_body[:300]}") from e


def llm_json(system: str, user: str, model_cls: type[BaseModel], retries: int = 1):
    """Structured output: JSON mode + Pydantic schema validation + bounded repair retry."""
    schema = json.dumps(model_cls.model_json_schema())
    sys = f"{system}\nReturn ONLY a valid JSON object matching this JSON schema:\n{schema}"
    msgs = [{"role": "system", "content": sys}, {"role": "user", "content": user}]
    for _ in range(retries + 1):
        raw = _chat_completion(msgs, temperature=0.2)
        try:
            return model_cls.model_validate_json(raw), True
        except ValidationError as e:
            msgs += [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": f"Invalid JSON schema. Fix this validation error and return JSON only: {e}"},
            ]
    return None, False


def update_profile(message: str, prev: dict | None) -> ProfileQuery | None:
    sysmsg = (
        "You are an AI career copilot. Merge the user's new message with their remembered profile. "
        "'search_query' must be a rich 1-2 sentence description of the ideal roles. "
        "'keywords' must be 3-8 short job-search terms (roles, frameworks, domain skills)."
    )
    user = f"Remembered profile: {json.dumps(prev or {})}\nNew message: {message}"
    out, _ = llm_json(sysmsg, user, ProfileQuery)
    return out


def recommend(profile: ProfileQuery, cands: list[dict]):
    sysmsg = (
        "You rank job candidates for a candidate. Use ONLY the candidate jobs provided; never invent jobs. "
        "Pick the best up to 5, reference them by exact job_id, give an honest match_score (0-100), "
        "a concise one-sentence reason grounded in the job description, and list any missing_skills."
    )
    cand_txt = "\n".join(
        f"[{c['id']}] {c['title']} @ {c['company']} ({c['location']}): {c['snippet'][:400]}" for c in cands
    )
    user = f"User profile: {profile.model_dump_json()}\n\nCandidates:\n{cand_txt}"
    return llm_json(sysmsg, user, Recs)


def load_session(sid: str):
    with db.conn() as c:
        row = c.execute("SELECT profile FROM sessions WHERE id=%s", (sid,)).fetchone()
        fb = c.execute("SELECT job_id, rating FROM feedback WHERE session_id=%s", (sid,)).fetchall()
    liked = [f["job_id"] for f in fb if f["rating"] > 0]
    disliked = [f["job_id"] for f in fb if f["rating"] < 0]
    return (row["profile"] if row else None), liked, disliked


def save_profile(sid: str, profile: dict):
    with db.conn() as c:
        c.execute(
            """INSERT INTO sessions(id, profile) VALUES (%s, %s::jsonb)
               ON CONFLICT (id) DO UPDATE SET profile=EXCLUDED.profile, updated_at=now()""",
            (sid, json.dumps(profile)),
        )


def run(session_id: str, message: str) -> dict:
    t0 = time.time()
    prev, liked, disliked = load_session(session_id)
    profile = update_profile(message, prev)
    if profile is None:
        return {"ok": False, "error": "Could not parse user profile into structured schema"}
    save_profile(session_id, profile.model_dump())

    cands = retrieval.hybrid_search(profile.search_query, profile.keywords, liked=liked, disliked=disliked)
    by_id = {c["id"]: c for c in cands}
    recs, valid = recommend(profile, cands) if cands else (None, False)

    jobs, hallucinated = [], 0
    if recs:
        for j in recs.jobs:
            if j.job_id not in by_id:
                hallucinated += 1
                continue
            c = by_id[j.job_id]
            jobs.append(
                {
                    **j.model_dump(),
                    "title": c["title"],
                    "company": c["company"],
                    "location": c["location"],
                    "url": c["url"],
                    "snippet": c.get("snippet", ""),
                }
            )

    grounded = recs is not None and hallucinated == 0
    latency = int((time.time() - t0) * 1000)

    with db.conn() as c:
        c.execute(
            "INSERT INTO query_log(session_id, latency_ms, n_candidates, n_results, valid_json, grounded) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (session_id, latency, len(cands), len(jobs), valid, grounded),
        )

    return {
        "ok": True,
        "session_id": session_id,
        "profile": profile.model_dump(),
        "summary": recs.summary if recs else "No matching roles found in the current catalog.",
        "jobs": jobs,
        "meta": {
            "latency_ms": latency,
            "valid_json": valid,
            "grounded": grounded,
            "candidates": len(cands),
            "liked_count": len(liked),
            "disliked_count": len(disliked),
        },
    }
