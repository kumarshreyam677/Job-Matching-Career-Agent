from pydantic import BaseModel, Field


class ProfileQuery(BaseModel):
    """What the agent understood about the user (persisted in Postgres JSONB memory)."""
    search_query: str
    keywords: list[str] = []
    skills: list[str] = []
    location: str | None = None
    seniority: str | None = None


class RecJob(BaseModel):
    job_id: str
    match_score: int = Field(ge=0, le=100)
    reason: str
    missing_skills: list[str] = []


class Recs(BaseModel):
    summary: str
    jobs: list[RecJob]


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=2, max_length=6000)


class FeedbackRequest(BaseModel):
    session_id: str
    job_id: str
    rating: int = Field(ge=-1, le=1)  # -1 bad, 1 good
