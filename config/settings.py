# -*- coding: utf-8 -*-
"""
config/settings.py — Life OS 設定中心
載入環境變數，定義 Google Sheets 欄位對照
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# ── Google API Scopes ────────────────────────────────
SHEETS_SCOPES  = ["https://www.googleapis.com/auth/spreadsheets"]
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
COMBINED_SCOPES = SHEETS_SCOPES + CALENDAR_SCOPES

# ── 帳號設定 ─────────────────────────────────────────
ACCOUNTS = {
    "work": {
        "credentials_file": BASE_DIR / "config" / "credentials_work.json",
        "token_file":       BASE_DIR / "config" / "token_work.json",
        "spreadsheet_id":   os.getenv("WORK_SPREADSHEET_ID", ""),
        "calendar_id":      os.getenv("WORK_CALENDAR_ID", "primary"),
        "label":            "🏢 工作帳號",
    },
    "personal": {
        "credentials_file": BASE_DIR / "config" / "credentials_personal.json",
        "token_file":       BASE_DIR / "config" / "token_personal.json",
        "spreadsheet_id":   os.getenv("PERSONAL_SPREADSHEET_ID", ""),
        "calendar_id":      os.getenv("PERSONAL_CALENDAR_ID", "primary"),
        "label":            "🏠 個人帳號",
    },
}

# ── Work Sheets Tab 名稱 ─────────────────────────────
WORK_SHEETS = {
    "clients":  "Clients",
    "tasks":    "Tasks",
    "todos":    "ToDos",
    "meetings": "Meetings",
}

# ── Personal Sheets Tab 名稱 ─────────────────────────
PERSONAL_SHEETS = {
    "reading": "Reading",
    "fitness": "Fitness",
    "habits":  "Habits",
    "finance": "Finance",
    "goals":   "Goals",
}

# ── 日記本地路徑（硬隔離：不上 Google）──────────────
DIARY_PATH = Path(os.getenv("DIARY_LOCAL_PATH", BASE_DIR / "data" / "personal" / "diary"))
DIARY_PATH.mkdir(parents=True, exist_ok=True)

# ── Anthropic ────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"
