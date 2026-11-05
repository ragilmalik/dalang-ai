"""Stage 6 (animate) and stage 7 (narrate): motion fallbacks, the Muse Wonder plan, partial re-renders, the child's voice."""

import pytest
from PIL import Image

from api import meta_client
from api.config import settings
from api.jobs import Job
from api.pipeline import animate, engine, media, mock, narrate, scenes
from api.schemas import Script


def script() -> Script:
    return Script(**mock.SAMPLE_SCRIPT)


def make_job() -> Job:
    return Job.create("id", "classic", True)


def stage(job, key):
    return next(s for s in job.s["stages"] if s["key"] == key)


def with_motion(sc, text):
    sc = sc.model_copy(deep=True)
    sc.motion_prompt = text
    return sc


# ---------------------------------------------------------------- animate: fallback_plan
def test_fallback_plan_covers_every_staged_puppet_and_validates():
    from api.schemas import MotionPlan
    for sc in script().scenes:
        plan = animate.fallback_plan(sc)
        MotionPlan(**plan)
        assert {p["id"] for p in plan["puppets"]} == {st.id for st in sc.staging}


@pytest.mark.parametrize("words,minimum,peak", [
    ("the hero will jump over the log", 4, "lift"),
    ("a deep bow to the king", 4, "angle"),
    ("the bird can fly away", 3, "lift"),
    ("gentle sway", 2, None),
])
def test_fallback_plan_motion_words(words, minimum, peak):
    sc = with_motion(script().scenes[1], words)
    plan = animate.fallback_plan(sc)
    frames = plan["puppets"][0]["keyframes"]
    assert len(frames) == minimum
    if peak:
        assert any(f[peak] != 0 for f in frames)
    assert [f["t"] for f in frames] == sorted(f["t"] for f in frames)


def test_fallback_plan_first_scene_enters_from_off_screen():
    sc = script().scenes[0]
    plan = animate.fallback_plan(with_motion(sc, "calm"))
    for tr, st in zip(plan["puppets"], sc.staging, strict=False):
        start = tr["keyframes"][0]["x"]
        assert start < 0 if st.facing == "right" else start > 1


def test_fallback_plan_tense_scene_first_puppet_trembles():
    sc = script().scenes[2].model_copy(deep=True)
    sc.mood = "tense"
    plan = animate.fallback_plan(sc)
    assert plan["puppets"][0]["idle"] == "tremble"
    assert all(p["idle"] == "sway" for p in plan["puppets"][1:])


# ---------------------------------------------------------------- animate: plan_scene
def job_with_still(sc):
    job = make_job()
    Image.new("RGB", (64, 36), (120, 60, 20)).save(job.dir / f"still_{sc.n}.jpg")
    return job


def test_plan_scene_keeps_model_plan_and_adds_missing_puppets(monkeypatch):
    s = script()
    sc = next(x for x in s.scenes if len(x.staging) >= 2)
    job = job_with_still(sc)
    first, second = sc.staging[0], sc.staging[1]
    raw = {"camera": {"zoom_from": 1.0, "zoom_to": 1.1, "pan_x": 0.1, "pan_y": 0.0}, "lamp_flicker": 0.5,
           "puppets": [{"id": first.id, "idle": "bob", "keyframes": [{"t": 0, "x": 0.2}]},
                       {"id": "ghost_not_on_stage", "idle": "sway", "keyframes": [{"t": 0, "x": 0.5}]}]}
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: raw)
    plan = animate.plan_scene(job, s, sc)
    ids = [p["id"] for p in plan["puppets"]]
    assert "ghost_not_on_stage" not in ids
    assert first.id in ids and second.id in ids
    assert settings.animate_model in job.s["models"]


def test_plan_scene_falls_back_when_the_model_fails(monkeypatch):
    s = script()
    sc = s.scenes[0]
    job = job_with_still(sc)

    def boom(*a, **k):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(meta_client, "chat_json", boom)
    plan = animate.plan_scene(job, s, sc)
    assert plan == animate.fallback_plan(sc)


def test_plan_scene_falls_back_on_invalid_plan(monkeypatch):
    s = script()
    sc = s.scenes[0]
    job = job_with_still(sc)
    monkeypatch.setattr(meta_client, "chat_json", lambda *a, **k: {"puppets": [{"id": "x", "keyframes": []}]})
    assert animate.plan_scene(job, s, sc) == animate.fallback_plan(sc)


