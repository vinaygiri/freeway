"""Local admin UI routes and APIs."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import ipaddress
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api.models.anthropic import MessagesRequest
from api.recommend import recommend as recommend_models
from api.recommend import suggest_chain
from config.model_quality import quality_for
from config.model_refs import parse_provider_type
from config.paths import config_dir_path
from config.provider_catalog import PROVIDER_CATALOG
from config.provider_ids import SUPPORTED_PROVIDER_IDS
from config.settings import Settings
from config.settings import get_settings as get_cached_settings
from core.model_probe import PROBE_FILENAME, ProbeStore, classify_probe
from providers.runtime import ProviderRuntime

from .admin_config.manifest import FIELD_BY_KEY
from .admin_config.persistence import validate_updates, write_managed_env
from .admin_config.sources import is_locked_source
from .admin_config.status import provider_config_status
from .admin_config.values import load_config_response, load_value_state
from .admin_urls import local_admin_url
from .data_governor import DataGovernor
from .dependencies import (
    maybe_circuit_breaker,
    maybe_health_store,
    maybe_quota_governor,
    maybe_recent_request_store,
    maybe_response_cache,
)

router = APIRouter()

STATIC_DIR = Path(__file__).resolve().parent / "admin_static"
LOCAL_PROVIDER_PATHS = {
    "lmstudio": "/models",
    "llamacpp": "/models",
    "ollama": "/api/tags",
}


class AdminConfigPayload(BaseModel):
    """Partial config update submitted by the admin UI."""

    values: dict[str, Any] = Field(default_factory=dict)


def _is_loopback_host(host: str | None) -> bool:
    if host is None:
        return False
    normalized = host.strip().strip("[]").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _origin_is_local(origin: str | None) -> bool:
    if not origin:
        return True
    parsed = urlsplit(origin)
    return _is_loopback_host(parsed.hostname)


def require_loopback_admin(request: Request) -> None:
    """Allow admin access only from the local machine."""

    client_host = request.client.host if request.client else None
    if not _is_loopback_host(client_host):
        raise HTTPException(status_code=403, detail="Admin UI is local-only")

    origin = request.headers.get("origin")
    if not _origin_is_local(origin):
        raise HTTPException(status_code=403, detail="Admin UI is local-only")


def _asset_response(filename: str) -> FileResponse:
    path = STATIC_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Admin asset not found")
    # Force revalidation on every load. FileResponse still sends ETag/Last-Modified,
    # so unchanged assets return a cheap 304 — but a redeploy is always picked up
    # immediately, instead of the browser silently running a stale cached admin.js.
    return FileResponse(path, headers={"Cache-Control": "no-cache"})


@router.get("/admin", include_in_schema=False)
async def admin_page(request: Request):
    require_loopback_admin(request)
    return _asset_response("index.html")


@router.get("/admin/assets/{filename}", include_in_schema=False)
async def admin_asset(filename: str, request: Request):
    require_loopback_admin(request)
    if filename not in {"admin.css", "admin.js"}:
        raise HTTPException(status_code=404, detail="Admin asset not found")
    return _asset_response(filename)


@router.get("/admin/api/config")
async def get_admin_config(request: Request):
    require_loopback_admin(request)
    return load_config_response()


@router.post("/admin/api/config/validate")
async def validate_admin_config(payload: AdminConfigPayload, request: Request):
    require_loopback_admin(request)
    return validate_updates(_filtered_values(payload.values))


@router.post("/admin/api/config/apply")
async def apply_admin_config(
    payload: AdminConfigPayload,
    request: Request,
    background_tasks: BackgroundTasks,
):
    require_loopback_admin(request)
    result = write_managed_env(_filtered_values(payload.values))
    if not result["applied"]:
        return result

    get_cached_settings.cache_clear()
    restart = _restart_metadata(result["pending_fields"], request)
    result["restart"] = restart
    if restart["required"] and restart["automatic"]:
        callback = request.app.state.admin_restart_callback
        background_tasks.add_task(_invoke_admin_restart_callback, callback)
        request.app.state.admin_pending_fields = []
        return result

    # Only rebuild the provider runtime when a provider credential/endpoint changed.
    # Rebuilding drops the cached model discovery, so UI-only changes (model choice,
    # favourites, fallback chain, auto-fit) must NOT wipe the Models list.
    changed = set(payload.values or {})
    provider_env_keys = {
        d.credential_env for d in PROVIDER_CATALOG.values() if d.credential_env
    }
    needs_rebuild = bool(changed & provider_env_keys) or any(
        key.endswith(("_BASE_URL", "_PROXY", "_ACCOUNT_ID")) for key in changed
    )
    if needs_rebuild:
        old_runtime = getattr(request.app.state, "provider_runtime", None)
        if isinstance(old_runtime, ProviderRuntime):
            await old_runtime.cleanup()
        request.app.state.provider_runtime = ProviderRuntime(get_cached_settings())
    request.app.state.admin_pending_fields = result["pending_fields"]
    return result


@router.get("/admin/api/status")
async def admin_status(request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    runtime = getattr(request.app.state, "provider_runtime", None)
    cached_models: dict[str, list[str]] = {}
    if isinstance(runtime, ProviderRuntime):
        cached_models = {
            provider_id: sorted(model_ids)
            for provider_id, model_ids in runtime.cached_model_ids().items()
        }
    return {
        "status": "running",
        "host": settings.host,
        "port": settings.port,
        "model": settings.model,
        "provider": parse_provider_type(settings.model),
        "pending_fields": getattr(request.app.state, "admin_pending_fields", []),
        "provider_status": provider_config_status(),
        "cached_models": cached_models,
    }


@router.get("/admin/api/health")
async def admin_health(request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    store = maybe_health_store(request.app)
    return {
        "enabled": settings.enable_health_probes,
        "interval_seconds": settings.health_probe_interval_seconds,
        "sample_window": settings.health_probe_sample_window,
        "targets": store.snapshot() if store is not None else {},
    }


@router.get("/admin/api/quota")
async def admin_quota(request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    governor = maybe_quota_governor(request.app)
    return {
        "enabled": settings.enable_quota_tracking,
        "providers": governor.snapshot() if governor is not None else {},
    }


@router.get("/admin/api/router")
async def admin_router(request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    breaker = maybe_circuit_breaker(request.app)
    return {
        "fallbacks": [
            ref.strip() for ref in settings.model_fallbacks.split(",") if ref.strip()
        ],
        "circuits": breaker.snapshot() if breaker is not None else {},
    }


@router.get("/admin/api/requests")
async def admin_requests(request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    store = maybe_recent_request_store(request.app)
    return {
        "enabled": settings.enable_request_inspector,
        "requests": store.snapshot() if store is not None else [],
    }


@router.get("/admin/api/policy")
async def admin_policy(request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    governor = DataGovernor.from_settings(settings)
    return {
        "active": governor.active,
        "require_no_training": settings.require_no_training,
        "require_local_only": settings.require_local_only,
        "allowed_regions": [
            region.strip()
            for region in settings.allowed_regions.split(",")
            if region.strip()
        ],
        "providers": {
            provider_id: {
                "allowed": governor.allowed(provider_id),
                "reason": governor.reason(provider_id),
            }
            for provider_id in SUPPORTED_PROVIDER_IDS
        },
    }


@router.get("/admin/api/cache")
async def admin_cache(request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    cache = maybe_response_cache(request.app)
    stats = cache.snapshot() if cache is not None else {}
    return {
        "enabled": settings.enable_response_cache,
        "window": settings.response_cache_window,
        "ttl_seconds": settings.response_cache_ttl_seconds,
        "stats": stats,
    }


def _model_refs(spec: str) -> set[tuple[str, str]]:
    """Parse 'provider/model, ...' refs into a set of (provider_id, model_id)."""
    refs: set[tuple[str, str]] = set()
    for ref in spec.split(","):
        ref = ref.strip()
        if "/" in ref:
            provider, model = ref.split("/", 1)
            refs.add((provider.strip(), model.strip()))
    return refs


def _score_num(swe_score: str | None) -> float:
    """Parse a '60.0%' SWE score into a float for ranking; unknown -> -1.0."""
    if not swe_score:
        return -1.0
    try:
        return float(swe_score.rstrip("%").strip())
    except ValueError:
        return -1.0


def _model_entry(
    pid: str,
    mid: str,
    current: set[tuple[str, str]],
    fallbacks: set[tuple[str, str]],
    favourites: set[tuple[str, str]],
    usable: bool,
) -> dict:
    """Build one model row enriched with the static quality catalog."""
    q = quality_for(mid) or {}
    return {
        "id": mid,
        "is_current": (pid, mid) in current,
        "is_fallback": (pid, mid) in fallbacks,
        "is_favourite": (pid, mid) in favourites,
        "usable": usable,
        "tier": q.get("tier"),
        "swe_score": q.get("swe_score"),
        "context": q.get("context"),
        "score_num": _score_num(q.get("swe_score")),
    }


@router.get("/admin/api/models")
async def admin_models(request: Request):
    """Aggregate every provider + its models with live routing status."""
    require_loopback_admin(request)
    settings = get_cached_settings()
    runtime = getattr(request.app.state, "provider_runtime", None)
    cached: dict[str, list[str]] = {}
    if isinstance(runtime, ProviderRuntime):
        cached = {pid: sorted(ids) for pid, ids in runtime.cached_model_ids().items()}

    health = maybe_health_store(request.app) or None
    health_snap = health.snapshot() if health is not None else {}
    quota = maybe_quota_governor(request.app)
    quota_snap = quota.snapshot() if quota is not None else {}
    breaker = maybe_circuit_breaker(request.app)
    circuit_snap = breaker.snapshot() if breaker is not None else {}
    governor = DataGovernor.from_settings(settings)

    current = _model_refs(settings.model)
    fallbacks = _model_refs(settings.model_fallbacks)
    favourites = _model_refs(settings.favourite_models)
    status_by_provider = {e["provider_id"]: e for e in provider_config_status()}
    probes = _probe_store(request).snapshot()

    def _provider_usable(pid: str, configured: bool) -> tuple[bool, str]:
        """Whether requests to this provider should currently succeed, + why not."""
        if not configured:
            return False, "no API key"
        if not governor.allowed(pid):
            return False, f"blocked: {governor.reason(pid) or 'policy'}"
        circuit = circuit_snap.get(pid) or {}
        if circuit.get("state") == "open":
            return False, "circuit open"
        quota = quota_snap.get(pid) or {}
        if quota.get("status") == "exhausted":
            return False, "quota exhausted"
        health = health_snap.get(pid) or {}
        verdict = str(health.get("verdict") or health.get("status") or "")
        if verdict and verdict.lower() in {"not active", "offline", "error", "down"}:
            return False, f"health: {verdict}"
        return True, "usable"

    providers = []
    for pid in SUPPORTED_PROVIDER_IDS:
        info = status_by_provider.get(pid, {})
        descriptor = PROVIDER_CATALOG.get(pid)
        # provider_config_status() reports a "status" string, not a bool: a remote
        # provider is configured once its key is set ("configured"); local providers
        # use a static credential and need no key.
        configured = str(info.get("status")) in {"configured", "reachable"}
        if descriptor is not None and descriptor.static_credential is not None:
            configured = True
        usable, reason = _provider_usable(pid, configured)
        models = [
            _model_entry(pid, mid, current, fallbacks, favourites, usable)
            | {"probe": probes.get(f"{pid}/{mid}")}
            for mid in cached.get(pid, [])
        ]
        providers.append(
            {
                "provider_id": pid,
                "display_name": info.get("display_name", pid),
                "configured": configured,
                "usable": usable,
                "usable_reason": reason,
                "credential_url": descriptor.credential_url if descriptor else None,
                "credential_env": descriptor.credential_env if descriptor else None,
                "is_local": bool(
                    descriptor and descriptor.static_credential is not None
                ),
                "health": health_snap.get(pid),
                "quota": quota_snap.get(pid),
                "circuit": circuit_snap.get(pid),
                "data_policy": {
                    "allowed": governor.allowed(pid),
                    "reason": governor.reason(pid),
                },
                "model_count": len(models),
                "models": models,
            }
        )

    # Usable + configured providers first, then configured, then the rest.
    providers.sort(
        key=lambda p: (not p["usable"], not p["configured"], p["display_name"].lower())
    )

    # A MODEL/MODEL_FALLBACKS set via a process env var (or explicit env file) can't be
    # changed from the UI — apply writes .env but the locked source shadows it. Surface
    # that so the Models page can explain instead of silently no-op'ing "Use".
    value_state = load_value_state()
    model_locked = is_locked_source(
        value_state.get("MODEL", {}).get("source", "default")
    )
    fallbacks_locked = is_locked_source(
        value_state.get("MODEL_FALLBACKS", {}).get("source", "default")
    )

    return {
        "current_model": settings.model,
        "model_locked": model_locked,
        "fallbacks_locked": fallbacks_locked,
        "locked_source": value_state.get("MODEL", {}).get("source", "default"),
        "fallbacks": [
            r.strip() for r in settings.model_fallbacks.split(",") if r.strip()
        ],
        "favourites": [
            r.strip() for r in settings.favourite_models.split(",") if r.strip()
        ],
        "auto_fit_max_tokens": settings.auto_fit_max_tokens,
        "providers": providers,
    }


@router.post("/admin/api/cache/clear")
async def clear_cache(request: Request):
    require_loopback_admin(request)
    cache = maybe_response_cache(request.app)
    if cache is not None:
        cache.clear()
    return {"cleared": cache is not None, "stats": cache.snapshot() if cache else {}}


@router.get("/admin/api/providers/local-status")
async def local_provider_status(request: Request):
    require_loopback_admin(request)
    config = load_config_response()
    values = {field["key"]: field["value"] for field in config["fields"]}
    checks = []
    for provider_id, path in LOCAL_PROVIDER_PATHS.items():
        base_url = _local_provider_url(provider_id, values)
        checks.append(await _check_local_provider(provider_id, base_url, path))
    return {"providers": checks}


@router.post("/admin/api/providers/{provider_id}/test")
async def test_provider(provider_id: str, request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    runtime = _provider_runtime_for_admin(request, settings)
    try:
        provider = runtime.resolve_provider(provider_id)
        infos = await provider.list_model_infos()
    except Exception as exc:
        return {
            "provider_id": provider_id,
            "ok": False,
            "error_type": type(exc).__name__,
        }
    runtime.cache_model_infos(provider_id, infos)
    return {
        "provider_id": provider_id,
        "ok": True,
        "models": sorted(info.model_id for info in infos),
    }


class PingModelPayload(BaseModel):
    provider_id: str
    model_id: str


def _probe_store(request: Request) -> ProbeStore:
    store = getattr(request.app.state, "model_probes", None)
    if not isinstance(store, ProbeStore):
        store = ProbeStore(config_dir_path() / PROBE_FILENAME)
        request.app.state.model_probes = store
    return store


async def _ping_model(
    runtime: ProviderRuntime, provider_id: str, model_id: str, timeout: float = 12.0
) -> dict[str, Any]:
    """Send a minimal request to one model and classify the result (live/down)."""
    started = perf_counter()
    try:
        provider = runtime.resolve_provider(provider_id)
    except Exception as exc:  # provider not built (e.g. missing credential)
        return classify_probe([], exc) | {"latency_ms": None}

    request_body = MessagesRequest.model_validate(
        {
            "model": model_id,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
            "stream": True,
        }
    )
    chunks: list[str] = []
    raised: BaseException | None = None
    iterator = None
    try:
        async with asyncio.timeout(timeout):
            iterator = provider.stream_response(
                request_body,
                input_tokens=1,
                request_id="probe",
                thinking_enabled=False,
            )
            async for chunk in iterator:
                chunks.append(chunk)
                if len(chunks) >= 8:  # max_tokens=1 keeps this tiny; cap just in case
                    break
    except Exception as exc:
        raised = exc
    finally:
        aclose = getattr(iterator, "aclose", None)
        if aclose is not None:
            with contextlib.suppress(Exception):
                await aclose()
    verdict = classify_probe(chunks, raised)
    verdict["latency_ms"] = round((perf_counter() - started) * 1000)
    return verdict


@router.get("/admin/api/models/recommend")
async def recommend_models_route(request: Request):
    """Rank discovered models (live-verify x quality x context) and propose a
    provider-diversified fallback chain to apply in one click."""
    require_loopback_admin(request)
    runtime = getattr(request.app.state, "provider_runtime", None)
    pairs: list[tuple[str, str]] = []
    if isinstance(runtime, ProviderRuntime):
        for provider_id, model_ids in runtime.cached_model_ids().items():
            pairs.extend((provider_id, model_id) for model_id in model_ids)
    probes = _probe_store(request).snapshot()

    def probe_getter(provider_id: str, model_id: str):
        return probes.get(f"{provider_id}/{model_id}")

    ranked = recommend_models(pairs, probe_getter=probe_getter, limit=12)
    chain = suggest_chain(pairs, probe_getter=probe_getter, max_models=4)
    return {
        "chain": chain,
        "recommended": [
            {
                "ref": s.ref,
                "score": s.score,
                "tier": s.tier,
                "liveness": s.liveness,
                "context_tokens": s.context_tokens,
                "reasons": s.reasons,
            }
            for s in ranked
        ],
    }


@router.post("/admin/api/models/ping")
async def ping_model(payload: PingModelPayload, request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    runtime = _provider_runtime_for_admin(request, settings)
    result = await _ping_model(runtime, payload.provider_id, payload.model_id)
    entry = _probe_store(request).record(payload.provider_id, payload.model_id, result)
    return {
        "provider_id": payload.provider_id,
        "model_id": payload.model_id,
        "probe": entry,
    }


@router.post("/admin/api/models/refresh")
async def refresh_models(request: Request):
    require_loopback_admin(request)
    settings = get_cached_settings()
    runtime = _provider_runtime_for_admin(request, settings)
    await runtime.refresh_model_list_cache()
    return {
        "cached_models": {
            provider_id: sorted(model_ids)
            for provider_id, model_ids in runtime.cached_model_ids().items()
        }
    }


def _provider_runtime_for_admin(
    request: Request, settings: Settings
) -> ProviderRuntime:
    runtime = getattr(request.app.state, "provider_runtime", None)
    if isinstance(runtime, ProviderRuntime):
        return runtime
    runtime = ProviderRuntime(settings)
    request.app.state.provider_runtime = runtime
    return runtime


def _filtered_values(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if key in FIELD_BY_KEY}


async def _invoke_admin_restart_callback(callback: Any) -> None:
    result = callback()
    if inspect.isawaitable(result):
        await result


def _restart_metadata(fields: list[str], request: Request) -> dict[str, Any]:
    callback = getattr(request.app.state, "admin_restart_callback", None)
    automatic = bool(fields and callable(callback))
    return {
        "required": bool(fields),
        "automatic": automatic,
        "admin_url": _next_admin_url() if automatic else None,
        "fields": fields,
    }


def _next_admin_url() -> str:
    fields = {
        field["key"]: field["value"] for field in load_config_response()["fields"]
    }
    settings = Settings.model_construct(
        host=fields.get("HOST") or "0.0.0.0",
        port=int(fields.get("PORT") or 8082),
    )
    return local_admin_url(settings)


def _local_provider_url(provider_id: str, values: dict[str, str]) -> str:
    if provider_id == "lmstudio":
        return values.get("LM_STUDIO_BASE_URL", "")
    if provider_id == "llamacpp":
        return values.get("LLAMACPP_BASE_URL", "")
    if provider_id == "ollama":
        return values.get("OLLAMA_BASE_URL", "")
    return ""


async def _check_local_provider(
    provider_id: str, base_url: str, path: str
) -> dict[str, Any]:
    clean_url = base_url.strip().rstrip("/")
    if not clean_url:
        return {
            "provider_id": provider_id,
            "status": "missing_url",
            "label": "Missing URL",
            "base_url": base_url,
        }

    url = f"{clean_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(url)
        ok = 200 <= response.status_code < 300
        return {
            "provider_id": provider_id,
            "status": "reachable" if ok else "offline",
            "label": "Reachable" if ok else "Offline",
            "base_url": base_url,
            "status_code": response.status_code,
        }
    except Exception as exc:
        return {
            "provider_id": provider_id,
            "status": "offline",
            "label": "Offline",
            "base_url": base_url,
            "error_type": type(exc).__name__,
        }
