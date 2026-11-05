"""The fake Meta API must behave like the documented one (auth, validation, routing), because every other
test and the keyless demo run against it."""
import base64
import io
import json
import wave

import httpx
from PIL import Image

from api import fake_meta
from api.pipeline import mock

AUTH = {"authorization": "Bearer test"}


def call(path, body=None, host="api.meta.ai", headers=AUTH, content=None):
    data = content if content is not None else json.dumps(body or {}).encode()
    req = httpx.Request("POST", f"https://{host}{path}", headers=headers, content=data)
    return fake_meta.handler(req)


def chat(messages, name=None, host="api.meta.ai", model="muse-spark-1.3"):
    body = {"model": model, "messages": messages}
    if name:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": name, "schema": {}}}
    return call("/v1/chat/completions", body, host=host)


def reply(r):
    assert r.status_code == 200, r.text
    return json.loads(r.json()["choices"][0]["message"]["content"])


def test_missing_bearer_is_401():
    r = call("/v1/chat/completions", {}, headers={})
    assert r.status_code == 401


def test_unknown_route_is_404():
    r = call("/v1/nope", {})
    assert r.status_code == 404 and "no fake route" in r.json()["error"]["message"]


def test_delay_env_is_applied(monkeypatch):
    slept = []
    monkeypatch.setenv("FAKE_META_DELAY", "0.5")
    monkeypatch.setattr(fake_meta.time, "sleep", slept.append)
    call("/v1/nope", {})
    assert slept == [0.5]


def test_calls_are_logged():
    fake_meta.CALLS.clear()
    call("/v1/nope", {})
    assert fake_meta.CALLS == ["/v1/nope"]


# ----------------------------------------------------------------------------- chat
def test_moderation_blocks_war_and_allows_gentle_stories():
    bad = reply(chat([{"role": "user", "content": "cerita tentang perang dan bom"}], "moderation"))
    assert bad["allowed"] is False and bad["category"] == "war" and bad["message_to_user"]
    ok = reply(chat([{"role": "user", "content": "kancil dan buaya"}], "moderation"))
    assert ok == {"allowed": True, "category": "none", "message_to_user": ""}


def test_lakon_picks_fixture_by_story_and_language():
    before_timun = mock.SAMPLE_SCRIPT_TIMUN["language"]
    timun = reply(chat([{"role": "user", "content": "Timun Mas and Buto Ijo. code 'jv'"}], "lakon"))
    assert timun["language"] == "jv" and timun["title"] == mock.SAMPLE_SCRIPT_TIMUN["title"]
    snail = reply(chat([{"role": "user", "content": "the golden snail, code 'en'"}], "lakon"))
    assert snail["language"] == "en" and snail["title"] == mock.SAMPLE_SCRIPT_SNAIL["title"]
    kancil = reply(chat([{"role": "user", "content": "something else"}], "lakon"))
    assert kancil["title"] == mock.SAMPLE_SCRIPT["title"]
    assert mock.SAMPLE_SCRIPT_TIMUN["language"] == before_timun  # the fixture is copied, not mutated


def test_audio_input_returns_javanese_transcript():
    msgs = [{"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": "AA", "format": "wav"}}]}]
    r = chat(msgs)
    assert r.json()["choices"][0]["message"]["content"] == mock.SAMPLE_TRANSCRIPT_JV


def test_polish_keeps_moral_and_decorates_title():
    out = reply(chat([{"role": "user", "content": "Title: Kancil\nMoral: Be kind"}], "polish"))
    assert out == {"title": "Kancil ✨", "moral": "Be kind"}
    bare = reply(chat([{"role": "user", "content": "nothing"}], "polish"))
    assert bare["title"].startswith("Kancil") and bare["moral"] == ""


def test_motion_plan_reads_puppet_positions():
    text = "kancil (starts at x=0.3, facing right)\nbuaya (starts at x=0.7, facing left)"
    plan = reply(chat([{"role": "user", "content": text}], "motion_plan"))
    assert [p["id"] for p in plan["puppets"]] == ["kancil", "buaya"]
    assert plan["puppets"][0]["keyframes"][0]["x"] == -0.2  # the first puppet walks in from the left
    assert plan["puppets"][1]["keyframes"][0]["x"] == 0.7
    assert plan["puppets"][1]["keyframes"][2]["angle"] == 9.0  # left-facing puppets bow the other way


def test_gara_gara_question_follows_language_and_defaults_to_indonesian():
    for lang in ("id", "jv", "en"):
        out = reply(chat([{"role": "user", "content": f"code '{lang}'"}], "gara_gara"))
        assert out == mock.GARA_QUESTION[lang]
    assert reply(chat([{"role": "user", "content": "no language"}], "gara_gara")) == mock.GARA_QUESTION["id"]