# ---------------------------------------------------------------- animate: run (rendering stubbed)
@pytest.fixture
def stubbed_engine(monkeypatch):
    calls = {"encoded": []}
    monkeypatch.setattr(engine, "cover", lambda *a, **k: None)
    monkeypatch.setattr(engine, "Shot", lambda **k: k)
    monkeypatch.setattr(engine, "Film", lambda *a, **k: k)
    monkeypatch.setattr(engine, "Kelir", lambda film, pup: film)
    monkeypatch.setattr(scenes, "load_puppets", lambda *a, **k: {})

    def enc(kel, out, fps=12):
        out.write_bytes(b"mp4")
        calls["encoded"].append(out.name)
    monkeypatch.setattr(engine, "encode", enc)
    return calls


def test_run_plans_every_scene_and_saves_the_plans(monkeypatch, stubbed_engine):
    s = script()
    job = make_job()
    planned = []
    monkeypatch.setattr(animate, "plan_scene", lambda j, sc_, sc: planned.append(sc.n) or {"puppets": [], "n": sc.n})
    plans = animate.run(job, s)
    assert planned == [sc.n for sc in s.scenes] and len(plans) == len(s.scenes)
    assert (job.dir / "motion_1.json").exists()
    assert stage(job, "animate")["status"] == "done" and f"{len(plans)} scenes choreographed" in stage(job, "animate")["detail"]
    assert len(stubbed_engine["encoded"]) == len(plans)


def test_run_only_replans_chosen_scenes_and_reuses_the_rest(monkeypatch, stubbed_engine):
    s = script()
    job = make_job()
    monkeypatch.setattr(animate, "plan_scene", lambda j, sc_, sc: {"puppets": [], "n": sc.n, "v": 1})
    animate.run(job, s)
    stubbed_engine["encoded"].clear()
    monkeypatch.setattr(animate, "plan_scene", lambda j, sc_, sc: {"puppets": [], "n": sc.n, "v": 2})
    plans = animate.run(job, s, only={2})
    assert [p["v"] for p in plans] == [2 if p["n"] == 2 else 1 for p in plans]
    assert stubbed_engine["encoded"] == ["clip_2.mp4"]
    assert "reused" in stage(job, "animate")["detail"]


def test_run_rerenders_a_reused_scene_when_its_clip_is_missing(monkeypatch, stubbed_engine):
    s = script()
    job = make_job()
    monkeypatch.setattr(animate, "plan_scene", lambda j, sc_, sc: {"puppets": [], "n": sc.n})
    animate.run(job, s)
    (job.dir / "clip_1.mp4").unlink()
    stubbed_engine["encoded"].clear()
    monkeypatch.setattr(animate, "plan_scene", lambda j, sc_, sc: {"puppets": [], "n": sc.n} if sc.n == 3 else pytest.fail("saved plan must be reused"))
    animate.run(job, s, only={3})
    assert "clip_1.mp4" in stubbed_engine["encoded"]


# ---------------------------------------------------------------- narrate: child groups and plan
def turns(n, length=1000, gap=200):
    return [{"start_ms": i * (length + gap), "end_ms": i * (length + gap) + length, "text": f"kata {i}"} for i in range(n)]


def test_child_groups_need_one_turn_per_scene():
    assert narrate.child_groups(turns(3), 4) is None
    assert narrate.child_groups(turns(3), 0) is None


@pytest.mark.parametrize("n_turns,total", [(4, 4), (9, 5), (12, 6)])
def test_child_groups_cover_all_turns_in_order(n_turns, total):
    groups = narrate.child_groups(list(reversed(turns(n_turns))), total)
    assert groups is not None and len(groups) == total
    flat = [t for g in groups for t in g]
    assert len(flat) == n_turns and all(g for g in groups)
    assert [t["start_ms"] for t in flat] == sorted(t["start_ms"] for t in flat)


def test_child_plan_empty_unless_child_voice_with_recording():
    job = make_job()
    assert narrate.child_plan(job) == {}
    job.set(narration_voice="child", voice_turns=turns(5), voice_scene_total=5)
    assert narrate.child_plan(job) == {}  # no recording on disk
    narrate.recording(job).write_bytes(b"x")
    plan = narrate.child_plan(job)
    assert sorted(plan) == [1, 2, 3, 4, 5]


def test_child_plan_leaves_fresh_scenes_to_the_narrator():
    job = make_job()
    narrate.recording(job).write_bytes(b"x")
    job.set(narration_voice="child", voice_turns=turns(5), voice_scene_total=5, fresh_scenes=[4, 5])
    assert sorted(narrate.child_plan(job)) == [1, 2, 3]


def test_child_plan_empty_when_too_few_turns():
    job = make_job()
    narrate.recording(job).write_bytes(b"x")
    job.set(narration_voice="child", voice_turns=turns(2), voice_scene_total=5)
    assert narrate.child_plan(job) == {}


