CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  title TEXT,
  company TEXT,
  location TEXT,
  description TEXT,
  url TEXT,
  embedding vector(384),
  tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title,'')||' '||coalesce(company,'')||' '||coalesce(description,''))) STORED
);
CREATE INDEX IF NOT EXISTS jobs_tsv_idx ON jobs USING gin(tsv);
CREATE INDEX IF NOT EXISTS jobs_emb_idx ON jobs USING hnsw (embedding vector_cosine_ops);
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  profile JSONB,
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS feedback (
  id SERIAL PRIMARY KEY,
  session_id TEXT,
  job_id TEXT,
  rating INT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS query_log (
  id SERIAL PRIMARY KEY,
  session_id TEXT,
  latency_ms INT,
  n_candidates INT,
  n_results INT,
  valid_json BOOLEAN,
  grounded BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT now()
);