def test_gara_gara_rewrite_keeps_scene_numbers_and_bends_the_next_scene():
    text = 'Kept scenes: 1-2\nChild\'s choice: "kancil menolong buaya!"'
    out = reply(chat([{"role": "user", "content": text}], "gara_gara_rewrite"))
    assert [s["n"] for s in out["scenes"]][0] == 3
    first = out["scenes"][0]
    assert first["narration"].startswith("Gara-gara! Kancil menolong buaya.")
    assert len(first["narration"].split()) <= 32 and first["mood"] == "magical"
    assert "The child chose" in first["action"]
    assert not mock.SAMPLE_SCRIPT["scenes"][2]["narration"].startswith("Gara-gara!")  # fixture untouched
    dflt = reply(chat([{"role": "user", "content": "no hints"}], "gara_gara_rewrite"))
    assert dflt["scenes"][0]["n"] == 3 and "Kancil berteman dengan buaya" in dflt["scenes"][0]["narration"]


def test_ad_hoc_schema_gets_a_minimal_valid_value():
    schema = {"type": "object", "properties": {
        "ok": {"type": "boolean"}, "n": {"type": "integer"}, "x": {"type": "number"}, "s": {"type": "string"},
        "kind": {"enum": ["a", "b"]}, "tags": {"type": "array", "items": {"type": "string"}, "minItems": 2}}}
    body = {"model": "m", "messages": [{"role": "user", "content": "ping"}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "ping", "schema": schema}}}
    out = reply(call("/v1/chat/completions", body))
    assert out == {"ok": True, "n": 1, "x": 1.0, "s": "ok", "kind": "a", "tags": ["ok", "ok"]}
    plain = call("/v1/chat/completions", {"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    assert plain.json()["choices"][0]["message"]["content"] == "OK"


def test_example_covers_unknown_types():
    assert fake_meta._example({"type": "array"}) == []
    assert fake_meta._example({"type": "weird"}) == "ok"
    assert fake_meta._example({}) == "ok"


def test_text_of_handles_strings_lists_and_junk():
    msgs = [{"content": "a"}, {"content": [{"type": "text", "text": "b"}, {"type": "image_url"}, "junk"]}, {"content": None}]
    assert fake_meta._text_of(msgs) == "a\nb"


def test_usage_is_reported_for_the_cost_meter():
    u = chat([{"role": "user", "content": "x"}]).json()["usage"]
    assert u["total_tokens"] == u["prompt_tokens"] + u["completion_tokens"] > 0


# ----------------------------------------------------------------------------- hosts and models
def test_glimmer_requires_documented_model_and_rejects_greedy_decoding():
    msgs = [{"role": "user", "content": "x"}]
    body = {"model": "meta-models/Muse-Glimmer-30B", "messages": msgs}
    assert call("/v1/chat/completions", body, host="api.together.xyz").status_code == 200
    assert call("/v1/chat/completions", {**body, "temperature": 0}, host="api.together.xyz").status_code == 400
    assert call("/v1/chat/completions", {**body, "model": "glimmer-wrong"}, host="api.together.xyz").status_code == 404


def test_baseten_accepts_only_muse_spark_open_ids():
    msgs = [{"role": "user", "content": "x"}]
    host = "inference.baseten.co"
    ok = call("/v1/chat/completions", {"model": "meta-models/muse-spark-open", "messages": msgs}, host=host)
    dated = call("/v1/chat/completions", {"model": "meta-models/muse-spark-open-1026", "messages": msgs}, host=host)
    bad = call("/v1/chat/completions", {"model": "other", "messages": msgs}, host=host)
    assert ok.status_code == 200 and dated.status_code == 200 and bad.status_code == 404


# ----------------------------------------------------------------------------- images
def png_of(r):
    return Image.open(io.BytesIO(base64.b64decode(r.json()["data"][0]["b64_json"])))


def test_image_rejects_unknown_model_and_unknown_fields():
    assert call("/v1/images/generations", {"model": "dalle", "prompt": "x"}).status_code == 400
    r = call("/v1/images/generations", {"model": "muse-image-1.0", "prompt": "x", "bogus": 1})
    assert r.status_code == 400 and "bogus" in r.json()["error"]["message"]


def test_image_size_is_honoured_and_art_is_deterministic():
    body = {"model": "muse-image-1.0", "prompt": "a calm river", "size": "320x192"}
    a, b = png_of(call("/v1/images/generations", body)), png_of(call("/v1/images/generations", body))
    assert a.size == (320, 192) and a.tobytes() == b.tobytes()
    default = png_of(call("/v1/images/edits", {"model": "muse-image-1.0", "prompt": "a calm river", "size": "auto"}))
    assert default.size[0] > 320


def test_image_kinds_each_draw_something():
    prompts = ["single gunungan, wayang kulit", "full-body puppet of Kancil (a clever deer) animal",
               "full-body puppet of Siti (a girl)", "tense stormy sky", "dusk river", "plain meadow"]
    sizes = set()
    for p in prompts:
        im = png_of(call("/v1/images/generations", {"model": "muse-image-1.0", "prompt": p}))
        assert im.getbbox() is not None
        sizes.add(im.size)
    assert sizes


def test_fix_prompt_redraw_passes_the_next_check():
    fake_meta._fixed_images.clear()
    r = call("/v1/images/generations", {"model": "muse-image-1.0", "prompt": fake_meta.FIX_PROMPT})
    img = Image.open(io.BytesIO(base64.b64decode(r.json()["data"][0]["b64_json"]))).convert("RGB")
    assert len(fake_meta._fixed_images) == 1
    assert fake_meta._is_fixed(fake_meta._digest(img))
    assert not fake_meta._is_fixed(None)
    assert not fake_meta._matches_fix(None)
    assert fake_meta._matches_fix(fake_meta._digest(fake_meta._draw_for_prompt(fake_meta.FIX_PROMPT).resize((1536, 1024))))


def test_verdict_fails_the_first_crocodile_backdrop_then_passes_after_the_redraw():
    def verdict(img):
        buf = io.BytesIO()
        img.save(buf, "JPEG")
        url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        msgs = [{"role": "user", "content": [
            {"type": "text", "text": "Script context: The crocodile rises from the river"},
            {"type": "image_url", "image_url": {"url": url}}]}]
        return reply(chat(msgs, "verdict"))

    fake_meta._fixed_images.clear()
    first = fake_meta._draw_for_prompt("a calm river")
    bad = verdict(first)
    assert bad["passed"] is False and bad["fix_prompt"] == fake_meta.FIX_PROMPT and bad["issues"]
    fixed = fake_meta._draw_for_prompt(fake_meta.FIX_PROMPT)
    call("/v1/images/generations", {"model": "muse-image-1.0", "prompt": fake_meta.FIX_PROMPT})
    assert verdict(fixed)["passed"] is True
    other = reply(chat([{"role": "user", "content": "Script context: a quiet morning"}], "verdict"))
    assert other["passed"] is True


# ----------------------------------------------------------------------------- SAM
def sam_body(img, stream=True, model="sam-3.1"):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return {"model": model, "stream": stream, "input": [{"role": "user", "content": [
        {"type": "input_text", "text": "puppet"}, {"type": "input_image", "image_url": url}]}]}


def test_sam_returns_box_and_mask_for_a_foreground_shape():
    img = Image.new("RGB", (200, 120), (240, 240, 240))
    img.paste((10, 10, 10), (50, 30, 120, 100))
    r = call("/v1/responses", sam_body(img))
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    assert "<|box;x1=50;y1=30;x2=120;y2=100;w=200;h=120" in r.text and "<|mask;" in r.text and "[DONE]" in r.text


def test_sam_on_an_empty_image_returns_no_detection():
    r = call("/v1/responses", sam_body(Image.new("RGB", (64, 64), (255, 255, 255))))
    assert "<|box" not in r.text and "response.completed" in r.text


def test_sam_rejects_other_models_and_non_streaming():
    img = Image.new("RGB", (8, 8))
    assert call("/v1/responses", sam_body(img, stream=False)).status_code == 400
    assert call("/v1/responses", sam_body(img, model="other")).status_code == 400


# ----------------------------------------------------------------------------- ASR
def wav_bytes(seconds=2.0, rate=8000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


def multipart(request_json, audio):
    boundary = b"xx"
    parts = [b'--xx\r\nContent-Disposition: form-data; name="request"\r\n\r\n' + request_json.encode() + b"\r\n",
             b'--xx\r\nContent-Disposition: form-data; name="audio"; filename="a.wav"\r\n\r\n' + audio + b"\r\n",
             b"--xx--\r\n"]
    return b"".join(parts), {**AUTH, "content-type": "multipart/form-data; boundary=" + boundary.decode()}


def test_asr_needs_both_multipart_parts():
    r = call("/v1/asr/transcribe", content=b"nothing here")
    assert r.status_code == 400


def test_asr_reports_real_duration_and_turns_when_endpointing():
    content, headers = multipart('{"mode":"ENDPOINTING"}', wav_bytes(3.0))
    out = call("/v1/asr/transcribe", content=content, headers=headers).json()
    assert out["audioDurationMs"] == 3000 and out["transcript"] == mock.SAMPLE_TRANSCRIPT
    turns = out["turns"]
    assert len(turns) >= 2 and all(a["endMs"] <= b["startMs"] for a, b in zip(turns, turns[1:], strict=False))
    assert turns[-1]["endMs"] <= 3000


def test_asr_without_turn_mode_has_no_turns_and_survives_a_broken_wav():
    content, headers = multipart('{"mode":"FILE"}', b"RIFFgarbage")
    out = call("/v1/asr/transcribe", content=content, headers=headers).json()
    assert out["turns"] == [] and out["audioDurationMs"] == 4000


def test_transport_is_a_mock_transport():
    assert isinstance(fake_meta.transport(), httpx.MockTransport)
