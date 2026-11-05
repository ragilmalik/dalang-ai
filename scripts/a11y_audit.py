"""Automated accessibility audit with axe-core (WCAG 2.0/2.1 A and AA rules) in Playwright, on the five pages a
family uses: home, film (finished film with share bar and agent trace), watch, gallery and Kotak Wayang.

    bash scripts/a11y_local.sh                         # starts API + website, runs this, stops both
    python scripts/a11y_audit.py http://127.0.0.1:3000  # app already running; writes docs/ACCESSIBILITY.md

axe-core comes from the `axe-playwright-python` package (it bundles axe.min.js), or set AXE_JS=/path/axe.min.js.
Exit code 1 if any page has a serious or critical violation.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_path import launch_kwargs  # noqa: E402

TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
BLOCKING = {"serious", "critical"}


def axe_source() -> str:
    if os.environ.get("AXE_JS"):
        return Path(os.environ["AXE_JS"]).read_text(encoding="utf-8")
    import axe_playwright_python

    return (Path(axe_playwright_python.__file__).parent / "axe.min.js").read_text(encoding="utf-8")


def make_film(base: str) -> str:
    """A finished, shared film to audit the film and watch pages on (fake Meta API, placeholder art)."""
    c = httpx.Client(base_url=base, trust_env=False, timeout=60)
    r = c.post("/api/jobs", data={"text": "Kancil yang cerdik ingin menyeberang sungai penuh buaya untuk makan "
                                          "mentimun.", "language": "id", "review": "false"})
    r.raise_for_status()
    jid = r.json()["id"]
    t0 = time.time()
    while (s := c.get(f"/api/jobs/{jid}").json()["status"]) not in {"done", "failed", "blocked"}:
        if time.time() - t0 > 600:
            raise TimeoutError(jid)
        time.sleep(1)
    if s != "done":
        raise RuntimeError(f"film {jid} ended {s}")
    c.post(f"/api/jobs/{jid}/share", json={"public": True}).raise_for_status()
    return jid


def audit(base: str, jid: str, axe_js: str) -> list[dict]:
    from playwright.sync_api import sync_playwright

    pages = [("Home", "/", "text=Jadikan wayang"), ("Film", f"/film/{jid}", "video"),
             ("Watch", f"/watch/{jid}", "video"), ("Gallery", "/gallery", "main"), ("Kotak Wayang", "/kotak", "main"),
             ("Judge mode", "/judge", "main"), ("Teachers", "/guru", "main"),
             # Pentas wall, Kelir Live stage, phone voting page
             ("Pentas", "/pentas", "[data-testid=pentas-wall]"),
             ("Kelir Live", f"/kelir/{jid}", "[data-testid=kelir][data-ready='1']"),
             ("Vote (phone)", f"/vote/{jid}", "main :is(h1, [role=alert])"),
             # the 404 page (an empty kelir)
             ("Not found", "/tidak-ada", "main h1")]
    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs())  # type: ignore[arg-type]
        for vp_name, vp in (("phone", {"width": 390, "height": 844}), ("desktop", {"width": 1280, "height": 800})):
            ctx = browser.new_context(viewport=vp)  # type: ignore[arg-type]
            page = ctx.new_page()
            for name, path, ready in pages:
                page.goto(base + path, wait_until="networkidle")
                page.wait_for_selector(ready, timeout=30000)
                # open the collapsible agent trace so its table is audited too
                page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
                page.add_script_tag(content=axe_js)
                res = page.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
                out.append({"page": name, "path": path, "viewport": vp_name, "passes": len(res["passes"]),
                            "violations": [{"id": v["id"], "impact": v["impact"], "help": v["help"],
                                            "nodes": len(v["nodes"]),
                                            "targets": [n["target"] for n in v["nodes"][:3]]}
                                           for v in res["violations"]]})
            ctx.close()
        browser.close()
    return out


def write_report(results: list[dict], axe_js: str, path: Path) -> None:
    version = axe_js[axe_js.find("axe v") + 5:].split()[0] if "axe v" in axe_js[:200] else "?"
    lines = ["# Accessibility audit (axe-core)", "",
             f"Automated audit with **axe-core {version}** (rules tagged {', '.join(TAGS)}) in Chromium via Playwright,",
             "run by `bash scripts/a11y_local.sh` on the fake Meta API (placeholder art). Each page is checked on a",
             "phone (390x844) and a desktop (1280x800) screen; collapsible sections (the agent trace) are opened first.",
             "Automated rules find about a third of real accessibility problems; a manual screen-reader pass is still",
             "worth doing.", "",
             f"Run: {time.strftime('%Y-%m-%d %H:%M %Z')}", "",
             "| Page | Screen | Rules passed | Critical | Serious | Moderate | Minor |", "|---|---|---|---|---|---|---|"]
    for r in results:
        count = {k: sum(1 for v in r["violations"] if v["impact"] == k) for k in ("critical", "serious", "moderate", "minor")}
        lines.append(f"| {r['page']} (`{r['path'].split('/')[1] or '/'}`) | {r['viewport']} | {r['passes']} | "
                     f"{count['critical']} | {count['serious']} | {count['moderate']} | {count['minor']} |")
    rest = [(r, v) for r in results for v in r["violations"]]
    lines += ["", "## Findings", ""]  # axe's "incomplete" (needs review) items are not counted
    if not rest:
        lines.append("No violations on any page.")
    for r, v in rest:
        lines.append(f"* {r['page']} ({r['viewport']}): **{v['impact']}** `{v['id']}`: {v['help']} "
                     f"({v['nodes']} element(s), e.g. `{json.dumps(v['targets'][0]) if v['targets'] else ''}`)")
    lines += ["", "Not counted above: axe's \"needs review\" items, which it cannot decide automatically (for example text",
              "contrast over a picture). Re-run after UI changes: `cd web && npm run build && cd .. && bash scripts/a11y_local.sh`",
              "(exit code 1 on any serious or critical violation)."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="http://127.0.0.1:3000")
    ap.add_argument("--job", default="", help="audit this finished film instead of making one")
    ap.add_argument("--out", default=str(ROOT / "docs" / "ACCESSIBILITY.md"))
    ap.add_argument("--json", default="/tmp/dalang-a11y.json")
    a = ap.parse_args()
    axe_js = axe_source()
    jid = a.job or make_film(a.base)
    results = audit(a.base, jid, axe_js)
    Path(a.json).write_text(json.dumps(results, indent=1))
    write_report(results, axe_js, Path(a.out))
    bad = [(r["page"], r["viewport"], v["id"], v["impact"]) for r in results for v in r["violations"]
           if v["impact"] in BLOCKING]
    total = sum(len(r["violations"]) for r in results)
    print(f"axe: {len(results)} page checks, {total} violation(s), {len(bad)} serious/critical")
    for b in bad:
        print("  ", *b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
