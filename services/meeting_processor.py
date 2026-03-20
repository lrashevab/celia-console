# -*- coding: utf-8 -*-
"""
services/meeting_processor.py — 逐字稿 → 結構化會議記錄
輸出格式對應 Celia 標準會議記錄模板（Header + 項目/內容表格）
主要：Claude API；備援：規則解析
"""
import json
import re
from datetime import date, timedelta
from typing import Optional

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL

# ── 預設記錄人 ───────────────────────────────────────
DEFAULT_RECORDER = "Celia"


# ══════════════════════════════════════════════════════
# 標準會議記錄格式（對應實體表單）
# ══════════════════════════════════════════════════════
EMPTY_MEETING = {
    # Header 欄位
    "meeting_theme": "",      # 會議主題（如：澄塘工事品牌陪跑會議）
    "meeting_date":  "",      # 會議日期 YYYY/MM/DD
    "client_attendees": "",   # 客戶出席
    "location": "",           # 會議地點
    "internal_attendees": "", # 與會同仁（公司內部）
    "recorder": DEFAULT_RECORDER,  # 會議記錄人
    "agenda": "",             # 會議 Agenda 標題
    # 議題表格（list of {topic, content}）
    "topics": [],
    # 其他（供 Calendar / Sheets 用）
    "action_items": [],       # 從 topics 中提取的追蹤事項
    "mode": "rules",
}


