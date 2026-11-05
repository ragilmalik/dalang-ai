"""Evaluation harness: 6 golden stories (2 per language) through the pipeline up to the storyboard, scored on
scene count, narration length bounds, language match, Penjaga Budaya cultural-rule pass rate and the
character-consistency score. Writes docs/EVAL_REPORT.md and docs/eval.json.

Runs on the built-in fake Meta API by default (no key, no cost): the scores then measure OUR pipeline code
(schema checks, cultural review, cut-outs, consistency scoring) on the fixture scripts, not Meta model quality.
With a real key and FAKE_META=0 the same harness scores live output (costs about $0.10-0.20 per story).

    .venv/bin/python scripts/eval.py            # all 6, writes the report
    .venv/bin/python scripts/eval.py --only 2   # the first 2 (quick check)
    .venv/bin/python scripts/eval.py --skip-r5  # only the golden stories (no Director/remix/vote/gamelan/robustness)

Also checks: Dalang Director validity, gamelan rendering, Remix (language + villain), the audience vote, and
robustness (each Meta stage failing once / always, injected with FAKE_META_FAIL) with pass rates, plus the
open-weights per-stage routing check (fake-mode plumbing numbers, clearly labelled).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("FAKE_META", "1")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="dalang-eval-"))
os.environ.setdefault("NARRATION_VOICE", "0")
os.environ.setdefault("MAKE_VERTICAL", "0")
os.environ.setdefault("RATE_LIMIT_PER_HOUR", "0")
os.environ.setdefault("MAX_ACTIVE_JOBS", "0")
os.environ.setdefault("VIDEO_FPS", "6")  # the Director/Remix checks render films; frame rate does not change any score
sys.path.insert(0, str(ROOT))

GOLDEN: list[dict[str, str]] = [
    {"id": "id-kancil-buaya", "lang": "id",
     "story": "Si Kancil lapar dan ingin ke kebun mentimun di seberang sungai. Sungainya penuh buaya. Kancil minta buaya berbaris supaya dihitung, lalu melompat di atas punggung mereka."},
    {"id": "id-kancil-teman", "lang": "id",
     "story": "Kancil bertemu Raja Buaya di sungai. Awalnya buaya ingin menangkapnya, tapi akhirnya mereka tertawa bersama dan berteman."},
    {"id": "jv-timun-mas", "lang": "jv",
     "story": "Mbok Sirni nemu bayi ing jero timun mas. Buto Ijo teka ngoyak, Timun Mas mlayu lan nguncalake wiji ajaib."},
    {"id": "jv-buto-ijo", "lang": "jv",
     "story": "Timun Mas wani banget. Buto Ijo sing gedhe kalah karo akal lan wiji timun, banjur Timun Mas bali menyang Mbok Sirni."},
    {"id": "en-golden-snail", "lang": "en",
     "story": "A grandmother finds a golden snail in the river. Every morning her house is clean. The snail is really a princess."},
    {"id": "en-keong-mas", "lang": "en",
     "story": "Keong Mas, the golden snail, helps a kind old woman, and one day turns back into Princess Candra Kirana."},
]

STOPWORDS = {
    "id": {"dan", "yang", "di", "itu", "ke", "dari", "dengan", "tapi", "ingin", "akan"},
    "jv": {"lan", "sing", "ing", "iku", "karo", "banjur", "ora", "saka", "nanging", "uga", "dheweke"},
    "en": {"the", "and", "a", "is", "to", "of", "her", "his", "in", "with"},
}
MAX_WORDS, MIN_WORDS, MAX_READ_S = 32, 4, 90.0


def detect(text: str) -> str:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    scores = {lang: sum(w in sw for w in words) for lang, sw in STOPWORDS.items()}
    return max(scores, key=lambda k: scores[k])


def score_script(script: dict[str, Any], lang: str) -> dict[str, Any]:
    scenes = script.get("scenes", [])
    lens = [len(s["narration"].split()) for s in scenes]
    in_bounds = sum(MIN_WORDS <= n <= MAX_WORDS for n in lens)
    read_s = sum(lens) / 2.3  # words per second for a calm narrator
    text = " ".join(s["narration"] for s in scenes)
    return {"scenes": len(scenes), "scene_ok": 4 <= len(scenes) <= 6,
            "narration_in_bounds": round(in_bounds / max(1, len(scenes)), 3), "read_aloud_s": round(read_s, 1),
            "read_ok": read_s <= MAX_READ_S, "language_field_ok": script.get("language") == lang,
            "detected": detect(text), "language_ok": script.get("language") == lang and detect(text) == lang}


def run_one(case: dict[str, str]) -> dict[str, Any]:
    from api import runner
    from api.jobs import Job

    job = Job.create(case["lang"], "classic", True)  # stop at the storyboard: everything scored exists by then
    t0 = time.time()
    runner._front(job, None, case["story"])
    s = job.s
    row: dict[str, Any] = {"id": case["id"], "lang": case["lang"], "status": s["status"], "seconds": round(time.time() - t0, 1),
                           "job": job.id}
    if s["status"] != "review":
        return {**row, "error": s.get("error") or s.get("message")}
    row.update(score_script(s["script"], case["lang"]))
    cr = s.get("cultural_review") or {}
    row.update(cultural_first=cr.get("pass_rate_first"), cultural_after=cr.get("pass_rate_after"),
               cultural_fixes=cr.get("fixes"), consistency=(s.get("consistency") or {}).get("score"),
               calls=(s.get("trace_summary") or {}).get("calls"), cost_usd=s.get("cost_usd"), title=s.get("title"))
    return row


def totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in rows if r["status"] == "review"]
    n = max(1, len(ok))

    def mean(k: str) -> float:
        return round(sum(float(r.get(k) or 0) for r in ok) / n, 3)

    return {"stories": len(rows), "completed": len(ok),
            "scene_count_ok": round(sum(r["scene_ok"] for r in ok) / n, 3),
            "narration_in_bounds": mean("narration_in_bounds"),
            "read_aloud_ok": round(sum(r["read_ok"] for r in ok) / n, 3),
            "language_match": round(sum(r["language_ok"] for r in ok) / n, 3),
            "cultural_pass_first": mean("cultural_first"), "cultural_pass_after": mean("cultural_after"),
            "consistency": round(sum(float(r.get("consistency") or 0) for r in ok) / n, 1)}


def report(rows: list[dict[str, Any]], tot: dict[str, Any], fake: bool) -> str:
    when = time.strftime("%Y-%m-%d %H:%M %Z")
    head = (f"# Evaluation report\n\nGenerated by `scripts/eval.py` on {when}. Mode: "
            + ("**fake Meta API** (fixture scripts and placeholder art). These numbers check our pipeline code "
               "(schema bounds, language routing, the Penjaga Budaya review, SAM cut-outs and consistency scoring), "
               "not the quality of Meta's models; rerun with a real key for that." if fake else "**live Meta Model API**.")
            + "\n\n")
    summ = ("| Metric | Score |\n|---|---|\n"
            f"| Stories completed to storyboard | {tot['completed']}/{tot['stories']} |\n"
            f"| Scene count within 4-6 | {tot['scene_count_ok']:.0%} |\n"
            f"| Narration lines within {MIN_WORDS}-{MAX_WORDS} words | {tot['narration_in_bounds']:.0%} |\n"
            f"| Whole film reads aloud in under {MAX_READ_S:.0f} s | {tot['read_aloud_ok']:.0%} |\n"
            f"| Language match (script field + stop-word check) | {tot['language_match']:.0%} |\n"
            f"| Cultural rules: scenes passing first time | {tot['cultural_pass_first']:.0%} |\n"
            f"| Cultural rules: scenes passing after Penjaga Budaya fixes | {tot['cultural_pass_after']:.0%} |\n"
            f"| Character consistency (mean, 0-100) | {tot['consistency']} |\n\n")
    table = ("| Story | Lang | Scenes | Narration in bounds | Read-aloud s | Language | Cultural first / after (fixes) | Consistency | Calls |\n"
             "|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        if r["status"] != "review":
            table += f"| {r['id']} | {r['lang']} | failed: {r.get('error', '')[:60]} | | | | | | |\n"
            continue
        table += (f"| {r['id']} | {r['lang']} | {r['scenes']} | {r['narration_in_bounds']:.0%} | {r['read_aloud_s']} | "
                  f"{'ok' if r['language_ok'] else 'MISMATCH (' + r['detected'] + ')'} | "
                  f"{r['cultural_first']:.0%} / {r['cultural_after']:.0%} ({r['cultural_fixes']}) | {r['consistency']} | {r['calls']} |\n")
    notes = ("\nHow each score is measured: scene count and narration length come from the validated script; "
             "language match needs both the script's language field and a stop-word check of the narration; "
             "the cultural pass rates come from the Penjaga Budaya report (content/cultural_rules.json, curated by us "
             "and not yet reviewed by a dalang); consistency is the per-film score from api/pipeline/consistency.py "
             "(SAM mask source, mask quality, checker redraws, same cut-out pixels).\n")
    return head + summ + table + notes


# --------------------------------------------------------------------------- Director, gamelan, Remix, vote, robustness
def eval_director(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Director plan on every golden script: one valid shot per scene, enums respected, last shot fades."""
    from api import cost
    from api.jobs import Job
    from api.pipeline import director
    from api.schemas import Script

    ok, n, cues, moves, sfx = 0, 0, 0, 0, 0
    for r in rows:
        if r.get("status") != "review":
            continue
        job = Job.get(r["job"])
        if job is None:
            continue
        script = Script(**job.s["script"])
        cost.use(cost.Meter(5.0))
        try:
            d = director.plan(job, script)
        finally:
            cost.use(None)
        shots = d["shots"]
        n += 1
        valid = ([s["n"] for s in shots] == [sc.n for sc in script.scenes] and shots[-1]["transition"] == "fade"
                 and all(director.CAMERA.get(s["camera"]) for s in shots))
        ok += valid
        cues += sum(s["gamelan"] != "none" for s in shots)
        moves += sum(len(s["enter"]) + len(s["exit"]) for s in shots)
        sfx += sum(len(s["sfx"]) for s in shots)
    return {"films": n, "valid": round(ok / max(1, n), 3), "cues_per_film": round(cues / max(1, n), 1),
            "moves_per_film": round(moves / max(1, n), 1), "sfx_per_film": round(sfx / max(1, n), 1)}


