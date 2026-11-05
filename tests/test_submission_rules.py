"""Hard rules from the hackathon form, checked against the shipped files."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "docs" / "demo"


def _secs(stamp: str) -> float:
    h, m, rest = stamp.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _cues() -> list[tuple[float, float, str]]:
    text = (DEMO / "dalang-ai-demo.srt").read_text(encoding="utf-8")
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        a, b = lines[1].split(" --> ")
        out.append((_secs(a.strip()), _secs(b.strip()), " ".join(lines[2:])))
    return out


def _video_seconds() -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        str(DEMO / "dalang-ai-demo.mp4")], capture_output=True, text=True, check=True)
    return float(r.stdout)


def test_demo_video_is_within_the_three_minute_limit() -> None:
    assert 60 <= _video_seconds() <= 180


def test_captions_are_ordered_and_inside_the_video() -> None:
    cues = _cues()
    assert len(cues) >= 20
    total = _video_seconds()
    prev_end = 0.0
    for start, end, text in cues:
        assert text.strip()
        assert 0 <= start < end <= total + 0.5, (start, end)
        assert start >= prev_end - 0.01, "caption overlaps the previous one"
        assert end - start <= 8, f"caption stays on screen too long: {text!r}"
        prev_end = end


def test_caption_reading_speed_is_comfortable() -> None:
    for start, end, text in _cues():
        clean = re.sub(r"\{[^}]*\}", "", text)
        cps = len(clean) / (end - start)
        assert cps <= 28, f"too fast to read ({cps:.0f} chars/s): {clean!r}"


def test_tagline_fits_the_form_limit() -> None:
    text = (ROOT / "docs" / "SUBMISSION.md").read_text(encoding="utf-8")
    m = re.search(r"## Tagline[^\n]*\n(.+)", text)
    assert m and 10 <= len(m.group(1).strip()) <= 100


def test_form_notes_cover_every_field_in_order() -> None:
    text = (ROOT / "docs" / "SUBMISSION_FORM.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| (\d+) \|", text, flags=re.M)
    assert rows == [str(i) for i in range(1, 15)]
    for needle in ("Indie Developer Track", "Build for Your World", "Nov 5, 09:00 WIB"):
        assert needle in text


def test_submission_lists_every_meta_model_the_code_calls() -> None:
    text = (ROOT / "docs" / "SUBMISSION.md").read_text(encoding="utf-8")
    for model in ("muse-voice-transcribe-1.0", "muse-spark-1.3", "muse-spark-1.2", "muse-image-1.0",
                  "sam-3.1", "muse-wonder-1.0"):
        assert model in text, model


def test_tagline_and_no_unverified_json_claim() -> None:
    tag = "A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film."
    assert tag in (ROOT / "docs" / "SUBMISSION.md").read_text(encoding="utf-8")
    assert tag in (ROOT / "README.md").read_text(encoding="utf-8")
    assert tag in (ROOT / "web" / "app" / "layout.tsx").read_text(encoding="utf-8")
    for p in [ROOT / "README.md", ROOT / "README.id.md", *(ROOT / "docs").glob("*.md")]:
        low = p.read_text(encoding="utf-8").lower()
        assert "constrained decoding" not in low and "guarantees valid json" not in low, p.name


def test_x_launch_times_follow_the_us_clock_change() -> None:
    text = (ROOT / "docs" / "X_LAUNCH.md").read_text(encoding="utf-8")
    assert "20:00 WIB (08:00 ET)" in text and "X_CAMPAIGN.md" in text
    assert "8:30 ET" not in text  # 19:30 WIB was 8:30 EDT; after Nov 1 it is 07:30 EST
