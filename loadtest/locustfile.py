"""SYNTHETIC load test (not real users). Run:
  locust -f loadtest/locustfile.py --host https://YOUR-API.onrender.com -u 100 -r 10 -t 2m --headless --csv loadtest/out
Free LLM tiers rate-limit: use /search for high concurrency, /chat at lower concurrency."""
import random
import uuid

from locust import HttpUser, between, task

QUERIES = [
    "python backend fastapi",
    "react frontend developer",
    "llm rag engineer",
    "data analyst sql",
    "devops docker kubernetes",
    "search ranking pgvector",
    "ai agents tool use",
]


class User(HttpUser):
    wait_time = between(1, 3)

    @task(6)
    def search(self):
        self.client.get("/search", params={"q": random.choice(QUERIES), "k": 10})

    @task(1)
    def chat(self):
        self.client.post(
            "/chat",
            json={"session_id": str(uuid.uuid4()), "message": f"Looking for {random.choice(QUERIES)} roles"},
        )
