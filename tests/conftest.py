"""Tests run against the built-in fake Meta API: no keys, no network, no cost."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.update({
    "FAKE_META": "1", "META_API_KEY": "", "MODEL_API_KEY": "", "DATA_DIR": tempfile.mkdtemp(prefix="dalang-test-"),
    "VIDEO_FPS": "6", "MAKE_VERTICAL": "0", "NARRATION_VOICE": "0", "DEMO_MODE": "0", "USE_OPEN_WEIGHTS": "0",
    "RATE_LIMIT_PER_HOUR": "0", "BUNDLED_SAMPLES": "0", "MAX_ACTIVE_JOBS": "0",  # limits have their own tests (test_limits.py)
})
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_breakers():
    """Circuit breakers and injected fake failures are process-wide; every test starts with them cleared."""
    from api import fake_meta, resilience

    resilience.reset_breakers()
    fake_meta.reset_failures()
    os.environ.pop("FAKE_META_FAIL", None)
    yield
    resilience.reset_breakers()
    os.environ.pop("FAKE_META_FAIL", None)


@pytest.fixture(autouse=True)
def _fresh_visitor_memory():
    """The API remembers who already gave a Sembah (in memory); tests must not see each other's visitors."""
    from api import main

    main._bowed.clear()
    yield
    main._bowed.clear()
