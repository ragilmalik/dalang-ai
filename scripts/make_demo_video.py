"""Make the 2-3 minute demo video from the WORKING app: a real browser session is recorded, cut into
scenes, and given an English voice-over with burned-in captions. Works on the fake Meta API (placeholder
art) today; run it again after adding the Meta key and the same video shows the real Muse Image art.

    # terminal 1: the backend (FAKE_META_DELAY slows the fake API so the progress screen is watchable)
    FAKE_META_DELAY=1.2 python -m uvicorn api.main:app --port 8000
    # terminal 2: the website
    cd web && npm run build && npm run start
    # terminal 3:
    python -m playwright install chromium     # or install Chrome/Chromium, or set CHROME=/path/to/chrome
    python scripts/make_demo_video.py http://localhost:3000

The browser is found by scripts/browser_path.py (no hardcoded path). With no browser at all, the video is still
made: the film is generated through the same HTTP API and the app segments use docs/screenshots/ stills (ffmpeg only).

Outputs docs/demo/: dalang-ai-demo.mp4 (1920x1080, captions burned in), dalang-ai-demo.srt, voiceover.txt,
timeline.json, and two cuts for X that open on Kelir Live: teaser_60s.mp4 (16:9: the Kelir Live shot, the film's
opening to the classroom vote, the close card) and teaser_vertical.mp4 (9:16: Kelir Live recorded on a 432x768 phone
screen, then the vertical film and an end card).

Shot order (v3, 2:50-2:58): the child's voice in the first 3 s, the film, the gara-gara classroom vote (three
phone votes arrive as API calls), the rest of the film, Kelir Live (the child performs it), why, the home hero and a
Story Starter, the pipeline theatre, the trace + receipt, share (read-along, Pentas, stickers + GIF), print, close.

Malik's own footage and voice (--real docs/demo/real, see docs/demo/real/README.md): any clip or voice-over file
found there replaces that shot's screen recording / still and its synthetic voice-over line. Missing files fall back to the
recording, so a half-filled folder still renders.

The synthetic voice-over is a stand-in narrator (DEMO_VOICE, default Kokoro-82M af_heart, picked in docs/VOICES.md),
not Malik. With only the app's own venv it falls back to edge-tts; set TTS_PYTHON to a venv with requirements-tts.txt.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_path import launch_kwargs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO = ROOT / "assets" / "sample-story" / "sample_story_synthetic.mp3"


def _args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="http://127.0.0.1:3000")
    # --reuse=/tmp/dalang-demo-xxxx: skip recording and reuse that run's segments and voice lines; the close card,
    # captions and final mix are rebuilt (caption or card fixes without a new 8-minute recording).
    ap.add_argument("--reuse", default="")
    # The story recording uploaded in the "tell" shot. Default: the MOCK synthetic sample; pass a real one.
    ap.add_argument("--audio", default=str(DEFAULT_AUDIO))
    # --real=docs/demo/real: Malik's phone clips (A-E) and recorded voice-over, used instead of the recording/synthetic VO
    ap.add_argument("--real", default=str(Path(__file__).resolve().parents[1] / "docs" / "demo" / "real"))
    # --plan: speak the voice-over lines only and print each shot's length and the total (no app, no recording)
    ap.add_argument("--plan", action="store_true")
    return ap.parse_args()


_A = _args()
BASE = _A.base
REUSE = _A.reuse
AUDIO = Path(_A.audio)
# DEMO_OUT=<dir>: write the cut, captions and teasers there instead of docs/demo (render, check, then swap in)
OUT = Path(os.environ["DEMO_OUT"]) if os.environ.get("DEMO_OUT") else ROOT / "docs" / "demo"
OUT.mkdir(parents=True, exist_ok=True)
# DEMO_TMP=<dir>: keep the work folder somewhere that survives a reboot (then --reuse=<dir> resumes after recording)
_DT = os.environ.get("DEMO_TMP", "")
if _DT:
    Path(_DT).mkdir(parents=True, exist_ok=True)
TMP = Path(REUSE) if REUSE else (Path(tempfile.mkdtemp(prefix="dalang-demo-", dir=_DT)) if _DT else
                                  Path(tempfile.mkdtemp(prefix="dalang-demo-")))
W, H = 1920, 1080  # output size (DEMO_VIDEO_REVIEW: 1080p)
PHONE_VW, PHONE_VH = 432, 768  # the phone-sized Kelir Live recording for the vertical teaser
RW, RH = 1280, 720  # browser viewport and recording size (the UI is laid out for this), scaled up to W x H
REAL = Path(_A.real)
# The stand-in narrator (until Malik records his own lines): engine:voice[@speed], see api/tts.py and docs/VOICES.md.
# Needs the optional local engine (requirements-tts.txt, or TTS_PYTHON=<venv python>); falls back to edge-tts.
VOICE = os.environ.get("DEMO_VOICE", "kokoro:af_heart@1.0")  # 1.0 scored the same as 0.92 and keeps the cut under 3:00
VOICE_FALLBACK = "edge:en-US-AndrewNeural@4"
SENTENCE_GAP = float(os.environ.get("DEMO_SENTENCE_GAP", "0.25"))  # seconds of quiet between sentences
STORY = ("Dulu ada kancil yang pintar. Dia lapar dan mau makan mentimun di seberang sungai. Tapi di sungai banyak "
         "buaya yang lapar juga. Kancil bilang raja mau menghitung semua buaya, jadi buaya-buaya berbaris dan "
         "kancil melompat di punggung mereka. Sampai di seberang, kancil minta maaf dan mereka jadi teman.")

# (key, voice-over). Each recorded segment is stretched or trimmed to fit its line. Order and lines follow the
# 2:50 shot list in deliverables/win-kit/DEMO_VIDEO_REVIEW.md. With the synthetic voice nobody claims to be Malik:
# his first-person lines are used only when his own recording (real/vo_<key>.wav) is present.
SCRIPT = [
    ("voice", ""),  # 0:00-0:03 the child's voice over black (real clip A, or the labelled stand-in recording)
    ("opening", ""),  # gong, gunungan, title, "Kocap kacarita" (film sound only)
    ("film1", "That's a kid's story. Ninety seconds of talking, performed back as wayang kulit."),
    ("garagara", "Then the gara-gara. The show pauses and the whole class votes on their phones for what happens next."),
    ("film2", ""),  # the rewritten scenes, film sound only
    ("kelir", "Then the child takes the puppets. In Kelir Live they're on a lamp-lit screen. Drag them, tilt them, "
              "tap the gunungan for the next scene."),
    ("why", "Wayang is a thousand years old, but most kids around Semarang have never sat in front of a kelir. "
            "With Dalang AI, every child gets to be the dalang."),
    ("landing", "Any child can tell a story in Indonesian, Javanese or English. Tap a story starter, or just talk. "
                "Nothing to type."),
    ("progress", "Six Meta models work as one troupe, and you can watch them on stage. Muse Voice Transcribe listens, "
                 "Muse Spark one point two hears Javanese, and Muse Spark one point three writes the lakon. The Penjaga "
                 "Budaya agent checks every scene against its cultural rules. Muse Image carves each puppet once and "
                 "SAM three point one cuts it out. Muse Wonder plans every move, and the Dalang Director sets the camera "
                 "and the gamelan."),
    ("trace", "It checks its own work. A vision agent redraws any picture that breaks the script, and every film shows "
              "its trace and a receipt for every model call."),
    ("share", "Read-along captions light up each word as it's spoken. Share the film to the Pentas wall, and the puppets "
              "turn into a WhatsApp sticker pack."),
    ("print", "Print the puppets and the storybook, grab a torch, and the show moves off the screen."),
    ("close", "Dalang AI. A child tells a story out loud, and six Meta models perform it. Every child can be a dalang."),
]
# Malik's first-person versions, used ONLY with his own recorded voice-over file for that shot (real/vo_<key>.wav)
REAL_LINES = {
    "why": "I'm Malik, from Semarang. Wayang is a thousand years old, but the kids around me have never sat in front "
           "of a kelir. So I built Dalang AI.",
    "close": "Built solo this week with Meta's models. Dalang AI: every child can be a dalang. Matur nuwun.",
}
# Malik's phone clips (DEMO_VIDEO_REVIEW §3): file stem -> the shot it replaces. Any of .mp4 .mov .m4v .webm.
REAL_CLIPS = {"A_child_tells": "voice", "C_garagara_answer": "garagara", "B_family_watching": "why",
              "E_tap_record": "landing", "D_shadow_play": "print"}
VOICE_SECONDS = 3.2
OPENING_SECONDS = 7.0
FILM1_SECONDS = 19.0
FILM2_SECONDS = 15.0


# Captions show the written form of what the voice says aloud.
CAPTION_FORMS = {"SAM three point one": "SAM 3.1", "Muse Spark one point two": "Muse Spark 1.2",
                 "Muse Spark one point three": "Muse Spark 1.3", "sixteen by nine and nine by sixteen": "16:9 and 9:16",
                 "after scene two": "after scene 2",
                 "Dalang Cilik hashtag": "#DalangCilik hashtag"}
MAX_CAPTION_WORDS = 12


def caption_chunks(line: str) -> list[str]:
    """Split a voice-over line into caption cues: sentence by sentence, long sentences into balanced parts of at
    most MAX_CAPTION_WORDS words (no one-word leftovers like "film.")."""
    for spoken, written in CAPTION_FORMS.items():
        line = line.replace(spoken, written)
    out: list[str] = []
    sentences = [x.strip() for x in line.replace(". ", ".\n").replace("? ", "?\n").replace("! ", "!\n").split("\n")]
    for sentence in filter(None, sentences):
        words = sentence.split()
        parts = -(-len(words) // MAX_CAPTION_WORDS)
        size = -(-len(words) // parts)
        out += [" ".join(words[k:k + size]) for k in range(0, len(words), size)]
    return out


def sentences(text: str) -> list[str]:
    return [x.strip() for x in text.replace(". ", ".\n").replace("? ", "?\n").replace("! ", "!\n").split("\n") if x.strip()]


def demo_voices() -> list:
    sys.path.insert(0, str(ROOT))
    from api import tts

    return [v for v in (tts.parse_voice(VOICE) or tts.Voice("edge", VOICE, rate="+4%"), tts.parse_voice(VOICE_FALLBACK)) if v]


def sentence_cache(sentence: str, voice) -> Path:
    import hashlib

    d = TMP / "tts_cache"
    d.mkdir(exist_ok=True)
    return d / (hashlib.sha1(f"{voice}|{sentence}".encode()).hexdigest()[:16] + ".wav")


def prespeak(lines: list[str]) -> None:
    """Render every voice-over sentence with the local engine in one model load (api/tts.batch)."""
    sys.path.insert(0, str(ROOT))
    from api import tts

    v = demo_voices()[0]
    todo = [(s, v, sentence_cache(s, v)) for line in lines for s in sentences(line)]
    tts.batch([j for j in todo if not j[2].exists()])


def say(text: str, out: Path) -> float:
    """English voice-over line: each sentence spoken by the stand-in narrator voice (api/tts.py), SENTENCE_GAP of
    quiet between sentences, loudness-normalised to -16 LUFS, 48 kHz stereo. Returns its length in seconds."""
    sys.path.insert(0, str(ROOT))
    from api import tts

    voices = demo_voices()
    parts: list[Path] = []
    for k, sentence in enumerate(sentences(text)):
        piece = out.with_name(f"{out.stem}_s{k}.wav")
        cached = sentence_cache(sentence, voices[0])
        if cached.exists():  # pre-rendered by prespeak()
            parts.append(tts.finish(cached, piece, sr=48000))
            continue
        got = tts.speak(sentence, voices, piece, sr=48000)
        if not got:
            raise RuntimeError(f"no voice could speak: {sentence!r}")
        parts.append(got[0])
    gap = out.with_name("gap.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t",
                    f"{SENTENCE_GAP:.3f}", str(gap)], check=True)
    seq = [p for part in parts for p in (part, gap)][:-1]
    inputs = [a for p in seq for a in ("-i", str(p))]
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex",
                    "".join(f"[{i}:a]" for i in range(len(seq))) + f"concat=n={len(seq)}:v=0:a=1,{tts.loudnorm_filter()}",
                    "-ar", "48000", "-ac", "2", str(out)], check=True)
    for p in parts:
        p.unlink(missing_ok=True)
    return probe_seconds(out)


def probe_seconds(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "C:/Windows/Fonts/georgiab.ttf",
              "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def still_card(out: Path, title: str, sub: str, image: Path | None = None) -> Path:
    im = Image.new("RGB", (W, H), (27, 15, 7))
    if image and image.exists():
        pic = Image.open(image).convert("RGB")
        pic.thumbnail((W - 160, H - 580))
        im.paste(pic, ((W - pic.width) // 2, 30))
    d = ImageDraw.Draw(im)
    # 1080p layout: title and subtitle above the end-card lines (H-385..H-277); the bottom ~290 px stay free for a
    # two-line burned-in caption (71 px DejaVu Sans, 82 px margin), so no caption ever covers the card's text
    for text, f, y in ((title, font(64), H - 540), (sub, font(32), H - 455)):
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2, y), text, font=f, fill=(227, 177, 79) if f.size == 64 else (251, 239, 213))  # type: ignore[union-attr]
    im.save(out)
    return out


def add_qr(card: Path) -> None:
    """QR to the app in the close shot's corner; labelled PLACEHOLDER until PUBLIC_BASE_URL is set."""
    sys.path.insert(0, str(ROOT))
    from api import qr

    im = Image.open(card).convert("RGB")
    code = qr.image(qr.app_url(), box=6).resize((170, 170), Image.Resampling.NEAREST)
    x, y = W - 170 - 28, 28
    im.paste(code, (x, y))
    d = ImageDraw.Draw(im)
    label = "PLACEHOLDER link" if qr.is_placeholder() else qr.base_url().split("://", 1)[-1][:24]
    f = font(16)
    d.text((x + (170 - d.textlength(label, font=f)) / 2, y + 176), label, font=f,
           fill=(255, 140, 120) if qr.is_placeholder() else (251, 239, 213))
    im.save(card)


