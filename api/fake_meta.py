"""Fake Meta Model API for running and testing Dalang AI before real keys exist.

It is an httpx transport that answers the SAME HTTP requests meta_client sends to https://api.meta.ai/v1
(and to Baseten for Muse Spark Open), with replies shaped exactly like the documented responses:
  POST /v1/asr/transcribe          -> {"transcript", "turns", "audioDurationMs"}
  POST /v1/chat/completions        -> {"choices":[{"message":{"content": <JSON string>}}], "usage"}
  POST /v1/images/generations|edits-> {"data":[{"b64_json": <png>}]}
  POST /v1/responses (stream)      -> SSE events whose output text uses SAM's <|box|><|mask|> grammar
So every line of the real client (request building, retries, parsing, cost metering) runs in tests.
Replies come from recorded fixtures (the sample lakon) and procedurally drawn placeholder art.
It is used automatically when no META_API_KEY is set, or when FAKE_META=1.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import tempfile
import threading
import time
import zlib
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from PIL import Image

from .pipeline import mock

_lock = threading.Lock()
_fixed_images: list[np.ndarray] = []  # images drawn from a checker's fix prompt (they pass the next check)
CALLS: list[str] = []  # request log, handy for tests


def _json(data: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=data)


def _usage(pt: int = 800, ct: int = 400) -> dict[str, int]:
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}


def _chat(content: Any) -> httpx.Response:
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    return _json({"id": "chatcmpl-fake", "object": "chat.completion", "model": "fake",
                  "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
                  "usage": _usage()})


def _text_of(messages: list[dict[str, Any]]) -> str:
    out = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, list):
            out += [p.get("text", "") for p in c if isinstance(p, dict) and p.get("type") == "text"]
    return "\n".join(out)


# ----------------------------------------------------------------------------- chat completions
BLOCK_WORDS = re.compile(r"\b(perang|war|bom|bomb|pistol|gun|darah|blood|pemilu|election|obat|medicine)\b", re.I)


FIX_PROMPT = ("Wide wayang kulit backdrop of a dark river with tall reeds at dusk, warm blencong "
              "lamp glow, batik clouds. Completely empty: no animals, no people, no puppets, no text.")
_fix_digest: list[np.ndarray] = []


def _matches_fix(fp: np.ndarray | None) -> bool:
    """The redraw may come from the app's image cache (no new fake call), so also recognise it by its pixels."""
    if fp is None:
        return False
    if not _fix_digest:
        _fix_digest.append(_digest(_draw_for_prompt(FIX_PROMPT).resize((1536, 1024), Image.Resampling.LANCZOS)))
    return float(np.abs(fp - _fix_digest[0]).mean()) < 4.0


def _motion_plan(text: str) -> dict[str, Any]:
    puppets = []
    for i, (pid, x, face) in enumerate(re.findall(r"(\w+) \(starts at x=([\d.]+), facing (left|right)\)", text)):
        x = float(x)
        start = -0.2 if face == "right" else 1.2
        bow = -9 if face == "right" else 9
        puppets.append({"id": pid, "idle": "sway", "keyframes": [
            {"t": 0.0, "x": start if i == 0 else x, "lift": 0.0, "angle": 0.0, "facing": face},
            {"t": 0.35, "x": x, "lift": 0.0, "angle": 0.0, "facing": face},
            {"t": 0.6, "x": x, "lift": 0.06, "angle": float(bow), "facing": face},
            {"t": 0.85, "x": x, "lift": 0.0, "angle": 0.0, "facing": face}]})
    return {"camera": {"zoom_from": 1.0, "zoom_to": 1.08, "pan_x": 0.2, "pan_y": 0.0}, "lamp_flicker": 0.5, "puppets": puppets}


def sample_script_for(text: str) -> dict[str, Any]:
    """Pick the fixture script that matches the story (Timun Mas, Keong Mas), else the Kancil one."""
    low = text.lower()
    if "timun mas" in low or "buto ijo" in low:
        return mock.SAMPLE_SCRIPT_TIMUN
    if "golden snail" in low or "keong mas" in low:
        return mock.SAMPLE_SCRIPT_SNAIL
    return mock.SAMPLE_SCRIPT


