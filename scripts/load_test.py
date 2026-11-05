"""Concurrency check: N films started at the same moment on the fake Meta API all finish with no errors, the
MAX_ACTIVE_JOBS guard turns the next one away kindly, and nothing is left running. Writes a JSON summary.

    bash scripts/load_local.sh            # starts the API on a scratch DATA_DIR, runs this, stops it
    python scripts/load_test.py http://127.0.0.1:8000 --jobs 6 --out /tmp/load.json
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import httpx

STORIES = [
    ("id", "Kancil yang cerdik ingin menyeberang sungai penuh buaya untuk makan mentimun."),
    ("jv", "Timun Mas mlayu saka Buto Ijo lan nyebar wiji timun ing alas."),
    ("en", "An old woman finds a golden snail in the river and takes it home."),
    ("id", "Seekor burung kecil belajar terbang bersama ibunya di atas sawah."),
    ("jv", "Bocah cilik nulungi kucing sing kecemplung kali, banjur dadi kanca."),
    ("en", "A shy elephant learns to dance at the village festival."),
]
END = {"done", "failed", "blocked"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="http://127.0.0.1:8000")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--out", default="")
    ap.add_argument("--limit", type=int, default=6, help="the server's MAX_ACTIVE_JOBS (0 = no cap)")
    a = ap.parse_args()
    c = httpx.Client(base_url=a.base, trust_env=False, timeout=60)
    limit = a.limit
    c.get("/api/health").raise_for_status()
    created: list[dict] = []
    errors: list[str] = []
    barrier = threading.Barrier(a.jobs)

    def start(i: int) -> None:
        lang, text = STORIES[i % len(STORIES)]
        barrier.wait()  # all requests leave at the same moment
        t = time.time()
        r = httpx.post(a.base + "/api/jobs", data={"text": text, "language": lang, "review": "false"},
                       trust_env=False, timeout=60)
        if r.status_code != 200:
            errors.append(f"create {i}: HTTP {r.status_code} {r.text[:120]}")
            return
        created.append({"id": r.json()["id"], "lang": lang, "t0": t})

    t0 = time.time()
    threads = [threading.Thread(target=start, args=(i,)) for i in range(a.jobs)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    # one more while all N are in progress: the abuse guard should answer 429 (kind message), not queue it
    extra = httpx.post(a.base + "/api/jobs", data={"text": STORIES[0][1], "language": "id", "review": "false"},
                       trust_env=False, timeout=60)
    results: dict[str, dict] = {}
    while len(results) < len(created) and time.time() - t0 < a.timeout:
        for job in created:
            if job["id"] in results:
                continue
            s = c.get(f"/api/jobs/{job['id']}").json()
            if s.get("status") in END:
                results[job["id"]] = {"lang": job["lang"], "status": s["status"], "title": s.get("title", ""),
                                      "seconds": round(time.time() - job["t0"], 1), "error": s.get("error", "")}
        time.sleep(1)
    wall = round(time.time() - t0, 1)
    for job in created:
        r = results.get(job["id"])
        if not r:
            errors.append(f"{job['id']} not finished after {a.timeout:.0f} s")
        elif r["status"] != "done":
            errors.append(f"{job['id']} {r['status']}: {r['error']}")
    # every finished film has its MP4 reachable
    for jid in results:
        v = c.get(f"/api/jobs/{jid}").json().get("videos", {}).get("landscape")
        ok_video = False
        if v:
            with c.stream("GET", v if v.startswith("/") else "/" + v) as resp:  # the media route answers GET only
                ok_video = resp.status_code < 400 and int(resp.headers.get("content-length", "1")) > 0
        if not ok_video:
            errors.append(f"{jid}: video missing")
    still_active = [j["id"] for j in created if c.get(f"/api/jobs/{j['id']}").json().get("status") in
                    {"queued", "running", "rendering"}]
    summary = {
        "jobs": a.jobs, "created": len(created), "done": sum(r["status"] == "done" for r in results.values()),
        "errors": errors, "wall_seconds": wall,
        "per_job_seconds": sorted(r["seconds"] for r in results.values()),
        "max_active_jobs": limit, "extra_request_status": extra.status_code,
        "extra_request_kind_message": extra.status_code == 429 and "dalang" in extra.text.lower(),
        "left_active": still_active,
    }
    ok = (not errors and summary["done"] == a.jobs and not still_active
          and (limit != a.jobs or extra.status_code == 429))
    summary["pass"] = ok
    print(json.dumps(summary, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(summary, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