def eval_gamelan() -> dict[str, Any]:
    import numpy as np

    from api.pipeline import gamelan

    rows: list[dict[str, Any]] = []
    for mood in gamelan.MOOD_NAMES:
        for scale in ("slendro", "pelog"):
            t0 = time.time()
            a = gamelan.render(mood, 8.0, scale=scale)
            peak = float(np.max(np.abs(a)))
            rows.append({"mood": mood, "scale": scale, "ok": 0.05 < peak <= 0.51 and np.array_equal(a, gamelan.render(mood, 8.0, scale=scale)),
                         "render_s": round(time.time() - t0, 2)})
    steps = np.diff(1200 * np.log2(gamelan.scale_hz("slendro")))
    return {"renders": len(rows), "ok": round(sum(r["ok"] for r in rows) / len(rows), 3),
            "slendro_equal_steps": bool(np.allclose(steps, 240)), "pelog_tones": len(gamelan.scale_hz("pelog")),
            "mean_render_s_per_8s": round(sum(r["render_s"] for r in rows) / len(rows) / 2, 3)}


def _film(text: str, lang: str = "id", review: bool = False, gara: bool = False) -> Any:
    from api import runner
    from api.jobs import Job

    job = Job.create(lang, "classic", review, gara_gara=gara)
    runner._front(job, None, text)
    return job


