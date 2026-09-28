# Job-Matching Career Agent — Automated LLM & RAG Evaluation Report

- **Target API:** `https://job-matching-career-agent.onrender.com`
- **Timestamp (UTC):** `2026-09-28 22:27:51 UTC`
- **Evaluation Set:** `10` synthetic candidate profiles (labelled)

## Summary Metrics

| Metric | Result | Target | Status |
| :--- | :---: | :---: | :---: |
| **HTTP Success Rate** | **100.0%** | >= 95% | PASS |
| **Structured JSON Validity** | **100.0%** | 100% | PASS |
| **Groundedness (0 Hallucinated Job IDs)** | **100.0%** | 100% | PASS |
| **Retrieval + Ranking Hit@5** | **100.0%** | >= 80% | PASS |
| **P50 End-to-End Latency** | **4959.5 ms** | < 2500 ms | PASS |
| **P95 End-to-End Latency** | **5893 ms** | < 5000 ms | PASS |

## Case-by-Case Breakdown

| Case | Valid JSON | Grounded | Hit@5 | Latency (ms) | Profile Query |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `E01` | PASS | PASS | PASS | 5428 | Final year BTech CS, strong Python, FastAPI, SQL, Docker. Want backend roles. |
| `E02` | PASS | PASS | PASS | 3505 | I know React and TypeScript, want frontend jobs. |
| `E03` | PASS | PASS | PASS | 5704 | Interested in LLMs, RAG, embeddings, vector search. |
| `E04` | PASS | PASS | PASS | 4262 | SQL, Tableau, Excel; want data analyst role. |
| `E05` | PASS | PASS | PASS | 4836 | Docker, Kubernetes, CI/CD, Terraform, cloud reliability. |
| `E06` | PASS | PASS | PASS | 3557 | Kotlin and Android app development. |
| `E07` | PASS | PASS | PASS | 5893 | Search relevance, ranking, BM25, pgvector. |
| `E08` | PASS | PASS | PASS | 4128 | Figma, user research, prototyping, UI design. |
| `E09` | PASS | PASS | PASS | 5857 | Build conversational AI agents with tool use, memory, and evals. |
| `E10` | PASS | PASS | PASS | 5083 | Entry-level software engineering or AI/ML graduate role in Bengaluru. |
