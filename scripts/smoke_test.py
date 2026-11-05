"""Full-stack smoke test through the Next.js website, the way a phone uses it.

    python scripts/smoke_test.py http://localhost:3000
"""
import json
import math
import struct
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import httpx


def ffmpeg_exe() -> str:
    import shutil

    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg

    return str(imageio_ffmpeg.get_ffmpeg_exe())


TMP = Path(tempfile.mkdtemp())

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3005"
c = httpx.Client(base_url=BASE, trust_env=False, timeout=120)
ok: list[bool] = []


def step(name, cond, info=""):
    ok.append(cond)
    print(("PASS " if cond else "FAIL ") + name + (f"  {info}" if info else ""), flush=True)


r = c.get("/")
step("landing page 200", r.status_code == 200 and "Ceritakan kisahmu" in r.text)
card = c.get("/opengraph-image.png")
man = c.get("/manifest.webmanifest")
step("link preview card + PWA manifest", 'property="og:image"' in r.text and 'name="twitter:card"' in r.text
     and card.status_code == 200 and card.content[:4] == b"\x89PNG" and man.status_code == 200
     and any(i["sizes"] == "512x512" for i in man.json()["icons"]))
h = c.get("/api/health").json()
step("health via Next proxy", h.get("ok") is True, json.dumps(h)[:120])

