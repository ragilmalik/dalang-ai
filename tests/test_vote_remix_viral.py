"""Gara-gara audience vote, Remix (other language / villain's view, same puppets), stickers + GIF, aksara."""
import io
import time
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api import aksara, runner
from api.jobs import Job
from api.main import app
from api.pipeline import mock

client = TestClient(app)


def wait(jid, statuses, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] in statuses:
            return j
        time.sleep(0.3)
    raise AssertionError(f"timeout, last status {j['status']}")


@pytest.fixture(scope="module")
def film():
    job = Job.create("id", "classic", False)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " remix source")
    assert job.s["status"] == "done", job.s.get("error")
    return job


# ---------------------------------------------------------------- vote
def test_vote_flow_picks_the_branch():
    j = client.post("/api/jobs", data={"text": mock.SAMPLE_TRANSCRIPT + " vote", "language": "id", "review": "false",
                                       "gara_gara": "true"}).json()
    j = wait(j["id"], {"choice", "failed", "done"})
    assert j["status"] == "choice", j.get("error")
    jid = j["id"]
    v = client.get(f"/api/jobs/{jid}/vote").json()
    assert v["status"] == "open" and v["total"] == 0 and len(v["options"]) == 2 and v["question"]
    assert client.post(f"/api/jobs/{jid}/vote/close").status_code == 409  # nobody voted yet
    for voter, opt in (("a", 0), ("b", 1), ("c", 1), ("a", 1)):  # "a" changes their mind
        r = client.post(f"/api/jobs/{jid}/vote", json={"option": opt, "voter": voter})
        assert r.status_code == 200
    assert r.json()["tally"] == [0, 3] and r.json()["total"] == 3
    assert client.post(f"/api/jobs/{jid}/vote", json={"option": 2}).status_code == 400
    c = client.post(f"/api/jobs/{jid}/vote/close").json()
    assert c["winner"] == 1 and c["answer"] == v["options"][1]
    done = wait(jid, {"done", "failed"})
    assert done["status"] == "done", done.get("error")
    assert done["gara_gara"]["answer"] == v["options"][1]
    assert any(e.get("agent") == "vote" for e in done["trace"])
    assert client.get(f"/api/jobs/{jid}/vote").json()["status"] == "closed"
    assert client.post(f"/api/jobs/{jid}/vote", json={"option": 0}).status_code == 409


def test_vote_is_off_for_a_film_without_gara_gara(film):
    assert client.get(f"/api/jobs/{film.id}/vote").json()["status"] == "off"
    assert client.post(f"/api/jobs/{film.id}/vote", json={"option": 0}).status_code == 409


# ---------------------------------------------------------------- remix
def _remix_calls(j):
    return [e for e in j["trace"] if e.get("kind") == "call"]


def test_remix_in_english_reuses_every_picture(film):
    r = client.post(f"/api/jobs/{film.id}/remix", json={"language": "en", "pov": "original"})
    assert r.status_code == 202
    rid = r.json()["id"]
    j = wait(rid, {"done", "failed"})
    assert j["status"] == "done", j.get("error")
    assert j["remix_of"] == film.id and j["language"] == "en" and j["script"]["language"] == "en"
    models = {e["model"] for e in _remix_calls(j)}
    assert models <= {"muse-spark-1.3"}, models  # only words: no Muse Image, SAM or Muse Wonder
    assert all(s["narration"].startswith("[English]") for s in j["script"]["scenes"])
    assert j["director"] == film.s["director"]
    assert all(st["status"] == "done" for st in j["stages"])
    assert rid in Job.get(film.id).s["remixes"]
    assert j["receipt"]["usd"] < film.s["receipt"]["usd"]


def test_remix_from_the_villains_point_of_view(film):
    rid = client.post(f"/api/jobs/{film.id}/remix", json={"language": "id", "pov": "villain"}).json()["id"]
    j = wait(rid, {"done", "failed"})
    assert j["status"] == "done", j.get("error")
    villain = j["remix"]["villain"]
    assert villain and all(villain in s["narration"] for s in j["script"]["scenes"])
    assert "told by" in j["title"]


