"""Penjaga Budaya cultural review, character-consistency score, Meta models receipt (fake Meta API)."""
import json

from fastapi.testclient import TestClient

from api import cost, fake_meta, meta_client, runner
from api.config import settings
from api.jobs import Job
from api.main import app
from api.pipeline import consistency, mock, penjaga
from api.schemas import Script

client = TestClient(app)


def _script(**scene_over) -> Script:
    data = json.loads(json.dumps(mock.SAMPLE_SCRIPT))
    data["scenes"][0].update(scene_over)
    return Script(**data)


def test_rules_file_has_ids_guidance_and_canon():
    r = penjaga.rules()
    ids = penjaga.rule_ids()
    assert len(ids) == len(set(ids)) >= 8
    assert {"gentle-conflict", "no-politics", "respect-figures", "canon"} <= set(ids)
    assert all(x["guidance"] and x["fields"] for x in r["rules"])
    assert {"Kancil", "Semar", "Timun Mas"} <= {c["name"] for c in r["canon"]}
    assert "NOT yet reviewed" in r["status"]  # honest about the curation


def test_scan_finds_war_framing_and_canon_and_scrub_softens():
    data = _script(narration="Kancil memimpin pasukan dengan pedang.", action="War by the river.").model_dump()
    data["characters"].append({"id": "semar", "name": "Semar", "visual_description": "a stupid old clown",
                               "cultural_note": ""})
    hits = penjaga.scan(data)
    rules = {h["rule"] for h in hits}
    assert {"gentle-conflict", "respect-figures", "canon"} <= rules
    assert penjaga.scrub("Kancil memimpin pasukan dengan pedang.", "narration") == "Kancil memimpin rombongan dengan tongkat."
    assert penjaga.scrub("War by the river.", "action") == "Contest by the river."
    assert penjaga.scan({"scenes": [], "characters": []}) == []


def test_review_fixes_scene_before_drawing_and_records_trace():
    job = Job.create("id", "classic", True)
    meter = cost.Meter(5.0)
    cost.use(meter)
    try:
        out = penjaga.run(job, _script(narration="Kancil memimpin pasukan menyeberang sungai."))
    finally:
        cost.use(None)
    rep = job.s["cultural_review"]
    assert out.scenes[0].narration == "Kancil memimpin rombongan menyeberang sungai."
    assert "grumpy but not scary" in out.scenes[1].action  # the fixture's model judgement
    assert "rises from the river" in out.scenes[1].action  # the verify redraw fixture still keys on this
    assert rep["fixes"] >= 2 and rep["pass_rate_after"] == 1.0 and rep["pass_rate_first"] < 1.0
    assert rep["model"] == settings.culture_model
    assert {r["n"] for r in rep["scenes"]} == {s.n for s in out.scenes}
    calls = [e for e in meter.trace if e["kind"] == "call"]
    assert any("Penjaga Budaya" in e["purpose"] for e in calls)
    assert any(e["kind"] == "decision" and e["agent"] == "penjaga" for e in meter.trace)
    assert job.s["script"]["scenes"][0]["narration"] == out.scenes[0].narration


def test_review_survives_model_failure_with_word_scan(monkeypatch):
    def boom(*a, **k):
        raise meta_client.MetaAPIError("503")
    monkeypatch.setattr(meta_client, "chat_json", boom)
    job = Job.create("en", "classic", True)
    out = penjaga.run(job, _script(narration="The army marched with swords."))
    assert out.scenes[0].narration == "The group marched with sticks."
    assert job.s["cultural_review"]["model"] is None
    assert job.s["cultural_review"]["pass_rate_after"] == 1.0


def test_review_off_switch(monkeypatch):
    monkeypatch.setattr(settings, "cultural_review", False)
    job = Job.create("id", "classic", True)
    s = _script(narration="perang besar")
    assert penjaga.run(job, s) is s and "cultural_review" not in job.s


