"""Draws docs/architecture.png (run: python docs/architecture.py)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1800, 1100
BG, INK, GOLD, RED, CREAM, BLUE = (27, 15, 7), (251, 239, 213), (227, 177, 79), (157, 43, 30), (60, 38, 20), (40, 52, 110)


def f(size: int, bold: bool = True):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)
d.text((40, 30), "Dalang AI · architecture", font=f(44), fill=GOLD)
d.text((40, 88), "Voice story -> animated wayang kulit short. Every Meta call goes through api/meta_client.py.", font=f(22, False), fill=INK)


def wrap(text, font, max_w):
    out, cur = [], ""
    for word in text.split():
        t = f"{cur} {word}".strip()
        if cur and d.textlength(t, font=font) > max_w:
            out.append(cur)
            cur = word
        else:
            cur = t
    return out + ([cur] if cur else [])


def box(x, y, w, h, title, lines, color=CREAM, edge=GOLD, size=18):
    d.rounded_rectangle([x, y, x + w, y + h], radius=18, fill=color, outline=edge, width=3)
    d.text((x + 14, y + 12), title, font=f(22), fill=GOLD)
    fo = f(size, False)
    yy = y + 46
    for ln in lines:
        for part in wrap(ln, fo, w - 28):
            d.text((x + 14, yy), part, font=fo, fill=INK)
            yy += size + 7


def arrow(x1, y1, x2, y2):
    d.line([x1, y1, x2, y2], fill=GOLD, width=4)
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    for s in (2.6, -2.6):
        d.line([x2, y2, x2 - 18 * math.cos(a + s / 6), y2 - 18 * math.sin(a + s / 6)], fill=GOLD, width=4)


box(40, 150, 360, 210, "Browser (phone / laptop)", ["Next.js + Tailwind (web/)", "record 90 s + live waveform", "progress via SSE", "storyboard review, player", "share page + public gallery"])
box(470, 150, 400, 210, "FastAPI (api/main.py)", ["POST /api/jobs, SSE /events", "approve / redo scene / share", "SQLite job rows (api/db.py)", "media files, cost guard", "safety screen, audio deleted"])
box(940, 150, 400, 210, "Job runner (api/runner.py)", ["background thread per film", "budget meter (api/cost.py)", "transcript-hash cache", "DEMO_MODE replay on failure"])
box(1410, 150, 350, 210, "Storage (api/storage.py)", ["local disk (default)", "or Cloudflare R2 (S3 API)", "16:9 + 9:16 MP4, poster"])
arrow(400, 255, 470, 255)
arrow(870, 255, 940, 255)
arrow(1340, 255, 1410, 255)

stages = [
    ("1 Listen", "Muse Voice Transcribe", "Javanese: Muse Spark 1.2 audio"),
    ("2 Lakon", "Muse Spark 1.3 JSON schema", "or Muse Spark Open (Baseten)"),
    ("3 Casting", "Muse Image puppet sheets", "verified by Muse Spark vision"),
    ("4 Cut-out", "SAM 3.1 masks", "same puppet in every scene"),
    ("5 Scenes", "Muse Image backdrops", "checker redraws up to 2x"),
    ("6 Animate", "Muse Wonder keyframe plan", "kelir engine renders motion"),
    ("7 Narrate", "edge-tts neural voices", "id / jv / en"),
    ("8 Final cut", "ffmpeg: titles, subtitles", "gunungan wipes, gamelan"),
]
x0, y0, bw, bh, gap = 40, 470, 200, 210, 14
d.text((40, 420), "Pipeline (api/pipeline/)", font=f(28), fill=GOLD)
for i, (t, a, b) in enumerate(stages):
    x = x0 + i * (bw + gap)
    meta = i in (0, 1, 2, 3, 4, 5)
    box(x, y0, bw, bh, t, [a, b], color=BLUE if meta else CREAM, size=16)
    if i:
        arrow(x - gap, y0 + bh // 2, x, y0 + bh // 2)
arrow(1140, 360, 1140, 420)

box(40, 730, 830, 330, "Meta models used", [
    "muse-voice-transcribe-1.0  POST /v1/asr/transcribe",
    "muse-spark-1.3  POST /v1/chat/completions (json_schema)",
    "muse-spark-1.2  input_audio (Javanese stories)",
    "muse-image-1.0  POST /v1/images/generations",
    "sam-3.1  POST /v1/responses (stream) + meta-sam-parser",
    "muse-wonder-1.0  vision -> MotionPlan JSON",
    "Muse Spark Open (open weights)  Baseten, OpenAI-compatible",
    "Blue boxes above = Meta model calls",
], color=CREAM)
box(930, 730, 830, 330, "Agentic loops", [
    "Verify: Muse Spark vision checks every puppet sheet and",
    "backdrop against the script; failures are redrawn with",
    "the checker's corrected prompt (max 2 retries).",
    "Direct: Muse Wonder watches each storyboard frame and",
    "choreographs puppets + camera as keyframes.",
    "Consistency: SAM 3.1 cut-outs are reused in every scene.",
    "No keys yet? api/fake_meta.py answers the same HTTP calls.",
], color=CREAM)
out = Path(__file__).with_name("architecture.png")
im.save(out)
print(out)
