import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
import pytest
from pydantic import ValidationError

from app.schemas import RecJob, Recs


def test_valid_rec():
    Recs(summary="ok", jobs=[RecJob(job_id="a", match_score=80, reason="fits")])


def test_score_bounds():
    with pytest.raises(ValidationError):
        RecJob(job_id="a", match_score=150, reason="x")
