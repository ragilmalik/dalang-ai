"""Dalang Director (Muse Spark shot plan -> engine) and the procedural gamelan score."""
import json
import subprocess

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api import cost, meta_client, runner
from api.jobs import Job
from api.main import app
from api.pipeline import director, engine, gamelan, mock
from api.schemas import Script

client = TestClient(app)
SCRIPT = Script(**mock.SAMPLE_SCRIPT)


@pytest.fixture
def meter():
    m = cost.Meter(5.0)
    cost.use(m)
    yield m
    cost.use(None)


def test_rules_give_one_shot_per_scene_with_sensible_cues():
    shots = director.rules(SCRIPT)
    assert [s.n for s in shots] == [sc.n for sc in SCRIPT.scenes]
    assert shots[0].gamelan == "gong" and shots[-1].gamelan == "suwuk" and shots[-1].transition == "fade"
    assert shots[0].enter  # everyone on stage in scene 1 enters
    tense = [s for s, sc in zip(shots, SCRIPT.scenes, strict=True) if sc.mood == "tense"]
    assert all(s.camera == "push_in" and any(e.kind == "keprak" for e in s.sfx) for s in tense)


def test_validation_repairs_model_output():
    raw = {"shots": [
        {"n": 1, "camera": "push_in", "enter": [{"id": "ghost", "side": "left"}], "exit": [], "transition": "cut",
         "gamelan": "gong", "sfx": [{"t": 3, "kind": "wind"}] * 5, "note": "x" * 500},
        {"n": 99, "camera": "still", "enter": [], "exit": [], "transition": "cut", "gamelan": "none", "sfx": [], "note": ""},
        {"n": 2, "camera": "zoom_crazy"},
    ]}
    shots, fixes = director._validate(raw, SCRIPT)
    assert len(shots) == len(SCRIPT.scenes)
    assert shots[0].enter == [] and len(shots[0].sfx) == 3 and shots[0].sfx[0].t == 1.0 and len(shots[0].note) == 200
    assert shots[-1].transition == "fade"
    assert any("ghost" in f for f in fixes) and any("invalid shot" in f for f in fixes)
    assert any("no shot planned" in f for f in fixes)


def test_apply_adds_entrances_exits_and_camera():
    motion = {"camera": {"zoom_from": 1, "zoom_to": 1.06, "pan_x": 0, "pan_y": 0}, "lamp_flicker": 0.4,
              "puppets": [{"id": "kancil", "idle": "sway", "keyframes": [{"t": 0, "x": 0.4, "lift": 0, "angle": 0,
                                                                         "facing": "right"},
                                                                        {"t": 1, "x": 0.5, "lift": 0, "angle": 0,
                                                                         "facing": "right"}]}]}
    shot = {"camera": "pan_left", "enter": [{"id": "kancil", "from": "left"}], "exit": [{"id": "kancil", "to": "right"}]}
    out = director.apply(motion, shot)
    kfs = out["puppets"][0]["keyframes"]
    assert out["camera"]["pan_x"] < 0
    assert kfs[0]["t"] == 0 and kfs[0]["x"] < 0  # starts off stage left
    assert kfs[1]["t"] == pytest.approx(director.ENTER_END)
    assert kfs[-1]["t"] == 1.0 and kfs[-1]["x"] > 1  # leaves off stage right
    assert motion["puppets"][0]["keyframes"][0]["x"] == 0.4  # the original plan is untouched
    below = director.apply(motion, {"camera": "still", "enter": [{"id": "kancil", "from": "below"}], "exit": []})
    assert below["puppets"][0]["keyframes"][0]["lift"] < 0
    x, lift, _, _ = engine.pose(out["puppets"][0], 0.0, 0.0, 0)
    assert x < 0


def test_director_call_and_fallback(meter, monkeypatch, tmp_path):
    job = Job.create("id", "classic", True)
    job.set(script=SCRIPT.model_dump())
    out = director.plan(job, SCRIPT)
    assert out["source"] == "muse-spark-1.3" and len(out["shots"]) == len(SCRIPT.scenes)
    assert out["shots"][0]["sfx"][0]["kind"] == "keprak"
    assert set(out["shots"][0]["enter"][0]) == {"id", "from"}
    assert any(e.get("agent") == "director" and "semar_extra" in e["text"] for e in meter.trace)
    assert json.loads((job.dir / "director.json").read_text()) == out

    def down(*a, **k):
        raise meta_client.MetaAPIError("503")

    monkeypatch.setattr(meta_client, "chat_json", down)
    out2 = director.plan(job, SCRIPT)
    assert out2["source"] == "rule-based fallback" and len(out2["shots"]) == len(SCRIPT.scenes)


def test_film_has_director_and_score_and_endpoint():
    job = Job.create("id", "classic", False)
    runner._front(job, None, mock.SAMPLE_TRANSCRIPT + " director")
    assert job.s["status"] == "done", job.s.get("error")
    d = client.get(f"/api/jobs/{job.id}/director").json()
    assert d["shots"] and d == job.s["director"]
    score = job.s["score"]
    assert score["scale"] in {"slendro", "pelog"}
    assert score["procedural"] is False and "CC BY 4.0" in score["recording"]  # the bundled Kraton recording
    other = Job.create("id", "classic", True)
    assert client.get(f"/api/jobs/{other.id}/director").status_code == 404