def eval_remix() -> dict[str, Any]:
    from api import runner
    from api.pipeline import remix

    src = _film(GOLDEN[0]["story"] + " (remix eval)")
    if src.s["status"] != "done":
        return {"error": src.s.get("error")}
    out = []
    for lang, pov in (("en", "original"), ("jv", "original"), ("id", "villain")):
        job = remix.create(src, lang, pov)
        runner._remix(job)
        calls = [e for e in job.s.get("trace") or [] if e.get("kind") == "call"]
        models = sorted({e["model"] for e in calls})
        out.append({"remix": f"{lang}/{pov}", "status": job.s["status"], "calls": len(calls), "models": models,
                    "words_only": all(m.startswith("muse-spark") for m in models),
                    "same_scenes": len(job.s["script"]["scenes"]) == len(src.s["script"]["scenes"]),
                    "usd": job.s.get("cost_usd"), "source_usd": src.s.get("cost_usd")})
    good = [r for r in out if r["status"] == "done" and r["words_only"] and r["same_scenes"]]
    return {"remixes": out, "pass": round(len(good) / len(out), 3),
            "cost_ratio": round(sum(float(r["usd"] or 0) for r in out) / len(out) / max(1e-9, float(src.s.get("cost_usd") or 0)), 3)}


def eval_vote() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from api.main import app

    c = TestClient(app)
    job = _film(GOLDEN[1]["story"] + " (vote eval)", gara=True)
    if job.s["status"] != "choice":
        return {"error": f"status {job.s['status']}"}
    for i in range(7):
        c.post(f"/api/jobs/{job.id}/vote", json={"option": int(i % 3 == 0), "voter": f"kid{i}"})
    t = c.get(f"/api/jobs/{job.id}/vote").json()
    closed = c.post(f"/api/jobs/{job.id}/vote/close").json()
    for _ in range(600):
        if job.s["status"] in {"done", "failed"}:
            break
        time.sleep(0.5)
    return {"voters": t["total"], "tally": t["tally"], "winner": closed.get("winner"),
            "applied": job.s["gara_gara"].get("answer") == t["options"][closed.get("winner", 0)],
            "film": job.s["status"]}