def print_card(job: dict) -> Path:
    """The printable-puppets PDF, page 2 (first puppet) beside page 1 (how-to), as a still for the print shot."""
    pdf = TMP / "puppets.pdf"
    if not pdf.exists():
        pdf.write_bytes(httpx.get(f"{BASE}/api/jobs/{job['id']}/puppets.pdf", trust_env=False, timeout=120).content)
    pages = []
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-png", "-r", "60", "-f", "1", "-l", "2", str(pdf), str(TMP / "pdfpage")], check=True)
        pages = sorted(TMP.glob("pdfpage*.png"))
    im = Image.new("RGB", (W - 160, H - 330), (27, 15, 7))
    x = 0
    for pth in pages[:2]:
        pg = Image.open(pth).convert("RGB")
        pg.thumbnail(((W - 200) // 2, H - 340))
        im.paste(pg, (x + 10, 5))
        x += pg.width + 20
    tmp = TMP / "pdfpair.png"
    im.save(tmp)
    return still_card(TMP / "print.png", "Cetak wayang · Print the puppets", "Gunting, tusuk sate, senter · cut, skewer, torch",
                      tmp if pages else None)


def wait_status(c: httpx.Client, jid: str, wanted: set[str], timeout: float = 1200) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = c.get(f"/api/jobs/{jid}").json()
        if j["status"] in wanted:
            return j
        time.sleep(0.5)
    raise TimeoutError(wanted)


def kelir_show(page, mark=None, slow: float = 1.0) -> None:
    """Perform on /kelir/{id}: drag the first puppet across the lamp-lit screen, lift it toward the lamp and back,
    turn the second one, tap the gunungan for the next scene, flip to the dalang's colour side."""
    page.wait_for_selector("[data-testid=kelir][data-ready='1']", timeout=30000)
    page.wait_for_function("document.querySelector('[data-testid=kelir]').dataset.state", timeout=10000)
    page.evaluate("document.querySelector('[data-testid=kelir]').scrollIntoView({block: 'center'})")
    time.sleep(0.8 * slow)
    if mark:
        mark("kelir")
    box = page.locator("[data-testid=kelir]").bounding_box()
    st = json.loads(page.get_attribute("[data-testid=kelir]", "data-state") or "[]")
    if not box or not st:
        time.sleep(4)
        return
    p0 = st[0]
    sx, sy = box["x"] + p0["x"] * box["width"], box["y"] + p0["y"] * box["height"]
    page.mouse.move(sx, sy)
    page.mouse.down()
    for i in range(1, 41):  # walk right, bobbing like a puppet's step
        page.mouse.move(sx + box["width"] * 0.32 * i / 40, sy - 18 * abs(((i % 10) - 5) / 5))
        time.sleep(0.035 * slow)
    time.sleep(0.6 * slow)
    page.mouse.up()
    time.sleep(0.8 * slow)
    page.focus("[data-testid=kelir]")
    for _ in range(8):  # back toward the middle with the keyboard (the accessible path)
        page.keyboard.press("ArrowLeft")
        time.sleep(0.08 * slow)
    if len(st) > 1:
        q = st[1]
        qx, qy = box["x"] + q["x"] * box["width"], box["y"] + q["y"] * box["height"]
        page.mouse.dblclick(qx, qy)  # double tap: the second puppet turns to face the first
        time.sleep(1.0 * slow)
    page.mouse.click(box["x"] + 0.89 * box["width"], box["y"] + 0.5 * box["height"])  # the gunungan sweeps
    time.sleep(2.6 * slow)
    toggle = page.get_by_role("button", name="Sisi dalang · Dalang's side (colour)")
    if toggle.count():
        toggle.first.click()
        # the button sits under the stage; bring the stage back so the colour side is on camera
        page.evaluate("document.querySelector('[data-testid=kelir]').scrollIntoView({block: 'center'})")
        time.sleep(1.8 * slow)
    if mark:
        mark("kelir")


SCROLL_PAD = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); "
              "s.textContent = 'html { scroll-padding-top: 88px; }'; document.head.appendChild(s); });")


