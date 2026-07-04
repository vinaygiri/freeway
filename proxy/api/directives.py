"""Inline model directives (``@``-mentions) parsed from the latest user turn.

A user can steer one request to a specific model by mentioning it in the prompt:

    @groq/llama-3.3-70b  fix this null check
    refactor this @fast

A directive resolves either directly (``@provider/model`` for a supported
provider) or through a configured alias table (``@fast`` -> ``groq/llama-3.3``).
The matched token is stripped before the prompt is forwarded upstream, so the
model never sees ``@fast``. Only **standalone** ``@`` tokens outside code fences
are considered, so decorators / emails / npm scopes are left untouched.

One directive wins per request: if several distinct targets are mentioned, the
first occurrence is used and the rest are reported as ignored. Per-request only;
session-sticky pins and semantic auto-classes (``@best``) are future work.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from config.provider_ids import SUPPORTED_PROVIDER_IDS

from .models.anthropic import ContentBlockText, Message, MessagesRequest

# A standalone ``@token`` at start-of-string or after whitespace; one trailing
# space is consumed so stripping leaves clean text.
_DIRECTIVE_RE = re.compile(r"(?:^|(?<=\s))@([\w./:-]+)[ \t]?")
_FENCE = "```"


@dataclass(frozen=True, slots=True)
class DirectiveResolution:
    """Outcome of scanning a request for an inline model directive."""

    override_ref: str | None
    ignored: list[str]


def parse_directive_aliases(raw: str) -> dict[str, str]:
    """Parse ``MODEL_DIRECTIVES`` (``key=ref, key2=ref2``) into an alias map."""
    aliases: dict[str, str] = {}
    for pair in raw.split(","):
        text = pair.strip()
        if not text or "=" not in text:
            continue
        key, _, ref = text.partition("=")
        key = key.strip().lstrip("@").strip()
        ref = ref.strip()
        if key and ref:
            aliases[key] = ref
    return aliases


def apply_inline_directive(
    request: MessagesRequest, aliases: Mapping[str, str]
) -> DirectiveResolution:
    """Resolve + strip an inline directive from the latest user message in place."""
    user_message = _latest_user_message(request)
    if user_message is None:
        return DirectiveResolution(None, [])

    resolved_refs: list[str] = []
    content = user_message.content
    if isinstance(content, str):
        new_text, refs = _scan_and_strip(content, aliases)
        if refs:
            user_message.content = new_text
            resolved_refs.extend(refs)
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, ContentBlockText):
                continue
            new_text, refs = _scan_and_strip(block.text, aliases)
            if refs:
                block.text = new_text
                resolved_refs.extend(refs)

    if not resolved_refs:
        return DirectiveResolution(None, [])

    distinct: list[str] = []
    for ref in resolved_refs:
        if ref not in distinct:
            distinct.append(ref)
    return DirectiveResolution(override_ref=distinct[0], ignored=distinct[1:])


def _latest_user_message(request: MessagesRequest) -> Message | None:
    for message in reversed(request.messages):
        if message.role == "user":
            return message
    return None


def _scan_and_strip(text: str, aliases: Mapping[str, str]) -> tuple[str, list[str]]:
    """Strip resolvable directive tokens outside code fences; return (text, refs)."""
    refs: list[str] = []

    def replace(match: re.Match[str]) -> str:
        ref = _resolve_token(match.group(1), aliases)
        if ref is None:
            return match.group(0)  # not a directive — leave untouched
        refs.append(ref)
        return ""

    segments = text.split(_FENCE)
    for index in range(0, len(segments), 2):  # even segments are outside fences
        segments[index] = _DIRECTIVE_RE.sub(replace, segments[index])
    return _FENCE.join(segments), refs


def _resolve_token(token: str, aliases: Mapping[str, str]) -> str | None:
    if token in aliases:
        return aliases[token]
    provider_id, separator, model = token.partition("/")
    if separator and model and provider_id in SUPPORTED_PROVIDER_IDS:
        return token
    return None
