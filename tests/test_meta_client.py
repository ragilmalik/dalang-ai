"""The real client code, exercised against the fake API (which validates request shapes like the docs)."""
import json

import httpx
import pytest

from api import cost, fake_meta, meta_client
from api.pipeline import mock


@pytest.fixture
def meter():
    m = cost.Meter(5.0)
    cost.use(m)
    yield m
    cost.use(None)


def test_chat_json_structured_output(meter):
    out = meta_client.chat_json([{"role": "user", "content": "STORY LANGUAGE: x (code 'jv')"}], {}, "lakon")
    assert out["language"] == "jv" and len(out["scenes"]) == 5
    assert meter.spent > 0  # tokens were metered at Muse Spark prices


def test_generate_image_png(tmp_path, meter):
    p = meta_client.generate_image("A single full-body wayang of Kancil (animal): deer", tmp_path / "a.png", size="1024x1536")
    from PIL import Image
    assert Image.open(p).size == (1024, 1536)
    assert meter.items["muse-image-1.0"] == pytest.approx(0.01)


def test_segment_roundtrip_with_meta_parser(tmp_path, meter):
    sheet = mock.puppet(tmp_path / "s.png", "Kancil", "animal", 1)
    masks = meta_client.segment(sheet, "mouse deer puppet")
    assert len(masks) == 1
    m = masks[0]
    assert m["right"] > m["left"] and m["bottom"] > m["top"]
    assert len(m["mask"]) == m["mw"] * m["mh"] and sum(m["mask"]) > 0


def test_transcribe_multipart(tmp_path, meter):
    import wave
    w = tmp_path / "t.wav"
    with wave.open(str(w), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b"\x00\x00" * 16000)
    assert "kancil" in meta_client.transcribe(w, 1.0, ["Indonesian"]).lower()


def test_request_shapes_match_docs(monkeypatch, tmp_path):
    """Capture what goes over the wire and compare with dev.meta.ai's documented fields."""
    seen = []

    def spy(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return fake_meta.handler(req)

    monkeypatch.setattr(meta_client, "_clients", {True: httpx.Client(transport=httpx.MockTransport(spy))})
    meta_client.generate_image("x", tmp_path / "x.png", size="1536x1024")
    meta_client.chat_json([{"role": "user", "content": "hi"}], {"type": "object", "properties": {}}, "ping")
    img, chat = seen
    assert str(img.url) == "https://api.meta.ai/v1/images/generations"
    body = json.loads(img.content)
    assert body["model"] == "muse-image-1.0" and body["size"] == "1536x1024" and body["output_format"] == "png"
    assert set(body["tool_enablement"]) <= {"enable_web_search", "enable_shell", "enable_image_search"}
    assert str(chat.url) == "https://api.meta.ai/v1/chat/completions"
    cbody = json.loads(chat.content)
    assert cbody["model"] == "muse-spark-1.3"
    assert cbody["response_format"]["type"] == "json_schema" and cbody["response_format"]["json_schema"]["name"] == "ping"
    assert chat.headers["authorization"].startswith("Bearer ")


def test_unknown_image_field_is_rejected_like_real_api(tmp_path):
    r = fake_meta.handler(httpx.Request("POST", "https://api.meta.ai/v1/images/generations",
                                        headers={"authorization": "Bearer x"},
                                        json={"model": "muse-image-1.0", "prompt": "p", "seed": 1}))
    assert r.status_code == 400


def test_budget_guard(tmp_path):
    cost.use(cost.Meter(0.005))
    try:
        with pytest.raises(cost.BudgetExceeded):
            meta_client.generate_image("x", tmp_path / "x.png")
    finally:
        cost.use(None)
