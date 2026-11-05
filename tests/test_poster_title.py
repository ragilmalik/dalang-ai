"""The share poster keeps a long title (a remix "· told by ...") inside its band, clear of the tagline."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from PIL import Image

from api.pipeline import engine


class _Kelir:
    def __init__(self) -> None:
        shot = SimpleNamespace(duration=4.0, bg=Image.new("RGB", (1280, 720), (200, 160, 100)), plan={}, mood="calm")
        self.f = SimpleNamespace(shots=[shot], gunungan=None)

    def shot_frame(self, shot, t):  # noqa: ANN001, ANN201 - test stub
        return Image.new("RGB", (1280, 720), (200, 160, 100))


def _title_rows(path) -> np.ndarray:  # noqa: ANN001
    im = np.asarray(Image.open(path).convert("RGB")).astype(int)
    gold = (im[..., 0] > 230) & (im[..., 1] > 190) & (im[..., 2] < 170)  # the title's gold, not the cream tagline
    return np.where(gold.any(axis=1))[0]


def test_long_title_stays_above_the_tagline(tmp_path):
    for title in ("Kancil", "Timun Mas lan Buto Ijo · told by Buto Ijo",
                  "Bawang Merah Bawang Putih · diceritakan oleh Bawang Merah yang iri hati sekali"):
        out = engine.poster(_Kelir(), title, tmp_path / "p.jpg")  # type: ignore[arg-type]
        rows = _title_rows(out)
        assert rows.size, title
        assert rows.min() >= 630 - int(630 * 0.26) - 2, title  # inside the band
        assert rows.max() < 630 - 44, title  # clear of the tagline line at H-40