def _chat_completions(body: dict[str, Any]) -> httpx.Response:
    messages = body.get("messages", [])
    rf = body.get("response_format") or {}
    name = (rf.get("json_schema") or {}).get("name", "")
    text = _text_of(messages)
    if any(isinstance(p, dict) and p.get("type") == "input_audio"
           for m in messages if isinstance(m.get("content"), list) for p in m["content"]):
        return _chat(mock.SAMPLE_TRANSCRIPT_JV)  # Muse Spark 1.2 audio understanding (Javanese)
    if name == "moderation":
        story = _text_of([m for m in messages if m.get("role") == "user"])
        bad = BLOCK_WORDS.search(story)
        return _chat({"allowed": bad is None, "category": "war" if bad else "none",
                      "message_to_user": "Yuk, ceritakan kisah lain yang ramah anak!" if bad else ""})
    if name == "lakon":
        script = json.loads(json.dumps(sample_script_for(text)))
        lang = re.search(r"code '(id|jv|en)'", text)
        if lang:
            script["language"] = lang.group(1)
        return _chat(script)
    if name == "verdict":
        # Scripted behaviour so the redraw loop shows up in demos and tests: the first backdrop for the
        # scene where the crocodile "rises from the river" fails; the redraw from the fix prompt passes.
        ctx = re.search(r"Script context: (.*)", text)
        key = ctx.group(1).strip() if ctx else ""
        with _lock:
            fp = _image_key(messages)
            if "rises from the river" in key and not _is_fixed(fp) and not _matches_fix(fp):
                return _chat({"passed": False, "issues": ["a crocodile figure is painted into the backdrop, which must be empty"],
                              "fix_prompt": FIX_PROMPT})
        return _chat({"passed": True, "issues": [], "fix_prompt": ""})
    if name == "cultural_review":
        return _chat(_cultural_review(text))
    if name == "motion_plan":
        return _chat(_motion_plan(text))
    if name == "polish":
        t = re.search(r"^Title: (.*)$", text, re.M)
        m = re.search(r"^Moral: (.*)$", text, re.M)
        return _chat({"title": (t.group(1).strip() if t else "Kancil") + " ✨", "moral": m.group(1).strip() if m else ""})
    if name == "gara_gara":
        lang = re.search(r"code '(id|jv|en)'", text)
        return _chat(mock.GARA_QUESTION.get(lang.group(1) if lang else "id", mock.GARA_QUESTION["id"]))
    if name == "gara_gara_rewrite":
        return _chat(_rewrite(text))
    if name == "director":
        return _chat(_director(text))
    if name == "remix":
        return _chat(_remix(text))
    schema = (rf.get("json_schema") or {}).get("schema")
    return _chat(_example(schema) if schema else "OK")


def _director(text: str) -> dict[str, Any]:
    """Dalang Director fixture: the rule-based shots for the script, with one recorded model touch (the first shot
    opens on a gong with the dalang's keprak) and one deliberate slip (a puppet id that is not in the script) so the
    validation repair shows in the trace."""
    from .pipeline import director
    from .schemas import Script

    m = re.search(r"SCRIPT JSON:\n(.*)", text, re.S)
    script = Script(**json.loads(m.group(1) if m else json.dumps(mock.SAMPLE_SCRIPT)))
    shots = [s.model_dump() for s in director.rules(script)]
    for sh in shots:
        sh["note"] = sh["note"].replace("rule-based:", "fake API fixture:")
    if shots:
        shots[0]["sfx"] = [{"t": 0.05, "kind": "keprak"}] + shots[0]["sfx"][:2]
        shots[0]["note"] = "Open on the gong and the keprak, as a dalang opens the lakon."
        shots[-1]["enter"] = shots[-1]["enter"] + [{"id": "semar_extra", "side": "below"}]
    return {"shots": shots}


def _remix(text: str) -> dict[str, Any]:
    """Remix fixture: the same narration, re-voiced (villain: first person) and tagged with the target language, so
    tests can see the words changed while the pictures did not. A real key gives a real re-telling."""
    m = re.search(r"SCRIPT JSON:\n(.*)", text, re.S)
    script: Any = json.loads(m.group(1)) if m else dict(mock.SAMPLE_SCRIPT)
    lm = re.search(r"code '(id|jv|en)'", text)
    lang = lm.group(1) if lm else "id"
    pov = re.search(r"POINT OF VIEW: (.+?) \(first person\)", text)
    tag = {"id": "Bahasa Indonesia", "jv": "Basa Jawa", "en": "English"}[lang]
    who = pov.group(1) if pov else None
    lines = []
    for sc in script.get("scenes", []):
        words = sc["narration"]
        lines.append({"n": sc["n"], "narration": (f"Aku, {who}, ingat: {words}" if who else f"[{tag}] {words}")[:290]})
    title = script.get("title", "Kancil")
    return {"title": f"{title} \u00b7 {('told by ' + who) if who else tag}", "moral": script.get("moral", ""),
            "opening": script.get("opening", ""), "scenes": lines}


