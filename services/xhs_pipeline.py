# -*- coding: utf-8 -*-
"""
services/xhs_pipeline.py — 小紅書爆款內容生成 Pipeline

4 步驟工作流：
1. 信息檢索   — Tavily REST API（或手動貼入）
2. 撰寫文章   — Claude API，800-1200 字 XHS 風格
3. 格式適配   — 標題萃取、Hashtag 轉換、圖片驗證、JSON 輸出
4. 發佈       — 輸出發佈包（預留 XHS API 接口）
"""
from __future__ import annotations

import json
import os
import re
import requests
from datetime import datetime, timedelta
from typing import Generator


# ══════════════════════════════════════════════════════
# Step 1 — 信息檢索
# ══════════════════════════════════════════════════════
def step1_research(topic: str, days: int = 14) -> dict:
    """
    呼叫 Tavily API 搜尋最近 N 天的高品質資料與圖片。
    若無 API Key，回傳 empty，上層 UI 引導使用者手動貼入。
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    try:
        from config.settings import TAVILY_API_KEY as cfg_key  # type: ignore
        if not api_key and cfg_key:
            api_key = cfg_key
    except Exception:
        pass

    result = {
        "articles": [],
        "images":   [],
        "query":    topic,
        "source":   "tavily" if api_key else "manual",
    }

    if not api_key:
        return result

    try:
        payload = {
            "api_key":       api_key,
            "query":         f"{topic} 最新趨勢 小紅書",
            "search_depth":  "advanced",
            "include_images": True,
            "max_results":   6,
            "days":          days,
        }
        resp = requests.post(
            "https://api.tavily.com/search",
            json=payload, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("results", []):
            result["articles"].append({
                "title":   item.get("title", ""),
                "url":     item.get("url", ""),
                "content": item.get("content", "")[:500],  # 節省 tokens
                "score":   item.get("score", 0),
            })

        # 圖片：最多 4 張
        for img in data.get("images", [])[:4]:
            result["images"].append(img if isinstance(img, str) else img.get("url", ""))

    except Exception as e:
        result["error"] = str(e)

    return result


# ══════════════════════════════════════════════════════
# Step 2 — 撰寫文章（Generator Pattern，逐 token 回傳）
# ══════════════════════════════════════════════════════
SYSTEM_PROMPT_XHS = """你是一位在小紅書上有 50 萬粉絲的內容創作者，專門寫科技與 AI 工具使用心得。

你的寫作風格：
- 語氣：年輕、活潑、真實，像在跟閨蜜分享，不是在寫報告
- 結構：開頭一句爆款金句（10-15字，引發好奇心）→ 正文（分段，每段 emoji 開頭）→ 結語（號召互動）
- 字數：800-1200 字
- emoji：每個段落開頭必用，正文自然穿插，但不過度
- 口頭禪：「真的很絕」「姐妹們」「絕了」「震驚」「好家伙」等偶爾出現，但要自然
- 禁止：不說廢話、不用「綜上所述」「總而言之」等書面語
- 標題：另外單獨在第一行寫，格式「【標題】」，20字以內

寫文章步驟：
1. 先寫吸睛標題（放在【】中）
2. 開頭金句（獨立一行，讓人想繼續讀）
3. 正文（4-6 個段落，每段有 emoji + 小標題）
4. 結尾互動句（問讀者問題，引導評論）
5. 最後一行：5 個 hashtag（用 # 標記）"""


def step2_generate_stream(topic: str, research: dict) -> Generator[str, None, None]:
    """用統一 LLM Client（Gemini 優先，fallback Claude）streaming 生成文章"""
    from services.llm_client import generate_stream, LLMNotConfiguredError

    ref_parts = []
    for art in research.get("articles", [])[:4]:
        if art.get("content"):
            ref_parts.append(f"來源：{art['title']}\n{art['content']}")
    ref_text = "\n\n---\n\n".join(ref_parts) if ref_parts else "（使用者提供的主題，無外部資料）"

    user_prompt = f"""主題：{topic}

參考資料（最近搜尋結果）：
{ref_text}

請基於以上資料，用你的風格寫一篇小紅書爆款文章。"""

    try:
        yield from generate_stream(SYSTEM_PROMPT_XHS, user_prompt, max_tokens=1800)
    except LLMNotConfiguredError as e:
        yield str(e)


