# -*- coding: utf-8 -*-
"""
services/google_auth.py — 雙帳號 OAuth 統一入口
支援 work / personal 兩組 credential，各自存 token
"""
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.settings import ACCOUNTS, COMBINED_SCOPES


def get_credentials(account: str = "work") -> Credentials:
    """
    取得指定帳號的 OAuth Credentials。
    首次執行會開啟瀏覽器授權。
    後續從 token 檔案快取讀取。
    """
    cfg = ACCOUNTS[account]
    token_file = Path(cfg["token_file"])
    creds_file = Path(cfg["credentials_file"])

    creds = None

    # 讀取已存 token
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), COMBINED_SCOPES)

    # Token 過期或不存在 → 重新授權
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_file.exists():
                raise FileNotFoundError(
                    f"找不到 {account} 帳號的 credentials 檔案：{creds_file}\n"
                    f"請從 Google Cloud Console 下載 OAuth 2.0 Client JSON 並放置於此路徑。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), COMBINED_SCOPES)
            creds = flow.run_local_server(port=0)

        # 儲存 token
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_sheets_service(account: str = "work"):
    """回傳 Google Sheets API service 物件"""
    return build("sheets", "v4", credentials=get_credentials(account))


def get_calendar_service(account: str = "work"):
    """回傳 Google Calendar API service 物件"""
    return build("calendar", "v3", credentials=get_credentials(account))


def is_authenticated(account: str) -> bool:
    """檢查指定帳號是否已完成授權"""
    token_file = Path(ACCOUNTS[account]["token_file"])
    return token_file.exists()
