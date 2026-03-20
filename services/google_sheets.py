# -*- coding: utf-8 -*-
"""
services/google_sheets.py — Google Sheets 讀寫服務
支援 work / personal 雙帳號，各自存取不同 Spreadsheet
"""
import pandas as pd
from typing import Optional

from config.settings import ACCOUNTS, WORK_SHEETS, PERSONAL_SHEETS
from services.google_auth import get_sheets_service

# ── 欄位定義 ─────────────────────────────────────────
WORK_COLUMNS = {
    "clients":  ["id", "name", "industry", "contact", "email", "phone",
                 "contract_status", "account_type", "monthly_value", "created_date", "notes"],
    "tasks":    ["id", "title", "client", "type", "status", "priority",
                 "due_date", "owner", "assigned_to", "confirmed_by_client", "notes"],
    "todos":    ["id", "title", "client", "type", "status",
                 "due_date", "assigned_to", "confirmed_by_client"],
    "meetings": ["id", "date", "client", "title", "attendees", "summary", "action_items", "calendar_link"],
}
PERSONAL_COLUMNS = {
    "reading": ["book", "author", "pages_total", "pages_read", "start_date", "status"],
    "fitness": ["date", "activity", "duration_min", "notes"],
    "habits":  ["date", "habit", "completed"],
    "finance": ["date", "category", "type", "amount", "note"],
    "goals":   ["goal", "category", "target_date", "progress_pct", "milestones"],
}


def _read_sheet(service, spreadsheet_id: str, sheet_name: str, expected_cols: list) -> pd.DataFrame:
    """通用讀取：從指定 Sheet Tab 讀取資料為 DataFrame"""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name
    ).execute()

    values = result.get("values", [])
    if not values or len(values) < 2:
        return pd.DataFrame(columns=expected_cols)

    headers = values[0]
    rows = values[1:]
    # 補齊欄位長度
    rows = [r + [""] * (len(headers) - len(r)) for r in rows]
    df = pd.DataFrame(rows, columns=headers)

    # 補足缺少的欄位
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    return df[expected_cols]


def _append_row(service, spreadsheet_id: str, sheet_name: str, row: list):
    """向指定 Sheet 新增一行"""
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=sheet_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


# ══════════════════════════════════════════════════════
# 工作帳號 — Work Data
# ══════════════════════════════════════════════════════

def get_clients(account: str = "work") -> pd.DataFrame:
    svc = get_sheets_service(account)
    sid = ACCOUNTS[account]["spreadsheet_id"]
    df = _read_sheet(svc, sid, WORK_SHEETS["clients"], WORK_COLUMNS["clients"])
    df["_account"] = account  # 標記來源帳號
    return df


def get_tasks(task_type: Optional[str] = None, account: str = "work") -> pd.DataFrame:
    svc = get_sheets_service(account)
    sid = ACCOUNTS[account]["spreadsheet_id"]
    df = _read_sheet(svc, sid, WORK_SHEETS["tasks"], WORK_COLUMNS["tasks"])
    df["_account"] = account
    if task_type:
        df = df[df["type"].str.lower() == task_type.lower()]
    return df


def get_todos(todo_type: Optional[str] = None, account: str = "work") -> pd.DataFrame:
    svc = get_sheets_service(account)
    sid = ACCOUNTS[account]["spreadsheet_id"]
    df = _read_sheet(svc, sid, WORK_SHEETS["todos"], WORK_COLUMNS["todos"])
    df["_account"] = account
    if todo_type:
        df = df[df["type"].str.lower() == todo_type.lower()]
    return df


def get_meetings(account: str = "work") -> pd.DataFrame:
    svc = get_sheets_service(account)
    sid = ACCOUNTS[account]["spreadsheet_id"]
    return _read_sheet(svc, sid, WORK_SHEETS["meetings"], WORK_COLUMNS["meetings"])


def append_meeting(meeting_row: list, account: str = "work"):
    svc = get_sheets_service(account)
    sid = ACCOUNTS[account]["spreadsheet_id"]
    _append_row(svc, sid, WORK_SHEETS["meetings"], meeting_row)


def append_task(task_row: list, account: str = "work"):
    """新增任務"""
    svc = get_sheets_service(account)
    sid = ACCOUNTS[account]["spreadsheet_id"]
    _append_row(svc, sid, WORK_SHEETS["tasks"], task_row)


def append_todo(todo_row: list, account: str = "work"):
    """新增待辦"""
    svc = get_sheets_service(account)
    sid = ACCOUNTS[account]["spreadsheet_id"]
    _append_row(svc, sid, WORK_SHEETS["todos"], todo_row)


def update_row_by_id(
    row_id: str,
    sheet_key: str,           # "tasks" | "todos" | "clients"
    updated_fields: dict,     # {column_name: new_value}
    account: str = "work",
) -> bool:
    """
    找到指定 ID 的 row 並更新指定欄位，回傳是否成功。
    使用一次 read + 一次 write，避免逐欄更新的 quota 消耗。
    """
    svc = get_sheets_service(account)
    sid = ACCOUNTS[account]["spreadsheet_id"]
    sheet_name = WORK_SHEETS.get(sheet_key, sheet_key)

    result = svc.spreadsheets().values().get(
        spreadsheetId=sid, range=sheet_name
    ).execute()
    values = result.get("values", [])
    if len(values) < 2:
        return False

    headers = values[0]
    id_col = headers.index("id") if "id" in headers else 0

    for row_idx, row in enumerate(values[1:], start=2):
        row_ext = row + [""] * max(0, len(headers) - len(row))
        if row_ext[id_col] != row_id:
            continue
        # 更新指定欄位
        for col_name, new_val in updated_fields.items():
            if col_name in headers:
                col_i = headers.index(col_name)
                while len(row_ext) <= col_i:
                    row_ext.append("")
                row_ext[col_i] = str(new_val)
        # 寫回整行
        svc.spreadsheets().values().update(
            spreadsheetId=sid,
            range=f"{sheet_name}!A{row_idx}",
            valueInputOption="USER_ENTERED",
            body={"values": [row_ext]},
        ).execute()
        return True
    return False


# ══════════════════════════════════════════════════════
# 個人帳號 — Personal Data
# ══════════════════════════════════════════════════════

def get_reading() -> pd.DataFrame:
    svc = get_sheets_service("personal")
    sid = ACCOUNTS["personal"]["spreadsheet_id"]
    return _read_sheet(svc, sid, PERSONAL_SHEETS["reading"], PERSONAL_COLUMNS["reading"])


def get_fitness() -> pd.DataFrame:
    svc = get_sheets_service("personal")
    sid = ACCOUNTS["personal"]["spreadsheet_id"]
    return _read_sheet(svc, sid, PERSONAL_SHEETS["fitness"], PERSONAL_COLUMNS["fitness"])


def get_habits() -> pd.DataFrame:
    svc = get_sheets_service("personal")
    sid = ACCOUNTS["personal"]["spreadsheet_id"]
    return _read_sheet(svc, sid, PERSONAL_SHEETS["habits"], PERSONAL_COLUMNS["habits"])


def get_finance() -> pd.DataFrame:
    svc = get_sheets_service("personal")
    sid = ACCOUNTS["personal"]["spreadsheet_id"]
    return _read_sheet(svc, sid, PERSONAL_SHEETS["finance"], PERSONAL_COLUMNS["finance"])


def get_goals() -> pd.DataFrame:
    svc = get_sheets_service("personal")
    sid = ACCOUNTS["personal"]["spreadsheet_id"]
    return _read_sheet(svc, sid, PERSONAL_SHEETS["goals"], PERSONAL_COLUMNS["goals"])
