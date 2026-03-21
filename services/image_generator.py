# -*- coding: utf-8 -*-
"""
services/image_generator.py — 小紅書封面圖生成器

使用 Pollinations.ai — 完全免費，不需要任何 API Key。
直接回傳可顯示的圖片 URL，Streamlit 可用 st.image() 直接渲染。

支援：
  • generate_cover_url()   — 回傳 URL（最快，適合即時預覽）
  • generate_cover_bytes() — 下載圖片 bytes（適合本地儲存）
  • build_xhs_prompt()     — 根據文章內容自動生成圖片描述
"""
from __future__ import annotations
import urllib.parse
import requests
from typing import Optional


# ── XHS 封面尺寸 ──────────────────────────────────────
XHS_WIDTH  = 1080
XHS_HEIGHT = 1440   # 3:4 直版（小紅書主流封面比例）
XHS_SQUARE = 1080   # 1:1 方版（備選）

# ── Pollinations 可用模型 ────────────────────────────
MODELS = {
    "flux":        "Flux（預設，品質佳）",
    "flux-realism":"Flux Realism（真實感）",
    "turbo":       "Turbo（最快速）",
    "flux-pro":    "Flux Pro（最高品質）",
}
DEFAULT_MODEL = "flux"


def build_xhs_prompt(
    title:    str,
    topic:    str,
    keywords: list[str] | None = None,
    style:    str = "modern",
) -> str:
    """
    根據文章標題與主題，生成適合小紅書封面的英文圖片描述。
    （Pollinations 對英文提示效果最好）

    style 選項：
      'modern'   — 現代簡約科技感
      'warm'     — 溫暖生活感
      'bold'     — 大字報爆款風
      'minimal'  — 極簡白底
    """
    style_prompts = {
        "modern": (
            "modern minimalist tech aesthetic, dark blue gradient background, "
            "clean typography, glowing UI elements, professional design"
        ),
        "warm": (
            "warm cozy aesthetic, soft pastel colors, lifestyle photography style, "
            "natural light, Instagram-worthy composition"
        ),
        "bold": (
            "bold graphic design, high contrast colors, large text overlay space, "
            "eye-catching vibrant colors, social media cover design"
        ),
        "minimal": (
            "clean minimal design, white background, subtle shadows, "
            "professional typography space, modern flat design"
        ),
    }

    kw_str = ", ".join(keywords[:3]) if keywords else topic
    style_desc = style_prompts.get(style, style_prompts["modern"])

    return (
        f"Xiaohongshu (Little Red Book) cover image about {topic}, "
        f"featuring {kw_str}, {style_desc}, "
        f"vertical format 3:4 ratio, suitable for social media cover, "
        f"high quality, photorealistic, 8k resolution, "
        f"leave space at top and bottom for text overlay"
    )


def generate_cover_url(
    prompt: str,
    width:  int    = XHS_WIDTH,
    height: int    = XHS_HEIGHT,
    model:  str    = DEFAULT_MODEL,
    seed:   Optional[int] = None,
) -> str:
    """
    回傳 Pollinations.ai 圖片 URL。
    直接放進 st.image() 即可顯示，不消耗任何 API 額度。
    """
    encoded = urllib.parse.quote(prompt)
    base    = f"https://image.pollinations.ai/prompt/{encoded}"
    params  = f"?width={width}&height={height}&model={model}&nologo=true"
    if seed is not None:
        params += f"&seed={seed}"
    return base + params


def generate_cover_variants(
    prompt:   str,
    count:    int = 3,
    width:    int = XHS_WIDTH,
    height:   int = XHS_HEIGHT,
    model:    str = DEFAULT_MODEL,
) -> list[str]:
    """
    生成 N 個不同變體（不同 seed），回傳 URL 列表。
    """
    import random
    urls = []
    for _ in range(count):
        seed = random.randint(1, 99999)
        urls.append(generate_cover_url(prompt, width, height, model, seed))
    return urls


def generate_cover_bytes(url: str, timeout: int = 30) -> bytes:
    """下載圖片 bytes，供儲存或進一步處理。"""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content
