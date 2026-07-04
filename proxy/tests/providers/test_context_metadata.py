from __future__ import annotations

from providers.model_listing import (
    ProviderModelInfo,
    extract_openrouter_tool_model_infos,
)
from providers.runtime.model_cache import ProviderModelCache


def test_openrouter_captures_context_length():
    payload = {
        "data": [
            {
                "id": "a/b",
                "supported_parameters": ["tools", "reasoning"],
                "context_length": 128000,
            },
            {"id": "c/d", "supported_parameters": ["tool_choice"]},  # no context_length
            {
                "id": "e/f",
                "supported_parameters": ["tools"],
                "context_length": 0,  # invalid -> None
            },
        ]
    }
    infos = {
        info.model_id: info
        for info in extract_openrouter_tool_model_infos(
            payload, provider_name="OPENROUTER"
        )
    }
    assert infos["a/b"].context_window == 128000
    assert infos["a/b"].supports_thinking is True
    assert infos["c/d"].context_window is None
    assert infos["e/f"].context_window is None


def test_cache_model_info_roundtrip():
    cache = ProviderModelCache()
    cache.cache_model_infos(
        "open_router", [ProviderModelInfo(model_id="a/b", context_window=128000)]
    )
    info = cache.cached_model_info("open_router", "a/b")
    assert info is not None
    assert info.context_window == 128000
    assert cache.cached_model_info("open_router", "missing") is None
    assert cache.cached_model_info("unknown_provider", "x") is None
