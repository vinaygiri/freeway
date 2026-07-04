from __future__ import annotations

from typing import Any

from api.directives import apply_inline_directive, parse_directive_aliases
from api.model_router import ModelRouter
from api.models.anthropic import ContentBlockText, MessagesRequest
from config.settings import Settings


def _req(content: Any, model: str = "claude-sonnet-4") -> MessagesRequest:
    return MessagesRequest.model_validate(
        {"model": model, "messages": [{"role": "user", "content": content}]}
    )


# -- alias parsing ----------------------------------------------------------
def test_parse_directive_aliases():
    parsed = parse_directive_aliases("fast=groq/llama, @best = open_router/x, bad, k=")
    assert parsed == {"fast": "groq/llama", "best": "open_router/x"}


# -- directive resolution + stripping ---------------------------------------
def test_direct_provider_model_ref_is_stripped():
    req = _req("@groq/llama-3.3-70b fix this null check")
    result = apply_inline_directive(req, {})
    assert result.override_ref == "groq/llama-3.3-70b"
    assert result.ignored == []
    assert req.messages[0].content == "fix this null check"


def test_alias_resolves_and_strips():
    req = _req("refactor this @fast please")
    result = apply_inline_directive(req, {"fast": "groq/llama"})
    assert result.override_ref == "groq/llama"
    assert req.messages[0].content == "refactor this please"


def test_unresolved_tokens_left_intact():
    req = _req("mail @someone and @notaprovider/x")
    result = apply_inline_directive(req, {})
    assert result.override_ref is None
    assert req.messages[0].content == "mail @someone and @notaprovider/x"


def test_conflict_first_wins_rest_ignored_all_stripped():
    req = _req("@groq/a then @cerebras/b")
    result = apply_inline_directive(req, {})
    assert result.override_ref == "groq/a"
    assert result.ignored == ["cerebras/b"]
    assert "@groq" not in req.messages[0].content
    assert "@cerebras" not in req.messages[0].content


def test_same_target_twice_is_not_a_conflict():
    req = _req("@groq/a and again @groq/a")
    result = apply_inline_directive(req, {})
    assert result.override_ref == "groq/a"
    assert result.ignored == []


def test_directive_inside_code_fence_is_ignored():
    req = _req("literal ```@groq/a``` but @cerebras/b routes")
    result = apply_inline_directive(req, {})
    assert result.override_ref == "cerebras/b"
    assert "@groq/a" in req.messages[0].content  # fenced token preserved


def test_directive_in_content_block_text():
    req = MessagesRequest.model_validate(
        {
            "model": "x",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "go @groq/a now"}],
                }
            ],
        }
    )
    result = apply_inline_directive(req, {})
    assert result.override_ref == "groq/a"
    block = req.messages[0].content[0]
    assert isinstance(block, ContentBlockText)
    assert block.text == "go now"


def test_only_latest_user_message_is_scanned():
    req = MessagesRequest.model_validate(
        {
            "model": "x",
            "messages": [
                {"role": "user", "content": "@groq/a old"},
                {"role": "assistant", "content": "ok"},
                {"role": "user", "content": "@cerebras/b new"},
            ],
        }
    )
    result = apply_inline_directive(req, {})
    assert result.override_ref == "cerebras/b"


# -- router integration -----------------------------------------------------
def test_router_directive_overrides_routed_provider():
    router = ModelRouter(Settings())
    routed = router.resolve_messages_request(_req("@groq/llama-3.3 do it"))
    assert routed.resolved.provider_id == "groq"
    assert routed.resolved.provider_model == "llama-3.3"
    assert routed.request.messages[0].content == "do it"


def test_router_alias_directive_from_settings():
    settings = Settings()
    settings.model_directives = "fast=groq/llama-3.3"
    router = ModelRouter(settings)
    routed = router.resolve_messages_request(_req("@fast go"))
    assert routed.resolved.provider_id == "groq"


def test_router_without_directive_uses_request_model():
    router = ModelRouter(Settings())
    routed = router.resolve_messages_request(_req("no directive", model="nvidia_nim/m"))
    assert routed.resolved.provider_id == "nvidia_nim"
    assert routed.request.messages[0].content == "no directive"
