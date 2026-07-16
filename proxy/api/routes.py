"""FastAPI route handlers."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from loguru import logger

from config.model_refs import parse_provider_type
from config.settings import Settings
from core.anthropic import get_token_count
from core.trace import trace_event

from . import dependencies
from .data_governor import DataGovernor
from .dependencies import get_settings, require_api_key
from .handlers import (
    ChatCompletionsHandler,
    MessagesHandler,
    ResponsesHandler,
    TokenCountHandler,
)
from .model_catalog import build_models_list_response
from .models.anthropic import MessagesRequest, TokenCountRequest
from .models.openai_chat_completions import ChatCompletionsRequest
from .models.openai_responses import OpenAIResponsesRequest
from .models.responses import ModelsListResponse
from .router_policy import RoutingPolicy

router = APIRouter()


def _provider_getter(request: Request, settings: Settings):
    return lambda provider_type: dependencies.resolve_provider(
        provider_type, app=request.app
    )


def _routing_policy(request: Request, settings: Settings) -> RoutingPolicy:
    """Build a per-request routing policy from app-scoped health/quota/circuit state."""
    runtime = dependencies.maybe_provider_runtime(request.app)
    return RoutingPolicy(
        circuit_breaker=dependencies.maybe_circuit_breaker(request.app),
        quota_governor=dependencies.maybe_quota_governor(request.app),
        health_store=dependencies.maybe_health_store(request.app),
        model_info_lookup=runtime.cached_model_info if runtime is not None else None,
        recent_requests=dependencies.maybe_recent_request_store(request.app),
        data_governor=DataGovernor.from_settings(settings),
    )


def get_messages_handler(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> MessagesHandler:
    """Build the Claude Messages product handler for route handlers."""
    return MessagesHandler(
        settings,
        provider_getter=_provider_getter(request, settings),
        token_counter=get_token_count,
        quota_tracker=dependencies.maybe_quota_tracker(request.app),
        routing_policy=_routing_policy(request, settings),
        response_cache=dependencies.maybe_response_cache(request.app),
    )


def get_responses_handler(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ResponsesHandler:
    """Build the OpenAI Responses product handler for route handlers."""
    return ResponsesHandler(
        settings,
        provider_getter=_provider_getter(request, settings),
        quota_tracker=dependencies.maybe_quota_tracker(request.app),
        routing_policy=_routing_policy(request, settings),
    )


def get_chat_completions_handler(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ChatCompletionsHandler:
    """Build the OpenAI Chat Completions product handler for route handlers."""
    return ChatCompletionsHandler(
        settings,
        provider_getter=_provider_getter(request, settings),
        quota_tracker=dependencies.maybe_quota_tracker(request.app),
        routing_policy=_routing_policy(request, settings),
    )


def get_token_count_handler(
    settings: Settings = Depends(get_settings),
) -> TokenCountHandler:
    """Build the token-count product handler for route handlers."""
    return TokenCountHandler(settings, token_counter=get_token_count)


def _probe_response(allow: str) -> Response:
    """Return an empty success response for compatibility probes."""
    return Response(status_code=204, headers={"Allow": allow})


# =============================================================================
# Routes
# =============================================================================
@router.post("/v1/messages")
async def create_message(
    request_data: MessagesRequest,
    handler: MessagesHandler = Depends(get_messages_handler),
    _auth=Depends(require_api_key),
):
    """Create a message (always streaming)."""
    return await handler.create(request_data)


@router.api_route("/v1/messages", methods=["HEAD", "OPTIONS"])
async def probe_messages(_auth=Depends(require_api_key)):
    """Respond to Claude compatibility probes for the messages endpoint."""
    return _probe_response("POST, HEAD, OPTIONS")


@router.post("/v1/responses")
async def create_response(
    request_data: OpenAIResponsesRequest,
    handler: ResponsesHandler = Depends(get_responses_handler),
    _auth=Depends(require_api_key),
):
    """Create an OpenAI Responses-compatible response through this proxy."""
    return await handler.create(request_data)


@router.api_route("/v1/responses", methods=["HEAD", "OPTIONS"])
async def probe_responses(_auth=Depends(require_api_key)):
    """Respond to OpenAI Responses compatibility probes."""
    return _probe_response("POST, HEAD, OPTIONS")


@router.post("/v1/chat/completions")
async def create_chat_completion(
    request_data: ChatCompletionsRequest,
    handler: ChatCompletionsHandler = Depends(get_chat_completions_handler),
    _auth=Depends(require_api_key),
):
    """Create an OpenAI Chat Completions-compatible response through this proxy."""
    return await handler.create(request_data)


@router.api_route("/v1/chat/completions", methods=["HEAD", "OPTIONS"])
async def probe_chat_completions(_auth=Depends(require_api_key)):
    """Respond to OpenAI Chat Completions compatibility probes."""
    return _probe_response("POST, HEAD, OPTIONS")


@router.post("/v1/messages/count_tokens")
async def count_tokens(
    request_data: TokenCountRequest,
    handler: TokenCountHandler = Depends(get_token_count_handler),
    _auth=Depends(require_api_key),
):
    """Count tokens for a request."""
    return handler.count(request_data)


@router.api_route("/v1/messages/count_tokens", methods=["HEAD", "OPTIONS"])
async def probe_count_tokens(_auth=Depends(require_api_key)):
    """Respond to Claude compatibility probes for the token count endpoint."""
    return _probe_response("POST, HEAD, OPTIONS")


@router.get("/")
async def root(
    settings: Settings = Depends(get_settings), _auth=Depends(require_api_key)
):
    """Root endpoint."""
    return {
        "status": "ok",
        "provider": parse_provider_type(settings.model),
        "model": settings.model,
    }


@router.api_route("/", methods=["HEAD", "OPTIONS"])
async def probe_root():
    """Respond to unauthenticated local compatibility probes for the root endpoint."""
    return _probe_response("GET, HEAD, OPTIONS")


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/v1/health/stats")
async def health_stats(request: Request, _auth=Depends(require_api_key)):
    """Return per-provider health/latency stats and stability scores."""
    store = dependencies.maybe_health_store(request.app)
    if store is None:
        return {"enabled": False, "targets": {}}
    return {"enabled": True, "targets": store.snapshot()}


@router.api_route("/v1/health/stats", methods=["HEAD", "OPTIONS"])
async def probe_health_stats(_auth=Depends(require_api_key)):
    """Respond to compatibility probes for the health stats endpoint."""
    return _probe_response("GET, HEAD, OPTIONS")


@router.get("/v1/quota/stats")
async def quota_stats(request: Request, _auth=Depends(require_api_key)):
    """Return per-provider quota consumption, headroom, and exhaustion signals."""
    governor = dependencies.maybe_quota_governor(request.app)
    if governor is None:
        return {"enabled": False, "providers": {}}
    return {"enabled": True, "providers": governor.snapshot()}


@router.api_route("/v1/quota/stats", methods=["HEAD", "OPTIONS"])
async def probe_quota_stats(_auth=Depends(require_api_key)):
    """Respond to compatibility probes for the quota stats endpoint."""
    return _probe_response("GET, HEAD, OPTIONS")


@router.api_route("/health", methods=["HEAD", "OPTIONS"])
async def probe_health():
    """Respond to compatibility probes for the health endpoint."""
    return _probe_response("GET, HEAD, OPTIONS")


@router.get("/v1/models", response_model=ModelsListResponse)
async def list_models(
    request: Request,
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_api_key),
):
    """List the model ids this proxy advertises to Claude-compatible clients."""
    trace_event(stage="ingress", event="api.models.list", source="api")
    provider_runtime = dependencies.maybe_provider_runtime(request.app)
    return build_models_list_response(settings, provider_runtime)


@router.post("/stop")
async def stop_cli(request: Request, _auth=Depends(require_api_key)):
    """Stop all CLI sessions and pending tasks."""
    workflow = getattr(request.app.state, "messaging_workflow", None)
    if not workflow:
        # Fallback if messaging not initialized
        cli_manager = getattr(request.app.state, "cli_manager", None)
        if cli_manager:
            await cli_manager.stop_all()
            logger.info("STOP_CLI: source=cli_manager cancelled_count=N/A")
            return {"status": "stopped", "source": "cli_manager"}
        raise HTTPException(status_code=503, detail="Messaging system not initialized")

    count = await workflow.stop_all_tasks()
    trace_event(
        stage="ingress",
        event="api.cli.stop_via_messaging_workflow",
        source="api",
        cancelled_nodes=count,
    )
    logger.info("STOP_CLI: source=messaging_workflow cancelled_count={}", count)
    return {"status": "stopped", "cancelled_count": count}
