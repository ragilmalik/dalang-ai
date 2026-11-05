"""Printable puppets PDF: valid A4 PDF, a how-to page plus one page per puppet (and the gunungan)."""
import re
import time

from fastapi.testclient import TestClient

from api.main import app
from api.pipeline import mock

client = TestClient(app)


def wait(jid, statuses, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] in statuses:
            return j
        time.sleep(0.3)
    raise AssertionError(j["status"])


def test_puppets_pdf(tmp_path):
    j = client.post("/api/jobs", data={"text": mock.SAMPLE_TRANSCRIPT, "review": "true"}).json()
    early = client.get(f"/api/jobs/{j['id']}/puppets.pdf")
    j = wait(j["id"], {"review", "failed"})
    assert j["status"] == "review"
    assert early.status_code in {200, 409}
    r = client.get(f"/api/jobs/{j['id']}/puppets.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-" and b"%%EOF" in r.content[-64:]
    assert "wayang.pdf" in r.headers["content-disposition"]
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(r.content)
    pages = len(re.findall(rb"/Type\s*/Page[^s]", r.content))
    assert pages == 1 + len(j["cast"]) + 1, pages  # how-to + each puppet + gunungan
    assert re.search(rb"/MediaBox\s*\[0 0 595\.2\d* 841\.8\d*\]", r.content), "A4 pages"
    assert client.get("/api/jobs/nope/puppets.pdf").status_code == 404


def test_cut_sheet_draws_dashed_outline(tmp_path):
    import numpy as np
    from PIL import Image

    from api import printable

    im = Image.new("RGBA", (120, 200), (0, 0, 0, 0))
    im.paste((180, 60, 20, 255), (30, 30, 90, 170))
    src = tmp_path / "c.png"
    im.save(src)
    out = printable.cut_sheet(src, tmp_path / "s.png")
    a = np.asarray(Image.open(out).convert("RGB"))
    dark = (a.sum(axis=2) < 200)
    assert dark.sum() > 50  # dashes exist
    assert dark[:, :10].sum() == 0 or dark[:, :5].sum() == 0  # outline sits around the figure, not at the page edge