def record() -> tuple[Path, dict[str, tuple[float, float]], dict]:
    """Drive the real app in Chromium and note when each segment starts and ends (seconds into the recording)."""
    marks: dict[str, list[float]] = {}
    api = httpx.Client(base_url=BASE, trust_env=False, timeout=60)
    kwargs = launch_kwargs()  # RuntimeError when there is no browser -> main() falls back to stills
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**kwargs)  # type: ignore[arg-type]
        ctx = browser.new_context(viewport={"width": RW, "height": RH}, record_video_dir=str(TMP),
                                  record_video_size={"width": RW, "height": RH})
        # scrollIntoView stops below the sticky site header, so no heading is cut in half under it on camera
        ctx.add_init_script(SCROLL_PAD)
        page = ctx.new_page()
        t0 = time.time()

        def mark(key: str) -> None:
            marks.setdefault(key, []).append(time.time() - t0)

        page.goto(BASE + "/")
        page.wait_for_selector("[data-testid=hero-tell]")
        time.sleep(1.0)
        mark("landing")  # the hero: the sample film looping on the kelir, one big 'Tell a story' button
        time.sleep(3.0)
        starter = page.locator("[data-testid=story-starters] button", has_text="Kancil dan Buaya")
        if starter.count():  # one-tap Story Starter: the read-aloud card appears
            starter.first.scroll_into_view_if_needed()
            time.sleep(1.2)
            starter.first.click()
            time.sleep(2.5)
        if AUDIO.is_file():  # the voice path: upload the story recording (MOCK sample unless --audio is given)
            page.get_by_role("button", name="Unggah").click()
            time.sleep(0.6)
            page.set_input_files("input[type=file]", str(AUDIO))
            time.sleep(1.0)
        else:
            page.get_by_role("button", name="Ketik").click()
            page.fill("textarea", STORY)
            time.sleep(0.6)
        options = page.locator("details:has(summary:has-text('Pilihan'))").first
        if options.count() and options.get_attribute("open") is None:  # the folded Options panel
            options.locator("summary").scroll_into_view_if_needed()
            options.locator("summary").click()
            time.sleep(0.6)
        if AUDIO.is_file():
            page.click("text=Suaraku sendiri")  # the child's own voice narrates
            time.sleep(0.8)
        page.locator("text=Mode Gara-gara").first.scroll_into_view_if_needed()
        page.click("text=Mode Gara-gara")  # turn on Gara-gara
        time.sleep(0.8)
        page.click("text=Jadikan wayang")
        page.wait_for_url("**/film/**")
        mark("landing")
        jid = page.url.rstrip("/").split("/")[-1]
        page.wait_for_selector("[data-testid=pipeline-theatre]", timeout=20000)
        time.sleep(0.5)
        mark("progress")  # the pipeline theatre: each Meta model a troupe member, lit by the live trace
        page.evaluate("document.querySelector('[data-testid=pipeline-theatre]').scrollIntoView({block: 'start', behavior: 'smooth'})")
        job = wait_status(api, jid, {"choice", "review"})
        time.sleep(0.4)
        mark("progress")
        page.reload()
        if job["status"] == "choice":
            page.wait_for_selector("[data-testid=classroom-vote]")
            page.evaluate("document.querySelector('[data-testid=classroom-vote]').scrollIntoView({block: 'start'})")
            time.sleep(0.8)
            mark("garagara")
            page.get_by_role("button", name="Buka voting · Open the vote").click()
            page.wait_for_selector("img[alt^='QR code: scan to vote']")
            time.sleep(0.4)
            page.evaluate("document.querySelector('[data-testid=classroom-vote]').scrollIntoView({block: 'start'})")
            time.sleep(1.5)
            for voter, opt in (("hp-ani", 1), ("hp-budi", 0), ("hp-citra", 1)):
                api.post(f"/api/jobs/{jid}/vote", json={"option": opt, "voter": voter}).raise_for_status()
                time.sleep(1.8)  # the class screen polls every 1.5 s: the bars grow vote by vote
            page.mouse.wheel(0, 260)
            time.sleep(1.2)
            page.get_by_role("button", name="Tutup voting, lanjutkan cerita · Close the vote and continue").click()
            time.sleep(1.5)
            mark("garagara")
            wait_status(api, jid, {"review"})
            page.reload()
        page.wait_for_selector("text=Storyboard")
        time.sleep(1.0)
        mark("trace")  # Penjaga Budaya, consistency and the models receipt, then the agent trace, opened
        page.evaluate("document.querySelector('[data-testid=models-receipt]')?.scrollIntoView({block: 'start'})")
        time.sleep(3.0)
        page.mouse.wheel(0, 300)
        time.sleep(2.0)
        page.evaluate("document.querySelectorAll('[data-testid=agent-trace], [data-testid=agent-trace] details')"
                      ".forEach(d => d.open = true)")
        page.evaluate("document.querySelector('[data-testid=agent-trace]')?.scrollIntoView({block: 'start'})")
        time.sleep(2.5)
        page.mouse.wheel(0, 260)
        time.sleep(2.0)
        mark("trace")
        page.mouse.wheel(0, -6000)
        time.sleep(0.5)
        # by role: the opened agent trace can also contain the words "Bring it to life"
        page.get_by_role("button", name="Bring it to life").first.click()
        job = wait_status(api, jid, {"done"})
        page.reload()
        page.wait_for_selector("video")
        try:  # the read-along panel appears once the film's captions are fetched; scroll to it only then
            page.wait_for_selector("[data-testid=read-along]", timeout=15000)
        except Exception:  # noqa: BLE001 - no captions: the shot still shows the player
            pass
        mark("share")
        page.evaluate("(() => { const v = document.querySelector('video'); if (v) { v.muted = true; v.currentTime = 12; v.play(); } })()")
        time.sleep(0.6)
        page.evaluate("document.querySelector('[data-testid=read-along]')?.scrollIntoView({block: 'center'})")
        time.sleep(4.5)
        page.mouse.wheel(0, -2000)
        time.sleep(0.4)
        page.get_by_role("button", name="Share to gallery").first.click()
        time.sleep(1.2)
        try:
            page.wait_for_selector("[data-testid=viral-extras]", timeout=20000)
            page.evaluate("document.querySelector('[data-testid=viral-extras]').scrollIntoView({block: 'center'})")
            time.sleep(1.5)
            page.get_by_role("button", name="Lihat GIF · Preview").click()
            time.sleep(0.6)
            page.evaluate("document.querySelector('[data-testid=viral-extras]').scrollIntoView({block: 'center'})")
            time.sleep(3.0)
        except Exception:  # noqa: BLE001 - no sticker endpoint: the share bar still shows
            time.sleep(2)
        page.goto(f"{BASE}/pentas")
        page.wait_for_selector("[data-testid=pentas-wall]")
        time.sleep(2.5)
        mark("share")
        page.goto(f"{BASE}/kelir/{jid}")
        kelir_show(page, mark)
        ctx.close()
        video = Path(page.video.path()) if page.video else None
        # the same performance on a phone, for the vertical teaser (9:16)
        try:
            pctx = browser.new_context(viewport={"width": PHONE_VW, "height": PHONE_VH}, device_scale_factor=2.5,
                                       has_touch=True, record_video_dir=str(TMP / "phone"),
                                       record_video_size={"width": PHONE_VW, "height": PHONE_VH})
            pp = pctx.new_page()
            pp.goto(f"{BASE}/kelir/{jid}")
            kelir_show(pp, None, slow=0.8)
            pctx.close()
            if pp.video:
                shutil.copy(pp.video.path(), TMP / "kelir_phone.webm")
        except Exception as e:  # noqa: BLE001 - the vertical teaser then opens on the film
            print(f"phone kelir recording skipped: {e}", flush=True)
        browser.close()
    assert video and video.exists(), "no browser recording"
    spans = {k: (v[0], v[-1]) for k, v in marks.items()}
    return video, spans, job


