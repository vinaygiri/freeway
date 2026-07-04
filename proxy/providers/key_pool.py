"""Round-robin API-key pool for multi-key providers.

Configuring more than one key for a provider (comma-separated in that
provider's key env var) multiplies the effective free-tier headroom: requests
are spread across the keys round-robin, so each key sees ~1/N of the traffic.

Selection is a single non-awaiting operation, so it is safe under asyncio
concurrency (no interleaving mid-select). A single configured key behaves
exactly as before. Per-key parking on 429 is a planned follow-up; this slice
ships rotation only.
"""

from __future__ import annotations

from collections.abc import Sequence


class KeyPool:
    """Rotate over a de-duplicated list of non-empty API keys."""

    def __init__(self, keys: Sequence[str]) -> None:
        seen: set[str] = set()
        unique: list[str] = []
        for key in keys:
            if key and key not in seen:
                seen.add(key)
                unique.append(key)
        self._keys = unique
        self._index = 0

    def __len__(self) -> int:
        return len(self._keys)

    def keys(self) -> list[str]:
        return list(self._keys)

    def select(self) -> str:
        """Return the next key round-robin (empty string when no keys)."""
        if not self._keys:
            return ""
        key = self._keys[self._index % len(self._keys)]
        self._index += 1
        return key
