"""One command from "key pasted into .env" to "everything for the submission regenerated with real Meta art".

    python scripts/go_live.py                       # LIVE: needs META_API_KEY in .env (costs about $0.30-0.60)
    python scripts/go_live.py --audio my_story.m4a  # a real child recording (default: assets/sample-story MOCK sample)
    python scripts/go_live.py --dry-run             # rehearsal on the built-in fake Meta API (FAKE_META=1, free)
    python scripts/go_live.py --plan                # only print the steps
    python scripts/go_live.py --preflight           # ONE cheapest call per Meta model, pass/fail table (~$0.02)
    python scripts/go_live.py --preflight --dry-run # the same table on the fake Meta API (free)
    python scripts/go_live.py --steps keys,seed     # a subset (keys, seed, clips, build, shots, video, storyboard, kit)

Steps, in order:
  keys        scripts/check_keys.py (live) or check_keys.py --self-test (dry run)
  seed        scripts/demo_seed.py: regenerates the demo film kept as the DEMO_MODE fallback (data/demo/)
  clips       scripts/make_launch_clips.py: three captioned 9:16 clips for X (docs/launch/)
  build       npx next build in web/ (the screenshots and demo video drive the built website)
  shots       starts the API on :8000 and the website on :3005, runs scripts/screenshots.py
  video       scripts/make_demo_video.py on the same servers (docs/demo/dalang-ai-demo.mp4)
  storyboard  scripts/demo_storyboard.py (stills, contact sheet, WebVTT)
  kit         scripts/make_submission_kit.py (../deliverables/submission-kit/ and .zip)
Every step prints PASS or FAIL; the run stops at the first failure and exits 1.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SAMPLE_AUDIO = ROOT / "assets" / "sample-story" / "sample_story_synthetic.mp3"
STEPS = ["keys", "seed", "clips", "build", "shots", "video", "storyboard", "kit"]
SERVER_STEPS = {"shots", "video"}
API_PORT, WEB_PORT = 8000, 3005  # web/next.config.mjs proxies /api to 127.0.0.1:8000 unless API_ORIGIN is set


def py() -> str:
    venv = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(venv) if venv.exists() else sys.executable


def npx() -> str:
    return shutil.which("npx") or "npx"


def has_key() -> bool:
    from api.config import settings

    return bool(settings.meta_api_key)


def wait_http(url: str, seconds: int = 90) -> bool:
    import httpx

    for _ in range(seconds):
        try:
            if httpx.get(url, trust_env=False, timeout=3).status_code == 200:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
    return False


class Servers:
    """API (uvicorn) + website (next start) for the recording steps; stopped by PID, never by pattern."""

    def __init__(self, env: dict[str, str]):
        self.env = env
        self.procs: list[subprocess.Popen[bytes]] = []

    def __enter__(self) -> Servers:
        log = Path(tempfile.gettempdir())
        self.procs.append(subprocess.Popen([py(), "-m", "uvicorn", "api.main:app", "--port", str(API_PORT)], cwd=ROOT,
                                           env=self.env, stdout=open(log / "go_live_api.log", "wb"),
                                           stderr=subprocess.STDOUT))
        self.procs.append(subprocess.Popen([npx(), "next", "start", "-p", str(WEB_PORT)], cwd=ROOT / "web", env=self.env,
                                           stdout=open(log / "go_live_web.log", "wb"), stderr=subprocess.STDOUT,
                                           start_new_session=True))
        if not wait_http(f"http://127.0.0.1:{WEB_PORT}/api/health"):
            self.__exit__()
            raise RuntimeError("the API or website did not start (see go_live_api.log / go_live_web.log in the temp folder)")
        return self

    def __exit__(self, *exc: object) -> None:
        for p in self.procs:
            if p.poll() is None:
                try:
                    if p.args and "next" in p.args:  # type: ignore[operator]
                        os.killpg(p.pid, 15)  # next start spawns next-server; stop the whole group
                    else:
                        p.terminate()
                except Exception:  # noqa: BLE001
                    p.terminate()
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    p.kill()


# --------------------------------------------------------------------------- preflight
TINY_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
FIXES = {
    "401": "The key was refused. Copy the Meta Model API key again into META_API_KEY in .env (no spaces).",
    "403": "This key cannot use this model yet. Check the model is enabled for your app on dev.meta.ai/platform.",
    "404": "The model id or address was not found. Check the *_MODEL lines in .env match dev.meta.ai/docs/models.",
    "429": "Rate limited. Wait a minute and run --preflight again.",
    "refused locally": "Our request does not match Meta's documented shape: nothing was sent. Tell the developer.",
    "circuit open": "This model failed several times in a row; wait a minute and try again.",
    "MAX_USD_TOTAL": "The total spend cap is reached. Raise MAX_USD_TOTAL in .env if you mean to spend more.",
}


def _fix(err: str) -> str:
    return next((v for k, v in FIXES.items() if k in err), "Unexpected error. Try again in a minute; if it repeats, "
                "send the developer this line.")


def preflight_checks() -> list[tuple[str, str, float, object]]:
    """(model, what it checks, estimated USD, callable). Each makes the cheapest documented call for that model."""
    import math
    import struct
    import wave

    from api import meta_client
    from api.config import settings
    from api.pipeline import mock

    tmp = Path(tempfile.mkdtemp(prefix="dalang-preflight-"))
    wav = tmp / "one_second.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(1500 * math.sin(i / 9))) for i in range(16000)))
    sheet = mock.puppet(tmp / "sheet.png", "Kancil", "animal", 1)
    ping = [{"role": "user", "content": 'Reply with {"ok": true}.'}]

    def chat(model: str) -> object:
        return lambda: meta_client.chat_json(ping, TINY_SCHEMA, "preflight", model=model, reasoning_effort="low",
                                             purpose="preflight")

    checks: list[tuple[str, str, float, object]] = [
        (settings.asr_model, "hears 1 second of audio", 0.18 / 3600,
         lambda: meta_client.transcribe_turns(wav, 1.0, ["Indonesian", "English"])),
        (settings.lakon_model, "writes structured JSON (lakon, checker, Director)", 0.0005, chat(settings.lakon_model)),
        (settings.audio_model, "Javanese listening model answers", 0.0005, chat(settings.audio_model)),
        (settings.animate_model, "Muse Wonder answers (motion plans)", 0.002, chat(settings.animate_model)),
        (settings.image_model, "draws one small picture", 0.01,
         lambda: meta_client.generate_image("a single small wayang leaf ornament, plain background", tmp / "img.png",
                                            size="1024x1024", fast=True, purpose="preflight")),
        (settings.sam_model, "cuts out one puppet", 0.0025, lambda: meta_client.segment(sheet, "puppet")),
    ]
    if settings.open_weights_active:
        checks.append((settings.open_model, "Muse Spark Open on Baseten (open weights)", 0.0,
                       lambda: meta_client.chat_json(ping, TINY_SCHEMA, "preflight", open_weights=True,
                                                     reasoning_effort="low", purpose="preflight")))
    if settings.glimmer_active:
        checks.append((settings.glimmer_model, "Muse Glimmer (open weights)", 0.0,
                       lambda: meta_client.chat_json(ping, TINY_SCHEMA, "preflight", glimmer=True, purpose="preflight")))
    return checks


def preflight() -> int:
    """ONE cheapest call per model, each guarded by the documented-shape contract, then a plain-language table."""
    import httpx

    from api import contract, cost, fake_meta, meta_client
    from api.config import settings

    inner: httpx.BaseTransport = fake_meta.transport() if settings.fake_meta else meta_client.real_transport()
    guard = contract.Guard(inner)
    meta_client._clients.clear()
    meta_client._clients[settings.fake_meta] = httpx.Client(transport=guard, timeout=120)
    meter = cost.Meter(1.0)
    cost.use(meter)
    rows = []
    for model, what, usd, fn in preflight_checks():
        t0 = time.time()
        try:
            fn()  # type: ignore[operator]
            rows.append((model, what, True, time.time() - t0, usd, ""))
        except Exception as e:  # noqa: BLE001 - every failure becomes a row with a fix
            rows.append((model, what, False, time.time() - t0, 0.0, f"{type(e).__name__}: {str(e)[:120]}"))
    cost.use(None)
    print(f"\nDalang AI preflight ({'FAKE Meta API, no cost' if settings.fake_meta else 'LIVE Meta API'})\n")
    print(f"{'':4} {'Model':<32} {'What it checks':<50} {'Time':>6} {'~USD':>8}")
    for model, what, ok, secs, usd, _ in rows:
        print(f"{'PASS' if ok else 'FAIL':4} {model:<32} {what:<50} {secs:5.1f}s {usd:8.4f}")
    for model, _, ok, _, _, err in rows:
        if not ok:
            print(f"\n  {model}: {err}\n  What to do: {_fix(err)}")
    passed = all(r[2] for r in rows)
    spent = meter.spent if not settings.fake_meta else 0.0
    print(f"\nPreflight {'PASS' if passed else 'FAIL'}: {sum(r[2] for r in rows)}/{len(rows)} models ready"
          f" · spent about ${spent:.4f}" + (" (fake: $0)" if settings.fake_meta else ""))
    if guard.violations:
        print("Contract guard refused: " + "; ".join(sorted(set(guard.violations))))
    return 0 if passed else 1


def commands(step: str, dry: bool, audio: str | None, base: str) -> list[tuple[list[str], Path]]:
    a = ["--audio", audio] if audio else []
    return {
        "keys": [([py(), "scripts/check_keys.py", *(["--self-test"] if dry else [])], ROOT)],
        "seed": [([py(), "scripts/demo_seed.py", *a], ROOT)],
        "clips": [([py(), "scripts/make_launch_clips.py"], ROOT)],
        "build": [([npx(), "next", "build"], ROOT / "web")],
        "shots": [([py(), "scripts/screenshots.py", base], ROOT)],
        "video": [([py(), "scripts/make_demo_video.py", base, *a], ROOT)],
        "storyboard": [([py(), "scripts/demo_storyboard.py"], ROOT)],
        "kit": [([py(), "scripts/make_submission_kit.py"], ROOT)],
    }[step]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="run every step on the fake Meta API (FAKE_META=1)")
    ap.add_argument("--plan", action="store_true", help="print the steps and exit")
    ap.add_argument("--preflight", action="store_true",
                    help="make ONE cheapest call per Meta model and print a pass/fail table (live: about $0.02)")
    ap.add_argument("--steps", default=",".join(STEPS), help="comma-separated subset of: " + ",".join(STEPS))
    ap.add_argument("--audio", default=str(SAMPLE_AUDIO) if SAMPLE_AUDIO.exists() else None,
                    help="the story recording for the demo film and video (default: the MOCK synthetic sample in "
                         "assets/sample-story/; pass a real child's recording here)")
    a = ap.parse_args(argv)
    steps = [s.strip() for s in a.steps.split(",") if s.strip()]
    bad = [s for s in steps if s not in STEPS]
    if bad:
        print(f"Unknown step(s): {', '.join(bad)}. Choose from {', '.join(STEPS)}.")
        return 2
    if a.audio and not Path(a.audio).is_file():
        print(f"--audio file not found: {a.audio}")
        return 2
    if a.preflight:
        if a.dry_run:
            os.environ["FAKE_META"] = "1"
        elif not has_key():
            print("FAIL keys  No META_API_KEY in .env. Paste your Meta Model API key after META_API_KEY= and run again.")
            print("           To see the same table for free first: python scripts/go_live.py --preflight --dry-run")
            return 1
        return preflight()  # api.config is first imported here, after FAKE_META is set
    mode = "DRY RUN on the fake Meta API (placeholder art, no cost)" if a.dry_run else "LIVE with your Meta key"
    base = f"http://127.0.0.1:{WEB_PORT}"
    env = {**os.environ, "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
           "PYTHONPATH": str(ROOT)}
    if a.dry_run:
        env["FAKE_META"] = "1"
    print(f"Dalang AI go-live: {mode}\nSteps: {' -> '.join(steps)}" + (f"\nStory audio: {a.audio}" if a.audio else ""))
    if a.plan:
        for s in steps:
            for cmd, cwd in commands(s, a.dry_run, a.audio, base):
                print(f"  {s:<11} (cd {cwd.relative_to(ROOT.parent)}) {' '.join(Path(c).name if i == 0 else c for i, c in enumerate(cmd))}")
        return 0
    if not a.dry_run:
        if not has_key():
            print("FAIL keys  No META_API_KEY in .env. Paste your Meta Model API key after META_API_KEY= in the .env "
                  "file and run this again (or use --dry-run to rehearse on the fake API).")
            return 1
        env["FAKE_META"] = "0"
        env["MOCK"] = "0"

    results: list[tuple[str, bool, float]] = []
    server_env = {**env, "DATA_DIR": tempfile.mkdtemp(prefix="dalang-golive-")}
    if a.dry_run:
        server_env["FAKE_META_DELAY"] = env.get("FAKE_META_DELAY", "1.2")  # keeps the progress screen watchable
    servers: Servers | None = None
    try:
        for s in steps:
            if s in SERVER_STEPS and servers is None:
                servers = Servers(server_env).__enter__()
            if s not in SERVER_STEPS and servers is not None:
                servers.__exit__()
                servers = None
            t0 = time.time()
            print(f"\n== {s}", flush=True)
            ok = True
            for cmd, cwd in commands(s, a.dry_run, a.audio, base):
                if s == "kit" and not (ROOT / "scripts" / "make_submission_kit.py").exists():
                    print("SKIP kit (scripts/make_submission_kit.py not present)")
                    continue
                r = subprocess.run(cmd, cwd=cwd, env=server_env if s in SERVER_STEPS else env)
                ok = ok and r.returncode == 0
            results.append((s, ok, time.time() - t0))
            print(f"{'PASS' if ok else 'FAIL'} {s} ({time.time() - t0:.0f}s)", flush=True)
            if not ok:
                break
    finally:
        if servers is not None:
            servers.__exit__()
    print("\n" + "-" * 40)
    for s, ok, secs in results:
        print(f"{'PASS' if ok else 'FAIL'} {s:<11} {secs:6.0f}s")
    passed = len(results) == len(steps) and all(ok for _, ok, _ in results)
    print(("go_live PASS" if passed else "go_live FAIL") + f" ({'dry run' if a.dry_run else 'live'})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
