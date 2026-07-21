"""Freeway — resilient free-tier LLM routing as a Python library.

    from freeway import Freeway

    fw = Freeway(
        primary="gemini/models/gemini-2.5-flash",
        fallbacks=["cerebras/gpt-oss-120b"],
        keys={"gemini": "...", "cerebras": "..."},
    )
    completion = fw.chat(messages=[{"role": "user", "content": "Hello"}])
    print(completion.text, completion.served_model, completion.was_fallback)

Cross-provider failover, multi-key rotation, and tool-schema compression are
applied automatically. The ``freeway`` proxy server is a front-end over this
same core.
"""

from __future__ import annotations

from api.recommend import ModelScore

from ._facade import (
    AllProvidersFailed,
    Completion,
    Freeway,
    StreamEvent,
    ToolCall,
)

__all__ = [
    "AllProvidersFailed",
    "Completion",
    "Freeway",
    "ModelScore",
    "StreamEvent",
    "ToolCall",
]