def step2_generate(topic: str, research: dict) -> str:
    """非 streaming 版本，回傳完整文章"""
    return "".join(step2_generate_stream(topic, research))


# ══════════════════════════════════════════════════════
# Step 3 — 格式適配
# ══════════════════════════════════════════════════════
def step3_format(raw_article: str, images: list[str]) -> dict:
    """
    解析文章，萃取標題、轉換 hashtag、驗證圖片、輸出標準 JSON。
    """
    # ── 萃取標題 ─────────────────────────────────────
    title = ""
    title_match = re.search(r"【(.+?)】", raw_article)
    if title_match:
        title = title_match.group(1)[:20]
    else:
        # fallback：取第一行非空行
        for line in raw_article.splitlines():
            line = line.strip()
            if line and len(line) <= 30:
                title = line[:20]
                break

    # ── 正文（去掉標題行）────────────────────────────
    content = re.sub(r"^【.+?】\s*\n?", "", raw_article, count=1, flags=re.MULTILINE).strip()

    # ── 萃取 hashtag ─────────────────────────────────
    raw_tags = re.findall(r"#(\S+)", raw_article)
    # 去掉 hashtag 行，讓 content 乾淨
    content_clean = re.sub(r"\n?#\S+(\s+#\S+)*\s*$", "", content, flags=re.MULTILINE).strip()

    # ── Hashtag → 自然語言（在 content 內轉換）────────
    # 小紅書演算法偏好自然語言話題標籤，而非 #tag 語法
    natural_topics = [t for t in raw_tags[:5]]  # 保留 5 個

    # 如果 hashtag 不足，用 AI 規則補足
    if len(natural_topics) < 5:
        topic_fallbacks = ["AI工具", "效率提升", "設計師日常", "ClaudeCode", "AI工作流"]
        for fb in topic_fallbacks:
            if fb not in natural_topics:
                natural_topics.append(fb)
            if len(natural_topics) >= 5:
                break

    # ── 圖片驗證 ─────────────────────────────────────
    valid_images = []
    for url in images[:4]:
        if not url:
            continue
        try:
            r = requests.head(url, timeout=5, allow_redirects=True)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and "image" in ct:
                valid_images.append(url)
        except Exception:
            pass  # 無效連結直接跳過

    # ── 字數統計 ─────────────────────────────────────
    word_count = len(content_clean)

    return {
        "title":         title,
        "content":       content_clean,
        "topics":        natural_topics[:5],
        "images":        valid_images,
        "word_count":    word_count,
        "within_limit":  800 <= word_count <= 1200,
        "raw_article":   raw_article,
        "generated_at":  datetime.now().isoformat(),
    }


# ══════════════════════════════════════════════════════
# Step 4 — 發佈包輸出
# ══════════════════════════════════════════════════════
def step4_publish_package(formatted: dict) -> dict:
    """
    組裝標準發佈包（JSON 格式），預留 XHS API 接口。
    目前輸出結構化 JSON，供手動發佈或接 XHS MCP 使用。
    """
    package = {
        "platform":   "xiaohongshu",
        "title":      formatted["title"],
        "content":    formatted["content"],
        "topics":     formatted["topics"],
        "images":     formatted["images"],
        "status":     "ready",
        "publish_at": None,  # None = 立即發佈
        "meta": {
            "word_count":   formatted["word_count"],
            "within_limit": formatted["within_limit"],
            "generated_at": formatted["generated_at"],
        },
    }

    # ── 嘗試呼叫 XHS API（若已配置）─────────────────
    xhs_cookie = os.environ.get("XHS_COOKIE", "")
    if xhs_cookie:
        try:
            result = _call_xhs_api(package, xhs_cookie)
            package["status"]    = "published"
            package["xhs_result"] = result
        except Exception as e:
            package["status"] = "ready"  # fallback to manual
            package["xhs_error"] = str(e)

    return package


def _call_xhs_api(package: dict, cookie: str) -> dict:
    """
    預留：呼叫小紅書發佈 API。
    目前為 stub，待 XHS MCP 或第三方庫整合後填入。
    """
    # TODO: 接入 XHS MCP 或 https://github.com/hominsu/xhs-api
    raise NotImplementedError("XHS API 尚未配置，請手動複製貼上發佈")
