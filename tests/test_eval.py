"""Evaluation script (scripts/eval.py): scoring functions and one golden story end to end on the fake API."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("dalang_eval", Path(__file__).resolve().parents[1] / "scripts" / "eval.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)  # type: ignore[union-attr]


def test_six_golden_stories_two_per_language():
    langs = [c["lang"] for c in ev.GOLDEN]
    assert len(ev.GOLDEN) == 6 and all(langs.count(x) == 2 for x in ("id", "jv", "en"))


def test_language_detector_and_bounds():
    assert ev.detect("Si Kancil lapar dan ingin ke kebun yang hijau") == "id"
    assert ev.detect("Timun Mas mlayu lan nguncalake wiji sing ajaib ing alas") == "jv"
    assert ev.detect("The snail is really a princess and the house is clean") == "en"
    s = {"language": "en", "scenes": [{"narration": "word " * 40}, {"narration": "The snail and the river."}]}
    r = ev.score_script(s, "en")
    assert r["scenes"] == 2 and not r["scene_ok"] and r["narration_in_bounds"] == 0.5


def test_one_golden_story_scores_and_reports(tmp_path):
    row = ev.run_one(ev.GOLDEN[0])
    assert row["status"] == "review" and row["scene_ok"] and row["language_ok"]
    assert row["cultural_after"] == 1.0 and 0 < row["consistency"] <= 100
    tot = ev.totals([row])
    md = ev.report([row], tot, True)
    assert "fake Meta API" in md and "id-kancil-buaya" in md and "Character consistency" in md


def test_round5_gamelan_and_report_render():
    g = ev.eval_gamelan()
    assert g["renders"] == 14 and g["ok"] == 1.0 and g["slendro_equal_steps"] and g["pelog_tones"] == 7
    rb = {"rows": [{"stage": "images", "what": "Muse Image", "mode": "always", "completed": True, "graceful": True,
                    "fallbacks": 9, "retried": 9, "error": ""},
                   {"stage": "lakon", "what": "lakon writer", "mode": "always", "completed": False, "graceful": True,
                    "fallbacks": 0, "retried": 1, "error": "503"}],
          "once_completed": 1.0, "always_completed": 0.5, "graceful": 1.0}
    md = ev.report_r5({"director": {"valid": 1.0, "films": 6}, "gamelan": g, "remix": {"pass": 1.0, "cost_ratio": 0.1},
                       "vote": {"voters": 7, "tally": [3, 4], "applied": True, "film": "done"}, "robustness": rb,
                       "open": {"rows": [{"setup": "x", "calls": 2, "models": ["m"], "meta_billed_usd": 0,
                                          "valid_script": True}]}})
    assert "Failure test detail" in md and "stopped kindly" in md and "FAKE MODE" in md and "| Muse Image | always |" in md


def test_robustness_targets_are_injectable():
    from api import fake_meta

    names = {t for t, _, _ in ev.ROBUST_STAGES}
    assert {"images", "lakon", "motion_plan", "director", "sam-3.1", "asr"} <= names
    assert fake_meta._target("/v1/chat/completions", {"model": "muse-spark-1.3",
                                                      "response_format": {"json_schema": {"name": "director"}}}) == \
        ["chat", "director", "muse-spark-1.3"]