# a real audio upload (webm via ffmpeg, like a phone's MediaRecorder)
wav = str(TMP / "smoke.wav")
with wave.open(wav, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(44100)
    w.writeframes(b"".join(struct.pack("<h", int(4000 * math.sin(2 * math.pi * 330 * i / 44100))) for i in range(44100 * 3)))
subprocess.run([ffmpeg_exe(), "-loglevel", "error", "-y", "-i", wav, "-c:a", "libopus", str(TMP / "smoke.webm")], check=True)
with open(TMP / "smoke.webm", "rb") as f:
    j = c.post("/api/jobs", data={"language": "id", "style": "classic", "review": "true"},
               files={"audio": ("story.webm", f, "audio/webm")}).json()
jid = j["id"]
step("job created from audio upload", bool(jid))

# SSE through the Next proxy until review
states = []
t0 = time.time()
with c.stream("GET", f"/api/jobs/{jid}/events") as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            states.append((round(time.time() - t0, 1), json.loads(line[6:])["status"]))
step("SSE streams incrementally through Next", len(states) > 3 and states[-1][1] == "review",
     f"{len(states)} events, first at {states[0][0]}s, last at {states[-1][0]}s")
j = c.get(f"/api/jobs/{jid}").json()
step("transcript from ASR", "kancil" in j["transcript"].lower())
step("storyboard has stills", all(c.get(s["still"]).status_code == 200 for s in j["scenes"]))
step("film page renders", c.get(f"/film/{jid}").status_code == 200)

c.post(f"/api/jobs/{jid}/approve")
while True:
    j = c.get(f"/api/jobs/{jid}").json()
    if j["status"] in {"done", "failed"}:
        break
    time.sleep(1)
step("film finished", j["status"] == "done", f"{j.get('duration_s')} s, cost ${j['cost_usd']}")
tr = c.get(f"/api/jobs/{jid}/trace").json()
models = {e["model"] for e in tr["trace"] if e["kind"] == "call"}
step("agent trace lists Meta calls and decisions",
     {"muse-voice-transcribe-1.0", "muse-image-1.0", "sam-3.1", "muse-wonder-1.0"} <= models and tr["summary"]["calls"] > 10,
     f"{tr['summary']['calls']} calls, {tr['summary']['decisions']} decisions, {len(models)} models")
for k in ("landscape", "vertical"):
    v = c.get(j["videos"][k])
    (TMP / f"smoke_{k}.mp4").write_bytes(v.content)
    step(f"{k} video served", v.status_code == 200 and len(v.content) > 100_000, f"{len(v.content) // 1024} KB")
step("watch page hidden before share", c.get(f"/watch/{jid}").status_code == 404)
c.post(f"/api/jobs/{jid}/share", json={"public": True})
page = c.get(f"/watch/{jid}")
step("watch page public after share, with OG + X card tags", page.status_code == 200 and 'property="og:image"' in page.text
     and 'name="twitter:image"' in page.text and 'property="og:description"' in page.text and "Copy link" in page.text)
g = c.get("/gallery")
step("gallery lists the film", j["title"] in g.text)

# ---- features added in the ten-upgrades run, all through the Next.js proxy
qr = c.get("/api/qr.png", params={"path": f"/watch/{jid}"})
info = c.get("/api/share-info").json()
step("QR code + share info", qr.status_code == 200 and qr.content[:4] == b"\x89PNG" and "url" in info,
     f"{info.get('url')} public={info.get('public')}")
pdf = c.get(f"/api/jobs/{jid}/puppets.pdf")
step("printable puppets PDF", pdf.status_code == 200 and pdf.content[:5] == b"%PDF-", f"{len(pdf.content) // 1024} KB")
book = c.get(f"/api/jobs/{jid}/storybook.pdf")
step("storybook PDF (A5)", book.status_code == 200 and book.content[:5] == b"%PDF-", f"{len(book.content) // 1024} KB")
rec = c.get(f"/api/jobs/{jid}/receipt").json()
cr = rec.get("cultural_review") or {}
step("models receipt + Penjaga Budaya + consistency", rec["calls"] > 0 and rec["tokens_in"] > 0
     and cr.get("pass_rate_after") == 1.0 and (rec.get("consistency") or {}).get("score", 0) > 0,
     f"{rec['calls']} calls, consistency {(rec.get('consistency') or {}).get('score')}/100, {cr.get('fixes')} cultural fixes")
jp, gp = c.get("/judge"), c.get("/guru")
step("judge mode + teacher page", jp.status_code == 200 and "Judge mode" in jp.text and gp.status_code == 200
     and "30-minute" in gp.text)
docs = c.get("/api/docs")
step("judge's API docs link works through the website", 'href="/api/docs"' in jp.text and docs.status_code == 200
     and "/api/openapi.json" in docs.text and c.get("/api/openapi.json").status_code == 200)
fb = c.post("/api/feedback", json={"job_id": jid, "rating": 5, "page": "watch"})
summary = c.get("/api/feedback/summary").json()
step("feedback widget stores a rating", fb.status_code == 200 and summary["count"] >= 1, json.dumps(summary["by_rating"]))
step("no testimonials endpoint (the feature was removed: no fake quotes)", c.get("/api/testimonials").status_code == 404)
fam = "fam_smoke_0123456789abcdef"
saved = c.post("/api/kotak", json={"family_id": fam, "job_id": jid, "char_id": "kancil"}).json()
box = c.get("/api/kotak", params={"family": fam}).json()
step("Kotak Wayang saves a puppet", c.get("/kotak").status_code == 200 and [p["id"] for p in box] == [saved["id"]]
     and c.get(saved["cutout"]).status_code == 200)

# Gara-gara: pause, answer, rewrite, finish; and Kancil coming back from the Kotak Wayang
gj = c.post("/api/jobs", data={"text": "Kancil bertemu buaya lagi di sungai, lalu mereka bermain bersama sampai sore.",
                               "language": "id", "review": "false", "gara_gara": "true", "family_id": fam,
                               "returning": saved["id"]}).json()
gid = gj["id"]
while (gj := c.get(f"/api/jobs/{gid}").json())["status"] not in {"choice", "failed", "done", "blocked"}:
    time.sleep(1)
step("Gara-gara pauses with a question", gj["status"] == "choice" and len(gj["gara_gara"]["options"]) == 2
     and c.get(f"/film/{gid}").status_code == 200, gj["gara_gara"].get("question", ""))
step("returning puppet reused, not redrawn", any(x.get("returning") for x in gj["cast"]))
c.post(f"/api/jobs/{gid}/choice", data={"text": gj["gara_gara"]["options"][0]})
while (gj := c.get(f"/api/jobs/{gid}").json())["status"] not in {"done", "failed", "blocked"}:
    time.sleep(1)
step("Gara-gara film finished after the choice", gj["status"] == "done" and gj["fresh_scenes"] == [3, 4, 5],
     f"{gj.get('duration_s')} s")
print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
