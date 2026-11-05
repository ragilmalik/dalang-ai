"""Pre-flight check before deploying (spends nothing, creates no accounts).

    python scripts/deploy_preflight.py --api-origin https://dalang-ai-api.onrender.com

Checks: render.yaml and web/vercel.json parse and point at files that exist; no secret is committed;
the backend image builds if Docker is installed; the website builds with the API_ORIGIN you will set on
Vercel (Next.js bakes it in at build time). Prints the exact values to paste into Render and Vercel.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ok = True


def report(name: str, passed: bool, info: str = "") -> None:
    global ok
    ok = ok and passed
    print(("PASS " if passed else "FAIL ") + name + (f"  {info}" if info else ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-origin", default="https://dalang-ai-api.onrender.com")
    ap.add_argument("--skip-build", action="store_true")
    a = ap.parse_args()

    try:
        import yaml

        blueprint = yaml.safe_load((ROOT / "render.yaml").read_text())
        svc = blueprint["services"][0]
        report("render.yaml parses", True, f"service {svc['name']}, plan {svc.get('plan')}, disk {svc.get('disk', {}).get('sizeGB')} GB")
        report("Dockerfile.api exists", (ROOT / svc["dockerfilePath"]).exists())
        report("health check path", svc.get("healthCheckPath") == "/api/health")
        secrets = [e["key"] for e in svc["envVars"] if e.get("sync") is False]
        report("secrets are dashboard-only (sync: false)", "META_API_KEY" in secrets, ", ".join(secrets))
    except ImportError:
        report("render.yaml parses", False, "pip install pyyaml")
    vercel = json.loads((ROOT / "web" / "vercel.json").read_text())
    report("web/vercel.json parses", vercel.get("framework") == "nextjs")

    sys.path.insert(0, str(ROOT))
    from api import qr

    if qr.is_placeholder():
        print("WARN PUBLIC_BASE_URL is not set: QR codes use the visitor's own address and no QR goes into films. After "
              "deploying, set PUBLIC_BASE_URL to the Vercel URL (Render + Vercel + .env), then run "
              "python scripts/make_qr.py and python scripts/go_live.py --steps seed,shots,video,storyboard,kit")
    else:
        report("PUBLIC_BASE_URL is an https URL", qr.base_url().startswith("https://"), qr.base_url())

    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    report("no .env committed", not any(Path(f).name == ".env" for f in tracked))

    if not a.skip_build:
        if shutil.which("docker"):
            d = subprocess.run(["docker", "build", "-f", "Dockerfile.api", "-t", "dalang-api", "."], cwd=ROOT)
            report("docker build (backend)", d.returncode == 0)
        else:
            print("SKIP docker build (Docker not installed; CI builds it on every push)")
        env = {**__import__("os").environ, "API_ORIGIN": a.api_origin, "NEXT_TELEMETRY_DISABLED": "1"}
        r = subprocess.run(["npx", "next", "build"], cwd=ROOT / "web", env=env, capture_output=True, text=True)
        report("website builds with API_ORIGIN", r.returncode == 0, a.api_origin if r.returncode == 0 else r.stdout[-400:])
        manifest = ROOT / "web" / ".next" / "routes-manifest.json"
        if manifest.exists():
            report("rewrite points at API_ORIGIN", a.api_origin in manifest.read_text())

    print("\nPaste into Render (dalang-ai-api -> Environment): META_API_KEY=<your key>, PUBLIC_BASE_URL=<Vercel URL>")
    print(f"Paste into Vercel (Project -> Settings -> Environment Variables): API_ORIGIN={a.api_origin}, PUBLIC_BASE_URL=<Vercel URL>")
    print("Then redeploy Vercel so the new API_ORIGIN is built in.")
    print("\nAll checks passed." if ok else "\nSome checks failed.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
