from PIL import Image

from api.pipeline import engine


def test_wrap_px_fits_width():
    f = engine.font(40)
    text = "Tapi sungai itu dijaga Raja Buaya dan kawan-kawannya yang juga lapar sekali hari itu."
    lines = engine.wrap_px(text, f, 500, 10)
    from PIL import ImageDraw
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    assert all(d.textlength(ln, font=f) <= 500 for ln in lines)
    assert " ".join(lines) == text


def test_pose_interpolates_and_faces():
    tr = {"id": "a", "idle": "still", "keyframes": [
        {"t": 0, "x": 0.0, "lift": 0, "angle": 0, "facing": "right"},
        {"t": 1, "x": 1.0, "lift": 0, "angle": 0, "facing": "left"}]}
    x0, _, _, f0 = engine.pose(tr, 0.0, 0.0, 0)
    xm, _, _, _ = engine.pose(tr, 0.5, 0.0, 0)
    x1, _, _, f1 = engine.pose(tr, 1.0, 0.0, 0)
    assert x0 == 0.0 and abs(xm - 0.5) < 1e-6 and x1 == 1.0
    assert f0 == "right" and f1 == "left"


def test_frame_sizes_landscape_and_vertical(tmp_path):
    for W, H in ((640, 360), (360, 640)):
        film = engine.Film(W, H, shots=[engine.Shot(duration=2, bg=Image.new("RGB", (W * 2, H * 2), (90, 60, 30)),
                                                    plan={"puppets": []}, caption=engine.caption_layer("Halo", W, H))])
        fr = engine.Kelir(film, {}).frame(1.0)
        assert fr.size == (W, H)


def test_rotation_cache_quantises_and_stays_bounded():
    im = Image.new("RGBA", (40, 80), (200, 150, 50, 255))
    p = engine.Puppet(im, im.transpose(Image.Transpose.FLIP_LEFT_RIGHT), im, im)
    film = engine.Film(320, 180, shots=[])
    kel = engine.Kelir(film, {"a": p})
    assert kel._rotated("a", p, "right", 0.04) == (p.img, p.shadow)  # under half a step: no rotation
    a1 = kel._rotated("a", p, "right", 1.01)
    a2 = kel._rotated("a", p, "right", 0.99)  # same 0.2-degree bucket -> same cached images
    assert a1[0] is a2[0] and a1[0].size != im.size
    assert kel._rotated("a", p, "left", 1.0)[0] is not a1[0]  # facing is part of the key
    for k in range(engine.Kelir.CACHE_MAX + 20):
        kel._rotated("a", p, "right", 2 + k * engine.Kelir.ANGLE_STEP)
    assert len(kel._rot) == engine.Kelir.CACHE_MAX


def test_end_card_shows_qr_only_in_last_three_seconds():
    from PIL import Image

    from api import qr
    from api.pipeline import engine

    W, H = 320, 180
    end = Image.new("RGBA", (W, H), (10, 10, 10, 255))
    film = engine.Film(W, H, end_card=end, end_len=4.0)
    film.end_qr = engine.qr_badge(qr.image("https://example.org"), W, H, "example.org")
    kel = engine.Kelir(film, {})
    early, late = kel.frame(0.5), kel.frame(3.0)  # end card starts at t=0 (no title, no shots)
    corner = (W - 20, H - 20)
    assert early.getpixel(corner)[:3] == (10, 10, 10)
    assert sum(late.getpixel(corner)[:3]) > 300  # cream QR tile


def test_qr_png_and_share_info_endpoints():
    from fastapi.testclient import TestClient

    from api.main import app

    c = TestClient(app)
    info = c.get("/api/share-info").json()
    assert info["public"] is False and info["url"] == "http://testserver"  # the address the request came in on
    r = c.get("/api/qr.png", params={"path": "/watch/abc"})
    assert r.status_code == 200 and r.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert c.get("/api/qr.png", params={"path": "https://evil.example"}).status_code == 400


def test_qr_decodes_to_url_when_public_base_url_set(monkeypatch):
    from api import qr
    from api.config import settings

    monkeypatch.setattr(settings, "public_base_url", "https://dalang.test")
    assert not qr.is_placeholder() and qr.app_url("/watch/x") == "https://dalang.test/watch/x"


def test_puppet_rods_stop_at_the_caption_band():
    """A puppet whose rod hangs past the floor is cut at the top of the caption band, so no rod crosses the words.
    Before the caption fades in, the rod is drawn in full."""
    W, H = 360, 640
    rod = Image.new("RGBA", (30, 520), (0, 255, 0, 255))  # tall enough to reach the bottom of the frame
    p = engine.Puppet(rod, rod, Image.new("RGBA", rod.size, (0, 0, 0, 0)), Image.new("RGBA", rod.size, (0, 0, 0, 0)))
    cap = engine.caption_layer("Si Kancil melompat ke punggung buaya satu per satu sambil menghitung.", W, H)
    plan = {"puppets": [{"id": "a", "idle": "none", "keyframes": [{"t": 0, "x": 0.5, "lift": -0.2}]}]}
    sh = engine.Shot(duration=3, bg=Image.new("RGB", (W * 2, H * 2), (90, 60, 30)), plan=plan, caption=cap)
    top = sh.caption_top
    assert top is not None and H * 0.6 < top < H
    kel = engine.Kelir(engine.Film(W, H, shots=[sh]), {"a": p})

    def green_rows(fr):
        px = fr.convert("RGB").load()
        return [y for y in range(H) if any(px[x, y][1] > 200 and px[x, y][0] < 80 for x in range(W // 2 - 20, W // 2 + 20))]

    shown = green_rows(kel.shot_frame(sh, 2.0))
    assert shown and max(shown) < top
    early = green_rows(kel.shot_frame(sh, 0.1))
    assert max(early) > top
    assert engine.Shot(duration=1, bg=sh.bg, plan={}).caption_top is None


def test_caption_never_leaves_one_word_alone_on_the_last_line():
    f = engine.font(28)
    text = "Tapi sungai itu dijaga Raja Buaya dan kawan-kawannya yang juga lapar."
    from PIL import ImageDraw
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    width = d.textlength("Tapi sungai itu dijaga Raja Buaya dan kawan-kawannya yang juga", font=f) + 2
    lines = engine.wrap_px(text, f, width, 3)
    assert len(lines) == 2 and lines[-1].count(" ") >= 1 and " ".join(lines) == text
    assert all(d.textlength(ln, font=f) <= width for ln in lines)