def _cultural_review(text: str) -> dict[str, Any]:
    """Penjaga Budaya fixture: the rules-file word scan plus one recorded model judgement, so the fix loop shows
    up in demos and tests: in the Kancil sample the crocodile king "rises from the river, hungry", which the
    reviewer softens (child-friendly pictures) before the backdrop is drawn."""
    from .pipeline import penjaga

    m = re.search(r"SCRIPT JSON:\n(.*)", text, re.S)
    data = json.loads(m.group(1)) if m else {"scenes": [], "characters": []}
    hits = penjaga.scan(data)
    scenes = []
    for sc in data.get("scenes", []):
        mine = [h for h in hits if h.get("scene") == sc["n"]]
        row = {"n": sc["n"], "passed": not mine, "rules": sorted({h["rule"] for h in mine}),
               "issue": ", ".join(sorted({h["word"] for h in mine})), "narration": "", "action": "", "image_prompt": ""}
        for f in penjaga.SCENE_FIELDS:
            if any(h["field"] == f for h in mine):
                row[f] = penjaga.scrub(sc[f], f)
        if "rises from the river, hungry" in sc.get("action", ""):
            row.update(passed=False, rules=sorted({*row["rules"], "kid-friendly-pictures"}),
                       issue="a hungry crocodile rising at a small animal reads as frightening for young children",
                       action=sc["action"].replace("rises from the river, hungry", "rises from the river, grumpy but not scary"),
                       image_prompt=sc["image_prompt"] + ", calm water, gentle light, nothing frightening")
        scenes.append(row)
    chars = []
    for ch in data.get("characters", []):
        mine = [h for h in hits if h.get("character") == ch["id"]]
        row = {"id": ch["id"], "passed": not mine, "rules": sorted({h["rule"] for h in mine}),
               "issue": ", ".join(sorted({h["word"] for h in mine})), "visual_description": "", "cultural_note": ""}
        for f in penjaga.CHAR_FIELDS:
            if any(h["field"] == f for h in mine):
                row[f] = penjaga.scrub(ch.get(f, ""), f)
        chars.append(row)
    return {"scenes": scenes, "characters": chars, "note": "Checked against the curated rules file (fake API fixture)."}


def _rewrite(text: str) -> dict[str, Any]:
    """Scenes after the gara-gara, bent toward the child's choice (recorded fixture + the choice itself)."""
    km = re.search(r"Kept scenes: 1-(\d+)", text)
    kept = int(km.group(1)) if km else 2
    cm = re.search(r'Child\'s choice: "(.*)"', text)
    choice = cm.group(1).strip() if cm else "Kancil berteman dengan buaya"
    scenes = json.loads(json.dumps(mock.SAMPLE_SCRIPT["scenes"][kept:]))
    first = scenes[0]
    words = f"Gara-gara! {choice[:1].upper()}{choice[1:].rstrip('.!?')}. {first['narration']}".split()
    first["narration"] = " ".join(words[:32])
    first["action"] = f"The child chose: {choice}. " + first["action"]
    first["image_prompt"] += ", after the gara-gara storm clears"
    first["mood"] = "magical"
    for i, sc in enumerate(scenes, kept + 1):
        sc["n"] = i
    return {"moral": mock.SAMPLE_SCRIPT["moral"], "scenes": scenes}


def _example(schema: dict[str, Any]) -> Any:
    """Smallest value that satisfies a JSON schema (for ad-hoc schemas such as the key-check ping)."""
    t = schema.get("type")
    if "enum" in schema:
        return schema["enum"][0]
    if t == "object":
        return {k: _example(v) for k, v in (schema.get("properties") or {}).items()}
    if t == "array":
        return [_example(schema.get("items") or {"type": "string"})] * int(schema.get("minItems", 0))
    return {"boolean": True, "integer": 1, "number": 1.0, "string": "ok"}.get(t or "string", "ok")


# ----------------------------------------------------------------------------- images
def _png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _draw_for_prompt(prompt: str) -> Image.Image:
    seed = zlib.crc32(prompt.encode()) % 9973
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "x.png"
        if "gunungan" in prompt.lower() and "single gunungan" in prompt.lower():
            mock.gunungan(out)
        elif "full-body" in prompt:
            m = re.search(r" of (.+?) \(", prompt)
            name = m.group(1) if m else "Puppet"
            kind = "animal" if re.search(r"animal|kancil|buaya|crocodile|deer|gajah|bird", prompt, re.I) else "human"
            mock.puppet(out, name, kind, seed)
        else:
            mood = next((k for k in ("night", "tense", "magical", "triumphant", "happy") if k in prompt.lower()), "calm")
            if "dusk" in prompt.lower() or "stormy" in prompt.lower():
                mood = "tense"
            mock.background(out, mood, seed)
        return Image.open(out).convert("RGB").copy()