# ---------------------------------------------------------------- narrate: cut_child, voice_for
def test_cut_child_pads_and_returns_none_on_ffmpeg_error(monkeypatch, tmp_path):
    job = make_job()
    seen = []
    monkeypatch.setattr(media, "run", lambda args: seen.append(args))
    out = narrate.cut_child(job, turns(2), tmp_path / "a.wav")
    assert out == tmp_path / "a.wav"
    args = seen[0]
    assert args[args.index("-ss") + 1] == "0.000"  # padding never goes below zero
    assert "loudnorm" in args[args.index("-af") + 1]

    def bad(args):
        raise RuntimeError("ffmpeg failed")
    monkeypatch.setattr(media, "run", bad)
    assert narrate.cut_child(job, turns(2), tmp_path / "b.wav") is None


def test_voice_for_uses_child_words_and_records_the_line(monkeypatch):
    s = script()
    job = make_job()
    monkeypatch.setattr(narrate, "cut_child", lambda j, g, out: out)
    got = narrate.voice_for(job, s, s.scenes[0], {1: turns(2)})
    assert got is not None and got.name == "scene_1.wav"
    assert job.s["child_lines"]["1"] == "kata 0 kata 1"
    assert (job.dir / "voice" / "scene_1.txt").read_text().startswith("child:")


def test_voice_for_falls_back_to_tts_when_the_cut_fails(monkeypatch):
    s = script()
    job = make_job()
    monkeypatch.setattr(narrate, "cut_child", lambda j, g, out: None)
    monkeypatch.setattr(settings, "narration_voice", True)
    monkeypatch.setattr(media, "narrate", lambda text, lang, out: out)
    got = narrate.voice_for(job, s, s.scenes[0], {1: turns(2)})
    assert got is not None
    assert (job.dir / "voice" / "scene_1.txt").read_text() == s.scenes[0].narration


def test_voice_for_is_none_with_narration_switched_off(monkeypatch):
    s = script()
    monkeypatch.setattr(settings, "narration_voice", False)
    assert narrate.voice_for(make_job(), s, s.scenes[0], {}) is None


# ---------------------------------------------------------------- narrate: run
def test_run_tts_says_opening_and_each_scene(monkeypatch):
    s = script()
    job = make_job()
    monkeypatch.setattr(settings, "narration_voice", True)
    said = []
    monkeypatch.setattr(media, "narrate", lambda text, lang, out: said.append(out.name) or out)
    out = narrate.run(job, s)
    assert len([o for o in out if o]) == len(s.scenes)
    if s.opening:
        assert "opening.wav" in said
    assert "Narrated in" in stage(job, "narrate")["detail"]


def test_run_reuses_unchanged_lines_on_partial_rerender(monkeypatch):
    s = script()
    job = make_job()
    monkeypatch.setattr(settings, "narration_voice", True)
    said = []

    def fake(text, lang, out):
        said.append(out.name)
        out.write_bytes(b"w")
        return out
    monkeypatch.setattr(media, "narrate", fake)
    narrate.run(job, s)
    said.clear()
    s2 = s.model_copy(deep=True)
    s2.scenes[1].narration = "Kalimat baru untuk adegan dua."
    narrate.run(job, s2, only={2})
    assert said == ["scene_2.wav"]


def test_run_reports_subtitles_only_when_voice_unreachable(monkeypatch):
    s = script()
    job = make_job()
    monkeypatch.setattr(settings, "narration_voice", True)
    monkeypatch.setattr(media, "narrate", lambda text, lang, out: None)
    out = narrate.run(job, s)
    assert not any(out)
    assert "Subtitles only" in stage(job, "narrate")["detail"]


def test_run_child_voice_without_timestamps_says_so(monkeypatch):
    s = script()
    job = make_job()
    job.set(narration_voice="child")
    monkeypatch.setattr(settings, "narration_voice", True)
    monkeypatch.setattr(media, "narrate", lambda text, lang, out: out)
    narrate.run(job, s)
    assert "no speech timestamps" in stage(job, "narrate")["detail"]


def test_run_mixes_child_and_tts_voices(monkeypatch):
    s = script()
    job = make_job()
    narrate.recording(job).write_bytes(b"x")
    job.set(narration_voice="child", voice_turns=turns(len(s.scenes)), voice_scene_total=len(s.scenes),
            fresh_scenes=[len(s.scenes)])
    monkeypatch.setattr(settings, "narration_voice", True)
    monkeypatch.setattr(narrate, "cut_child", lambda j, g, out: out)
    monkeypatch.setattr(media, "narrate", lambda text, lang, out: out)
    narrate.run(job, s)
    detail = stage(job, "narrate")["detail"]
    assert f"{len(s.scenes) - 1} scene(s) in the child's own voice" in detail and "by " in detail
