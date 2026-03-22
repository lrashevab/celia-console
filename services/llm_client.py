# -*- coding: utf-8 -*-
"""
services/llm_client.py — 統一 LLM 呼叫層

支援：
  • Gemini API   (google-genai，設定 GEMINI_API_KEY)
  • Anthropic    (anthropic，設定 ANTHROPIC_API_KEY)

優先順序：GEMINI → ANTHROPIC
若都未設定，raise LLMNotConfiguredError。

Streaming 版本：generate_stream() → Generator[str]
同步版本：generate() → str
"""
from __future__ import annotations
import os
from typing import Generator

# ── 預設模型 ────────────────────────────────────────
DEFAULT_GEMINI    = "gemini-2.5-flash-lite"
DEFAULT_ANTHROPIC = "claude-sonnet-4-6"


class LLMNotConfiguredError(Exception):
    pass


def _get_keys() -> tuple[str, str]:
    gemini_key    = os.environ.get("GEMINI_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    # fallback to config/settings.py
    try:
        from config.settings import ANTHROPIC_API_KEY
        if not anthropic_key and ANTHROPIC_API_KEY:
            anthropic_key = ANTHROPIC_API_KEY
    except Exception:
        pass
    try:
        from config.settings import GEMINI_API_KEY  # type: ignore
        if not gemini_key and GEMINI_API_KEY:
            gemini_key = GEMINI_API_KEY
    except Exception:
        pass
    return gemini_key, anthropic_key


def active_provider() -> str | None:
    """回傳目前可用的 provider：'gemini' | 'anthropic' | None"""
    gk, ak = _get_keys()
    if gk:
        return "gemini"
    if ak:
        return "anthropic"
    return None


def provider_label() -> str:
    p = active_provider()
    if p == "gemini":
        return f"✅ Gemini ({DEFAULT_GEMINI})"
    if p == "anthropic":
        return f"✅ Claude ({DEFAULT_ANTHROPIC})"
    return "❌ 未設定任何 LLM API Key"


# ══════════════════════════════════════════════════════
# Streaming 生成
# ══════════════════════════════════════════════════════
def generate_stream(
    system: str,
    user:   str,
    max_tokens: int = 2000,
) -> Generator[str, None, None]:
    """
    依可用 provider 生成文字，逐 token yield。
    """
    gk, ak = _get_keys()

    if gk:
        yield from _gemini_stream(gk, system, user, max_tokens)
    elif ak:
        yield from _anthropic_stream(ak, system, user, max_tokens)
    else:
        raise LLMNotConfiguredError(
            "請設定 GEMINI_API_KEY 或 ANTHROPIC_API_KEY\n"
            "Gemini 免費 Key 取得：https://aistudio.google.com/apikey"
        )


def generate(
    system: str,
    user:   str,
    max_tokens: int = 2000,
) -> str:
    return "".join(generate_stream(system, user, max_tokens))


# ── Gemini streaming ─────────────────────────────────
def _gemini_stream(
    api_key: str, system: str, user: str, max_tokens: int
) -> Generator[str, None, None]:
    from google import genai
    from google.genai import types

    client   = genai.Client(api_key=api_key)
    combined = f"{system}\n\n---\n\n{user}" if system else user

    for chunk in client.models.generate_content_stream(
        model=DEFAULT_GEMINI,
        contents=combined,
        config=types.GenerateContentConfig(max_output_tokens=max_tokens),
    ):
        if chunk.text:
            yield chunk.text


# ── Anthropic streaming ──────────────────────────────
def _anthropic_stream(
    api_key: str, system: str, user: str, max_tokens: int
) -> Generator[str, None, None]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=DEFAULT_ANTHROPIC,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for text in stream.text_stream:
            yield text