@pytest.mark.parametrize("mood", gamelan.MOOD_NAMES)
def test_every_mood_renders_bounded_audible_gamelan(mood):
    a = gamelan.render(mood, 4.0)
    assert len(a) == 4 * gamelan.SR and a.dtype == np.float32
    assert 0.05 < float(np.max(np.abs(a))) <= 0.51
    assert np.array_equal(a, gamelan.render(mood, 4.0))  # deterministic


def test_tunings_and_scale_override():
    sl, pe = gamelan.scale_hz("slendro"), gamelan.scale_hz("pelog")
    assert len(sl) == 5 and len(pe) == 7
    steps = np.diff(1200 * np.log2(sl))
    assert np.allclose(steps, 240)  # slendro: near-equal steps
    assert len(set(np.round(np.diff(1200 * np.log2(pe))))) > 2  # pelog: unequal steps
    st = gamelan.style_for("happy", "slendro")
    assert st.scale == "slendro" and max(st.balungan) <= 5
    assert not np.array_equal(gamelan.render("happy", 2.0), gamelan.render("happy", 2.0, scale="slendro"))


@pytest.mark.parametrize("kind", ["gong", "kempul", "kendang_rush", "bonang_run", "suwuk"])
def test_cues_render(kind):
    assert float(np.max(np.abs(gamelan.cue(kind)))) > 0.02


@pytest.mark.parametrize("kind", ["keprak", "cempala", "gong", "wind", "water", "birds"])
def test_sfx_render(kind):
    s = gamelan.sfx(kind)
    assert len(s) > 1000 and float(np.max(np.abs(s))) > 0.005
    assert gamelan.sfx("nonsense").size == 1


def test_gamelan_preview_endpoint():
    r = client.get("/api/gamelan/tense.wav?scale=pelog&seconds=3")
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content[:4] == b"RIFF"
    assert client.get("/api/gamelan/angry.wav").status_code == 400
    assert client.get("/api/gamelan/calm.wav?scale=diatonic").status_code == 400


def test_transitions_draw_differently():
    from PIL import Image

    g = Image.new("RGBA", (40, 120), (200, 50, 30, 255))
    bg = Image.new("RGB", (200, 120), (90, 90, 90))
    plan = {"camera": {}, "puppets": []}

    def frame(kind):
        film = engine.Film(160, 90, gunungan=g, shots=[
            engine.Shot(2.0, bg, plan, cue={"transition": kind}), engine.Shot(2.0, bg, plan)])
        return np.asarray(engine.Kelir(film, {}).frame(1.9).convert("RGB")).astype(int)

    sweep, rise, fade, cut = (frame(k) for k in ("gunungan_sweep", "gunungan_rise", "fade", "cut"))
    assert not np.array_equal(sweep, cut) and not np.array_equal(rise, cut) and fade.mean() < cut.mean()


# --- real recording bed (assets/music, CC BY 4.0) --------------------------------------------------------------
def test_recording_is_the_default_and_procedural_switch_works(monkeypatch):
    assert gamelan.source() == "recording"
    monkeypatch.setenv("GAMELAN_SOURCE", "procedural")
    assert gamelan.source() == "procedural"
    assert gamelan.summary(["calm"])["procedural"] is True and "recording" not in gamelan.summary(["calm"])


def test_missing_recordings_fall_back_to_procedural(monkeypatch, tmp_path):
    monkeypatch.setattr(gamelan, "MUSIC_DIR", tmp_path)
    assert gamelan.source() == "procedural"


@pytest.mark.parametrize("mood,name", [("calm", "kraton-yogyakarta-1.ogg"), ("night", "kraton-yogyakarta-1.ogg"),
                                       ("tense", "kraton-yogyakarta-2.ogg"), ("triumphant", "kraton-yogyakarta-2.ogg")])
def test_mood_picks_the_excerpt(mood, name):
    assert gamelan.recording_for(mood).name == name


def test_recorded_bed_is_exact_length_bounded_and_loops():
    x = gamelan.recorded("calm", 3.0, offset=10.0)
    assert len(x) == int(gamelan.SR * 3.0) and x.dtype == np.float32
    assert 0.005 < float(np.sqrt(np.mean(x ** 2))) < 0.2 and float(np.max(np.abs(x))) <= 0.95
    full = len(gamelan._decode(str(gamelan.recording_for("calm")))) / gamelan.SR
    y = gamelan.recorded("calm", 5.0, offset=full - 1.0)  # runs past the end: wraps to the start
    assert len(y) == int(gamelan.SR * 5.0) and float(np.max(np.abs(y[-gamelan.SR:]))) > 0


def test_decode_rejects_an_empty_file(tmp_path):
    bad = tmp_path / "empty.ogg"
    bad.write_bytes(b"")
    with pytest.raises((subprocess.CalledProcessError, ValueError)):
        gamelan._decode(str(bad))
