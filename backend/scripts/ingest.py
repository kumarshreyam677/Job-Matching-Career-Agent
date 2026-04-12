"""Ingest jobs -> embeddings -> pgvector. Run locally from backend/:
  DATABASE_URL=<neon_url> python -m scripts.ingest --file data/sample_jobs.csv
  DATABASE_URL=<neon_url> python -m scripts.ingest --hf <hf_dataset_id> --limit 30000
"""
import argparse
import csv
import hashlib
import os
import pathlib

import psycopg
from pgvector.psycopg import register_vector

COLS = {
    "title": ["title", "job_title", "position"],
    "company": ["company", "company_name", "employer"],
    "location": ["location", "job_location", "city"],
    "description": ["description", "job_description", "text", "summary"],
    "url": ["url", "job_url", "apply_url", "link"],
    "id": ["id", "job_id", "uuid"],
}


def pick(row, names):
    for n in names:
        if n in row and row[n] not in (None, ""):
            return str(row[n])
    return ""


def rows_from_args(a):
    if a.file:
        if a.file.endswith(".csv"):
            with open(a.file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= a.limit:
                        break
                    yield row
        else:
            import pandas as pd
            df = pd.read_parquet(a.file)
            yield from df.head(a.limit).to_dict("records")
    else:
        from datasets import load_dataset
        ds = load_dataset(a.hf, split="train", streaming=True)
        for i, r in enumerate(ds):
            if i >= a.limit:
                break
            yield r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--hf")
    ap.add_argument("--limit", type=int, default=30000)
    a = ap.parse_args()

    from app import retrieval

    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url, autocommit=True) as c:
        c.execute(pathlib.Path(__file__).with_name("schema.sql").read_text())
        register_vector(c)
        batch = []

        def flush():
            if not batch:
                return
            vecs = retrieval.embed(
                [f"{b['title']} at {b['company']} ({b['location']}). {b['description'][:1200]}" for b in batch]
            )
            with c.cursor() as cur:
                cur.executemany(
                    "INSERT INTO jobs(id,title,company,location,description,url,embedding) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                    [
                        (b["id"], b["title"], b["company"], b["location"], b["description"][:2500], b["url"], v)
                        for b, v in zip(batch, vecs)
                    ],
                )
            print(f"Inserted {len(batch)} jobs...")
            batch.clear()

        for r in rows_from_args(a):
            d = {k: pick(r, v) for k, v in COLS.items()}
            if not d["title"] or not d["description"]:
                continue
            d["id"] = d["id"] or hashlib.md5((d["title"] + d["company"] + d["description"][:200]).encode()).hexdigest()
            batch.append(d)
            if len(batch) >= 64:
                flush()
        flush()
    print("Ingestion complete!")


if __name__ == "__main__":
    main()
