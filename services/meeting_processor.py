# -*- coding: utf-8 -*-
"""
services/meeting_processor.py — 逐字稿 → 結構化會議記錄
主要：Claude API（claude-sonnet-4-6）
備援：規則解析（無 API Key 時自動切換）
"""
import json
import re
from datetime import date, timedelta
from typing import Optional

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL


# ══════════════════════════════════════════════════════
# 主入口：自動選擇 AI / 規則 處理
# ══════════════════════════════════════════════════════
def process_transcript(raw_text: str) -> dict:
    """
    輸入：會議逐字稿或條列重點
    輸出：結構化 dict
    有 API Key → 用 Claude API；無 → 規則備援
    """
    if ANTHROPIC_API_KEY:
        try:
            return _process_with_claude(raw_text)
        except Exception:
            pass
    return _process_with_rules(raw_text)


# ══════════════════════════════════════════════════════
# 方案 A：Claude API
# ══════════════════════════════════════════════════════
def _process_with_claude(raw_text: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today  = date.today().isoformat()

    prompt = f"""你是一位專業的廣告代理商會議記錄助理。今天日期：{today}

請將以下會議內容結構化，用繁體中文輸出，必須回傳合法 JSON，不要有任何 markdown 包裹。

會議內容：
{raw_text}

JSON 格式：
{{
  "title": "會議主題（15字以內）",
  "date": "YYYY-MM-DD（若無明確日期則用今天）",
  "start_time": "HH:MM（若無則用 10:00）",
  "duration_hours": 1,
  "attendees": ["參與者1", "參與者2"],
  "client": "客戶名稱（若無則留空）",
  "summary": "三句話以內的會議摘要",
  "decisions": ["決策1", "決策2"],
  "action_items": [
    {{"task": "任務描述", "owner": "負責人", "deadline": "YYYY-MM-DD"}}
  ],
  "next_meeting": "下次會議時間（若無則為 null）",
  "mode": "ai"
}}"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    result = json.loads(raw)
    result["mode"] = "ai"
    return result


# ══════════════════════════════════════════════════════
# 方案 B：規則備援（無 API Key）
# ══════════════════════════════════════════════════════
def _process_with_rules(raw_text: str) -> dict:
    """純規則解析，不需 API Key"""
    today = date.today()
    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]

    # ── 標題：取第一行 ────────────────────────────────
    title = lines[0][:20] if lines else "未命名會議"

    # ── 日期 ─────────────────────────────────────────
    date_str = _extract_date(raw_text, today)

    # ── 時間 ─────────────────────────────────────────
    m = re.search(r"(\d{1,2}):(\d{2})", raw_text)
    start_time = f"{int(m.group(1)):02d}:{m.group(2)}" if m else "10:00"

    # ── 出席者 ───────────────────────────────────────
    attendees = _extract_attendees(raw_text)

    # ── 客戶 ─────────────────────────────────────────
    client = _extract_client(raw_text)

    # ── 決策（「決定」「決策」「確認」開頭的行）────────
    decisions = []
    for line in lines:
        if re.match(r"(決定|決策|確認|結論|agreed|decided)[：:：]?\s*", line, re.I):
            text = re.sub(r"^(決定|決策|確認|結論|agreed|decided)[：:：]?\s*", "", line, flags=re.I)
            if text:
                decisions.append(text)

    # ── Action Items（「負責」「截止」「要做」「action」）
    action_items = _extract_action_items(lines, today)

    # ── 摘要：取前3行有實質內容的句子 ─────────────────
    summary_lines = [l for l in lines[1:] if len(l) > 8][:3]
    summary = "。".join(summary_lines) if summary_lines else lines[0] if lines else "—"

    return {
        "title": title,
        "date": date_str,
        "start_time": start_time,
        "duration_hours": 1,
        "attendees": attendees,
        "client": client,
        "summary": summary,
        "decisions": decisions,
        "action_items": action_items,
        "next_meeting": _extract_next_meeting(raw_text, today),
        "mode": "rules",
    }


def _extract_date(text: str, today: date) -> str:
    # YYYY-MM-DD
    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # M/D 或 M月D日
    m = re.search(r"(\d{1,2})[/月](\d{1,2})[日號]?", text)
    if m:
        return f"{today.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    # 今天/昨天/明天
    if "今天" in text or "今日" in text:
        return today.isoformat()
    if "昨天" in text or "昨日" in text:
        return (today - timedelta(days=1)).isoformat()
    return today.isoformat()


def _extract_attendees(text: str) -> list:
    attendees = []
    # 「出席：A、B、C」格式
    m = re.search(r"出席[人者]?[：:]\s*(.+)", text)
    if m:
        raw = m.group(1)
        attendees = [a.strip() for a in re.split(r"[、，,\s]+", raw) if a.strip()]
    if not attendees:
        # 找2~4字的中文名詞（非動詞）
        candidates = re.findall(r"(?<![的地得])[\u4e00-\u9fff]{2,4}(?=說|表示|負責|確認|提出)", text)
        attendees = list(dict.fromkeys(candidates))[:5]
    return attendees or ["Celia"]


def _extract_client(text: str) -> str:
    m = re.search(r"客戶[：:\s]*([^\s，,。\d]{2,10})", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:與|和|跟|for)\s*([\u4e00-\u9fff A-Za-z]{2,12})\s*(?:開會|討論|會議)", text)
    if m:
        return m.group(1).strip()
    return ""


def _extract_action_items(lines: list, today: date) -> list:
    items = []
    for line in lines:
        # 以「負責」「要」「去做」「需要」「請X」開頭的行
        m_owner = re.search(r"(?:請|由|麻煩)\s*([\u4e00-\u9fff]{2,4})\s*(?:負責|去|來|做)", line)
        m_task  = re.search(r"(?:負責|要|需要|去做|請.{2,4})\s*(.{4,30})", line)

        # 「X 負責 Y」格式
        m2 = re.match(r"([\u4e00-\u9fff]{2,4})\s*負責\s*(.+)", line)
        if m2:
            deadline = _find_deadline(line, today)
            items.append({"task": m2.group(2).strip(), "owner": m2.group(1), "deadline": deadline})
            continue

        if m_task:
            owner = m_owner.group(1) if m_owner else "Celia"
            deadline = _find_deadline(line, today)
            task_text = m_task.group(1).strip()
            if len(task_text) > 3:
                items.append({"task": task_text, "owner": owner, "deadline": deadline})
    return items[:8]  # 最多 8 項


def _find_deadline(text: str, today: date) -> str:
    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})[/月](\d{1,2})[日號]?(?:前|截止)?", text)
    if m:
        return f"{today.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    if "本週" in text or "這週" in text:
        days_left = 4 - today.weekday()
        return (today + timedelta(days=max(days_left, 1))).isoformat()
    if "下週" in text or "下星期" in text:
        return (today + timedelta(days=7)).isoformat()
    if "明天" in text:
        return (today + timedelta(days=1)).isoformat()
    return (today + timedelta(days=7)).isoformat()


def _extract_next_meeting(text: str, today: date) -> Optional[str]:
    m = re.search(r"下次(?:會議|開會)[：:\s]*(.{2,20})", text)
    if m:
        return m.group(1).strip()
    if "下週" in text and "開會" in text:
        return (today + timedelta(days=7)).isoformat()
    return None


# ══════════════════════════════════════════════════════
# 格式化 Calendar 描述
# ══════════════════════════════════════════════════════
def format_calendar_description(meeting: dict) -> str:
    lines = []
    mode_label = "🤖 AI 結構化" if meeting.get("mode") == "ai" else "📝 規則解析"
    lines.append(f"📋 {meeting.get('summary', '')}  [{mode_label}]")

    if meeting.get("decisions"):
        lines.append("\n✅ 決策事項：")
        for d in meeting["decisions"]:
            lines.append(f"  • {d}")

    if meeting.get("action_items"):
        lines.append("\n📌 追蹤事項：")
        for item in meeting["action_items"]:
            lines.append(f"  • [{item.get('owner','?')}] {item.get('task','')} — 截止：{item.get('deadline','TBD')}")

    if meeting.get("next_meeting"):
        lines.append(f"\n🗓 下次會議：{meeting['next_meeting']}")

    return "\n".join(lines)
