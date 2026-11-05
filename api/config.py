"""Settings, read from environment variables or a .env file in the repo root."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:  # pragma: no cover
    pass


def _env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.getenv(n)
        if v is not None and v.strip():
            return v.strip()
    return default


def _flag(*names: str, default: str = "0") -> bool:
    return _env(*names, default=default).lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # --- Meta Model API (https://dev.meta.ai/docs/overview). Docs call the key MODEL_API_KEY; both names work.
    meta_api_key: str = field(default_factory=lambda: _env("META_API_KEY", "MODEL_API_KEY"))
    meta_api_base: str = field(default_factory=lambda: _env("META_API_BASE", default="https://api.meta.ai/v1").rstrip("/"))

    # --- Model ids, verified against https://dev.meta.ai/docs/models on 2026-10-30
    asr_model: str = field(default_factory=lambda: _env("ASR_MODEL", default="muse-voice-transcribe-1.0"))
    lakon_model: str = field(default_factory=lambda: _env("LAKON_MODEL", default="muse-spark-1.3"))
    audio_model: str = field(default_factory=lambda: _env("AUDIO_MODEL", default="muse-spark-1.2"))
    verify_model: str = field(default_factory=lambda: _env("VERIFY_MODEL", default="muse-spark-1.3"))
    image_model: str = field(default_factory=lambda: _env("IMAGE_MODEL", default="muse-image-1.0"))
    sam_model: str = field(default_factory=lambda: _env("SAM_MODEL", default="sam-3.1"))
    animate_model: str = field(default_factory=lambda: _env("ANIMATE_MODEL", default="muse-wonder-1.0"))
    # Penjaga Budaya (cultural-review agent): Muse Spark checks the script against content/cultural_rules.json
    culture_model: str = field(default_factory=lambda: _env("CULTURE_MODEL", default="muse-spark-1.3"))
    cultural_review: bool = field(default_factory=lambda: _flag("CULTURAL_REVIEW", default="1"))

    # --- Open weights: Muse Spark Open on Baseten (https://dev.meta.ai/docs/muse-spark-open/deploy#baseten)
    use_open_weights: bool = field(default_factory=lambda: _flag("USE_OPEN_WEIGHTS"))
    baseten_api_key: str = field(default_factory=lambda: _env("BASETEN_API_KEY"))
    open_api_base: str = field(default_factory=lambda: _env("OPEN_API_BASE", default="https://inference.baseten.co/v1").rstrip("/"))
    # Meta's docs list the Baseten model string as "meta-models/muse-spark-open". If the Baseten
    # dashboard shows a dated id (e.g. meta-models/muse-spark-open-1026), put that here instead.
    open_model: str = field(default_factory=lambda: _env("OPEN_MODEL", default="meta-models/muse-spark-open"))
    # Which text stages run on Muse Spark Open when USE_OPEN_WEIGHTS=true (comma list). Text-only stages only:
    # lakon, director, remix, cultural_review, gara_gara, gara_gara_rewrite. Vision checks and motion plans stay on Meta.
    open_stages: frozenset[str] = field(default_factory=lambda: frozenset(
        x.strip() for x in _env("OPEN_WEIGHTS_STAGES", default="lakon").split(",") if x.strip()))

    # --- Open weights: Muse Glimmer (30B, Apache 2.0), https://dev.meta.ai/docs/muse-glimmer/deploy#hosted-providers
    # Documented hosted provider: Together AI, model string "meta-models/Muse-Glimmer-30B", OpenAI-compatible
    # chat completions at https://api.together.xyz/v1. A self-hosted server (vLLM/SGLang/llama.cpp/Ollama, all
    # OpenAI-compatible) works too: GLIMMER_API_BASE=http://localhost:8000/v1 and GLIMMER_MODEL=muse-glimmer.
    glimmer_api_key: str = field(default_factory=lambda: _env("GLIMMER_API_KEY", "TOGETHER_API_KEY"))
    glimmer_api_base: str = field(default_factory=lambda: _env("GLIMMER_API_BASE", default="https://api.together.xyz/v1").rstrip("/"))
    glimmer_model: str = field(default_factory=lambda: _env("GLIMMER_MODEL", default="meta-models/Muse-Glimmer-30B"))

    # --- Behaviour
    # SEED_SAMPLES=1: on start, make the 3 labelled sample films for the gallery in the background (fake API only)
    # CLEANUP_DAYS=30: on start, delete private films nobody shared that are older than this. 0 = off.
    cleanup_days: float = field(default_factory=lambda: float(_env("CLEANUP_DAYS", default="0")))
    # RECORDING_TTL_HOURS=6: a story recording that is still on disk after this long (unapproved storyboard,
    # crash) is deleted on start and whenever a new film is created. 0 = off.
    recording_ttl_hours: float = field(default_factory=lambda: float(_env("RECORDING_TTL_HOURS", default="6")))
    seed_samples: bool = field(default_factory=lambda: _flag("SEED_SAMPLES"))
    # BUNDLED_SAMPLES=1 (default): on start, copy the three sample films shipped in content/samples/ (made with the
    # live Meta models) into the gallery once. 0 = start with an empty gallery.
    bundled_samples: bool = field(default_factory=lambda: _flag("BUNDLED_SAMPLES", default="1"))
    demo_mode: bool = field(default_factory=lambda: _flag("DEMO_MODE"))  # replay a pre-made film if a live run fails
    # FAKE_META=1 (or MOCK=1): answer every Meta call from the built-in fake API (api/fake_meta.py) even if keys are set.
    fake_flag: bool = field(default_factory=lambda: _flag("FAKE_META", "MOCK"))
    max_verify_retries: int = field(default_factory=lambda: int(_env("MAX_VERIFY_RETRIES", default="2")))
    # --- Abuse limits for a public deployment. Requests from this machine (127.0.0.1) skip the hourly limit.
    rate_limit_per_hour: int = field(default_factory=lambda: int(_env("RATE_LIMIT_PER_HOUR", default="12")))
    # How many proxies of ours sit in front of the API (Vercel, Render ...). 0 keeps the old rule (first
    # X-Forwarded-For address). N > 0 trusts only the address our Nth proxy saw, so typed fake entries cannot rotate buckets.
    trusted_proxy_hops: int = field(default_factory=lambda: int(_env("TRUSTED_PROXY_HOPS", default="0")))
    max_active_jobs: int = field(default_factory=lambda: int(_env("MAX_ACTIVE_JOBS", default="6")))
    max_story_chars: int = field(default_factory=lambda: int(_env("MAX_STORY_CHARS", default="2000")))
    max_audio_seconds: int = field(default_factory=lambda: int(_env("MAX_AUDIO_SECONDS", default="120")))
    # MAX_USD_PER_FILM (or the older JOB_BUDGET_USD): hard cap per film. MAX_USD_TOTAL (api/resilience.py): cap for
    # everything this deployment spends on real Meta calls.
    job_budget_usd: float = field(default_factory=lambda: float(_env("MAX_USD_PER_FILM", "JOB_BUDGET_USD", default="1.50")))
    # Recorded-fixture mode (api/resilience.py): META_RECORD_DIR writes every Meta exchange; META_REPLAY_DIR serves them.
    meta_record_dir: str = field(default_factory=lambda: _env("META_RECORD_DIR"))
    meta_replay_dir: str = field(default_factory=lambda: _env("META_REPLAY_DIR"))
    make_vertical: bool = field(default_factory=lambda: _flag("MAKE_VERTICAL", default="1"))
    narration_voice: bool = field(default_factory=lambda: _flag("NARRATION_VOICE", default="1"))

    # --- Video
    fps: int = field(default_factory=lambda: int(_env("VIDEO_FPS", default="24")))
    render_workers: int = field(default_factory=lambda: int(_env("RENDER_WORKERS", default="2")))

    # --- Storage and URLs
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", default=str(ROOT / "data"))))
    public_base_url: str = field(default_factory=lambda: _env("PUBLIC_BASE_URL").rstrip("/"))
    storage_backend: str = field(default_factory=lambda: _env("STORAGE_BACKEND", default="local").lower())
    r2_account_id: str = field(default_factory=lambda: _env("STORAGE_R2_ACCOUNT_ID"))
    r2_access_key: str = field(default_factory=lambda: _env("STORAGE_R2_ACCESS_KEY_ID"))
    r2_secret_key: str = field(default_factory=lambda: _env("STORAGE_R2_SECRET_ACCESS_KEY"))
    r2_bucket: str = field(default_factory=lambda: _env("STORAGE_R2_BUCKET"))
    r2_public_url: str = field(default_factory=lambda: _env("STORAGE_R2_PUBLIC_URL").rstrip("/"))
    cors_origins: str = field(default_factory=lambda: _env("CORS_ORIGINS", default="*"))

    @property
    def fake_meta(self) -> bool:
        """FAKE_META=1 only (tests, CI, offline rehearsal): every Meta call is answered by the fake API with recorded
        fixtures and labelled placeholder art. The real request/parse code still runs. It is never switched on just
        because a key is missing: without a key the server is "not configured" and refuses to start new films."""
        return self.fake_flag

    @property
    def live(self) -> bool:
        """A Meta key is set and FAKE_META is off: every call goes to the real Meta Model API."""
        return bool(self.meta_api_key) and not self.fake_flag

    @property
    def mode(self) -> str:
        return "fake" if self.fake_flag else ("live" if self.meta_api_key else "not_configured")

    @property
    def offline(self) -> bool:  # kept for the UI label
        return self.fake_meta

    @property
    def glimmer_local(self) -> bool:
        return "://localhost" in self.glimmer_api_base or "://127.0.0.1" in self.glimmer_api_base

    @property
    def glimmer_active(self) -> bool:
        """Safety screen + title/moral polish run on Muse Glimmer when USE_OPEN_WEIGHTS=true and it is reachable."""
        return self.use_open_weights and (bool(self.glimmer_api_key) or self.glimmer_local or self.fake_meta)

    @property
    def open_weights_active(self) -> bool:
        return self.use_open_weights and (bool(self.baseten_api_key) or self.fake_meta)


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
