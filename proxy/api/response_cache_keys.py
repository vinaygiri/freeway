"""Exact-match cache key + cacheability policy for Anthropic Messages requests.

Lives in ``api`` (not ``core``) because it inspects the ``MessagesRequest``
model. Only conservatively-safe requests are cacheable: no tools (no
side-effecting tool loop) and ``temperature == 0`` (deterministic-ish). The key
hashes the semantically-relevant fields, excluding volatile transport/metadata.
"""

from __future__ import annotations

import hashlib
import json

from .models.anthropic import MessagesRequest

# Excluded from the key: per-call metadata + the streaming transport flag.
# (Routing/debug fields — original_model, resolved_provider_model, betas — are
# already ``exclude=True`` on the model and never appear in model_dump.)
_VOLATILE_FIELDS = {"metadata", "stream"}


def is_cacheable(request: MessagesRequest) -> bool:
    """Return whether this request is safe to serve from an exact-match cache."""
    return not request.tools and request.temperature == 0


def cache_key(request: MessagesRequest) -> str:
    """Return a stable hash of the semantically-relevant request fields."""
    payload = request.model_dump(mode="json", exclude=_VOLATILE_FIELDS)
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
