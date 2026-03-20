# -*- coding: utf-8 -*-
"""
services/chat_handler.py — 控制台對話框指令解析器
解析自然語言指令 → 操作 Google Sheets
不需 API Key，純規則解析
支援：截止時間、相關連結（任意數量）
"""
import re
import uuid
from datetime import date, datetime, timedelta


# ── 日期解析 ────────────────────────────────────────
def _parse_date(text: str) -> str:
    """從文字中提取日期，支援多種格式"""
    today = date.today()

    # 嘗試各種模式（先嘗試具體日期，再嘗試相對日期）
    m = re.search(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    m = re.search(r"(\d{1,2})[/\-月](\d{1,2})[日號]?", text)
    if m:
        return f"{today.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    if "今天" in text or "今日" in text:
        return today.isoformat()
    if "明天" in text:
        return (today + timedelta(days=1)).isoformat()
    if "後天" in text:
        return (today + timedelta(days=2)).isoformat()
    if "本週五" in text:
        days = (4 - today.weekday()) % 7
        return (today + timedelta(days=days)).isoformat()
    if "本週六" in text:
        days = (5 - today.weekday()) % 7
        return (today + timedelta(days=days)).isoformat()
    if "本週" in text:
        days = (4 - today.weekday()) % 7
        return (today + timedelta(days=days)).isoformat()
    if "下週" in text:
        return (today + timedelta(days=7)).isoformat()
    if "下個月" in text:
        return (today + timedelta(days=30)).isoformat()

    # 預設：7天後
    return (today + timedelta(days=7)).isoformat()


def _parse_account(text: str) -> str:
    if any(k in text for k in ["接案", "freelance", "個人專案", "lrashevab"]):
        return "personal"
    if any(k in text for k in ["工作", "sirius", "公司"]):
        return "work"
    return "work"


def _parse_priority(text: str) -> str:
    if any(k in text for k in ["緊急", "急", "重要", "high", "高優先"]):
        return "high"
    if any(k in text for k in ["low", "低優先", "不急"]):
        return "low"
    return "medium"


def _parse_links(text: str) -> list:
    """從文字中提取所有 URL（http/https）"""
    return re.findall(r"https?://[^\s，,。\)）>\"']+", text)


def _strip_links(text: str) -> str:
    """移除文字中的所有 URL"""
    return re.sub(r"https?://[^\s，,。\)）>\"']+", "", text).strip()


# ══════════════════════════════════════════════════
# 指令解析主函數
# ══════════════════════════════════════════════════
def parse_command(text: str, context: dict = None) -> dict:
    """
    解析用戶輸入，返回操作指令
    回傳格式：
    {
        "action": "add_task" | "add_todo" | "complete_task" | "add_client" | "query_today" | "unknown",
        "data": {...},
        "reply": "給用戶的回覆文字",
        "account": "work" | "personal",
    }
    """
    t = text.strip()
    links = _parse_links(t)
    t_clean = _strip_links(t)  # 移除連結再做其他解析

    # ── 新增任務 ─────────────────────────────────────
    if any(k in t_clean for k in ["新增任務", "加任務", "建立任務", "add task", "幫我記", "任務："]):
        title = re.sub(r"(新增任務|加任務|建立任務|幫我記|任務：)\s*", "", t_clean).strip()

        # 提取客戶名稱
        client = ""
        m = re.search(r"(?:給|客戶：?|for)\s*([^\s，,。\d截止到期到期前完成]+)", title)
        if m:
            client = m.group(1).strip()
            title = title.replace(m.group(0), "").strip()

        # 移除殘留的日期/優先級關鍵字
        title = re.sub(r"\s*(明天|後天|今天|本週[五六]?|下週|下個月|\d{1,4}[/\-月]\d{1,2}[日號]?)\s*", "", title).strip()
        title = re.sub(r"\s*(緊急|急|重要|high|高優先|low|低優先|不急)\s*", "", title).strip()

        due = _parse_date(t)
        priority = _parse_priority(t_clean)
        account = _parse_account(t_clean)
        task_id = f"T{uuid.uuid4().hex[:4].upper()}"
        links_str = ", ".join(links)

        reply_lines = [f"✅ 任務已建立：**{title}**"]
        reply_lines.append(f"客戶：{client or '—'} · 截止：{due} · 優先：{priority}")
        if links:
            reply_lines.append(f"連結：{len(links)} 個")

        return {
            "action": "add_task",
            "account": account,
            "data": {
                "row": [task_id, title, client, "client", "open", priority,
                        due, "Celia", links_str, "FALSE", ""],
            },
            "reply": "\n".join(reply_lines),
        }

    # ── 新增待辦 ─────────────────────────────────────
    if any(k in t_clean for k in ["新增待辦", "待辦：", "記得", "要做", "add todo", "todo"]):
        title = re.sub(r"(新增待辦|待辦：|記得|add todo|todo)\s*", "", t_clean).strip()

        client = ""
        m = re.search(r"(?:給|客戶：?|for)\s*([^\s，,。\d]+)", title)
        if m:
            client = m.group(1).strip()
            title = title.replace(m.group(0), "").strip()

        title = re.sub(r"\s*(明天|後天|今天|本週[五六]?|下週|下個月|\d{1,4}[/\-月]\d{1,2}[日號]?)\s*", "", title).strip()
        title = re.sub(r"\s*(緊急|急|重要|high|低優先|不急)\s*", "", title).strip()

        due = _parse_date(t)
        account = _parse_account(t_clean)
        todo_id = f"D{uuid.uuid4().hex[:4].upper()}"
        links_str = ", ".join(links)

        reply_lines = [f"📝 待辦已建立：**{title}**"]
        reply_lines.append(f"截止：{due}")
        if links:
            reply_lines.append(f"連結：{len(links)} 個")

        return {
            "action": "add_todo",
            "account": account,
            "data": {
                "row": [todo_id, title, client, "client", "open", due, "Celia", links_str, "FALSE"],
            },
            "reply": "\n".join(reply_lines),
        }

    # ── 標記完成 ─────────────────────────────────────
    if any(k in t_clean for k in ["完成", "done", "結束", "關閉", "mark"]):
        title_hint = re.sub(r"(完成了?|已完成|done|結束|關閉|mark|把|幫我|標記)\s*", "", t_clean).strip()
        return {
            "action": "complete_task",
            "data": {"hint": title_hint},
            "account": _parse_account(t_clean),
            "reply": f"🔍 正在搜尋「{title_hint}」相關任務...",
        }

    # ── 新增客戶 ─────────────────────────────────────
    if any(k in t_clean for k in ["新增客戶", "加客戶", "新客戶"]):
        name = re.sub(r"(新增客戶|加客戶|新客戶：?)\s*", "", t_clean).strip()
        account = _parse_account(t_clean)
        client_id = f"C{uuid.uuid4().hex[:4].upper()}"

        return {
            "action": "add_client",
            "account": account,
            "data": {
                "row": [client_id, name, "", "", "", "", "未簽",
                        "work" if account == "work" else "freelance",
                        "", date.today().isoformat(), ""],
            },
            "reply": f"👤 客戶已建立：**{name}**\n合約狀態：未簽 · 記得補充聯絡資訊",
        }

    # ── 查詢今日 ─────────────────────────────────────
    if any(k in t_clean for k in ["今天要做什麼", "開工", "今日任務", "work-start", "今天有什麼"]):
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
            "💬 支援的指令：\n"
            "• `新增任務 [名稱] 給 [客戶] 明天` — 加任務\n"
            "• `新增待辦 [事項] 本週五` — 加待辦\n"
            "• `新增客戶 [名稱]` — 加客戶\n"
            "• `完成了 [任務名稱]` — 標記完成\n"
            "• `今天要做什麼` — 今日清單\n\n"
            "💡 任何指令都可以附上截止時間和連結，例如：\n"
            "`新增任務 設計提案 給 客戶A 3/28 https://figma.com/xxx https://docs.google.com/yyy`"
        ),
    }