ROBUST_STAGES = [  # (FAKE_META_FAIL target, what it is, render the whole film?)
    ("moderation", "safety screen (Muse Spark)", False),
    ("lakon", "lakon writer (Muse Spark)", False),
    ("cultural_review", "Penjaga Budaya (Muse Spark)", False),
    ("images", "Muse Image (puppets, backdrops, gunungan)", False),
    ("verdict", "picture checker (Muse Spark vision)", False),
    ("sam-3.1", "SAM 3.1 cut-out", False),
    ("motion_plan", "Muse Wonder motion plans", True),
    ("director", "Dalang Director (Muse Spark)", True),
    ("asr", "Muse Voice Transcribe", False),
]
SAMPLE_AUDIO = ROOT / "assets" / "sample-story" / "sample_story_synthetic.mp3"


def eval_robustness() -> dict[str, Any]:
    """Each Meta stage failing once, then always (META_RETRIES=1 while it runs, so back-off waits stay short). Pass = the film still reaches its storyboard / finished film
    (with labelled fallbacks), or, where no fallback can exist (no script, no safety screen, no transcript), stops
    with a kind message instead of crashing."""
    import shutil

    from api import fake_meta, resilience, runner
    from api.config import settings
    from api.jobs import Job

    rows = []
    old_retries = os.environ.get("META_RETRIES")
    os.environ["META_RETRIES"] = "1"
    for k, (target, what, render) in enumerate(ROBUST_STAGES):
        for mode in ("once", "always"):
            os.environ["FAKE_META_FAIL"] = f"{target}:{mode}"
            shutil.rmtree(settings.data_dir / "cache", ignore_errors=True)  # every call really goes out (no cached art)
            fake_meta.reset_failures()
            resilience.reset_breakers()
            job = Job.create("id", "classic", not render)
            crashed = ""
            try:
                if target == "asr":
                    up = job.dir / "upload.mp3"
                    shutil.copyfile(SAMPLE_AUDIO, up)
                    runner._front(job, up, None)
                else:
                    runner._front(job, None, f"{GOLDEN[0]['story']} (robustness {k} {mode})")
            except Exception as e:  # noqa: BLE001 - a crash is exactly what this measures
                crashed = f"{type(e).__name__}: {e}"[:120]
            st = job.s["status"]
            target_ok = "done" if render else "review"
            completed = st == target_ok
            graceful = not crashed and (completed or (st in {"failed", "blocked"} and bool(job.s.get("error") or job.s.get("message"))))
            rows.append({"stage": target, "what": what, "mode": mode, "status": st, "completed": completed,
                         "graceful": graceful, "fallbacks": len(job.s.get("fallbacks") or []),
                         "retried": sum(1 for e in job.s.get("trace") or [] if e.get("attempts", 1) > 1),
                         "error": (crashed or job.s.get("error") or "")[:90]})
    os.environ.pop("FAKE_META_FAIL", None)
    if old_retries is None:
        os.environ.pop("META_RETRIES", None)
    else:
        os.environ["META_RETRIES"] = old_retries
    fake_meta.reset_failures()
    resilience.reset_breakers()

    def rate(mode: str, key: str) -> float:
        sel = [r for r in rows if r["mode"] == mode]
        return round(sum(r[key] for r in sel) / max(1, len(sel)), 3)

    return {"rows": rows, "once_completed": rate("once", "completed"), "always_completed": rate("always", "completed"),
            "graceful": round(sum(r["graceful"] for r in rows) / max(1, len(rows)), 3)}


