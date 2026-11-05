"""Family testing kit: feedback widget storage and counts. The testimonials feature was removed on 2026-11-05 (it
only ever held sample quotes, not real people), so there is no endpoint and no quotes file."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app
from api.pipeline import mock

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_feedback_is_stored_and_summarised():
    j = client.post("/api/jobs", data={"text": mock.SAMPLE_TRANSCRIPT, "review": "true"}).json()
    before = client.get("/api/feedback/summary").json()
    assert client.post("/api/feedback", json={"job_id": j["id"], "rating": 5, "comment": "seru!"}).status_code == 200
    assert client.post("/api/feedback", json={"job_id": j["id"], "rating": 3, "page": "watch"}).status_code == 200
    assert client.post("/api/feedback", json={"job_id": j["id"], "rating": 9}).status_code == 400
    assert client.post("/api/feedback", json={"job_id": j["id"], "rating": 4, "page": "x"}).status_code == 400
    assert client.post("/api/feedback", json={"job_id": "nope", "rating": 4}).status_code == 404
    s = client.get("/api/feedback/summary").json()
    assert s["count"] == before["count"] + 2
    assert s["by_rating"]["5"] == before["by_rating"]["5"] + 1 and s["with_comment"] >= 1
    assert "seru" not in json.dumps(s), "the public summary has counts only, no comments"


def test_testimonials_feature_is_gone():
    assert client.get("/api/testimonials").status_code == 404
    assert not (ROOT / "content" / "testimonials.json").exists()
    assert not (ROOT / "web" / "components" / "Testimonials.tsx").exists()


def test_user_testing_doc_marks_every_sample():
    text = (ROOT / "docs" / "USER_TESTING.md").read_text(encoding="utf-8")
    assert "Real sessions: 0" in text and "MOCK" not in text and "PLACEHOLDER" not in text
    assert "not reviewed yet" in (ROOT / "docs" / "CULTURAL_REVIEW.md").read_text(encoding="utf-8")
