"""Docs quote numbers (tests, e2e steps, coverage, demo length) from one source: docs/facts.json."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import facts  # noqa: E402


def test_docs_agree_with_facts_json():
    assert facts.stale(facts.rendered(facts.load())) == []


def test_rewrite_only_touches_marked_text():
    text = "We run <!-- facts:tests -->1<!-- /facts --> tests and 7 other things."
    assert facts.rewrite(text, {"tests": "130"}) == "We run <!-- facts:tests -->130<!-- /facts --> tests and 7 other things."


def test_marker_names_may_contain_digits():
    assert facts.rewrite("<!-- facts:e2e -->1/1<!-- /facts -->", {"e2e": "23/23"}) == "<!-- facts:e2e -->23/23<!-- /facts -->"


def test_demo_length_rendered_as_minutes_and_seconds():
    assert facts.rendered({"demo_seconds": 143.4, "coverage": 80})["demo_length"] == "2:23"
    assert facts.rendered({"coverage": 80})["coverage"] == "80%"


def test_e2e_count_read_from_log(tmp_path):
    log = tmp_path / "e2e.log"
    log.write_text("PASS a\n\n12/13 passed\n...\n22/22 passed\nsmoke exit 0\n")
    assert facts.e2e_from_log(log) == "22/22"


def test_a11y_checks_counts_page_rows():
    assert facts.a11y_checks() == facts.load()["a11y"]
