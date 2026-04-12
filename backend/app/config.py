import os


class S:
    database_url = os.getenv("DATABASE_URL", "")
    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    embed_model = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")  # 384 dims
    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
    top_k = int(os.getenv("TOP_K", "20"))
