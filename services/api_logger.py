# -*- coding: utf-8 -*-
"""
services/api_logger.py — Google API 呼叫日誌
符合 CLAUDE.md R7 規範：依 account 寫入對應路徑
  work    → data/work/api_log.json
  personal → data/personal/api_log.json
路徑白名單（R2）：嚴禁跨 account 寫入。
"""
import json
from datetime import datetime
from pathlib import Path

# R2 路徑白名單：account → 允許寫入的目錄
_ALLOWED_PATHS: dict[str, Path] = {
    "work":     Path(__file__).parent.parent / "data" / "work",
    "personal": Path(__file__).parent.parent / "data" / "personal",
}


def log_api_call(
    account: str,
    service: str,
    operation: str,
    resource: str,
    status: str,
) -> None:
    """
    將一筆 API 呼叫記錄寫入 data/{account}/api_log.json。

    Parameters
    ----------
    account   : "work" | "personal"
    service   : "sheets" | "calendar" | ...
    operation : "read" | "write" | "create" | ...
    resource  : 資源名稱，如 "Clients"、"Events"
    status    : "success" | "error"
    """
    # ── R2 路徑白名單檢查 ────────────────────────────────
    if account not in _ALLOWED_PATHS:
        raise ValueError(
            f"[ISOLATION BREACH] api_logger 不允許寫入 account='{account}'。"
            f"允許值：{list(_ALLOWED_PATHS)}"
        )

    log_dir = _ALLOWED_PATHS[account]
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "api_log.json"

    # ── 讀取現有日誌（若存在）───────────────────────────
    entries: list[dict] = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            entries = []

    # ── 附加新記錄（R7 格式）────────────────────────────
    entries.append({
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "account":   account,
        "service":   service,
        "operation": operation,
        "resource":  resource,
        "status":    status,
    })

    log_file.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
