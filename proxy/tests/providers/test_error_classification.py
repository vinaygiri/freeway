"""Tests for shared provider-error failover classification."""

from __future__ import annotations

from providers.exceptions import (
    APIError,
    AuthenticationError,
    InvalidRequestError,
    OverloadedError,
    RateLimitError,
    UnknownProviderTypeError,
    blocks_provider,
    should_failover,
)


def test_all_provider_errors_failover() -> None:
    assert should_failover(RateLimitError("429"))
    assert should_failover(OverloadedError("503"))
    assert should_failover(APIError("boom", status_code=500))
    assert should_failover(APIError("not found", status_code=404))
    assert should_failover(AuthenticationError("401"))  # try a different provider
    assert should_failover(UnknownProviderTypeError("provider x not registered"))
    assert should_failover(ConnectionError("dropped"))
    # 400 too: the common case is context_length_exceeded on a small free tier,
    # which a larger-context model can serve — so we fail over rather than stop.
    assert should_failover(InvalidRequestError("context_length_exceeded"))


def test_blocks_provider_only_on_auth() -> None:
    assert blocks_provider(AuthenticationError("401"))
    assert blocks_provider(APIError("forbidden", status_code=403))
    assert not blocks_provider(RateLimitError("429"))
    assert not blocks_provider(OverloadedError("503"))
