"""Background health probe service.

Periodically probes each configured provider with a lightweight
``list_model_ids()`` call, records the round-trip latency (or failure) into the
:class:`~core.health.HealthStore`, and computes stability scores. Mirrors the
lifecycle of :class:`providers.runtime.discovery.ProviderModelDiscovery`:
owns an ``asyncio.Task`` started on app startup and cancelled on shutdown.

The model-list probe costs no completion quota, so it is safe to run
continuously. Per-model latency from real request traffic is a separate,
richer signal added when the router consumes this store.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from contextlib import suppress

from loguru import logger

from config.settings import Settings
from core.health import HealthStore, Sample
from providers.base import BaseProvider
from providers.exceptions import AuthenticationError
from providers.runtime import model_list_provider_ids_for_settings

ProviderResolver = Callable[[str], BaseProvider]


class HealthProbeService:
    """Probe configured providers on an interval and record health samples."""

    def __init__(
        self,
        settings: Settings,
        provider_resolver: ProviderResolver,
        store: HealthStore,
        *,
        interval_s: float,
    ) -> None:
        self._settings = settings
        self._provider_resolver = provider_resolver
        self._store = store
        self._interval_s = max(1.0, interval_s)
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())

    async def cleanup(self) -> None:
        if self._task is None or self._task.done():
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task

    async def probe_once(self) -> None:
        """Probe every configured provider once, recording a sample each."""
        provider_ids = model_list_provider_ids_for_settings(self._settings)
        await asyncio.gather(
            *(self._probe_provider(provider_id) for provider_id in provider_ids)
        )

    async def _run_loop(self) -> None:
        try:
            while True:
                await self.probe_once()
                await asyncio.sleep(self._interval_s)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Health probe loop stopped: exc_type={}", type(exc).__name__)

    async def _probe_provider(self, provider_id: str) -> None:
        start = time.perf_counter()
        try:
            provider = self._provider_resolver(provider_id)
            await provider.list_model_ids()
        except asyncio.CancelledError:
            raise
        except AuthenticationError:
            # A 401 still proves the endpoint is reachable — a measurable sample.
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._store.record(provider_id, Sample(code="401", latency_ms=elapsed_ms))
        except Exception:
            self._store.record(provider_id, Sample(code="ERR", latency_ms=None))
        else:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._store.record(provider_id, Sample(code="200", latency_ms=elapsed_ms))