def eval_open_routing() -> dict[str, Any]:
    """Plumbing check of OPEN_WEIGHTS_STAGES on the fake API: which host each stage's call goes to and what Meta bills.
    FAKE MODE: both hosts answer from the same fixtures, so this says nothing about Muse Spark Open's quality."""
    from api import cost, meta_client
    from api.config import settings
    from api.jobs import Job
    from api.pipeline import director, lakon
    from api.schemas import Script

    out = []
    for label, stages in (("Meta Muse Spark 1.3", frozenset()), ("Muse Spark Open (lakon+director)", frozenset({"lakon", "director"}))):
        old = (settings.use_open_weights, settings.open_stages)
        settings.use_open_weights, settings.open_stages = bool(stages), stages
        m = cost.Meter(5.0)
        cost.use(m)
        try:
            job = Job.create("id", "classic", True)
            script: Script = lakon.run(job, GOLDEN[0]["story"] + f" (open routing {label})")
            director.plan(job, script)
        finally:
            cost.use(None)
            settings.use_open_weights, settings.open_stages = old
        calls = [e for e in m.trace if e.get("kind") == "call"]
        out.append({"setup": label, "calls": len(calls), "models": sorted({e["model"] for e in calls}),
                    "meta_billed_usd": round(m.spent, 5), "valid_script": len(script.scenes) >= 4,
                    "routed_open": [p for p in ("lakon", "director") if meta_client.routes_open(p)] if stages else []})
    return {"fake_mode": True, "rows": out}


