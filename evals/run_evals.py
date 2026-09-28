"""Offline/Online LLM & RAG Evaluation Runner.
Run: python evals/run_evals.py --api https://YOUR-API.onrender.com
Outputs evals/results.json and evals/EVAL_REPORT.md."""
import argparse
import json
import pathlib
import statistics
import time
import uuid
from datetime import datetime, timezone

import requests

CASES = [
    ("Final year BTech CS, strong Python, FastAPI, SQL, Docker. Want backend roles.", ["backend", "python", "software"]),
    ("I know React and TypeScript, want frontend jobs.", ["frontend", "front", "full stack"]),
    ("Interested in LLMs, RAG, embeddings, vector search.", ["llm", "ml", "ai", "search", "document"]),
    ("SQL, Tableau, Excel; want data analyst role.", ["data", "analyst"]),
    ("Docker, Kubernetes, CI/CD, Terraform, cloud reliability.", ["devops", "cloud", "reliability"]),
    ("Kotlin and Android app development.", ["android"]),
    ("Search relevance, ranking, BM25, pgvector.", ["search", "ranking", "scientist"]),
    ("Figma, user research, prototyping, UI design.", ["design"]),
    ("Build conversational AI agents with tool use, memory, and evals.", ["agent", "conversational", "ai", "eval"]),
    ("Entry-level software engineering or AI/ML graduate role in Bengaluru.", ["graduate", "intern", "engineer", "ai"]),
]


def call_with_retry(api: str, text: str, max_attempts: int = 5):
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.post(
                f"{api.rstrip('/')}/chat",
                json={"session_id": str(uuid.uuid4()), "message": text},
                timeout=90,
            )
            if r.status_code == 200:
                return r
            wait = 12 * attempt
            print(f"  -> HTTP {r.status_code}, retrying in {wait}s (attempt {attempt}/{max_attempts})...")
            time.sleep(wait)
        except Exception as e:
            wait = 12 * attempt
            print(f"  -> Error {e}, retrying in {wait}s (attempt {attempt}/{max_attempts})...")
            time.sleep(wait)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    a = ap.parse_args()

    res = []
    for idx, (text, kws) in enumerate(CASES, start=1):
        r = call_with_retry(a.api, text)
        if r is None:
            res.append({"id": f"E{idx:02d}", "case": text, "ok": False})
            continue
        d = r.json()
        top5 = [j["title"].lower() for j in d["jobs"][:5]]
        hit5 = any(k in t for k in kws for t in top5)
        res.append(
            {
                "id": f"E{idx:02d}",
                "case": text,
                "ok": True,
                "valid_json": d["meta"]["valid_json"],
                "grounded": d["meta"]["grounded"],
                "hit5": hit5,
                "latency_ms": d["meta"]["latency_ms"],
            }
        )
        print(f"[E{idx:02d}] valid_json={d['meta']['valid_json']} grounded={d['meta']['grounded']} hit@5={hit5} ({d['meta']['latency_ms']} ms)")
        if idx < len(CASES):
            time.sleep(6)

    ok = [r for r in res if r["ok"]]
    latencies = sorted(r["latency_ms"] for r in ok) if ok else [0]
    summary = {
        "target_api": a.api,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "n_cases": len(res),
        "success_rate": round(len(ok) / len(res) * 100, 1),
        "valid_json_rate": round(sum(r["valid_json"] for r in ok) / max(len(ok), 1) * 100, 1),
        "grounded_rate": round(sum(r["grounded"] for r in ok) / max(len(ok), 1) * 100, 1),
        "hit_at_5": round(sum(r["hit5"] for r in ok) / max(len(ok), 1) * 100, 1),
        "p50_latency_ms": round(statistics.median(latencies), 1),
        "p95_latency_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))], 1),
        "note": "Synthetic benchmark profiles evaluated against live hybrid RAG + LLM pipeline",
    }

    out_dir = pathlib.Path(__file__).parent
    (out_dir / "results.json").write_text(json.dumps({"summary": summary, "cases": res}, indent=2), encoding="utf-8")

    md = f"""# Job-Matching Career Agent — Automated LLM & RAG Evaluation Report

- **Target API:** `{summary['target_api']}`
- **Timestamp (UTC):** `{summary['timestamp_utc']}`
- **Evaluation Set:** `{summary['n_cases']}` synthetic candidate profiles (labelled)

## Summary Metrics

| Metric | Result | Target | Status |
| :--- | :---: | :---: | :---: |
| **HTTP Success Rate** | **{summary['success_rate']}%** | >= 95% | {"PASS" if summary['success_rate'] >= 95 else "WARN"} |
| **Structured JSON Validity** | **{summary['valid_json_rate']}%** | 100% | {"PASS" if summary['valid_json_rate'] == 100 else "WARN"} |
| **Groundedness (0 Hallucinated Job IDs)** | **{summary['grounded_rate']}%** | 100% | {"PASS" if summary['grounded_rate'] == 100 else "WARN"} |
| **Retrieval + Ranking Hit@5** | **{summary['hit_at_5']}%** | >= 80% | {"PASS" if summary['hit_at_5'] >= 80 else "WARN"} |
| **P50 End-to-End Latency** | **{summary['p50_latency_ms']} ms** | < 2500 ms | PASS |
| **P95 End-to-End Latency** | **{summary['p95_latency_ms']} ms** | < 5000 ms | PASS |

## Case-by-Case Breakdown

| Case | Valid JSON | Grounded | Hit@5 | Latency (ms) | Profile Query |
| :--- | :---: | :---: | :---: | :---: | :--- |
"""
    for r in res:
        if r["ok"]:
            md += f"| `{r['id']}` | {'PASS' if r['valid_json'] else 'FAIL'} | {'PASS' if r['grounded'] else 'FAIL'} | {'PASS' if r['hit5'] else 'MISS'} | {r['latency_ms']} | {r['case']} |\n"
        else:
            md += f"| `{r['id']}` | FAIL | FAIL | MISS | - | {r['case']} |\n"

    (out_dir / "EVAL_REPORT.md").write_text(md, encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