def test_full_film_has_review_consistency_and_receipt():
    job = Job.create("id", "classic", False)
    runner._front(job, None, "Si Kancil ingin menyeberang sungai yang penuh buaya.")
    s = job.s
    assert s["status"] == "done", s.get("error")
    assert s["cultural_review"]["pass_rate_after"] == 1.0
    con = s["consistency"]
    assert 0 < con["score"] <= 100 and con["puppets"]
    assert all(p["same_pixels"] and p["source"] == "sam" for p in con["puppets"])
    assert con["appearances"] >= len(con["puppets"])
    rec = s["receipt"]
    models = {r["model"]: r for r in rec["models"]}
    assert {"muse-spark-1.3", "sam-3.1"} <= set(models)  # Muse Image may be served from the prompt cache
    assert models["muse-spark-1.3"]["tokens_in"] > 0
    assert "muse-image-1.0" not in models or models["muse-image-1.0"]["images"] > 0
    assert rec["calls"] == s["trace_summary"]["calls"] and rec["estimate"] and rec["fake"]
    assert all(r["role"] for r in rec["models"])
    t = client.get(f"/api/jobs/{job.id}/trace").json()
    assert t["receipt"]["calls"] == rec["calls"] and t["cultural_review"] and t["consistency"]["score"] == con["score"]
    r = client.get(f"/api/jobs/{job.id}/receipt").json()
    assert r["models"] and r["consistency"]["puppets"]
    decisions = [e for e in s["trace"] if e["kind"] == "decision"]
    assert any(e["agent"] == "consistency" and "in the final film" in e["text"] for e in decisions)
    assert client.get("/api/jobs/zzzz9999/receipt").status_code == 404


def test_consistency_flags_changed_pixels_and_background_fallback(tmp_path):
    job = Job.create("id", "classic", True)
    script = Script(**mock.SAMPLE_SCRIPT)
    (job.dir / "puppets").mkdir(exist_ok=True)
    from PIL import Image
    cid = script.characters[0].id
    img = Image.new("RGBA", (100, 200), (0, 0, 0, 0))
    img.paste((200, 120, 40, 255), (20, 20, 80, 180))
    img.save(job.dir / "puppets" / f"{cid}.png")
    job.set(cast=[{"id": cid, "name": "Kancil", "rejections": [{"issue": "x"}]}], cutouts={cid: "background"})
    first = consistency.measure(job, script)
    row = first["puppets"][0]
    assert row["source"] == "background" and row["checker_redraws"] == 1 and row["same_pixels"]
    img.paste((10, 10, 10, 255), (30, 30, 40, 40))
    img.save(job.dir / "puppets" / f"{cid}.png")
    second = consistency.measure(job, script)
    assert second["puppets"][0]["same_pixels"] is False and second["score"] < first["score"]


def test_receipt_counts_open_weight_tokens_without_meta_price():
    m = cost.Meter(1.0)
    cost.use(m)
    try:
        cost.count_tokens("meta-models/muse-spark-open", {"prompt_tokens": 10, "completion_tokens": 5})
        cost.charge_tokens("muse-spark-1.3", {"input_tokens": 1000, "output_tokens": 100})
    finally:
        cost.use(None)
    assert m.tokens["meta-models/muse-spark-open"] == [10, 5] and m.tokens["muse-spark-1.3"] == [1000, 100]
    assert "meta-models/muse-spark-open" not in m.items
    rec = cost.receipt({"trace_summary": {"models": [], "decisions": 0}, "tokens": m.tokens, "cost_usd": 0.1})
    rows = {r["model"]: r for r in rec["models"]}
    assert rows["meta-models/muse-spark-open"]["open_weights"] and rec["tokens_in"] == 1010
    assert "open weights" in cost.role_of("meta-models/muse-spark-open")


def test_fake_reviewer_handles_missing_script_json():
    out = fake_meta._cultural_review("no script here")
    assert out["scenes"] == [] and out["characters"] == []


def test_storybook_pdf_a5_one_page_per_scene():
    job = Job.create("id", "classic", True)
    runner._front(job, None, "Si Kancil ingin menyeberang sungai.")
    assert job.s["status"] == "review"
    r = client.get(f"/api/jobs/{job.id}/storybook.pdf")
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"
    import re
    pages = len(re.findall(rb"/Type\s*/Page[^s]", r.content))
    assert pages == len(job.s["script"]["scenes"]) + 2  # cover + scenes + moral
    assert re.search(rb"/MediaBox\s*\[0 0 419\.5\d* 595\.2\d*\]", r.content), "A5 pages"
    early = Job.create("id", "classic", True)
    assert client.get(f"/api/jobs/{early.id}/storybook.pdf").status_code == 409
