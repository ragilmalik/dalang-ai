"""Which address counts as the visitor: the first X-Forwarded-For entry by default, or the one our own
proxy saw when TRUSTED_PROXY_HOPS is set, so typed fake entries cannot rotate hourly buckets."""
from types import SimpleNamespace

import pytest

from api import main
from api.config import settings


def _req(xff: str | None, peer: str = "10.0.0.5"):
    headers = {"x-forwarded-for": xff} if xff is not None else {}
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=peer))


def test_default_uses_first_entry(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    assert main._client_ip(_req("203.0.113.9, 198.51.100.2")) == "203.0.113.9"


def test_no_header_uses_socket_peer(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert main._client_ip(_req(None, "192.0.2.7")) == "192.0.2.7"


@pytest.mark.parametrize("xff,hops,want", [
    ("6.6.6.6, 203.0.113.9", 1, "203.0.113.9"),                 # visitor typed a fake first entry
    ("6.6.6.6, 203.0.113.9, 198.51.100.2", 2, "203.0.113.9"),   # two proxies of ours
    ("203.0.113.9", 3, "203.0.113.9"),                          # fewer hops than trusted: clamp to first
    (" , ,", 1, "10.0.0.5"),                                    # empty header junk falls back to the peer
])
def test_trusted_hops(monkeypatch, xff, hops, want):
    monkeypatch.setattr(settings, "trusted_proxy_hops", hops)
    assert main._client_ip(_req(xff)) == want


def test_rotating_fake_entries_share_one_bucket(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    monkeypatch.setattr(settings, "rate_limit_per_hour", 2)
    monkeypatch.setattr(settings, "max_active_jobs", 0)
    main._recent.clear()
    for i in range(2):
        main._limit(_req(f"9.9.9.{i}, 203.0.113.50"))
    with pytest.raises(main.HTTPException) as e:
        main._limit(_req("9.9.9.99, 203.0.113.50"))
    assert e.value.status_code == 429
    main._recent.clear()


def test_recent_table_is_pruned(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    monkeypatch.setattr(settings, "rate_limit_per_hour", 5)
    monkeypatch.setattr(settings, "max_active_jobs", 0)
    main._recent.clear()
    main._recent.update({f"1.1.{i // 250}.{i % 250}": [1.0] for i in range(5100)})  # long-expired entries
    main._limit(_req("203.0.113.77"))
    assert len(main._recent) == 1
    main._recent.clear()