def record_with_retry() -> tuple[Path, dict[str, tuple[float, float]], dict]:
    """Playwright records video with its own small ffmpeg build; fetch it once if it is missing."""
    try:
        return record()
    except Exception as e:  # noqa: BLE001
        if "ffmpeg" not in str(e).lower():
            raise
        print("Playwright's ffmpeg is missing; running `playwright install ffmpeg`...", flush=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "ffmpeg"], check=True, timeout=300)
        return record()


STILLS = {"landing": "r5/home.png", "progress": "r5/pipeline-theatre.png", "garagara": "r5/classroom-vote.png",
          "trace": "10-agent-trace.png", "share": "4-player.png", "kelir": "r5/kelir-live.png"}


def make_film_via_api() -> dict:
    """No-browser fallback: drive the same flow over HTTP (create with review, approve, wait for the film)."""
    api = httpx.Client(base_url=BASE, trust_env=False, timeout=60)
    form = {"language": "id", "style": "classic", "review": "true", "gara_gara": "true"}
    if AUDIO.is_file():
        with open(AUDIO, "rb") as f:
            r = api.post("/api/jobs", data=form, files={"audio": (AUDIO.name, f, "audio/mpeg")})
    else:
        r = api.post("/api/jobs", data={**form, "text": STORY})
    r.raise_for_status()
    jid = r.json()["id"]
    j = wait_status(api, jid, {"review", "choice"})
    if j["status"] == "choice":
        api.post(f"/api/jobs/{jid}/choice", data={"text": j["gara_gara"]["options"][1]}).raise_for_status()
        wait_status(api, jid, {"review"})
    api.post(f"/api/jobs/{jid}/approve").raise_for_status()
    job = wait_status(api, jid, {"done"})
    api.post(f"/api/jobs/{jid}/share", json={"public": True})
    return job


