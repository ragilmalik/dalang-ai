"""Per-job cost meter (spec §8 cost guard). Prices from https://dev.meta.ai/docs/pricing-rate-limits (2026-10-30)."""
from __future__ import annotations

import contextlib
import re
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

PRICES_PER_M = {  # USD per 1M tokens (input, output), Standard mode
    "muse-wonder-1.0": (4.00, 20.00),
    "muse-spark-1.3": (1.25, 4.25),
    "muse-spark-1.2": (1.25, 4.25),
    "muse-spark-1.1": (1.25, 4.25),
}
IMAGE_USD = 0.01  # Muse Image, per generated image
SAM_IMAGE_USD = 2.50 / 1000  # SAM 3.1, per image segmented
ASR_USD_PER_HOUR = 0.18  # Muse Voice Transcribe


TRACE_MAX = 400  # newest entries kept per film


class BudgetExceeded(RuntimeError):
    pass


class Meter:
    def __init__(self, budget: float):
        self.budget = budget
        self.spent = 0.0
        self.items: dict[str, float] = {}
        self.lock = threading.Lock()
        # Agent trace ("Di balik kelir"): one entry per model call or agent decision, shown on the film page.
        self.trace: list[dict[str, Any]] = []
        self.tokens: dict[str, list[int]] = {}  # model -> [input tokens, output tokens], as the API reported them
        self.stage_of: Callable[[], str | None] = lambda: None
        # Called with a copy of the trace after every new entry, so the film's live state (and SSE) carries the
        # agent trace while the film is being made, not only when a run part ends.
        self.listener: Callable[[list[dict[str, Any]]], None] | None = None

    def charge(self, what: str, usd: float) -> None:
        with self.lock:
            self.spent += usd
            self.items[what] = self.items.get(what, 0.0) + usd

    def count(self, model: str, tin: int, tout: int) -> None:
        with self.lock:
            row = self.tokens.setdefault(model, [0, 0])
            row[0] += int(tin)
            row[1] += int(tout)

    def record(self, entry: dict[str, Any]) -> None:
        with self.lock:
            entry.setdefault("t", round(time.time(), 2))
            entry.setdefault("stage", self.stage_of())
            self.trace.append(entry)
            del self.trace[:-TRACE_MAX]
            snapshot = list(self.trace)
        if self.listener is not None:
            self.listener(snapshot)

    def check(self, upcoming: float = 0.0) -> None:
        if self.spent + upcoming > self.budget:
            raise BudgetExceeded(f"Job budget ${self.budget:.2f} reached (spent ${self.spent:.3f}).")


_local = threading.local()


def use(meter: Meter | None) -> None:
    _local.meter = meter


def current() -> Meter | None:
    return getattr(_local, "meter", None)


def _real() -> bool:
    from .config import settings

    return not settings.fake_meta and not settings.meta_replay_dir


def charge(what: str, usd: float) -> None:
    m = current()
    if m:
        m.charge(what, usd)
    if usd and _real():  # MAX_USD_TOTAL counts only money really spent on Meta's API
        from .resilience import ledger

        ledger.add(usd)


def check(upcoming: float = 0.0) -> None:
    """Hard caps before a paid call: the film's MAX_USD_PER_FILM and the deployment's MAX_USD_TOTAL."""
    m = current()
    if m:
        m.check(upcoming)
    if _real():
        from .resilience import ledger

        if not ledger.room(upcoming):
            raise BudgetExceeded(f"Total spend cap MAX_USD_TOTAL ${ledger.cap:.2f} reached "
                                 f"(spent ${ledger.total():.3f}). Raise it in .env to continue.")


def _tok(usage: dict) -> tuple[int, int]:
    tin = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    tout = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    return int(tin), int(tout)


def count_tokens(model: str, usage: dict | None) -> None:
    """Count the tokens a call used (for the film's models receipt) without pricing them."""
    m = current()
    if m and usage:
        m.count(model, *_tok(usage))


def charge_tokens(model: str, usage: dict | None) -> None:
    if not usage:
        return
    count_tokens(model, usage)
    if model not in PRICES_PER_M:
        return
    pin, pout = PRICES_PER_M[model]
    tin, tout = _tok(usage)
    charge(model, tin / 1e6 * pin + tout / 1e6 * pout)


# --------------------------------------------------------------------------- agent trace
def label() -> str | None:
    return getattr(_local, "label", None)


@contextlib.contextmanager
def labelled(text: str) -> Iterator[None]:
    """Name what the model calls inside this block are for (e.g. "puppet Si Kancil"), for the trace."""
    old = label()
    _local.label = text
    try:
        yield
    finally:
        _local.label = old


def record_call(model: str, endpoint: str, purpose: str, ms: float, attempts: int, ok: bool, error: str = "") -> None:
    m = current()
    if m:
        lab = label()
        entry: dict[str, Any] = {"kind": "call", "model": model, "endpoint": endpoint,
                                 "purpose": f"{purpose} \u00b7 {lab}" if lab else purpose,
                                 "ms": round(ms), "attempts": attempts, "ok": ok}
        if error:
            from .errors import scrub

            entry["error"] = scrub(error)[:160]
        m.record(entry)


