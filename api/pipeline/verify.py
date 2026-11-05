"""Stage 8 - Verify (agentic): Muse Spark vision checks every generated picture against the script and
sends failures back to Muse Image with a corrected prompt, up to MAX_VERIFY_RETRIES times."""
from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Callable
from pathlib import Path

from .. import cost, fileio, meta_client, prompts, resilience
from ..config import settings
from ..jobs import Job
from ..schemas import Verdict

log = logging.getLogger("dalang.verify")


def check(image: Path, must_show: str, context: str = "") -> Verdict:
    """Muse Spark vision checks a picture against what it must show (right subject, no text, culturally fitting) and returns pass/fail, issues and a fix prompt for the redraw."""
    content = [
        {"type": "text", "text": f"The picture must be: {must_show}\n{('Script context: ' + context) if context else ''}\n"
                                 "Does it pass?"},
        meta_client.image_part(image),
    ]
    raw = meta_client.chat_json(
        [{"role": "system", "content": prompts.VERIFY_SYSTEM}, {"role": "user", "content": content}],
        prompts.VERIFY_SCHEMA, "verdict", model=settings.verify_model, reasoning_effort="low")
    return Verdict(**raw)


_key_locks: dict[str, threading.Lock] = {}
_key_locks_guard = threading.Lock()


def _lock_for(key: Path) -> threading.Lock:
    with _key_locks_guard:
        return _key_locks.setdefault(key.name, threading.Lock())


def cached_generate(prompt: str, out: Path, size: str) -> Path:
    """Muse Image with a prompt-hash cache, so rehearsing the demo doesn't pay twice for the same art.

    Two films with the same story ask for the same picture at the same moment, so: one painter per cache entry
    (a per-key lock), the entry is written atomically, a damaged entry is thrown away and painted again, and the
    copy into the film folder is atomic and checked too."""
    cache = settings.data_dir / "cache" / "img"
    cache.mkdir(parents=True, exist_ok=True)
    tag = "fake" if settings.fake_meta else settings.image_model
    key = cache / (hashlib.sha256(f"{tag}|{size}|{prompt}".encode()).hexdigest()[:32] + ".png")
    with _lock_for(key):
        if key.exists() and not fileio.image_ok(key):
            log.warning("image cache entry %s is damaged; painting it again", key.name)
            key.unlink(missing_ok=True)
        if not key.exists():
            meta_client.generate_image(prompt, key, size=size)
            if not fileio.image_ok(key):
                key.unlink(missing_ok=True)
                raise meta_client.MetaAPIError("Muse Image sent a picture that could not be read")
        else:
            cost.record_decision("same prompt painted before, reused from the image cache", agent="cache")
        data = key.read_bytes()
    fileio.atomic_write_bytes(out, data)
    if not fileio.image_ok(out):  # pragma: no cover - only a failing disk gets here
        fileio.atomic_write_bytes(out, data)
        if not fileio.image_ok(out):
            raise OSError("picture could not be saved")
    return out


PLACEHOLDER_LABEL = "PLACEHOLDER \u00b7 Muse Image was unavailable"


def placeholder(out: Path, stage: str, label: str, size: str) -> Path:
    """A labelled stand-in picture so a Muse Image outage never crashes a film: a flat kelir backdrop or a plain
    puppet silhouette, with the words PLACEHOLDER on it (the film page shows a badge too)."""
    from PIL import Image, ImageDraw

    from . import engine, mock

    seed = int(hashlib.sha256(label.encode()).hexdigest()[:6], 16)
    if stage == "casting":
        mock.puppet(out, label, "human", seed)
    else:
        mock.background(out, "calm", seed)
    im = Image.open(out).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    f = engine.font(max(18, W // 36))
    tw = d.textlength(PLACEHOLDER_LABEL, font=f)
    d.rectangle([0, 0, tw + 40, f.size + 30], fill=(20, 14, 10))
    d.text((20, 14), PLACEHOLDER_LABEL, fill=(255, 220, 150), font=f)
    im.save(out)
    return out


def make_verified(job: Job, stage: str, label: str, prompt: str, out: Path, must_show: str,
                  context: str = "", size: str = "1536x1024",
                  generate: Callable[[str, Path, str], Path] = cached_generate) -> dict:
    """Generate -> check -> (redraw with the checker's fix_prompt) loop. Returns a record for the UI."""
    history: list[dict] = []
    attempts = 0
    with cost.labelled(label):
        for attempt in range(settings.max_verify_retries + 1):
            attempts += 1
            try:
                generate(prompt, out, size)
            except cost.BudgetExceeded:
                raise
            except meta_client.MetaAPIError as e:
                # Muse Image failed even after its retries (or its breaker is open): a labelled placeholder keeps
                # the film going. A picture from an earlier attempt is kept instead when there is one.
                if attempt and out.exists():
                    resilience.fallback(job, stage, label, f"{label}: redraw failed ({str(e)[:60]}); kept the last picture",
                                        placeholder=False)
                    break
                placeholder(out, stage, label, size)
                resilience.fallback(job, stage, label, f"{label}: Muse Image unavailable ({str(e)[:60]}); "
                                                       "a labelled placeholder picture is used")
                return {"attempts": attempts, "rejections": history, "final_prompt": prompt, "placeholder": True}
            job.used(settings.image_model)
            try:
                verdict = check(out, must_show, context)
            except cost.BudgetExceeded:
                raise
            except Exception as e:  # noqa: BLE001 - the checker is a guard, not a gate: keep the picture
                resilience.fallback(job, stage, label, f"{label}: picture checker unavailable ({str(e)[:60]}); "
                                                       "picture kept unchecked", placeholder=False)
                break
            job.used(settings.verify_model)
            if verdict.passed:
                if attempt:
                    cost.record_decision(f"redraw {attempt} passed the check")
                break
            rejected = out.with_name(f"{out.stem}_rejected{attempt + 1}{out.suffix}")
            fileio.atomic_copy(out, rejected)
            issue = "; ".join(verdict.issues)[:160] or "did not match the script"
            history.append({"rejected": job.url(rejected), "issue": issue})
            if attempt < settings.max_verify_retries:
                cost.record_decision(f"checker rejected attempt {attempt + 1} ({issue}); redrawing with its fix_prompt")
                job.stage(stage, detail=f"Checker sent {label} back: {issue}. Redrawing...")
                prompt = verdict.fix_prompt or prompt
                out.unlink(missing_ok=True)
            else:
                cost.record_decision(f"still failing after {attempts} attempts ({issue}); keeping the last picture")
    return {"attempts": attempts, "rejections": history, "final_prompt": prompt}
