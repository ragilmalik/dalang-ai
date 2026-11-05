from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "docs" / "demo"


def test_demo_files_present():
    for name in ("dalang-ai-demo.mp4", "dalang-ai-demo.srt", "voiceover.txt"):
        assert (DEMO / name).stat().st_size > 0


def test_no_em_dash_in_voiceover():
    assert "\u2014" not in (DEMO / "voiceover.txt").read_text(encoding="utf-8")


def test_storyboard_and_vtt_present():
    assert (DEMO / "STORYBOARD.md").read_text(encoding="utf-8").count("storyboard/") >= 9
    assert (DEMO / "storyboard.jpg").stat().st_size > 0
    assert (DEMO / "dalang-ai-demo.vtt").read_text(encoding="utf-8").startswith("WEBVTT")


def test_mock_sample_story_recording_is_labelled_and_playable() -> None:
    import subprocess

    mp3 = ROOT / "assets" / "sample-story" / "sample_story_synthetic.mp3"
    assert mp3.exists() and "synthetic" in mp3.name
    assert "not a real child" in (mp3.parent / "README.md").read_text(encoding="utf-8")
    secs = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                                capture_output=True, text=True, check=True).stdout)
    assert 10 < secs < 90


def test_demo_seed_accepts_audio(tmp_path) -> None:
    import os
    import subprocess
    import sys

    mp3 = ROOT / "assets" / "sample-story" / "sample_story_synthetic.mp3"
    r = subprocess.run([sys.executable, "scripts/demo_seed.py", "--audio", str(mp3)], cwd=ROOT,
                       env={**os.environ, "DATA_DIR": str(tmp_path)}, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    assert "muse-voice-transcribe-1.0" in r.stdout  # the recording went through speech-to-text, not typed text
    assert (tmp_path / "demo" / "dalang_landscape.mp4").exists()


def test_make_demo_video_takes_audio_flag() -> None:
    src = (ROOT / "scripts" / "make_demo_video.py").read_text(encoding="utf-8")
    assert '"--audio"' in src and "set_input_files" in src and "sample_story_synthetic.mp3" in src


def test_launch_clips_are_vertical_and_15_to_30_seconds() -> None:
    import json
    import subprocess

    clips = sorted((ROOT / "docs" / "launch").glob("clip*.mp4"))
    assert len(clips) == 3
    for c in clips:
        info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                          "stream=width,height:format=duration", "-of", "json", str(c)],
                                         capture_output=True, text=True, check=True).stdout)
        w, h = info["streams"][0]["width"], info["streams"][0]["height"]
        assert (w, h) == (720, 1280)
        assert 15 <= float(info["format"]["duration"]) <= 30
        assert c.with_suffix(".srt").exists()


def test_x_launch_plan_covers_nov_1_to_8_and_both_languages() -> None:
    text = (ROOT / "docs" / "X_LAUNCH.md").read_text(encoding="utf-8")
    for day in range(1, 9):
        assert f"Nov {day}**" in text
    assert "#DalangCilik" in text and "Tantangan" in text and "Alt text" in text
    assert "Nothing here has been posted" in text
    for v in ("Post A", "Post B", "Post C"):
        assert v in text


def test_demo_captions_use_written_forms_and_no_orphan_words(monkeypatch) -> None:
    import importlib.util
    import sys
    from pathlib import Path

    monkeypatch.setattr(sys, "argv", ["make_demo_video.py"])
    path = Path(__file__).resolve().parents[1] / "scripts" / "make_demo_video.py"
    spec = importlib.util.spec_from_file_location("make_demo_video_t", path)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    cues = [c for _k, line in m.SCRIPT for c in m.caption_chunks(line)]
    text = " ".join(cues)
    assert "SAM 3.1" in text and "Muse Spark 1.2" in text and "three point one" not in text and "one point" not in text
    assert all(2 <= len(c.split()) <= m.MAX_CAPTION_WORDS for c in cues)
    assert any(k == "trace" for k, _ in m.SCRIPT)


def test_demo_v2_shot_order_real_footage_and_honest_voice(monkeypatch, tmp_path) -> None:
    import importlib.util
    import sys
    from pathlib import Path

    monkeypatch.setattr(sys, "argv", ["make_demo_video.py", "--real", str(tmp_path)])
    path = Path(__file__).resolve().parents[1] / "scripts" / "make_demo_video.py"
    spec = importlib.util.spec_from_file_location("make_demo_video_v2", path)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    keys = [k for k, _ in m.SCRIPT]
    assert keys[:5] == ["voice", "opening", "film1", "garagara", "film2"]  # child's voice, then the film, then how
    assert keys.index("progress") > keys.index("film2") and keys[-1] == "close"
    assert (m.W, m.H) == (1920, 1080)
    assert set(m.REAL_CLIPS.values()) <= set(keys)
    assert all("I'm Malik" not in line and "I built" not in line for _k, line in m.SCRIPT)  # synthetic voice never claims to be him
    assert "I'm Malik" in m.REAL_LINES["why"]
    assert m.real_clip("garagara") is None
    (tmp_path / "C_garagara_answer.mov").write_bytes(b"x")
    (tmp_path / "vo_progress.m4a").write_bytes(b"x")
    assert m.real_clip("garagara") == tmp_path / "C_garagara_answer.mov"
    assert m.real_file("vo_progress", m.VO_EXTS) == tmp_path / "vo_progress.m4a"
    readme = (Path(__file__).resolve().parents[1] / "docs" / "demo" / "real" / "README.md").read_text(encoding="utf-8")
    for stem in m.REAL_CLIPS:
        assert stem in readme


def _load_demo_module(monkeypatch, tmp_path, name: str):  # type: ignore[no-untyped-def]
    import importlib.util
    import sys
    from pathlib import Path

    monkeypatch.setattr(sys, "argv", ["make_demo_video.py", "--real", str(tmp_path)])
    monkeypatch.setenv("DEMO_TMP", str(tmp_path / "demo_tmp"))
    monkeypatch.setenv("DEMO_OUT", str(tmp_path / "out"))
    path = Path(__file__).resolve().parents[1] / "scripts" / "make_demo_video.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_end_card_has_no_placeholder_text_and_names_the_public_repo(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """The close card once said 'Live app link: added after deploy (PLACEHOLDER)' and '(planned)' for the repo.
    The repo is public now, so the card names it plainly and shows no placeholder line when nothing is deployed."""
    src = (Path(__file__).resolve().parents[1] / "scripts" / "make_demo_video.py").read_text(encoding="utf-8")
    end = src[src.index("def end_card"):src.index("def end_card") + 1500]
    assert "PLACEHOLDER" not in end and "(planned)" not in end
    assert "github.com/ragilmalik/dalang-ai" in end


def test_gamelan_bed_is_audible_and_exact_length(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """App shots get a soft gamelan bed instead of dead air (the Kelir Live and close shots outlast their lines)."""
    import shutil
    import subprocess

    import pytest

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    m = _load_demo_module(monkeypatch, tmp_path, "make_demo_video_bed")
    out = m.gamelan_bed(3.0, tmp_path / "bed.wav", seed=1)
    assert abs(m.probe_seconds(out) - 3.0) < 0.1
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(out), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    mean = float(r.stderr.split("mean_volume:")[1].split("dB")[0])
    assert mean > -45.0  # audible, not silence (anullsrc reads about -91 dB)
    assert not (tmp_path / "bed.gamelan.wav").exists()  # its scratch file is cleaned up
