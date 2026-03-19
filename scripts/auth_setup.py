#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/auth_setup.py — 手動授權模式（無需瀏覽器本地伺服器）
用法：
  python3 scripts/auth_setup.py personal    # 個人帳號授權
  python3 scripts/auth_setup.py work        # 工作帳號授權
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from config.settings import ACCOUNTS, COMBINED_SCOPES


def main():
    account = sys.argv[1] if len(sys.argv) > 1 else "personal"
    if account not in ACCOUNTS:
        print(f"錯誤：帳號必須是 'personal' 或 'work'")
        sys.exit(1)

    cfg = ACCOUNTS[account]
    creds_file = Path(cfg["credentials_file"])
    token_file = Path(cfg["token_file"])

    print(f"\n{'='*50}")
    print(f"  Life OS — Google 帳號授權設定")
    print(f"  帳號類型：{cfg['label']}")
    print(f"{'='*50}\n")

    if not creds_file.exists():
        print(f"❌ 找不到 credentials 檔案：{creds_file}")
        sys.exit(1)

    # 手動授權模式：產生 URL → 用戶貼碼 → 換 token
    import secrets, hashlib, base64, urllib.parse, requests

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), COMBINED_SCOPES)

    # 讀取 client_id / client_secret
    with open(creds_file) as f:
        client_cfg = json.load(f)
    client_data = client_cfg.get("installed") or client_cfg.get("web")
    client_id = client_data["client_id"]
    client_secret = client_data["client_secret"]

    REDIRECT_URI = "http://localhost"

    # 授權 URL
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(COMBINED_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    print("請在瀏覽器中開啟以下網址進行授權：")
    print(f"\n{auth_url}\n")
    print("授權完成後，瀏覽器會跳到 localhost（顯示無法連線）")
    print("請從網址列複製完整 URL，例如：")
    print("  http://localhost/?code=4/1Afr...&scope=...")
    print()
    raw = input("貼上完整網址（或只貼 code= 後面的值）：").strip()

    # 支援貼完整 URL 或只貼 code
    if raw.startswith("http"):
        parsed = urllib.parse.urlparse(raw)
        code = urllib.parse.parse_qs(parsed.query).get("code", [""])[0]
    else:
        code = raw

    if not code:
        print("❌ 無法取得授權碼，請確認貼入的是正確網址")
        sys.exit(1)

    # 換 token
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    token_data = resp.json()

    if "error" in token_data:
        print(f"❌ 換 token 失敗：{token_data}")
        sys.exit(1)

    # 轉成 google.oauth2.credentials.Credentials 格式
    from google.oauth2.credentials import Credentials
    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=COMBINED_SCOPES,
    )

    # 儲存 token
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json(), encoding="utf-8")

    print(f"\n✅ 授權完成！Token 已儲存至：{token_file}")
    print(f"   Scopes：{', '.join(creds.scopes or [])}")


if __name__ == "__main__":
    main()