# ══════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════
def process_transcript(raw_text: str) -> dict:
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
    today  = date.today().strftime("%Y/%m/%d")

    prompt = f"""你是廣告代理商 Celia 的會議記錄助理，今天日期：{today}

請將以下會議內容整理為標準會議記錄格式，用繁體中文，回傳合法 JSON，不要有 markdown 包裹。

規則：
- meeting_theme：完整的會議名稱（含客戶名稱，如「澄塘工事品牌陪跑第二次訪談」）
- meeting_date：格式 YYYY/MM/DD
- client_attendees：客戶方出席人員（姓名+職稱）
- location：會議地點（若無則留空）
- internal_attendees：公司內部與會人員（若無資訊則填 "Celia"）
- recorder：會議記錄人（預設 "Celia"）
- agenda：本次會議議程標題（一句話）
- topics：議題列表，每項包含 topic（項目名稱）和 content（詳細內容，保留層級結構）
- action_items：追蹤事項列表，每項包含 task、owner、deadline

會議內容：
{raw_text}

JSON 格式：
{{
  "meeting_theme": "...",
  "meeting_date": "YYYY/MM/DD",
  "client_attendees": "...",
  "location": "...",
  "internal_attendees": "...",
  "recorder": "Celia",
  "agenda": "...",
  "topics": [
    {{"topic": "業務模式", "content": "現況說明...\\n未來目標..."}},
    {{"topic": "品牌定位", "content": "..."}}
  ],
  "action_items": [
    {{"task": "...", "owner": "...", "deadline": "YYYY-MM-DD"}}
  ],
  "mode": "ai"
}}"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    result = json.loads(raw)
    result["mode"] = "ai"
    return result


# ══════════════════════════════════════════════════════
# 方案 B：規則備援
# ══════════════════════════════════════════════════════
def _process_with_rules(raw_text: str) -> dict:
    today = date.today()
    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
    result = dict(EMPTY_MEETING)

    # ── Header 欄位提取（支援多空格/Tab 分隔的表格格式）──
    # 分隔符：4個以上空格 或 Tab
    SEP = r"[ \t]{2,}"

    # 每行拆成欄位片段
    def extract_field(pattern, text):
        """在整段文字中找 label，取緊接的值（到下一個 label 或行尾）"""
        m = re.search(pattern + r"\s+" + r"([^\t\n]*?)(?=\s{3,}[\u4e00-\u9fffA-Za-z]|$)", text)
        if m:
            return m.group(1).strip()
        return ""

    # 會議主題：Meeting theme 後，到下一個欄位（Meeting Date）之前
    m = re.search(r"Meeting\s*[Tt]heme\s+(.+?)(?:\s{3,}Meeting\s*[Dd]ate|$)", raw_text, re.MULTILINE)
    result["meeting_theme"] = m.group(1).strip() if m else (lines[0] if lines else "未命名會議")

    # 日期
    m = re.search(r"Meeting\s*[Dd]ate\s+(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})", raw_text)
    result["meeting_date"] = m.group(1).replace("-", "/") if m else today.strftime("%Y/%m/%d")

    # 客戶出席（到下一個欄位前）
    m = re.search(r"客[戶户]出席\s+(.+?)(?:\s{3,}(?:會議地點|地點)|$)", raw_text, re.MULTILINE)
    result["client_attendees"] = m.group(1).strip() if m else ""

    # 會議地點
    m = re.search(r"(?:會議地點|地點)\s+(.+?)(?:\s{3,}[\u4e00-\u9fff]|$)", raw_text, re.MULTILINE)
    result["location"] = m.group(1).strip() if m else ""

    # 與會同仁（到「會議記錄」前）
    m = re.search(r"與會同仁\s+(.+?)(?:\s{3,}會議記錄|$)", raw_text, re.MULTILINE)
    result["internal_attendees"] = m.group(1).strip() if m else DEFAULT_RECORDER

    # 會議記錄人（取第一個中文名，避免後續內容混入）
    m = re.search(r"會議記錄\s+([\u4e00-\u9fff A-Za-z]{1,10})", raw_text)
    result["recorder"] = m.group(1).strip() if m else DEFAULT_RECORDER

    # Agenda
    m = re.search(r"會議\s*Agenda\s+(.+?)(?:\n|$)", raw_text)
    result["agenda"] = m.group(1).strip() if m else ""

    # ── 議題表格提取 ─────────────────────────────────
    topics = []
    current_topic = None
    current_content_lines = []

    # 找到「項目」+「內容」標題行後才開始讀議題（或從 Agenda 之後開始）
    start_idx = 0
    for i, line in enumerate(lines):
        if re.match(r"^項目\s+內容", line) or re.match(r"^項目$", line):
            start_idx = i + 1
            break
        if re.match(r"會議\s*Agenda", line):
            start_idx = i + 1  # 備援：從 Agenda 行之後開始
    content_lines = lines[start_idx:]

    for line in content_lines:
        # 判斷是否為新的議題標題：純中文、2-6字、不含標點符號
        is_heading = (
            not line.startswith("》")
            and not line.startswith("-")
            and not line.startswith("•")
            and not line.startswith("（")
            and re.match(r"^[\u4e00-\u9fff]{2,6}$", line)  # 純中文2-6字
        )
        if is_heading:
            if current_topic:
                topics.append({
                    "topic": current_topic,
                    "content": "\n".join(current_content_lines).strip(),
                })
            current_topic = line
            current_content_lines = []
        else:
            if current_topic:
                current_content_lines.append(line)
            elif line.startswith("》") or line.startswith("-"):
                # 沒有明確標題但有內容，歸入「討論事項」
                if not current_topic:
                    current_topic = "討論事項"
                current_content_lines.append(line)

    if current_topic:
        topics.append({
            "topic": current_topic,
            "content": "\n".join(current_content_lines).strip(),
        })

    # 若無法識別議題，將全文放入一個預設議題
    if not topics and len(content_lines) > 0:
        topics = [{"topic": "會議內容", "content": "\n".join(content_lines)}]

    result["topics"] = topics

    # ── Action Items ─────────────────────────────────
    action_items = []
    for line in lines:
        m2 = re.match(r"([\u4e00-\u9fff]{2,4})\s*負責\s*(.+)", line)
        if m2:
            deadline = _find_deadline(line, today)
            action_items.append({"task": m2.group(2).strip(), "owner": m2.group(1), "deadline": deadline})
    result["action_items"] = action_items
    result["mode"] = "rules"

    return result


def _find_deadline(text: str, today: date) -> str:
    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})[/月](\d{1,2})", text)
    if m:
        return f"{today.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    if "本週" in text:
        return (today + timedelta(days=4 - today.weekday())).isoformat()
    if "下週" in text:
        return (today + timedelta(days=7)).isoformat()
    if "明天" in text:
        return (today + timedelta(days=1)).isoformat()
    return (today + timedelta(days=7)).isoformat()


# ══════════════════════════════════════════════════════
# 格式化 Calendar 描述
# ══════════════════════════════════════════════════════
def format_calendar_description(meeting: dict) -> str:
    lines = []
    lines.append(f"📋 {meeting.get('agenda', meeting.get('meeting_theme', ''))}")
    lines.append(f"📍 {meeting.get('location', '—')}")
    lines.append(f"👥 客戶：{meeting.get('client_attendees', '—')}")
    lines.append(f"🏢 與會：{meeting.get('internal_attendees', '—')}")

    if meeting.get("topics"):
        lines.append("\n── 議題摘要 ──")
        for t in meeting["topics"][:3]:
            lines.append(f"\n【{t['topic']}】")
            content_preview = t["content"][:200] + ("..." if len(t["content"]) > 200 else "")
            lines.append(content_preview)

    if meeting.get("action_items"):
        lines.append("\n── 追蹤事項 ──")
        for item in meeting["action_items"]:
            lines.append(f"• [{item.get('owner','?')}] {item.get('task','')} — {item.get('deadline','TBD')}")

    return "\n".join(lines)
