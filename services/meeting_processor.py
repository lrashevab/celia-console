# -*- coding: utf-8 -*-
"""
services/meeting_processor.py — 逐字稿 → 結構化會議記錄
使用 Claude API，僅在工作 context 中使用
"""
import json
import re
from datetime import date

import anthropic

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL


def process_transcript(raw_text: str) -> dict:
    """
    輸入：會議逐字稿或條列重點
    輸出：結構化 dict，包含標題、摘要、action items、決策
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    today = date.today().isoformat()

    prompt = f"""你是一位專業的會議記錄助理。今天日期：{today}

請將以下會議內容結構化，用繁體中文輸出，必須回傳合法 JSON，不要有任何 markdown 包裹。

會議內容：
{raw_text}

JSON 格式：
{{
  "title": "會議主題（10字以內）",
  "date": "YYYY-MM-DD（若無明確日期則用今天）",
  "start_time": "HH:MM（若無則用 09:00）",
  "duration_hours": 1,
  "attendees": ["參與者1", "參與者2"],
  "client": "客戶名稱（若無則留空）",
  "summary": "三句話以內的會議摘要",
  "decisions": ["決策1", "決策2"],
  "action_items": [
    {{"task": "任務描述", "owner": "負責人", "deadline": "YYYY-MM-DD"}}
  ],
  "next_meeting": "下次會議時間（若無則為 null）"
}}"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # 移除可能的 markdown 包裹
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


def format_calendar_description(meeting: dict) -> str:
    """將結構化會議資料格式化為 Calendar 事件描述"""
    lines = [f"📋 {meeting.get('summary', '')}"]

    if meeting.get("decisions"):
        lines.append("\n✅ 決策事項：")
        for d in meeting["decisions"]:
            lines.append(f"  • {d}")

    if meeting.get("action_items"):
        lines.append("\n📌 追蹤事項：")
        for item in meeting["action_items"]:
            lines.append(f"  • [{item.get('owner','?')}] {item.get('task','')} — 截止：{item.get('deadline','TBD')}")

    return "\n".join(lines)
