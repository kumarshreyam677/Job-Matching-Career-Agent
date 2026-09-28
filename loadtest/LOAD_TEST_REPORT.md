# Job-Matching Career Agent — 1,000-User Synthetic Load Test Report

- **Target Deployment:** `http://127.0.0.1:8000`
- **Timestamp (UTC):** `2026-09-28 04:19:01 UTC`
- **Traffic Profile:** `1000` simulated user sessions (labelled synthetic load test; 90% hybrid `/search` + 10% LLM `/chat`)
- **Total Wall-Clock Duration:** `63.62 seconds`

## Observed Throughput & Latency

| Metric | Observed Value |
| :--- | :---: |
| **Total Simulated User Sessions** | **1000** |
| **HTTP 200 Success Rate** | **90.2%** (902 / 1000) |
| **Sustained Throughput** | **15.72 req/sec** |
| **Overall P50 Latency** | **573.3 ms** |
| **Overall P95 Latency** | **940.0 ms** |
| **Hybrid Vector+FTS `/search` P50** | **573.2 ms** |
| **Full Agentic LLM `/chat` P50** | **7973.4 ms** |

## Live PostgreSQL Telemetry (`/metrics/summary`)
```json
{
  "queries": {
    "queries": 31,
    "sessions": 21,
    "p50_ms": 5893.0,
    "p95_ms": 10199.0,
    "valid_json_rate": 1.0,
    "grounded_rate": 1.0
  },
  "feedback": {
    "total_ratings": 0,
    "up_rate": 0.0
  }
}
```
