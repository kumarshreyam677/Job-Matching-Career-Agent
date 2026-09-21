"""Synthetic 1,000-User Traffic Simulator for Live Render Deployment.
Simulates 1,000 user sessions across /search and /chat, then fetches live PostgreSQL telemetry
from /metrics/summary to generate loadtest/LOAD_TEST_REPORT.md.
Run: python loadtest/run_1000_users.py --api https://YOUR-API.onrender.com --users 1000
"""
import argparse
import concurrent.futures
import json
import pathlib
import random
import statistics
import time
import uuid
from datetime import datetime, timezone

import requests

QUERIES = [
    "python backend fastapi postgresql docker",
    "llm agents rag embeddings vector search",
    "react typescript frontend developer",
    "search engineer bm25 ranking pgvector",
    "devops kubernetes ci cd cloud",
    "data analyst sql dashboards",
    "machine learning document intelligence",
    "software engineer intern python api",
]


def simulate_session(api: str, idx: int):
    sid = f"synth_user_{idx:04d}_{uuid.uuid4().hex[:6]}"
    q = random.choice(QUERIES)
    t0 = time.perf_counter()
    try:
        # 90% hybrid search traffic + 10% full LLM agent chat traffic (respects free-tier Groq RPM limits)
        if idx % 10 == 0:
            r = requests.post(
                f"{api}/chat",
                json={"session_id": sid, "message": f"I have skills in {q}. Recommend matching roles."},
                timeout=45,
            )
            endpoint = "/chat"
        else:
            r = requests.get(f"{api}/search", params={"q": q, "k": 10}, timeout=20)
            endpoint = "/search"
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"ok": r.status_code == 200, "status": r.status_code, "ms": ms, "endpoint": endpoint}
    except Exception:
        return {"ok": False, "status": 0, "ms": round((time.perf_counter() - t0) * 1000, 1), "endpoint": "error"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--users", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()

    api = a.api.rstrip("/")
    print(f"Warming up {api}/health ...")
    requests.get(f"{api}/health", timeout=60)

    print(f"Simulating {a.users} synthetic user sessions (workers={a.workers})...")
    t_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futures = [ex.submit(simulate_session, api, i) for i in range(1, a.users + 1)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    total_s = round(time.perf_counter() - t_start, 2)

    ok = [r for r in results if r["ok"]]
    search_ms = sorted(r["ms"] for r in ok if r["endpoint"] == "/search") or [0]
    chat_ms = sorted(r["ms"] for r in ok if r["endpoint"] == "/chat") or [0]
    all_ms = sorted(r["ms"] for r in ok) or [0]

    db_metrics = {}
    try:
        m = requests.get(f"{api}/metrics/summary", timeout=15)
        if m.ok:
            db_metrics = m.json()
    except Exception:
        pass

    success_rate = round(len(ok) / a.users * 100, 2)
    rps = round(a.users / max(total_s, 0.1), 2)
    p50 = round(statistics.median(all_ms), 1)
    p95 = round(all_ms[min(len(all_ms) - 1, int(len(all_ms) * 0.95))], 1)
    search_p50 = round(statistics.median(search_ms), 1)
    chat_p50 = round(statistics.median(chat_ms), 1)

    report = f"""# CareerPilot AI — 1,000-User Synthetic Load Test Report

- **Target Deployment:** `{api}`
- **Timestamp (UTC):** `{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}`
- **Traffic Profile:** `{a.users}` simulated user sessions (labelled synthetic load test; 90% hybrid `/search` + 10% LLM `/chat`)
- **Total Wall-Clock Duration:** `{total_s} seconds`

## Observed Throughput & Latency

| Metric | Observed Value |
| :--- | :---: |
| **Total Simulated User Sessions** | **{a.users}** |
| **HTTP 200 Success Rate** | **{success_rate}%** ({len(ok)} / {a.users}) |
| **Sustained Throughput** | **{rps} req/sec** |
| **Overall P50 Latency** | **{p50} ms** |
| **Overall P95 Latency** | **{p95} ms** |
| **Hybrid Vector+FTS `/search` P50** | **{search_p50} ms** |
| **Full Agentic LLM `/chat` P50** | **{chat_p50} ms** |

## Live PostgreSQL Telemetry (`/metrics/summary`)
```json
{json.dumps(db_metrics, indent=2)}
```
"""

    out_path = pathlib.Path(__file__).parent / "LOAD_TEST_REPORT.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"Done! Success={success_rate}% | RPS={rps} | P50={p50}ms | P95={p95}ms -> saved {out_path}")


if __name__ == "__main__":
    main()
