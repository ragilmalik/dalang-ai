"""Write docs/qr.png: a QR code for the app's public URL (PUBLIC_BASE_URL in .env).

    python scripts/make_qr.py                 # uses PUBLIC_BASE_URL (refuses without it)
    python scripts/make_qr.py https://...     # any URL

There is no QR until the app is deployed: without PUBLIC_BASE_URL or a URL argument it writes nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import qr  # noqa: E402


def main(argv: list[str]) -> int:
    url = argv[0] if argv else qr.app_url()
    if not url.startswith(("https://", "http://")):
        print("No public link yet: set PUBLIC_BASE_URL after deploying (or pass a URL). Nothing written.")
        return 1
    out = qr.save(url, ROOT / "docs" / "qr.png")
    print(f"wrote {out} -> {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