def cut(src: Path, a: float, b: float, target: float, out: Path) -> Path:
    """Take [a, b] from the recording and speed it up or slow it down to last `target` seconds."""
    length = max(0.5, b - a)
    factor = target / length
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{length:.2f}", "-i", str(src),
                    "-vf", f"setpts={factor:.4f}*PTS,fps=30,scale={W}:{H}:flags=lanczos", "-an", "-c:v", "libx264", "-preset",
                    "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def image_clip(img: Path, seconds: float, out: Path) -> Path:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "30", "-t", f"{seconds:.2f}", "-i", str(img),
                    "-vf", f"scale={W}:{H},zoompan=z='min(zoom+0.0006,1.06)':d=1:s={W}x{H}:fps=30", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def record_or_stills() -> tuple[Path | None, dict[str, tuple[float, float]], dict]:
    print("Recording the app...", flush=True)
    try:
        return record_with_retry()
    except Exception as e:  # noqa: BLE001 - any recording failure still yields a video
        import traceback

        frames = [f"{f.name}:{f.lineno}" for f in traceback.extract_tb(e.__traceback__) if f.filename == __file__]
        print(f"Browser recording unavailable ({str(e).splitlines()[0]}, at {', '.join(frames)}).\n"
              "Falling back to stills + ffmpeg.", flush=True)
        return None, {}, make_film_via_api()


def real_file(stem: str, exts: tuple[str, ...]) -> Path | None:
    """Malik's own file for a shot in --real (docs/demo/real), if he dropped one there."""
    for ext in exts:
        p = REAL / f"{stem}{ext}"
        if p.is_file():
            return p
    return None


CLIP_EXTS = (".mp4", ".mov", ".m4v", ".webm")
VO_EXTS = (".wav", ".m4a", ".mp3", ".aac", ".ogg")


def real_clip(key: str) -> Path | None:
    stem = next((k for k, v in REAL_CLIPS.items() if v == key), None)
    return real_file(stem, CLIP_EXTS) if stem else None


def fit_clip(src: Path, seconds: float, out: Path, start: float = 0.0, keep_audio: Path | None = None) -> Path:
    """A phone clip (any size or orientation) letterboxed into W x H at 30 fps; optionally its sound to keep_audio."""
    vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps=30,setsar=1"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{seconds:.2f}", "-i", str(src),
                    "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    str(out)], check=True)
    if keep_audio is not None:
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{seconds:.2f}", "-i",
                            str(src), "-vn", "-ar", "48000", "-ac", "2", str(keep_audio)])
        if r.returncode != 0:  # a silent clip
            silence(seconds, keep_audio)
    return out


def silence(seconds: float, out: Path) -> Path:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t",
                    f"{seconds:.2f}", str(out)], check=True)
    return out


def voice_hook(seconds: float, out_v: Path, out_a: Path, labelled: bool) -> None:
    """0:00-0:03: the child's voice over black with its waveform (the stand-in recording is labelled as such)."""
    label = "Stand-in voice (synthetic sample). A real recording of a child goes here." if labelled else ""
    draw = (f",drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{label}':fontcolor=0xFFB08C:"
            f"fontsize=30:x=(w-text_w)/2:y=h*0.18") if label and Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf").exists() else ""
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-t", f"{seconds:.2f}", "-i", str(AUDIO), "-filter_complex",
                    f"[0:a]aformat=channel_layouts=mono,showwaves=s={W}x{H // 3}:mode=cline:colors=0xE3B14F:rate=30[w];"
                    f"color=c=black:s={W}x{H}:r=30:d={seconds:.2f}[bg];[bg][w]overlay=0:(H-h)/2{draw},format=yuv420p[v]",
                    "-map", "[v]", "-t", f"{seconds:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    str(out_v)], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-t", f"{seconds:.2f}", "-i", str(AUDIO), "-af",
                    f"apad,atrim=0:{seconds:.2f}", "-ar", "48000", "-ac", "2", str(out_a)], check=True)


def film_part(film: Path, start: float, seconds: float, out_v: Path, out_a: Path) -> None:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{seconds:.2f}", "-i", str(film),
                    "-vf", f"scale={W}:{H}:flags=lanczos,fps=30", "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", str(out_v)], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{seconds:.2f}", "-i", str(film),
                    "-vn", "-af", f"apad,atrim=0:{seconds:.2f}", "-ar", "48000", "-ac", "2", str(out_a)], check=True)