def _images(body: dict[str, Any]) -> httpx.Response:
    if body.get("model") != "muse-image-1.0" and not str(body.get("model", "")).startswith("muse-image"):
        return _json({"error": {"message": f"unknown model {body.get('model')}"}}, 400)
    allowed = {"model", "prompt", "n", "size", "output_format", "response_format", "reasoning_strength",
               "tool_enablement", "images", "background", "quality", "user", "mask"}
    extra = set(body) - allowed
    if extra:  # the real API rejects unknown top-level fields with 400
        return _json({"error": {"message": f"unknown fields {sorted(extra)}"}}, 400)
    prompt = body.get("prompt", "")
    img = _draw_for_prompt(prompt)
    size = str(body.get("size", ""))
    if re.fullmatch(r"\d+x\d+", size):
        w, h = (int(v) for v in size.split("x"))
        img = img.resize((w, h), Image.Resampling.LANCZOS) if (w, h) != img.size else img
    b64 = _png(img)
    if "Completely empty" in prompt:  # drawn from the fake checker's fix prompt
        with _lock:
            _fixed_images.append(_digest(img))
    return _json({"created": 0, "data": [{"b64_json": b64}]})


def _digest(img: Image.Image) -> np.ndarray:
    """Tiny grayscale fingerprint; survives the JPEG re-encode and resize meta_client applies before sending."""
    return np.asarray(img.convert("L").resize((32, 18), Image.Resampling.BILINEAR), dtype=float)


def _is_fixed(fp: np.ndarray | None) -> bool:
    return fp is not None and any(float(np.abs(fp - f).mean()) < 4.0 for f in _fixed_images)


