"""Stage 4 (puppet cut-out): SAM masks become transparent PNGs, with fallbacks when SAM finds nothing or fails."""
import numpy as np
import pytest
from PIL import Image

from api import cost, meta_client
from api.jobs import Job
from api.pipeline import puppet, segment


def sheet(path, size=(120, 90), bg=(240, 230, 200), fg=(20, 20, 20), box=(40, 20, 80, 70)):
    im = Image.new("RGB", size, bg)
    im.paste(fg, box)
    im.save(path)
    return path


def match(left, top, right, bottom, confidence=0.9, filled=True):
    mw, mh = right - left, bottom - top
    mask = (np.ones if filled else np.zeros)((mh, mw), dtype=np.uint8).tobytes()
    return {"left": left, "top": top, "right": right, "bottom": bottom, "confidence": confidence,
            "mask": mask, "mw": mw, "mh": mh}


def test_sam_mask_becomes_a_trimmed_transparent_cutout(tmp_path):
    src = sheet(tmp_path / "sheet.png")
    out = puppet.cutout_from_sam(src, [match(40, 20, 80, 70)], tmp_path / "p.png")
    assert out is not None
    im = Image.open(out)
    assert im.mode == "RGBA"
    assert im.width <= 40 + 12 + 2 and im.height <= 50 + 12 + 2  # trimmed to the puppet plus padding
    assert im.getpixel((im.width // 2, im.height // 2))[3] > 200  # the middle is solid
    assert im.getpixel((0, 0))[3] < 50  # the padding is transparent


def test_no_matches_or_empty_masks_give_no_cutout(tmp_path):
    src = sheet(tmp_path / "sheet.png")
    assert puppet.cutout_from_sam(src, [], tmp_path / "a.png") is None
    assert puppet.cutout_from_sam(src, [match(40, 20, 80, 70, filled=False)], tmp_path / "b.png") is None
    assert not (tmp_path / "a.png").exists() and not (tmp_path / "b.png").exists()


def test_touching_confident_part_is_kept_but_far_or_unsure_ones_are_not(tmp_path):
    src = sheet(tmp_path / "sheet.png", size=(200, 100))
    main = match(20, 10, 80, 90)
    rod = match(70, 0, 100, 40, confidence=0.8)       # overlaps the main box: kept
    far = match(150, 10, 190, 50, confidence=0.9)     # separate box: dropped
    unsure = match(60, 10, 90, 50, confidence=0.3)    # overlaps but low confidence: dropped
    out = puppet.cutout_from_sam(src, [main, rod, far, unsure], tmp_path / "p.png")
    assert out is not None
    # kept area spans x 20..100 (80 px) plus padding, so the far piece (x up to 190) is not in the crop
    assert 80 <= Image.open(out).width <= 80 + 12 + 2


def test_degenerate_box_is_skipped(tmp_path):
    src = sheet(tmp_path / "sheet.png")
    bad = {"left": 50, "top": 50, "right": 50, "bottom": 60, "confidence": 0.9, "mask": b"", "mw": 0, "mh": 0}
    assert puppet.cutout_from_sam(src, [bad], tmp_path / "p.png") is None


def test_background_key_removes_the_plain_paper(tmp_path):
    src = sheet(tmp_path / "sheet.png")
    out = puppet.cutout_by_background(src, tmp_path / "p.png")
    im = Image.open(out)
    assert im.mode == "RGBA" and im.width < 120 and im.height < 90
    assert im.getpixel((im.width // 2, im.height // 2))[3] > 200


def make_job() -> Job:
    return Job.create("id", "classic", True)


def test_cut_puppet_uses_sam_when_it_finds_the_phrase(tmp_path, monkeypatch):
    job = make_job()
    src = sheet(tmp_path / "sheet.png")
    queries: list[str] = []

    def fake(_img, query):
        queries.append(query)
        return [match(40, 20, 80, 70)]

    monkeypatch.setattr(meta_client, "segment", fake)
    out = segment.cut_puppet(job, src, "mouse deer puppet", "kancil")
    assert out == job.dir / "puppets" / "kancil.png" and out.exists()
    assert queries == ["mouse deer puppet"]


def test_cut_puppet_retries_with_puppet_then_falls_back_to_background(tmp_path, monkeypatch):
    job = make_job()
    src = sheet(tmp_path / "sheet.png")
    queries: list[str] = []

    def nothing(_img, query):
        queries.append(query)
        return []

    monkeypatch.setattr(meta_client, "segment", nothing)
    out = segment.cut_puppet(job, src, "odd phrase", "buaya")
    assert queries == ["odd phrase", "puppet"]
    assert out.exists() and Image.open(out).mode == "RGBA"


def test_cut_puppet_survives_a_sam_error(tmp_path, monkeypatch):
    job = make_job()
    src = sheet(tmp_path / "sheet.png")

    def boom(_img, _query):
        raise RuntimeError("503 from SAM")

    monkeypatch.setattr(meta_client, "segment", boom)
    assert segment.cut_puppet(job, src, "x", "semar").exists()


def test_cut_puppet_lets_a_budget_stop_through(tmp_path, monkeypatch):
    job = make_job()
    src = sheet(tmp_path / "sheet.png")

    def over(_img, _query):
        raise cost.BudgetExceeded("over budget")

    monkeypatch.setattr(meta_client, "segment", over)
    with pytest.raises(cost.BudgetExceeded):
        segment.cut_puppet(job, src, "x", "semar")
