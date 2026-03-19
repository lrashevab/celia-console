#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/create_work_sheets.py — 建立工作/接案追蹤 Google Sheet
用法：
  python3 scripts/create_work_sheets.py personal   # 建接案 Sheet（lrashevab）
  python3 scripts/create_work_sheets.py work        # 建工作 Sheet（sirius-brand）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.google_auth import get_credentials
from googleapiclient.discovery import build

# ── Sheet 結構定義 ─────────────────────────────────
SHEETS_CONFIG = {
    "personal": {
        "title": "Celia 接案專案追蹤板",
        "label": "🏠 接案（lrashevab@gmail.com）",
    },
    "work": {
        "title": "Celia 工作指揮室",
        "label": "🏢 工作（celia@sirius-brand.com）",
    },
}

TABS = {
    "Clients": {
        "headers": ["id", "name", "industry", "contact", "email", "phone",
                    "contract_status", "account_type", "monthly_value", "created_date", "notes"],
        "sample": [
            ["C001", "客戶A", "科技", "王小明", "client-a@example.com", "",
             "已簽", "work", "50000", "2026-01-01", ""],
            ["C002", "客戶B", "美妝", "林小華", "client-b@example.com", "",
             "洽談中", "freelance", "30000", "2026-02-01", ""],
        ],
        "col_widths": [60, 150, 100, 120, 200, 120, 100, 100, 100, 120, 200],
    },
    "Tasks": {
        "headers": ["id", "title", "client", "type", "status", "priority",
                    "due_date", "owner", "assigned_to", "confirmed_by_client", "notes"],
        "sample": [
            ["T001", "Q2 廣告提案", "客戶A", "client", "in-progress", "high",
             "2026-03-25", "Celia", "", "FALSE", ""],
            ["T002", "品牌識別系統建立", "客戶B", "client", "open", "medium",
             "2026-04-01", "Celia", "設計師小李", "FALSE", ""],
        ],
        "col_widths": [60, 200, 120, 100, 100, 80, 120, 100, 120, 140, 200],
    },
    "ToDos": {
        "headers": ["id", "title", "client", "type", "status",
                    "due_date", "assigned_to", "confirmed_by_client"],
        "sample": [
            ["D001", "寄送合約給客戶A", "客戶A", "client", "open", "2026-03-20", "Celia", "FALSE"],
            ["D002", "確認客戶B提案時間", "客戶B", "client", "open", "2026-03-21", "Celia", "FALSE"],
        ],
        "col_widths": [60, 250, 120, 100, 100, 120, 120, 140],
    },
    "Meetings": {
        "headers": ["id", "date", "client", "title", "attendees", "summary", "action_items", "calendar_link"],
        "sample": [],
        "col_widths": [60, 120, 120, 200, 200, 300, 300, 200],
    },
}

CONTRACT_STATUS_OPTIONS = ["未簽", "洽談中", "已簽", "執行中", "已完成", "暫停"]
TASK_STATUS_OPTIONS = ["open", "in-progress", "completed", "cancelled", "on-hold"]
PRIORITY_OPTIONS = ["high", "medium", "low"]


def create_sheet(account: str) -> str:
    cfg = SHEETS_CONFIG[account]
    creds = get_credentials(account)
    service = build("sheets", "v4", credentials=creds)

    # 建立試算表
    spreadsheet = service.spreadsheets().create(body={
        "properties": {"title": cfg["title"]},
        "sheets": [{"properties": {"title": tab}} for tab in TABS]
    }).execute()

    spreadsheet_id = spreadsheet["spreadsheetId"]
    print(f"✅ {cfg['label']} 試算表已建立")
    print(f"   ID: {spreadsheet_id}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

    # 逐 tab 寫入標題列 + 範例資料
    for tab_name, tab_cfg in TABS.items():
        rows = [tab_cfg["headers"]] + tab_cfg["sample"]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{tab_name}!A1",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()

    # 格式化：標題列加粗 + 凍結
    sheet_ids = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in spreadsheet["sheets"]
    }
    requests = []
    for tab_name, tab_cfg in TABS.items():
        sid = sheet_ids[tab_name]
        # 標題列粗體
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
            }},
            "fields": "userEnteredFormat(textFormat,backgroundColor)",
        }})
        # 凍結第一列
        requests.append({"updateSheetProperties": {
            "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }})

    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

    print(f"   格式化完成（標題加粗、凍結首列）")
    return spreadsheet_id


if __name__ == "__main__":
    account = sys.argv[1] if len(sys.argv) > 1 else "personal"
    sheet_id = create_sheet(account)
    print(f"\n請將以下 ID 填入 .env：")
    if account == "personal":
        print(f"PERSONAL_SPREADSHEET_ID={sheet_id}")
    else:
        print(f"WORK_SPREADSHEET_ID={sheet_id}")
