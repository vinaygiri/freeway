"""Persistent per-model liveness probes for the admin Models view.

Freeway's provider-level "ready" status is optimistic — it marks every model of a
healthy provider as ready without testing each one. This module adds on-demand,
per-model verification: the result of pinging an individual model is stored here
and persisted under ``~/.freeway/`` so a verification survives view switches and
restarts until it is re-run ("verify once and keep it").
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

# Neutral ``core`` must not import ``config`` (import-boundary contract); the caller
# resolves the on-disk location and injects it.
PROBE_FILENAME = "model_probes.json"


def _key(provider_id: str, model_id: str) -> str:
    return f"{provider_id}/{model_id}"


class ProbeStore:
    """In-memory per-model probe results, persisted to a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            loaded = json.loads(self._path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            loaded = None
        if isinstance(loaded, dict):
            self._data = {
                key: value for key, value in loaded.items() if isinstance(value, dict)
            }

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except OSError:
            pass

    def get(self, provider_id: str, model_id: str) -> dict[str, Any] | None:
        return self._data.get(_key(provider_id, model_id))

    def record(
        self, provider_id: str, model_id: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        entry = {**result, "at": time.time()}
        self._data[_key(provider_id, model_id)] = entry
        self._save()
        return entry

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return dict(self._data)


def classify_probe(chunks: list[str], raised: BaseException | None) -> dict[str, Any]:
    """Turn a streamed probe attempt into a {status, error} verdict.

    ``live`` when the model streamed real content; ``down`` when the attempt
    raised (HTTP/connection/auth error) or the stream carried an error event.
    """
    if raised is not None:
        message = (
            getattr(raised, "message", None) or str(raised) or type(raised).__name__
        )
        status_code = getattr(raised, "status_code", None)
        kind = _kind_from_error(status_code, type(raised).__name__, str(message))
        text = str(message)[:180]
        return {
            "status": "down",
            "kind": kind,
            "error": f"{status_code}: {text}" if status_code else text,
        }

    joined = "".join(chunks)
    lowered = joined.lower()
    if (
        "event: error" in lowered
        or '"type":"error"' in lowered
        or '"type": "error"' in lowered
    ):
        error = _extract_stream_error(chunks)
        return {"status": "down", "kind": _kind_from_message(error), "error": error}
    if not joined.strip():
        return {"status": "down", "kind": "error", "error": "empty response"}
    return {"status": "live", "kind": "live", "error": None}


# HTTP statuses that mean "works, just not right now" vs "won't work as configured".
_OVERLOADED_STATUS = {500, 502, 503, 504, 529}
_UNAVAILABLE_STATUS = {401, 403, 404}


def _kind_from_error(status_code: int | None, exc_name: str, message: str) -> str:
    """Classify a raised probe error into a status kind."""
    if status_code == 429:
        return "rate_limited"
    if status_code in _OVERLOADED_STATUS:
        return "overloaded"
    if status_code in _UNAVAILABLE_STATUS:
        return "unavailable"
    if status_code is not None:
        return "error"
    name = exc_name.lower()
    if "timeout" in name or "connect" in name:
        return "unreachable"
    return _kind_from_message(message)


def _kind_from_message(message: str) -> str:
    """Best-effort kind from an error message when no HTTP status is available."""
    low = message.lower()
    if "rate limit" in low or "too many requests" in low or "429" in low:
        return "rate_limited"
    if "overload" in low or "capacity" in low or "unavailable" in low or "503" in low:
        return "overloaded"
    if (
        "not found" in low
        or "does not exist" in low
        or "no access" in low
        or "404" in low
    ):
        return "unavailable"
    if "auth" in low or "api key" in low or "401" in low or "403" in low:
        return "unavailable"
    if "timeout" in low or "timed out" in low or "connect" in low:
        return "unreachable"
    return "error"


def _extract_stream_error(chunks: list[str]) -> str:
    for chunk in chunks:
        if "error" not in chunk.lower():
            continue
        for line in chunk.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                try:
                    payload = json.loads(line[5:].strip())
                except ValueError:
                    continue
                err = payload.get("error") if isinstance(payload, dict) else None
                if isinstance(err, dict) and err.get("message"):
                    return str(err["message"])[:180]
    return "provider returned an error"