def mix(bed: Path, vo: Path | None, seconds: float, out: Path, bed_volume: float = 1.0) -> Path:
    """Shot sound: the bed (film sound, clip sound or silence) with the voice-over on top, exactly `seconds` long."""
    if vo is None:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(bed), "-af",
                        f"volume={bed_volume},apad,atrim=0:{seconds:.2f}", "-ar", "48000", "-ac", "2", str(out)], check=True)
        return out
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(bed), "-i", str(vo), "-filter_complex",
                    f"[0:a]volume={bed_volume},apad,atrim=0:{seconds:.2f}[b];[1:a]aresample=48000,adelay=300|300[v];"
                    f"[b][v]amix=inputs=2:duration=first:normalize=0", "-ar", "48000", "-ac", "2", str(out)], check=True)
    return out


MIN_SECONDS = {"garagara": 13.0, "kelir": 18.0, "why": 10.0, "landing": 11.0, "progress": 28.0, "trace": 14.0,
               "share": 16.0, "print": 8.0, "close": 12.0, "film1": FILM1_SECONDS}
# the close card holds this long after its last caption, so the card's own lines are read without a caption over them
CLOSE_TAIL = 2.5


def end_card() -> Path:
    card = still_card(TMP / "close.png", "Dalang AI",
                      "A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film.",
                      ROOT / "docs" / "architecture.png")
    sys.path.insert(0, str(ROOT))
    from api import qr

    im = Image.open(card).convert("RGB")
    d = ImageDraw.Draw(im)
    lines = ["Muse Voice Transcribe · Muse Spark 1.2 · Muse Spark 1.3 · Muse Image · SAM 3.1 · Muse Wonder",
             ("Live app: " + qr.base_url().split("://", 1)[-1]) if not qr.is_placeholder() else
             "Live app link: added after deploy (PLACEHOLDER)", "MIT licensed · github.com/ragilmalik/dalang-ai (planned)"]
    f = font(28)
    for k, text in enumerate(lines):  # below the subtitle (H-455), above the caption area (bottom 290 px)
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2, H - 395 + k * 40), text, font=f, fill=(251, 239, 213))
    im.save(card)
    if not qr.is_placeholder():  # a real QR only; never a placeholder one
        add_qr(card)
    return card


# DEMO_ENCODE_DIR=<local dir>: encode and remux on a local disk, then copy the finished file into OUT (network
# filesystems can fail with an I/O error when ffmpeg seeks back to write the trailer or move the moov atom)
ENC = Path(os.environ.get("DEMO_ENCODE_DIR") or TMP)


def faststart(path: Path, dest: Path | None = None) -> None:
    """Move the moov atom to the front with a separate copy pass, then (if dest is given) copy the result there with a
    plain sequential write."""
    ENC.mkdir(parents=True, exist_ok=True)
    tmp = ENC / (path.stem + ".fs" + path.suffix)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-c", "copy", "-map", "0",
                    "-movflags", "+faststart", str(tmp)], check=True)
    if dest is None:
        tmp.replace(path)
        return
    shutil.copyfile(tmp, dest)
    if dest.stat().st_size != tmp.stat().st_size:
        raise OSError(f"copy to {dest} is incomplete")
    tmp.unlink(missing_ok=True)


def teasers(final: Path, job: dict, segs: list[tuple[str, float]]) -> list[Path]:
    """Two cuts for X that open on Kelir Live. 16:9 (60 s): the Kelir Live shot, then the film's opening, the first
    scenes and the classroom vote, then the close card. 9:16 (30-45 s): the phone Kelir Live performance, then the
    vertical film and an end card."""
    out = []
    at: dict[str, tuple[float, float]] = {}
    t = 0.0
    for key, secs in segs:
        at[key] = (t, t + secs)
        t += secs
    parts: list[tuple[float, float]] = []
    if "kelir" in at:
        parts.append(at["kelir"])
    parts.append((at["opening"][0], at["garagara"][1]))
    used = sum(b - a for a, b in parts)
    c0, c1 = at["close"]
    parts.append((max(c0, c1 - max(3.0, 60.0 - used)), c1))
    total = sum(b - a for a, b in parts)
    # one seeked input per part (trimming a single input out of order makes ffmpeg buffer GBs of decoded 1080p frames)
    ins = [x for a, b in parts for x in ("-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", str(final))]
    fc = "".join(f"[{k}:v]setpts=PTS-STARTPTS[v{k}];[{k}:a]asetpts=PTS-STARTPTS[a{k}];" for k in range(len(parts)))
    fc += "".join(f"[v{k}][a{k}]" for k in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=1[cv][ca];"
    fc += f"[cv]fade=t=out:st={total - 1:.2f}:d=1[v];[ca]afade=t=out:st={total - 1.5:.2f}:d=1.5[au]"
    t60, t60_raw = OUT / "teaser_60s.mp4", ENC / "teaser_60s_raw.mp4"
    ENC.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", fc, "-map", "[v]", "-map",
                    "[au]", "-t", "60", "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", str(t60_raw)], check=True)
    faststart(t60_raw, t60)
    out.append(t60)
    vurl = (job.get("videos") or {}).get("vertical")
    vert = TMP / "film_vertical.mp4"
    if vurl and not vert.exists():
        vert.write_bytes(httpx.get(BASE + vurl if vurl.startswith("/") else vurl, trust_env=False, timeout=120).content)
    if vert.exists():
        VW, VH = 1080, 1920
        phone = TMP / "kelir_phone.webm"
        lead = 0.0
        lab = TMP / "kelir_phone.mp4"
        if phone.exists():
            plen = probe_seconds(phone)
            # the drag, turn and gunungan sweep; the last ~2.4 s (the colour toggle scrolls the stage away) are left out
            lead = max(1.0, min(10.0, plen - 4.0))
            start = max(0.0, plen - lead - 2.4)
            label = ("drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='Kelir Live · placeholder art "
                     "(fake Meta API)':fontcolor=0xFFB08C:fontsize=34:x=(w-text_w)/2:y=h*0.215:box=1:boxcolor=0x000000AA:"
                     "boxborderw=14," if job.get("offline") else "")
            # crop to the phone viewport (older recordings padded a 432x768 page into 1080x1920 with grey)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{lead:.2f}", "-i", str(phone),
                            "-vf", f"crop='min(iw,{PHONE_VW})':'min(ih,{PHONE_VH})':0:0,scale={VW}:{VH}:flags=lanczos,{label}"
                            "fps=30,setsar=1,format=yuv420p", "-an", "-c:v",
                            "libx264", "-preset", "veryfast", "-crf", "20", str(lab)], check=True)
        body = min(28.0 if lead else 36.0, probe_seconds(vert))
        card = Image.new("RGB", (VW, VH), (27, 15, 7))
        d = ImageDraw.Draw(card)
        y = 640
        for text, size, color in (("Dalang AI", 96, (227, 177, 79)), ("A child tells a story out loud.", 44, (251, 239, 213)),
                                  ("Six Meta models perform it", 44, (251, 239, 213)),
                                  ("as a Javanese shadow-puppet film.", 44, (251, 239, 213)),
                                  ("#DalangCilik", 52, (227, 177, 79))):
            f = font(size)
            d.text(((VW - d.textlength(text, font=f)) / 2, y), text, font=f, fill=color)
            y += size + 40
        if job.get("offline"):
            f = font(30)
            msg = "Placeholder art (fake Meta API)"
            d.text(((VW - d.textlength(msg, font=f)) / 2, VH - 220), msg, font=f, fill=(255, 176, 140))
        cpath = TMP / "vcard.png"
        card.save(cpath)
        tv, tv_raw = OUT / "teaser_vertical.mp4", ENC / "teaser_vertical_raw.mp4"
        inputs = (["-i", str(lab), "-f", "lavfi", "-t", f"{lead:.2f}", "-i", "anullsrc=r=48000:cl=stereo"] if lead else [])
        k = 2 if lead else 0  # input index of the vertical film
        vparts = "[0:v]setsar=1[l];" if lead else ""
        fc = (vparts + f"[{k}:v]scale={VW}:{VH}:flags=lanczos,fps=30,setsar=1[a];[{k + 1}:v]scale={VW}:{VH},fps=30,setsar=1[b];"
              + ("[l][a][b]concat=n=3" if lead else "[a][b]concat=n=2") + ":v=1:a=0,format=yuv420p[v];"
              + f"[{k}:a]aresample=48000,afade=t=out:st={body - 1.5:.2f}:d=1.5[x];"
              + ("[1:a][x]" if lead else "[x]") + f"[{k + 2}:a]concat=n={3 if lead else 2}:v=0:a=1[au]")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-t", f"{body:.2f}", "-i", str(vert), "-loop", "1",
                        "-t", "4", "-i", str(cpath), "-f", "lavfi", "-t", "4", "-i", "anullsrc=r=48000:cl=stereo",
                        "-filter_complex", fc, "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "22", "-c:a", "aac", "-b:a", "160k", str(tv_raw)], check=True)
        faststart(tv_raw, tv)
        out.append(tv)
    return out