def _image_key(messages: list[dict[str, Any]]) -> np.ndarray | None:
    for m in messages:
        for p in m.get("content") or []:
            if isinstance(p, dict) and p.get("type") == "image_url":
                url = p["image_url"]["url"]
                return _digest(Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB"))
    return None


# ----------------------------------------------------------------------------- SAM 3.1
def _sam(body: dict[str, Any]) -> httpx.Response:
    from meta_sam_parser._mask_codec import _encode_raster  # Meta's own codec, so the parser round-trips

    content = body["input"][0]["content"]
    url = next(p["image_url"] for p in content if p.get("type") == "input_image")
    im = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB")
    W, H = im.size
    a = np.asarray(im).astype(int)
    bg = a[2, 2]
    fg = (np.abs(a - bg).sum(axis=2) > 60)
    ys, xs = np.nonzero(fg)
    if len(xs) == 0:
        text = ""
    else:
        x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        crop = Image.fromarray((fg[y1:y2, x1:x2] * 255).astype(np.uint8), "L")
        mw = min(160, crop.width)
        mh = max(1, int(crop.height * mw / crop.width))
        small = (np.asarray(crop.resize((mw, mh), Image.Resampling.NEAREST)) > 127).astype(int)
        payload = _encode_raster([int(v) for v in small.flatten()], mw, mh)
        text = (f"<0f>0<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={W};h={H};c=0.93|>"
                f"<|mask;x=0;y=0;c=0.93;data={mh},{mw},{payload}|>")
    events = [
        {"type": "response.created", "response": {"id": "resp_fake", "status": "in_progress", "output": []}},
        {"type": "response.output_item.added", "output_index": 0,
         "item": {"type": "message", "id": "msg_fake", "role": "assistant", "content": []}},
        {"type": "response.content_part.added", "output_index": 0, "content_index": 0, "item_id": "msg_fake",
         "part": {"type": "output_text", "text": ""}},
        {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "item_id": "msg_fake", "delta": text},
        {"type": "response.output_text.done", "output_index": 0, "content_index": 0, "item_id": "msg_fake", "text": text},
        {"type": "response.completed", "response": {"id": "resp_fake", "status": "completed"}},
    ]
    sse = "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse.encode())


def _asr(content: bytes) -> dict[str, Any]:
    """Shaped like the documented file-transcription response. In ENDPOINTING mode every sentence of the
    recorded transcript becomes a turn, spread over the real length of the uploaded WAV (startMs/endMs)."""
    import wave

    ms = 4000
    i = content.find(b"RIFF")
    if i >= 0:
        try:
            with wave.open(io.BytesIO(content[i:]), "rb") as w:
                ms = int(w.getnframes() / w.getframerate() * 1000)
        except Exception:  # noqa: BLE001
            pass
    turns: list[dict[str, Any]] = []
    if b'"ENDPOINTING"' in content or b'"DIARIZATION"' in content:
        sentences = [x.strip() + "." for x in mock.SAMPLE_TRANSCRIPT.split(".") if x.strip()]
        total = sum(len(x) for x in sentences)
        t = 300.0
        span = max(1.0, ms - 600.0)
        for k, sent in enumerate(sentences, 1):
            d = span * len(sent) / total
            turns.append({"turnId": k, "startMs": int(t), "endMs": int(t + d * 0.92), "transcript": sent})
            t += d
    return {"sessionId": "fake", "transcript": mock.SAMPLE_TRANSCRIPT, "turns": turns, "audioDurationMs": ms}


# ----------------------------------------------------------------------------- failure injection
_failed_once: set[str] = set()


def _target(path: str, body: dict[str, Any]) -> list[str]:
    """Names a request answers to in FAKE_META_FAIL: endpoint family, model and structured-output name."""
    names = []
    if path.endswith("/asr/transcribe"):
        names.append("asr")
    elif path.endswith("/chat/completions"):
        names.append("chat")
        names.append(((body.get("response_format") or {}).get("json_schema") or {}).get("name", ""))
    elif "/images/" in path:
        names.append("images")
    elif path.endswith("/responses"):
        names.append("sam")
    if body.get("model"):
        names.append(str(body["model"]))
    return [n for n in names if n]


def _injected(path: str, body: dict[str, Any]) -> httpx.Response | None:
    """FAKE_META_FAIL="images:always,motion_plan:once,sam-3.1:always": answer matching calls with HTTP 503
    (always, or only the first time). Used by the robustness eval and tests to break one Meta stage at a time."""
    spec = os.environ.get("FAKE_META_FAIL", "").strip()
    if not spec:
        return None
    names = _target(path, body)
    for item in spec.split(","):
        target, _, mode = item.strip().partition(":")
        if target in names:
            if mode == "once":
                with _lock:
                    if target in _failed_once:
                        continue
                    _failed_once.add(target)
            return _json({"error": {"message": f"injected failure for {target}", "type": "server_error"}}, 503)
    return None


def reset_failures() -> None:
    _failed_once.clear()


# ----------------------------------------------------------------------------- router
def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    delay = float(os.environ.get("FAKE_META_DELAY", "0") or 0)  # seconds per call, to mimic real latency in demos
    if delay:
        time.sleep(delay)
    CALLS.append(path)
    if not request.headers.get("authorization", "").startswith("Bearer "):
        return _json({"error": {"message": "missing bearer token"}}, 401)
    if path.endswith("/asr/transcribe"):
        injected = _injected(path, {"model": "muse-voice-transcribe-1.0"})
        if injected is not None:
            return injected
        if b'name="request"' not in request.content or b'name="audio"' not in request.content:
            return _json({"error": {"message": "multipart parts 'request' and 'audio' are required"}}, 400)
        return _json(_asr(request.content))
    body = json.loads(request.content or b"{}")
    injected = _injected(path, body)
    if injected is not None:
        return injected
    if request.url.host == "api.together.xyz" or "glimmer" in str(body.get("model", "")).lower():
        # Muse Glimmer (Together AI / self-hosted): documented model string, and greedy decoding is discouraged
        if body.get("model") not in {"meta-models/Muse-Glimmer-30B", "muse-glimmer"}:
            return _json({"error": {"message": f"unknown model {body.get('model')}"}}, 404)
        if body.get("temperature") == 0:
            return _json({"error": {"message": "temperature 0 is not supported for this model in the fake"}}, 400)
    if request.url.host == "inference.baseten.co" and not str(body.get("model", "")).startswith("meta-models/muse-spark-open"):
        # Muse Spark Open on Baseten: the docs' model string (a dated variant from the dashboard also starts with it)
        return _json({"error": {"message": f"unknown model {body.get('model')}"}}, 404)
    if path.endswith("/chat/completions"):
        return _chat_completions(body)
    if path.endswith("/images/generations") or path.endswith("/images/edits"):
        return _images(body)
    if path.endswith("/responses"):
        if body.get("model") != "sam-3.1" or not body.get("stream"):
            return _json({"error": {"message": "fake supports only sam-3.1 streaming"}}, 400)
        return _sam(body)
    return _json({"error": {"message": f"no fake route for {path}"}}, 404)


def transport() -> httpx.MockTransport:
    return httpx.MockTransport(handler)
