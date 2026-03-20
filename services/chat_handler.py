# -*- coding: utf-8 -*-
"""
services/chat_handler.py — 控制台對話框指令解析器
解析自然語言指令 → 操作 Google Sheets
不需 API Key，純規則解析
"""
import re
import uuid
from datetime import date, datetime, timedelta


# ── 日期解析 ────────────────────────────────────────
def _parse_date(text: str) -> str:
    """從文字中提取日期，支援多種格式"""
    today = date.today()
    text = text.strip()

    patterns = [
        (r"明天", lambda: (today + timedelta(days=1)).isoformat()),
        (r"後天", lambda: (today + timedelta(days=2)).isoformat()),
        (r"下週[一二三四五六日]?", lambda: (today + timedelta(days=7)).isoformat()),
        (r"本週[五六日]", lambda: (today + timedelta(days=4 - today.weekday())).isoformat()),
        (r"(\d{1,2})[/\-月](\d{1,2})[日號]?", lambda m: f"{today.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"),
        (r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
    ]

    for pat, resolver in patterns:
        m = re.search(pat, text)
        if m:
            try:
                result = resolver() if not callable(resolver.__code__) else resolver()
                return result if isinstance(result, str) else result(m)
            except Exception:
                pass

    # 預設：7天後
    return (today + timedelta(days=7)).isoformat()


def _parse_account(text: str, clients_work=None, clients_personal=None) -> str:
    """從文字判斷帳號類型"""
    if any(k in text for k in ["接案", "freelance", "個人專案", "lrashevab"]):
        return "personal"
    if any(k in text for k in ["工作", "sirius", "公司"]):
        return "work"
    return "work"  # 預設


def _parse_priority(text: str) -> str:
    if any(k in text for k in ["緊急", "急", "重要", "high", "高優先"]):
        return "high"
    if any(k in text for k in ["low", "低優先", "不急"]):
        return "low"
    return "medium"


# ══════════════════════════════════════════════════
# 指令解析主函數
# ══════════════════════════════════════════════════
def parse_command(text: str, context: dict = None) -> dict:
    """
    解析用戶輸入，返回操作指令
    回傳格式：
    {
        "action": "add_task" | "add_todo" | "complete_task" | "add_client" | "query" | "unknown",
        "data": {...},
        "reply": "給用戶的回覆文字",
        "account": "work" | "personal",
    }
    """
    t = text.strip()

    # ── 新增任務 ─────────────────────────────────────
    if any(k in t for k in ["新增任務", "加任務", "建立任務", "add task", "幫我記", "任務："]):
        title = re.sub(r"(新增任務|加任務|建立任務|幫我記|任務：)\s*", "", t).strip()
        # 提取客戶名稱
        client = ""
        m = re.search(r"(?:給|客戶：?|for)\s*([^\s，,。\d]+)", t)
        if m:
            client = m.group(1).strip()
            title = title.replace(m.group(0), "").strip()

        due = _parse_date(t)
        priority = _parse_priority(t)
        account = _parse_account(t)
        task_id = f"T{uuid.uuid4().hex[:4].upper()}"

        return {
            "action": "add_task",
            "account": account,
            "data": {
                "row": [task_id, title, client, "client", "open", priority,
                        due, "Celia", "", "FALSE", ""],
            },
            "reply": f"✅ 已新增任務\n**{title}**\n客戶：{client or '—'} · 截止：{due} · 優先：{priority}",
        }

    # ── 新增待辦 ─────────────────────────────────────
    if any(k in t for k in ["新增待辦", "待辦：", "記得", "要做", "add todo", "todo"]):
        title = re.sub(r"(新增待辦|待辦：|記得|add todo|todo)\s*", "", t).strip()
        client = ""
        m = re.search(r"(?:給|客戶：?|for)\s*([^\s，,。\d]+)", t)
        if m:
            client = m.group(1).strip()
            title = title.replace(m.group(0), "").strip()

        due = _parse_date(t)
        account = _parse_account(t)
        todo_id = f"D{uuid.uuid4().hex[:4].upper()}"

        return {
            "action": "add_todo",
            "account": account,
            "data": {
                "row": [todo_id, title, client, "client", "open", due, "Celia", "FALSE"],
            },
            "reply": f"📝 已新增待辦\n**{title}**\n截止：{due}",
        }

    # ── 標記完成 ─────────────────────────────────────
    if any(k in t for k in ["完成", "done", "結束", "關閉", "mark"]):
        title_hint = re.sub(r"(完成了?|已完成|done|結束|關閉|mark|把|幫我|標記)\s*", "", t).strip()
        return {
            "action": "complete_task",
            "data": {"hint": title_hint},
            "account": _parse_account(t),
            "reply": f"🔍 正在搜尋「{title_hint}」相關任務...",
        }

    # ── 新增客戶 ─────────────────────────────────────
    if any(k in t for k in ["新增客戶", "加客戶", "新客戶"]):
        name = re.sub(r"(新增客戶|加客戶|新客戶：?)\s*", "", t).strip()
        account = _parse_account(t)
        client_id = f"C{uuid.uuid4().hex[:4].upper()}"

        return {
            "action": "add_client",
            "account": account,
            "data": {
                "row": [client_id, name, "", "", "", "", "未簽",
                        "work" if account == "work" else "freelance",
                        "", date.today().isoformat(), ""],
            },
            "reply": f"👤 已新增客戶：**{name}**\n合約狀態：未簽 · 記得去 Sheets 補充聯絡資訊",
        }

    # ── 查詢今日 ─────────────────────────────────────
    if any(k in t for k in ["今天要做什麼", "開工", "今日任務", "work-start", "今天有什麼"]):
        return {
            "action": "query_today",
            "data": {},
            "account": "all",
            "reply": "📋 正在載入今日任務清單...",
        }

    # ── 未識別 ───────────────────────────────────────
    return {
        "action": "unknown",
        "data": {"raw": t},
        "account": "work",
        "reply": (
            "💬 我目前支援的指令：\n"
            "• `新增任務 [名稱] 給 [客戶] 明天` — 新增任務\n"
            "• `新增待辦 [事項]` — 新增待辦\n"
            "• `新增客戶 [名稱]` — 新增客戶\n"
            "• `完成了 [任務名稱]` — 標記完成\n"
            "• `今天要做什麼` — 查看今日清單"
        ),
    }