def prefetch(job: dict) -> None:
    """Download the film (16:9 and 9:16), poster and puppets PDF into TMP right after recording."""
    for name, url in (("film.mp4", (job.get("videos") or {}).get("landscape")),
                      ("film_vertical.mp4", (job.get("videos") or {}).get("vertical")), ("poster.jpg", job.get("poster")),
                      ("puppets.pdf", f"/api/jobs/{job['id']}/puppets.pdf" if job.get("id") else None)):
        dest = TMP / name
        if url and not dest.exists():
            try:
                dest.write_bytes(httpx.get(BASE + url if url.startswith("/") else url, trust_env=False, timeout=120).content)
            except httpx.HTTPError as e:
                print(f"prefetch {name} failed: {e}", flush=True)


def shot_seconds(key: str, vo_seconds: float) -> float:
    """How long a shot runs, given its voice-over length (0 for none). Same rules as main()."""
    if key == "voice":
        return VOICE_SECONDS
    if key in ("opening", "film1", "film2"):
        return {"opening": OPENING_SECONDS, "film1": FILM1_SECONDS, "film2": FILM2_SECONDS}[key]
    secs = max(MIN_SECONDS.get(key, 0.0), vo_seconds + 1.0 if vo_seconds else 0.0)
    if key == "close" and vo_seconds:
        secs = max(secs, vo_seconds + 0.8 + CLOSE_TAIL)
    return secs


def plan() -> float:
    """Dry run: speak every voice-over line with the current DEMO_VOICE / DEMO_SENTENCE_GAP and print the shot list
    timing. The film shots have a fixed length, so a line over them that runs past it is flagged."""
    prespeak([line for _key, line in SCRIPT if line])
    total = 0.0
    for key, line in SCRIPT:
        vo = say(line, TMP / f"vo_{key}.wav") if line else 0.0
        secs = shot_seconds(key, vo)
        total += secs
        flag = "  <- voice runs past the shot" if vo and vo + 0.3 > secs else ""
        print(f"{key:9s} vo {vo:5.1f} s  shot {secs:5.1f} s{flag}", flush=True)
    print(f"total {total:.1f} s ({int(total // 60)}:{total % 60:04.1f}) with {VOICE}, gap {SENTENCE_GAP} s: "
          + ("fits under 3:00" if total < 180 else "OVER 3:00"), flush=True)
    return total


