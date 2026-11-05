"""The helper scripts Malik runs himself must keep working: the key check, the deploy pre-flight and the
generated prompts doc. Each runs as a real subprocess, the way he would run it, against the fake Meta API."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def run(args: list[str], env: dict[str, str] | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    full = {**os.environ, "PYTHONPATH": str(ROOT), **(env or {})}
    r = subprocess.run([sys.executable, *args], cwd=ROOT, env=full, capture_output=True, text=True, timeout=timeout)
    r.stdout = ANSI.sub("", r.stdout)
    return r


def check_lines(out: str) -> dict[str, bool]:
    """PASS/FAIL lines of check_keys.py, keyed by the check name."""
    lines: dict[str, bool] = {}
    for line in out.splitlines():
        m = re.match(r"(PASS|FAIL)\s+(.+?)(\s{2}|$)", line)
        if m:
            lines[m.group(2).strip()] = m.group(1) == "PASS"
    return lines


def test_check_keys_self_test_passes_every_meta_model(tmp_path: Path) -> None:
    r = run(["scripts/check_keys.py", "--self-test"], {"DATA_DIR": str(tmp_path), "USE_OPEN_WEIGHTS": "0"})
    checks = check_lines(r.stdout)
    meta = {k: v for k, v in checks.items() if not k.startswith("Narration voice")}
    names = " ".join(meta)
    for model in ("muse-spark-1.3", "muse-wonder-1.0", "muse-voice-transcribe-1.0", "muse-spark-1.2", "muse-image-1.0", "sam-3.1"):
        assert model in names, f"{model} not checked:\n{r.stdout}"
    assert all(meta.values()), r.stdout
    # the narration voice needs the internet; offline the whole run fails only because of it
    voice_ok = all(v for k, v in checks.items() if k.startswith("Narration voice"))
    assert (r.returncode == 0) == voice_ok, r.stdout


def test_check_keys_self_test_includes_open_weights_when_enabled(tmp_path: Path) -> None:
    r = run(["scripts/check_keys.py", "--self-test", "--no-image"],
            {"DATA_DIR": str(tmp_path), "USE_OPEN_WEIGHTS": "1", "BASETEN_API_KEY": "test-baseten"})
    checks = check_lines(r.stdout)
    open_checks = [v for k, v in checks.items() if k.startswith("Muse Spark Open")]
    assert open_checks == [True], r.stdout
    assert not any("muse-image" in k or "sam-3.1" in k for k in checks), "--no-image must skip the paid image calls"


def test_check_keys_without_a_key_explains_what_to_do(tmp_path: Path) -> None:
    r = run(["scripts/check_keys.py"], {"DATA_DIR": str(tmp_path), "META_API_KEY": "", "MODEL_API_KEY": "",
                                         "FAKE_META": "0", "MOCK": "0"})
    if "Meta key:" in r.stdout:
        pytest.skip("a .env with a real key is present on this machine")
    assert r.returncode == 1
    assert "META_API_KEY" in r.stdout


def test_deploy_preflight_config_checks_pass() -> None:
    r = run(["scripts/deploy_preflight.py", "--skip-build"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FAIL" not in r.stdout
    for item in ("render.yaml parses", "health check path", "secrets are dashboard-only", "no .env committed"):
        assert item in r.stdout


def test_prompts_doc_is_up_to_date() -> None:
    doc = ROOT / "docs" / "prompts.md"
    before = doc.read_text(encoding="utf-8")
    try:
        r = run(["scripts/gen_prompts_doc.py"])
        assert r.returncode == 0, r.stderr
        after = doc.read_text(encoding="utf-8")
    finally:
        doc.write_text(before, encoding="utf-8")
    assert after == before, "docs/prompts.md is stale: run python scripts/gen_prompts_doc.py"


# ---------------------------------------------------------------- go_live (item: one command to go live)
def test_go_live_plan_lists_every_step() -> None:
    r = run(["scripts/go_live.py", "--dry-run", "--plan"])
    assert r.returncode == 0, r.stdout + r.stderr
    for step in ("keys", "seed", "clips", "build", "shots", "video", "storyboard", "kit"):
        assert f"  {step}" in r.stdout
    assert "check_keys.py --self-test" in r.stdout


def test_go_live_without_key_stops_with_instructions(tmp_path: Path) -> None:
    r = run(["scripts/go_live.py"], {"DATA_DIR": str(tmp_path), "META_API_KEY": "", "MODEL_API_KEY": "",
                                       "FAKE_META": "0", "MOCK": "0"})
    if "LIVE with your Meta key" in r.stdout and "No META_API_KEY" not in r.stdout:
        pytest.skip("a .env with a real key is present on this machine")
    assert r.returncode == 1 and "No META_API_KEY" in r.stdout


def test_go_live_rejects_unknown_step() -> None:
    assert run(["scripts/go_live.py", "--dry-run", "--steps", "keys,teleport"]).returncode == 2


def test_go_live_dry_run_keys_and_seed(tmp_path: Path) -> None:
    """The fake-mode dry run really runs the key self-test and regenerates the demo film."""
    r = run(["scripts/go_live.py", "--dry-run", "--steps", "keys,seed"],
            {"DATA_DIR": str(tmp_path), "USE_OPEN_WEIGHTS": "0"}, timeout=600)
    assert "PASS keys" in r.stdout or "Narration voice" in r.stdout, r.stdout[-2000:]
    assert "PASS seed" in r.stdout, r.stdout[-2000:]
    assert (tmp_path / "demo" / "dalang_landscape.mp4").exists()


def test_check_keys_self_test_checks_muse_glimmer_when_open_weights(tmp_path: Path) -> None:
    r = run(["scripts/check_keys.py", "--self-test", "--no-image"],
            {"DATA_DIR": str(tmp_path), "USE_OPEN_WEIGHTS": "1", "BASETEN_API_KEY": "b", "GLIMMER_API_KEY": "g"})
    checks = check_lines(r.stdout)
    assert [v for k, v in checks.items() if k.startswith("Muse Glimmer")] == [True], r.stdout


def test_submission_kit_builds_with_structure_and_placeholder_warning(tmp_path: Path) -> None:
    out = tmp_path / "submission-kit"
    r = run(["scripts/make_submission_kit.py", "--out", str(out)], timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    for d in ("1-video", "2-images", "3-sample-films", "4-text", "5-launch"):
        assert (out / d).is_dir(), d
    assert (out / "dalang-ai-source.zip").stat().st_size > 10_000
    assert not (out / "2-images" / "qr.png").exists()  # no QR until PUBLIC_BASE_URL is a real deployed link
    readme = (out / "README.txt").read_text(encoding="utf-8")
    assert "1-video/" in readme and "5-launch/" in readme and "MOCK" in readme
    zpath = tmp_path / "submission-kit.zip"
    assert zpath.exists() and zpath.stat().st_size > 10_000
    import zipfile

    names = zipfile.ZipFile(zpath).namelist()
    assert "submission-kit/README.txt" in names
    src = zipfile.ZipFile(out / "dalang-ai-source.zip").namelist()
    assert "dalang-ai/api/main.py" in src and not any(n.endswith("/.env") for n in src)
    assert "testimonial" not in readme.lower()


# ---------------------------------------------------------------- go_live --preflight
def test_go_live_preflight_dry_run_passes_every_model() -> None:
    r = run(["scripts/go_live.py", "--preflight", "--dry-run"], {"FAKE_META_FAIL": ""})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Preflight PASS: 6/6" in r.stdout
    for model in ("muse-voice-transcribe-1.0", "muse-spark-1.3", "muse-spark-1.2", "muse-wonder-1.0",
                  "muse-image-1.0", "sam-3.1"):
        assert f"PASS {model}" in r.stdout


def test_go_live_preflight_names_the_failing_model_and_the_fix() -> None:
    r = run(["scripts/go_live.py", "--preflight", "--dry-run"], {"FAKE_META_FAIL": "images:always",
                                                                   "META_RETRIES": "0"})
    assert r.returncode == 1
    assert "FAIL muse-image-1.0" in r.stdout and "What to do:" in r.stdout and "Preflight FAIL: 5/6" in r.stdout


def test_go_live_preflight_live_without_key_stops() -> None:
    r = run(["scripts/go_live.py", "--preflight"], {"META_API_KEY": "", "MODEL_API_KEY": "", "FAKE_META": "0"})
    assert r.returncode == 1 and "No META_API_KEY" in r.stdout
    assert "--preflight --dry-run" in r.stdout  # points at the free rehearsal
