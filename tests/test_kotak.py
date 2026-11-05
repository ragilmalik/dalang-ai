"""Kotak Wayang: keep a family's SAM cut-outs and bring them back in the next story without redrawing them."""
import time

from fastapi.testclient import TestClient

from api import fake_meta, kotak
from api.main import app
from api.pipeline import lakon, mock
from api.schemas import Script

client = TestClient(app)
FAM = "fam_test_0123456789abcdef"


def wait(jid, statuses, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] in statuses:
            return j
        time.sleep(0.3)
    raise AssertionError(j["status"])


def test_family_id_is_required_and_validated():
    assert client.get("/api/kotak", params={"family": "short"}).status_code == 400
    assert client.get("/api/kotak", params={"family": FAM + "x"}).json() == []
    r = client.post("/api/jobs", data={"text": mock.SAMPLE_TRANSCRIPT, "returning": "abc"})
    assert r.status_code == 400


def test_save_list_bring_back_and_delete():
    j = client.post("/api/jobs", data={"text": mock.SAMPLE_TRANSCRIPT, "language": "id", "review": "true"}).json()
    j = wait(j["id"], {"review", "failed"})
    assert j["status"] == "review"
    r = client.post("/api/kotak", json={"family_id": FAM, "job_id": j["id"], "char_id": "kancil"})
    assert r.status_code == 200, r.text
    saved = r.json()
    assert saved["name"] == "Si Kancil" and saved["note"]
    again = client.post("/api/kotak", json={"family_id": FAM, "job_id": j["id"], "char_id": "kancil"}).json()
    assert again["id"] == saved["id"], "saving the same puppet twice keeps one copy"
    assert client.post("/api/kotak", json={"family_id": FAM, "job_id": j["id"], "char_id": "nobody"}).status_code == 404
    box = client.get("/api/kotak", params={"family": FAM}).json()
    assert [p["id"] for p in box] == [saved["id"]]
    img = client.get(saved["cutout"])
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"
    other = "fam_other_0123456789abcdef"
    assert client.get(saved["cutout"].replace(FAM, other)).status_code == 404, "families never see each other's box"

    # a new story brings Kancil back: no new Muse Image drawing for Kancil, only for the crocodile
    fake_meta.CALLS.clear()
    j2 = client.post("/api/jobs", data={"text": "Kancil bertemu buaya lagi di sungai yang lain, lalu mereka bermain.",
                                        "language": "id", "review": "true", "family_id": FAM,
                                        "returning": saved["id"]}).json()
    assert j2["returning"][0]["id"] == saved["id"]
    j2 = wait(j2["id"], {"review", "failed"})
    assert j2["status"] == "review", j2.get("error")
    kancil = next(c for c in j2["cast"] if c["id"] == "kancil")
    assert kancil.get("returning") is True
    assert not any(c.get("returning") for c in j2["cast"] if c["id"] != "kancil")
    casting = next(s for s in j2["stages"] if s["key"] == "casting")
    assert "back from the Kotak Wayang" in casting["detail"]
    with open(kotak.folder(FAM) / f"{saved['id']}.png", "rb") as a:
        assert client.get(kancil["cutout"]).content == a.read(), "the same pixels come back"

    assert client.delete(f"/api/kotak/{saved['id']}", params={"family": FAM}).status_code == 200
    assert client.get("/api/kotak", params={"family": FAM}).json() == []
    assert client.delete(f"/api/kotak/{saved['id']}", params={"family": FAM}).status_code == 404


def test_lakon_prompt_lists_returning_puppets_and_cast_keeps_them():
    from api import prompts

    p = {"id": "x" * 12, "char_id": "kancil", "name": "Si Kancil", "archetype": "wayang animal", "kind": "animal",
         "look": "small golden mouse deer", "sam_phrase": "mouse deer puppet", "note": "n"}
    text = prompts.lakon_user("cerita", "id", [p])
    assert "Kotak Wayang" in text and 'id "kancil"' in text
    # the model renamed the id: it is mapped back by name; a missing puppet is added to the cast
    data = dict(mock.SAMPLE_SCRIPT)
    data["characters"] = [dict(c) for c in mock.SAMPLE_SCRIPT["characters"]]
    data["characters"][0]["id"] = "mousedeer"
    data["scenes"] = [dict(sc, characters=["mousedeer" if c == "kancil" else c for c in sc["characters"]],
                           staging=[dict(st, id="mousedeer" if st["id"] == "kancil" else st["id"]) for st in sc["staging"]])
                      for sc in mock.SAMPLE_SCRIPT["scenes"]]
    s = lakon.keep_returning(Script(**data), [p])
    assert s.characters[0].id == "kancil" and "kancil" in s.scenes[0].characters
    garuda = dict(p, char_id="garuda", name="Garuda", look="golden eagle")
    s2 = lakon.keep_returning(Script(**mock.SAMPLE_SCRIPT), [garuda])
    assert any(c.id == "garuda" for c in s2.characters) and "garuda" in s2.scenes[0].characters