def main() -> None:
    if _A.plan:
        plan()
        return
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH")
    rec: Path | None
    spans: dict[str, tuple[float, float]]
    session = TMP / "session.json"
    if REUSE:
        saved = json.loads(session.read_text()) if session.exists() else {}
        rec, spans, job = (Path(saved["rec"]) if saved.get("rec") and Path(saved["rec"]).exists() else None), \
            {k: tuple(v) for k, v in (saved.get("spans") or {}).items()}, saved.get("job", {"offline": True})
        print(f"Reusing {TMP}", flush=True)
    else:
        rec, spans, job = record_or_stills()
        session.write_text(json.dumps({"job": job, "spans": spans, "browser": rec is not None, "rec": str(rec) if rec else ""}))
        prefetch(job)  # everything later steps need from the server, so --reuse works without it
    film = TMP / "film.mp4"
    if not film.exists():
        film_url = job["videos"]["landscape"]
        film.write_bytes(httpx.get(BASE + film_url if film_url.startswith("/") else film_url, trust_env=False, timeout=120).content)
    print("Segments", {k: (round(a, 1), round(b, 1)) for k, (a, b) in spans.items()}, flush=True)
    film_len = probe_seconds(film)
    real_used: dict[str, str] = {}

    pieces: list[tuple[Path, Path, float, str]] = []  # (video, sound, seconds, caption text)
    prespeak([line for key, line in SCRIPT if line and not real_file(f"vo_{key}", VO_EXTS)])
    for key, line in SCRIPT:
        vid, aud, bed = TMP / f"seg_{key}.mp4", TMP / f"aud_{key}.wav", TMP / f"bed_{key}.wav"
        own_vo = real_file(f"vo_{key}", VO_EXTS)
        clip = real_clip(key)
        vo: Path | None = None
        if own_vo:  # Malik's own voice for this shot; captions use his first-person line when there is one
            vo = TMP / f"vo_{key}.wav"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(own_vo), "-ar", "48000", "-ac", "2", str(vo)], check=True)
            line = REAL_LINES.get(key, line)
            real_used[f"vo_{key}"] = own_vo.name
        elif line:
            vo = TMP / f"vo_{key}.wav"
            say(line, vo)
        secs = shot_seconds(key, probe_seconds(vo) if vo else 0.0)  # the close card holds after its last line
        if key == "voice":
            if clip:
                secs = min(8.0, probe_seconds(clip))
                fit_clip(clip, secs, vid, keep_audio=aud)
                real_used["A_child_tells"] = clip.name
                pieces.append((vid, aud, probe_seconds(vid), ""))
            else:
                voice_hook(VOICE_SECONDS, vid, aud, labelled=True)
                pieces.append((vid, aud, probe_seconds(vid), "(stand-in voice) Dulu ada kancil yang pintar..."))
            continue
        if key in ("opening", "film1", "film2"):
            start = {"opening": 0.0, "film1": OPENING_SECONDS, "film2": OPENING_SECONDS + FILM1_SECONDS}[key]
            want = {"opening": OPENING_SECONDS, "film1": FILM1_SECONDS, "film2": FILM2_SECONDS}[key]
            want = min(want, max(1.0, film_len - start))
            film_part(film, start, want, vid, bed)
            mix(bed, vo, probe_seconds(vid), aud, bed_volume=0.4 if vo else 1.0)
            pieces.append((vid, aud, probe_seconds(vid), line))
            continue
        if clip:
            secs = max(secs, min(12.0, probe_seconds(clip)))
            fit_clip(clip, secs, vid, keep_audio=bed)
            real_used[next(k for k, v in REAL_CLIPS.items() if v == key)] = clip.name
            mix(bed, vo, probe_seconds(vid), aud, bed_volume=0.5 if vo else 1.0)
            pieces.append((vid, aud, probe_seconds(vid), line))
            continue
        if key == "close":
            image_clip(end_card(), secs, vid)
        elif key == "why":
            poster = TMP / "poster.jpg"
            if not poster.exists() and job.get("poster"):
                poster.write_bytes(httpx.get(BASE + job["poster"], trust_env=False, timeout=60).content)
            image_clip(still_card(TMP / "why.png", "Every child can be a dalang", "Semarang, Central Java",
                                  poster if poster.exists() else None), secs, vid)
        elif key == "print":
            image_clip(print_card(job), secs, vid)
        elif rec is None or key not in spans:
            image_clip(ROOT / "docs" / "screenshots" / STILLS[key], secs, vid)
        else:
            a, b = spans[key]
            cut(rec, a, b, secs, vid)
        real_secs = probe_seconds(vid)  # the clip's real length keeps voice and captions locked to the picture
        mix(silence(real_secs, bed), vo, real_secs, aud)
        pieces.append((vid, aud, real_secs, line))

    # captions (SRT) from the voice-over lines; over the film they sit at the top (the film burns in its own)
    srt: list[str] = []
    t = 0.0
    for i, (_vid, _aud, secs, line) in enumerate(pieces):
        top = "{\\an8}" if SCRIPT[i][0] in ("opening", "film1", "film2") else ""
        if line:
            chunks = caption_chunks(line)
            total = sum(len(ch.split()) for ch in chunks)
            at = t + 0.2
            span = max(1.0, min(secs - 0.4, (probe_seconds(TMP / f"vo_{SCRIPT[i][0]}.wav") + 0.3)
                                if (TMP / f"vo_{SCRIPT[i][0]}.wav").exists() else secs - 0.4))
            for ch in chunks:  # each cue stays up in proportion to its words, like the voice
                dur = span * len(ch.split()) / total
                srt.append(f"{len(srt) + 1}\n{srt_time(at)} --> {srt_time(at + dur)}\n{top}{ch}\n")
                at += dur
        t += secs
    (OUT / "dalang-ai-demo.srt").write_text("\n".join(srt), encoding="utf-8")

    lst = TMP / "v.txt"
    lst.write_text("".join(f"file '{p[0]}'\n" for p in pieces))
    alst = TMP / "a.txt"
    alst.write_text("".join(f"file '{p[1]}'\n" for p in pieces))
    vcat, acat = TMP / "vcat.mp4", TMP / "acat.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-an", "-c", "copy", str(vcat)], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(alst), "-c", "copy", str(acat)], check=True)
    srt_path = str(OUT / "dalang-ai-demo.srt").replace(":", r"\:")
    style = ("FontName=DejaVu Sans,FontSize=19,PrimaryColour=&H00C4ECFF,OutlineColour=&H50000000,BackColour=&H50000000,"
             "BorderStyle=3,Outline=5,Shadow=0,MarginV=22")
    final = OUT / "dalang-ai-demo.mp4"
    raw = ENC / "final_raw.mp4"
    raw.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(vcat), "-i", str(acat), "-vf",
                    f"subtitles='{srt_path}':force_style='{style}'", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                    "-threads", os.environ.get("DEMO_THREADS", "2"),  # fewer encoder threads: less memory on a shared 8 GB box
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", str(raw)], check=True)
    faststart(raw, final)  # +faststart as a separate local copy pass, then a plain copy into OUT
    (OUT / "voiceover.txt").write_text("\n\n".join(
        f"[{k}]\n{v or '(film plays with its own narration and gamelan)' if k != 'voice' else '(the child tells the story)'}"
        + (f"\n(Malik, first person: {REAL_LINES[k]})" if k in REAL_LINES else "") for k, v in SCRIPT), encoding="utf-8")
    (OUT / "timeline.json").write_text(json.dumps({"segments": [{"key": SCRIPT[i][0], "seconds": round(p[2], 2)}
                                                                for i, p in enumerate(pieces)],
                                                   "total_seconds": round(probe_seconds(final), 2),
                                                   "size": f"{W}x{H}", "real_footage": real_used,
                                                   "recorded_in_fake_mode": bool(job.get("offline")),
                                                   "browser_recording": rec is not None}, indent=1))
    thumb = OUT / "thumbnail.jpg"
    poster_url = job.get("poster")
    if poster_url and not REUSE:
        thumb.write_bytes(httpx.get(BASE + poster_url, trust_env=False, timeout=60).content)
    made = teasers(final, job, [(SCRIPT[i][0], p[2]) for i, p in enumerate(pieces)])
    print(f"Wrote {final} ({probe_seconds(final):.1f} s); " + ", ".join(f"{p.name} {probe_seconds(p):.1f} s" for p in made))


if __name__ == "__main__":
    main()