def report_r5(r5: dict[str, Any]) -> str:
    d, g, rm, v, rb, ow = (r5.get(k, {}) for k in ("director", "gamelan", "remix", "vote", "robustness", "open"))
    md = "\n## Director, gamelan, Remix, vote, robustness (added Nov 1-2)\n\n"
    md += ("| Check | Result |\n|---|---|\n"
           f"| Director plans valid (one shot per scene, enums, last shot fades) | {d.get('valid', 0):.0%} of {d.get('films', 0)} films "
           f"· {d.get('cues_per_film')} gamelan cues, {d.get('moves_per_film')} entrances/exits, {d.get('sfx_per_film')} sfx per film |\n"
           f"| Gamelan renders (7 moods x slendro/pelog, audible, bounded, deterministic) | {g.get('ok', 0):.0%} of {g.get('renders')} "
           f"· slendro equal steps {g.get('slendro_equal_steps')} · pelog {g.get('pelog_tones')} tones · "
           f"{g.get('mean_render_s_per_8s')} s to render 8 s of music |\n"
           f"| Remix (en, jv, villain POV): done, words only, same scenes | {rm.get('pass', 0):.0%} · mean cost "
           f"{rm.get('cost_ratio', 0):.0%} of the original film |\n"
           f"| Audience vote: {v.get('voters')} voters, tally {v.get('tally')}, winner applied | "
           f"{'yes' if v.get('applied') else 'NO'} · film {v.get('film')} |\n"
           f"| Robustness: film completes when one Meta stage fails ONCE | {rb.get('once_completed', 0):.0%} |\n"
           f"| Robustness: film completes when one Meta stage fails ALWAYS | {rb.get('always_completed', 0):.0%} |\n"
           f"| Robustness: handled gracefully (completed, or a kind stop; no crash) | {rb.get('graceful', 0):.0%} |\n\n")
    md += ("### Robustness detail\n\nInjected with `FAKE_META_FAIL=<stage>:<once|always>` (HTTP 503 from the fake API), "
           "`META_RETRIES=1`. Storyboard stages are scored at the storyboard; motion and Director at the finished film.\n\n"
           "| Stage | Fails | Outcome | Fallbacks | Retried calls | Note |\n|---|---|---|---|---|---|\n")
    for r in rb.get("rows", []):
        outcome = "completed" if r["completed"] else ("stopped kindly" if r["graceful"] else "CRASH")
        md += f"| {r['what']} | {r['mode']} | {outcome} | {r['fallbacks']} | {r['retried']} | {r['error'][:70]} |\n"
    md += ("\nWhere a stage has no possible fallback (no transcript, no safety screen, no script) the film stops with "
           "a kind message (and DEMO_MODE would replay a pre-made film); every picture stage falls back to a labelled "
           "placeholder, the checker to unchecked pictures, Muse Wonder and the Director to rule-based plans.\n")
    if ow.get("rows"):
        md += ("\n### Open weights per stage (FAKE MODE plumbing numbers, not a quality comparison)\n\n"
               "Both hosts answer from the same fixtures on the fake API, so only routing and billing are compared. "
               "A real side-by-side needs a Baseten key (OPEN_WEIGHTS_STAGES=lakon,director).\n\n"
               "| Setup | Calls | Models | Billed by Meta (USD) | Valid script |\n|---|---|---|---|---|\n")
        for r in ow["rows"]:
            md += f"| {r['setup']} | {r['calls']} | {', '.join(r['models'])} | {r['meta_billed_usd']} | {r['valid_script']} |\n"
    return md


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=0, help="run only the first N stories")
    ap.add_argument("--skip-r5", action="store_true", help="skip the Director/gamelan/Remix/vote/robustness checks")
    ap.add_argument("--out", default=str(ROOT / "docs" / "EVAL_REPORT.md"))
    a = ap.parse_args()
    from api.config import settings

    cases = GOLDEN[: a.only] if a.only else GOLDEN
    rows = [run_one(c) for c in cases]
    tot = totals(rows)
    for r in rows:
        print(json.dumps({k: r.get(k) for k in ("id", "status", "scenes", "language_ok", "cultural_after", "consistency")}))
    print(json.dumps(tot))
    r5: dict[str, Any] = {}
    if not a.skip_r5:
        r5 = {"director": eval_director(rows), "gamelan": eval_gamelan(), "remix": eval_remix(), "vote": eval_vote(),
              "robustness": eval_robustness(), "open": eval_open_routing()}
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("rows", "remixes")} for k, v in r5.items()}))
    md = report(rows, tot, settings.fake_meta) + (report_r5(r5) if r5 else "")
    Path(a.out).write_text(md, encoding="utf-8")
    Path(a.out).with_name("eval.json").write_text(json.dumps({"totals": tot, "stories": rows, "round5": r5}, indent=1,
                                                             ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