def record_decision(text: str, agent: str = "verify") -> None:
    """An agent decision that changes what happens next (a checker rejecting a picture, a redraw, a fallback)."""
    m = current()
    if m:
        lab = label()
        from .errors import scrub

        text = scrub(text)
        m.record({"kind": "decision", "agent": agent, "text": f"{lab}: {text}" if lab else text})


def summary(trace: list[dict[str, Any]], items: dict[str, float]) -> dict[str, Any]:
    """Per-model totals for the UI and the docs: calls, failed calls, retries, total latency, cost."""
    per: dict[str, dict[str, Any]] = {}
    for e in trace:
        if e.get("kind") != "call":
            continue
        row = per.setdefault(e["model"], {"model": e["model"], "calls": 0, "failed": 0, "retries": 0, "ms": 0,
                                          "usd": 0.0})
        row["calls"] += 1
        row["failed"] += 0 if e.get("ok") else 1
        row["retries"] += max(0, int(e.get("attempts", 1)) - 1)
        row["ms"] += int(e.get("ms", 0))
    for model, usd in items.items():
        per.setdefault(model, {"model": model, "calls": 0, "failed": 0, "retries": 0, "ms": 0, "usd": 0.0})
        per[model]["usd"] = round(usd, 4)
    decisions = sum(1 for e in trace if e.get("kind") == "decision")
    return {"models": sorted(per.values(), key=lambda r: -r["calls"]), "calls": sum(r["calls"] for r in per.values()),
            "decisions": decisions}


ROLES = {  # what each model does in Dalang AI, for the receipt
    "muse-voice-transcribe": "hears the child's story (speech to text)",
    "muse-spark-1.2": "hears Javanese stories (audio understanding)",
    "muse-spark-1.3": "writes the lakon, safety screen, Penjaga Budaya cultural review, picture checker",
    "muse-image": "draws every puppet and backdrop",
    "sam-3.1": "cuts each puppet out (one reusable mask)",
    "muse-wonder": "choreographs each scene as keyframes",
    "muse-spark-open": "writes the lakon (open weights, Baseten)",
    "glimmer": "polishes title and moral (open weights)",
}
PRICING_URL = "https://dev.meta.ai/docs/pricing-rate-limits"


def role_of(model: str) -> str:
    low = model.lower()
    return next((v for k, v in ROLES.items() if k in low), "")


def final_fields(state: dict[str, Any]) -> dict[str, Any]:
    """Cost, trace and receipt from the running meter, to be saved in the SAME update that sets status "done", so
    a client that sees "done" never reads a film without its trace or receipt. Empty when no meter is running."""
    m = current()
    if not m:
        return {}
    out: dict[str, Any] = {"cost_usd": round(m.spent, 4), "cost_items": {k: round(v, 5) for k, v in m.items.items()},
                           "trace": list(m.trace), "trace_summary": summary(m.trace, m.items), "tokens": m.tokens}
    out["receipt"] = receipt({**state, **out})
    return out


def receipt(state: dict[str, Any]) -> dict[str, Any]:
    """The film's "Meta models used" receipt: per model its job, calls, tokens, images and estimated cost.
    Cost is an estimate from the published per-token / per-image prices (PRICES_PER_M etc. above)."""
    summ = state.get("trace_summary") or {}
    tokens = state.get("tokens") or {}
    trace = state.get("trace") or []
    rows = []
    for r in summ.get("models", []):
        model = r["model"]
        calls = [e for e in trace if e.get("kind") == "call" and e.get("model") == model and e.get("ok")]
        images = sum(1 for e in calls if e.get("endpoint", "").startswith(("/v1/images", "/images")))
        tin, tout = (tokens.get(model) or [0, 0])[:2]
        rows.append({"model": model, "role": role_of(model), "calls": r["calls"], "tokens_in": tin, "tokens_out": tout,
                     "images": images, "usd": round(float(r.get("usd", 0.0)), 4),
                     "open_weights": bool(re.search(r"glimmer|spark-open", model, re.I))})
    for model, (tin, tout) in tokens.items():  # a model with tokens but no trace row (trace was trimmed)
        if not any(x["model"] == model for x in rows):
            rows.append({"model": model, "role": role_of(model), "calls": 0, "tokens_in": tin, "tokens_out": tout,
                         "images": 0, "usd": 0.0, "open_weights": bool(re.search(r"glimmer|spark-open", model, re.I))})
    return {"models": rows, "calls": sum(r["calls"] for r in rows),
            "tokens_in": sum(r["tokens_in"] for r in rows), "tokens_out": sum(r["tokens_out"] for r in rows),
            "usd": round(float(state.get("cost_usd") or 0.0), 4), "decisions": summ.get("decisions", 0),
            "estimate": True, "pricing": PRICING_URL,
            "fake": bool(state.get("offline")),
            "note": ("Fake Meta API: token counts are the fixture's fixed usage, cost is what the same calls would cost."
                     if state.get("offline") else "Estimated from Meta's published prices; open-weight hosts bill separately.")}
