"""API input validation: every refusal is a clean 4xx with a message, never a 500, and nothing is created.
These tests never start the pipeline, so they are fast."""
import pytest
from fastapi.testclient import TestClient

from api import main
from api.config import settings
from api.jobs import Job

client = TestClient(main.app, raise_server_exceptions=False)


def _job(status: str, public: bool = False) -> Job:
    job = Job.create("id", "classic", review=True)
    job.set(status=status, public=public)
    return job


def _count() -> int:
    d = settings.data_dir / "jobs"
    return len(list(d.glob("*"))) if d.exists() else 0


def test_new_film_refusals_create_nothing():
    before = _count()
    cases = [
        {"data": {"text": "Kancil dan buaya.", "language": "fr"}},
        {"data": {"language": "id"}},
        {"data": {"text": "   ", "language": "id"}},
        {"data": {"text": "Kancil dan buaya.", "language": "id", "narration_voice": "robot"}},
    ]
    for case in cases:
        r = client.post("/api/jobs", **case)
        assert r.status_code == 400, case
        assert r.json()["detail"]
    r = client.post("/api/jobs", data={"text": "Kancil.", "returning": "abc", "family_id": "x"})
    assert r.status_code == 400  # a short family id cannot bring puppets back
    assert _count() == before


@pytest.mark.parametrize("jid", ["nope", "abc", "a" * 40, "..%2F..", "ab cd", "zzzzzzzz"])
def test_unknown_or_malformed_film_ids_are_404(jid):
    for method, path in [("get", f"/api/jobs/{jid}"), ("get", f"/api/jobs/{jid}/trace"),
                         ("post", f"/api/jobs/{jid}/approve"), ("post", f"/api/jobs/{jid}/applause"),
                         ("get", f"/api/jobs/{jid}/puppets.pdf")]:
        assert getattr(client, method)(path).status_code == 404, path


def test_actions_in_the_wrong_state_are_409():
    done = _job("done")
    waiting = _job("review")
    assert client.post(f"/api/jobs/{done.id}/approve").status_code == 409
    assert client.post(f"/api/jobs/{waiting.id}/choice", data={"text": "ke hutan"}).status_code == 409
    assert client.post(f"/api/jobs/{done.id}/scenes/1", json={"narration": "x"}).status_code == 409
    assert client.post(f"/api/jobs/{waiting.id}/share", json={"public": True}).status_code == 409
    assert Job.get(waiting.id).s["status"] == "review"  # nothing moved


def test_scene_edit_and_choice_bodies_are_checked():
    waiting = _job("review")
    assert client.post(f"/api/jobs/{waiting.id}/scenes/99", json={"narration": "x"}).status_code == 404
    assert client.post(f"/api/jobs/{waiting.id}/scenes/1", json={"narration": 5}).status_code == 422
    asking = _job("choice")
    assert client.post(f"/api/jobs/{asking.id}/choice", data={"text": "  "}).status_code == 400
    assert Job.get(asking.id).s["status"] == "choice"


def test_applause_only_counts_for_public_finished_films():
    private = _job("done", public=False)
    assert client.post(f"/api/jobs/{private.id}/applause").status_code == 404
    public = _job("done", public=True)
    first = client.post(f"/api/jobs/{public.id}/applause", headers={"x-forwarded-for": "203.0.113.5"}).json()
    again = client.post(f"/api/jobs/{public.id}/applause", headers={"x-forwarded-for": "203.0.113.5"}).json()
    other = client.post(f"/api/jobs/{public.id}/applause", headers={"x-forwarded-for": "198.51.100.9"}).json()
    assert (first["applause"], again["applause"], other["applause"]) == (1, 1, 2)
    assert again["repeat"] is True and "repeat" not in other  # one Sembah per visitor per film


def test_feedback_is_validated_and_keeps_no_extra_fields():
    job = _job("done")
    ok = {"job_id": job.id, "rating": 5, "comment": "x" * 900, "page": "film"}
    assert client.post("/api/feedback", json=ok).json()["thanks"] is True
    for bad in ({**ok, "rating": 0}, {**ok, "rating": 6}, {**ok, "page": "admin"}, {**ok, "job_id": "missing1"}):
        assert client.post("/api/feedback", json=bad).status_code in {400, 404}, bad
    assert client.post("/api/feedback", json={"job_id": job.id, "rating": "lots"}).status_code == 422
    summary = client.get("/api/feedback/summary").json()
    assert "xxxx" not in str(summary) and summary["count"] >= 1  # counts only, never the comment text


def test_kotak_needs_a_valid_family_and_known_files():
    assert client.get("/api/kotak", params={"family": "short"}).status_code == 400
    assert client.delete("/api/kotak/abc", params={"family": "short"}).status_code == 400
    fam = "fam_0123456789ab"
    assert client.delete("/api/kotak/abc", params={"family": fam}).status_code == 404
    assert client.get(f"/api/kotak/{fam}/not-a-puppet.png").status_code == 404
    assert client.get(f"/api/kotak/{fam}/{'0' * 12}.png").status_code == 404
    body = {"family_id": fam, "job_id": _job("running").id, "char_id": "kancil"}
    assert client.post("/api/kotak", json=body).status_code == 409  # not carved yet


def test_qr_only_points_at_our_own_site():
    for bad in ("https://evil.example", "//evil.example", "watch/abc", "/" + "a" * 130):
        assert client.get("/api/qr.png", params={"path": bad}).status_code == 400, bad
    ok = client.get("/api/qr.png", params={"path": "/watch/abc123"})
    assert ok.status_code == 200 and ok.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_health_reports_the_mode_without_leaking_secrets():
    r = client.get("/api/health")
    assert r.status_code == 200
    text = r.text.lower()
    assert "api_key" not in text and "secret" not in text