@pytest.mark.parametrize("body,code", [
    ({"language": "id", "pov": "original"}, 400),  # same language, same view: nothing to remix
    ({"language": "fr", "pov": "original"}, 400),
    ({"language": "en", "pov": "hero"}, 400),
])
def test_remix_rejects_requests_that_cannot_work(film, body, code):
    assert client.post(f"/api/jobs/{film.id}/remix", json=body).status_code == code


def test_remix_needs_a_finished_film():
    job = Job.create("id", "classic", True)
    assert client.post(f"/api/jobs/{job.id}/remix", json={"language": "en"}).status_code == 409


# ---------------------------------------------------------------- stickers + gif
def test_sticker_pack_is_whatsapp_ready(film):
    r = client.get(f"/api/jobs/{film.id}/stickers")
    assert r.status_code == 200
    items = r.json()["stickers"]
    assert len(items) >= 3
    for it in items:
        path = film.dir / "stickers" / f"{it['id']}.webp"
        im = Image.open(path)
        assert im.format == "WEBP" and im.size == (512, 512) and im.mode == "RGBA"
        assert im.getpixel((0, 0))[3] == 0  # transparent corner
        assert path.stat().st_size <= 100_000
    z = client.get(f"/api/jobs/{film.id}/stickers.zip")
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "tray.png" in names and "README.txt" in names and sum(n.endswith(".webp") for n in names) == len(items)
    assert Image.open(film.dir / "stickers" / "tray.png").size == (96, 96)


def test_gif_loop(film):
    r = client.get(f"/api/jobs/{film.id}/loop.gif")
    assert r.status_code == 200 and r.headers["content-type"] == "image/gif"
    im = Image.open(io.BytesIO(r.content))
    assert im.width <= 480 and getattr(im, "n_frames", 1) > 5 and len(r.content) < 4_000_000


def test_viral_not_ready_is_409():
    job = Job.create("id", "classic", True)
    assert client.get(f"/api/jobs/{job.id}/stickers").status_code == 409
    assert client.get(f"/api/jobs/{job.id}/stickers.zip").status_code == 409
    assert client.get(f"/api/jobs/{job.id}/loop.gif").status_code == 409


def test_sticker_pack_fills_a_small_cast_with_a_title(tmp_path, film):
    job = Job.create("id", "classic", True)
    (job.dir / "puppets").mkdir()
    Image.open(film.dir / "puppets" / f"{film.s['cast'][0]['id']}.png").save(job.dir / "puppets" / "solo.png")
    job.set(cast=[{"id": "solo", "name": "Solo"}], title="Satu Wayang")
    items = client.get(f"/api/jobs/{job.id}/stickers").json()["stickers"]
    assert [i["id"] for i in items] == ["solo", "title"] or len(items) >= 2
    assert any(i["id"] == "title" for i in items)


# ---------------------------------------------------------------- aksara
@pytest.mark.parametrize("latin,javanese", [
    ("Hanacaraka", "\ua9b2\ua9a4\ua995\ua9ab\ua98f"),
    ("Timun Mas", "\ua9a0\ua9b6\ua9a9\ua9b8\ua9a4\ua9c0 \ua9a9\ua9b1\ua9c0"),
    ("buaya", "\ua9a7\ua9b8\ua9ae\ua9aa"),  # bu-wa-ya
    ("yang", "\ua9aa\ua981"),  # final ng -> cecak
    ("pasar", "\ua9a5\ua9b1\ua982"),  # final r -> layar
    ("krama", "\ua98f\ua9bf\ua9a9"),  # cakra
    ("Toko 25.", "\ua9a0\ua9ba\ua9b4\ua98f\ua9ba\ua9b4 \ua9d2\ua9d5\ua9c9"),
    ("\u2728", ""),
])
def test_aksara_transliteration(latin, javanese):
    assert aksara.transliterate(latin) == javanese


def test_title_card_and_font_endpoint(film):
    assert film.s["title_aksara"] == aksara.transliterate(Job.get(film.id).s["script"]["title"])
    h = client.get("/api/health").json()
    assert h["fonts"]["javanese"] is True and "resilience" in h
    r = client.get("/api/fonts/NotoSansJavanese.ttf")
    assert r.status_code == 200 and len(r.content) > 50_000
