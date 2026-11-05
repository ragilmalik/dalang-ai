"""The /docs page a judge opens: every endpoint grouped, summarised, with examples where a body is sent."""
from api.main import app


def test_every_operation_has_a_tag_and_summary():
    spec = app.openapi()
    ops = [(path, m, op) for path, item in spec["paths"].items() for m, op in item.items()]
    assert len(ops) >= 20
    for path, m, op in ops:
        assert op.get("tags") and op.get("summary"), f"{m.upper()} {path}"
    assert {t["name"] for t in spec["tags"]} >= {"films", "community", "kotak wayang"}
    assert "fake Meta API" in spec["info"]["description"]


def test_create_job_form_fields_are_described():
    spec = app.openapi()
    ref = spec["paths"]["/api/jobs"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    props = spec["components"]["schemas"][ref.split("/")[-1]]["properties"]
    for field in ("text", "language", "review", "gara_gara", "narration_voice"):
        assert props[field].get("description"), field
    assert spec["components"]["schemas"]["Share"]["examples"] == [{"public": True}]


def test_docs_are_also_under_api_for_the_website_proxy():
    """The judge page links /api/docs: the website forwards only /api and /media to the API."""
    from fastapi.testclient import TestClient

    c = TestClient(app)
    spec = c.get("/api/openapi.json")
    assert spec.status_code == 200 and spec.json()["info"]["title"] == "Dalang AI"
    assert "/api/docs" not in spec.json()["paths"] and "/api/openapi.json" not in spec.json()["paths"]
    page = c.get("/api/docs")
    assert page.status_code == 200 and "/api/openapi.json" in page.text and "swagger" in page.text.lower()
    assert c.get("/docs").status_code == 200
