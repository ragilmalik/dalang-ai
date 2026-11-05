"""The small helper scripts (make_qr, make_sample_story, compress_images, seed_gallery) are imported and run
against a temp directory, so no tracked file in the repo is touched."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"script_{name}", ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_make_qr_uses_given_url_and_writes_png(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mod = load("make_qr")
    out = tmp_path / "qr.png"
    seen: dict[str, str] = {}

    def fake_save(url: str, path: Path) -> Path:
        seen["url"] = url
        out.write_bytes(mod.qr.png_bytes(url))
        return out

    monkeypatch.setattr(mod.qr, "save", fake_save)
    assert mod.main(["https://example.org/dalang"]) == 0
    assert seen["url"] == "https://example.org/dalang"
    assert "PLACEHOLDER" not in capsys.readouterr().out
    with Image.open(out) as im:
        assert im.format == "PNG" and im.width == im.height


def test_make_qr_flags_the_placeholder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mod = load("make_qr")
    monkeypatch.setattr(mod.qr.settings, "public_base_url", "")
    monkeypatch.setattr(mod.qr, "save", lambda url, path: tmp_path / "x.png")
    assert mod.main([]) == 1
    out = capsys.readouterr().out
    assert "No public link yet" in out and "dalang-ai.example" not in out


def test_make_sample_story_reports_tts_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mod = load("make_sample_story")
    monkeypatch.setattr(mod, "OUT", tmp_path / "a" / "story.mp3")

    def fail(*a: object, **k: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["edge_tts"], 1, "", "network down")

    monkeypatch.setattr(mod.subprocess, "run", fail)
    assert mod.main() == 1
    assert "network down" in capsys.readouterr().out
    assert (tmp_path / "a").is_dir()


def test_make_sample_story_success_says_synthetic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mod = load("make_sample_story")
    monkeypatch.setattr(mod, "OUT", tmp_path / "story.mp3")
    calls: list[list[str]] = []

    def ok(cmd: list[str], **k: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(mod.subprocess, "run", ok)
    assert mod.main() == 0
    cmd = calls[0]
    assert mod.VOICE in cmd and "--pitch=+0Hz" in cmd and "--write-media" in cmd and str(tmp_path / "story.mp3") in cmd
    assert "synthetic sample voice" in capsys.readouterr().out


def test_compress_images_shrinks_a_noisy_png_and_keeps_size(tmp_path: Path) -> None:
    mod = load("compress_images")
    import random
    rnd = random.Random(7)
    im = Image.new("RGB", (160, 160))
    im.putdata([(rnd.randrange(0, 256, 32), rnd.randrange(0, 256, 32), rnd.randrange(0, 256, 32)) for _ in range(160 * 160)])
    p = tmp_path / "shot.png"
    im.save(p)
    before, after = mod.shrink(p)
    assert after <= before
    with Image.open(p) as out:
        assert out.size == (160, 160)
    assert not p.with_suffix(".tmp.png").exists()


def test_compress_images_never_grows_a_small_png(tmp_path: Path) -> None:
    mod = load("compress_images")
    p = tmp_path / "flat.png"
    Image.new("RGB", (32, 32), (10, 20, 30)).save(p, optimize=True)
    before, after = mod.shrink(p)
    assert after <= before
    with Image.open(p) as out:
        assert out.size == (32, 32)
    assert not p.with_suffix(".tmp.png").exists()


def test_compress_images_targets_exist() -> None:
    mod = load("compress_images")
    assert mod.TARGETS and all(t.suffix == ".png" and t.exists() for t in mod.TARGETS)


def test_seed_gallery_exit_codes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    mod = load("seed_gallery")
    from api import samples

    class Job:
        def __init__(self, status: str) -> None:
            self.id = "abc"
            self.s = {"status": status, "title": "T", "sample_key": "kancil"}

    monkeypatch.setattr(samples, "seed", lambda: [Job("done")])
    monkeypatch.setenv("FAKE_META", "1")  # main() sets it; setenv makes pytest restore the original
    assert mod.main([]) == 0
    assert "kancil" in capsys.readouterr().out
    monkeypatch.setattr(samples, "seed", lambda: [Job("done"), Job("failed")])
    assert mod.main([]) == 1
    monkeypatch.setattr(samples, "seed", lambda: [])
    assert mod.main([]) == 0
    assert "already in the gallery" in capsys.readouterr().out
