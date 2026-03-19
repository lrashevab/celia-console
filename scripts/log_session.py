#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/log_session.py — Claude Code Stop Hook
每次 Claude Code 對話結束自動記錄到 data/claude_log.json

呼叫方式（由 Stop hook 自動執行）：
  python3 /root/life-os/scripts/log_session.py

環境變數（Claude Code hook 自動注入）：
  CLAUDE_PROJECT_PATH  — 當前專案路徑
  CLAUDE_SESSION_ID    — session ID
"""
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "data" / "claude_log.json"


def get_git_summary(project_path: str) -> dict:
    """讀取 git commits + 今日變動檔案統計"""
    result = {"recent_commits": [], "changed_files": [], "today_commits": []}
    try:
        # 最近 5 個 commits
        r = subprocess.run(
            ["git", "-C", project_path, "log", "--oneline", "-5", "--no-merges"],
            capture_output=True, text=True, timeout=5
        )
        result["recent_commits"] = r.stdout.strip().splitlines()

        # 今天新增的 commits（從今日 00:00 至今）
        today = datetime.now().strftime("%Y-%m-%d")
        r2 = subprocess.run(
            ["git", "-C", project_path, "log", "--oneline", "--no-merges",
             f"--after={today} 00:00", "--format=%s"],
            capture_output=True, text=True, timeout=5
        )
        result["today_commits"] = [l for l in r2.stdout.strip().splitlines() if l]

        # 最近一次 commit 改了哪些檔案
        r3 = subprocess.run(
            ["git", "-C", project_path, "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        result["changed_files"] = [l for l in r3.stdout.strip().splitlines() if l][:8]
    except Exception:
        pass
    return result


def read_task_plan(project_path: str) -> dict:
    """讀取 task_plan.md，萃取 Phase 狀態與最新進行中項目"""
    result = {"phases_done": [], "phase_inprogress": "", "recent_tasks": []}
    plan_file = Path(project_path) / "task_plan.md"
    if not plan_file.exists():
        # 向上找一層
        plan_file = Path(project_path).parent / "task_plan.md"
    if not plan_file.exists():
        return result

    try:
        text = plan_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        current_phase = ""
        for line in lines:
            # 識別 Phase 標題
            if line.startswith("### Phase") or line.startswith("## Phase"):
                current_phase = line.lstrip("#").strip()
                if "[complete]" in line.lower() or "complete" in line.lower():
                    result["phases_done"].append(current_phase.split("—")[0].strip())
                elif "[in_progress]" in line.lower() or "in_progress" in line.lower():
                    result["phase_inprogress"] = current_phase.split("—")[0].strip()
            # 識別已完成的 checkbox
            if line.strip().startswith("- [x]") and current_phase:
                task = line.strip()[5:].strip()
                if task and len(task) > 3:
                    result["recent_tasks"].append(task[:60])
    except Exception:
        pass

    result["recent_tasks"] = result["recent_tasks"][-5:]  # 最後 5 個完成項
    return result


def read_progress_md(project_path: str) -> str:
    """讀取 progress.md 的最新 session 摘要"""
    for path in [Path(project_path) / "progress.md",
                 Path(project_path).parent / "progress.md"]:
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8")
                # 取最後一個 ## Session 區塊的前 5 行
                lines = text.splitlines()
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].startswith("## Session") or lines[i].startswith("## 2026"):
                        snippet = "\n".join(lines[i:i+6]).strip()
                        return snippet[:300]
            except Exception:
                pass
    return ""


def get_project_name(project_path: str) -> str:
    """從路徑推斷專案名稱"""
    if not project_path:
        return "未知專案"
    p = Path(project_path)
    # 從 CLAUDE.md 讀第一行作為名稱
    claude_md = p / "CLAUDE.md"
    if claude_md.exists():
        first_line = claude_md.read_text(encoding="utf-8").splitlines()[0]
        name = first_line.lstrip("#").strip()
        return name[:60] if name else p.name
    return p.name


def infer_tags(project_path: str, commits: list) -> list:
    """從路徑和 commit 推斷活動標籤"""
    tags = []
    path_lower = (project_path or "").lower()
    combined = " ".join(commits).lower() + " " + path_lower

    tag_map = {
        "life-os": "🌗 Life OS",
        "dashboard": "📊 Dashboard",
        "oauth": "🔐 OAuth",
        "mcp": "🔌 MCP",
        "skill": "⚡ Skill",
        "agency": "📢 廣告代理",
        "script": "🐍 腳本",
        "api": "🌐 API",
        "deploy": "🚀 部署",
        "fix": "🐛 修復",
        "feature": "✨ 新功能",
        "test": "🧪 測試",
    }
    for keyword, label in tag_map.items():
        if keyword in combined:
            tags.append(label)

    return tags[:4] if tags else ["💻 開發"]


def auto_summary(commits: list, tags: list, project_name: str,
                 today_commits: list = None,
                 changed_files: list = None,
                 plan_info: dict = None) -> str:
    """
    從多個資料來源組裝詳細摘要（繁體中文，供用戶繼續補充）
    資料來源優先級：today_commits > task_plan 完成項 > changed_files > recent_commits
    """
    parts = []

    # ── 1. 今日 commit 訊息（最直接）──────────────────
    tc = today_commits or []
    if tc:
        parts.append("【今日完成】" + "；".join(tc[:3]))

    # ── 2. task_plan.md 正在進行的 Phase ──────────────
    plan = plan_info or {}
    if plan.get("phase_inprogress"):
        parts.append(f"【進行中】{plan['phase_inprogress']}")

    # ── 3. task_plan.md 已完成項目 ────────────────────
    done_tasks = plan.get("recent_tasks", [])
    if done_tasks:
        parts.append("【本次完成項目】" + "、".join(done_tasks[:3]))

    # ── 4. 改動的檔案（理解做了什麼）─────────────────
    cf = changed_files or []
    if cf and not tc:  # 有 today_commits 時不重複
        # 把路徑轉成易讀名稱
        readable = []
        for f in cf[:5]:
            name = Path(f).name
            readable.append(name)
        parts.append("【異動檔案】" + "、".join(readable))

    # ── 5. 最近 commit 訊息（fallback）────────────────
    if not parts:
        msgs = []
        for c in (commits or [])[:3]:
            msg = c.split(" ", 1)[1] if " " in c else c
            if len(msg) > 3:
                msgs.append(msg)
        if msgs:
            parts.append("；".join(msgs))
        else:
            return f"在 {project_name} 進行開發作業"

    return "\n".join(parts)


def build_entry(project_path: str, session_id: str) -> dict:
    """建立一筆活動記錄"""
    now = datetime.now()
    proj_path = project_path or "/root"
    git_info   = get_git_summary(proj_path)
    plan_info  = read_task_plan(proj_path)
    commits    = git_info.get("recent_commits", [])
    proj_name  = get_project_name(proj_path)
    tags       = infer_tags(proj_path, commits)

    summary = auto_summary(
        commits       = commits,
        tags          = tags,
        project_name  = proj_name,
        today_commits = git_info.get("today_commits", []),
        changed_files = git_info.get("changed_files", []),
        plan_info     = plan_info,
    )

    return {
        "id": f"{now.strftime('%Y%m%d%H%M%S')}_{(session_id or 'local')[:8]}",
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "project_path": proj_path,
        "project_name": proj_name,
        "session_id": session_id or "",
        "recent_commits": commits,
        "changed_files": git_info.get("changed_files", []),
        "tags": tags,
        "summary": summary,
        "published": False,
    }


def main():
    project_path = os.environ.get("CLAUDE_PROJECT_PATH", "")
    session_id   = os.environ.get("CLAUDE_SESSION_ID", "")

    # 讀取現有 log
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {"sessions": []}
    else:
        data = {"sessions": []}

    # 避免同一天同專案重複記錄（更新而非新增）
    entry = build_entry(project_path, session_id)
    today = entry["date"]
    proj  = entry["project_path"]

    existing_idx = next(
        (i for i, s in enumerate(data["sessions"])
         if s.get("date") == today and s.get("project_path") == proj),
        None
    )

    if existing_idx is not None:
        old = data["sessions"][existing_idx]
        old["recent_commits"] = entry["recent_commits"]
        old["changed_files"]  = entry.get("changed_files", [])
        old["tags"] = entry["tags"]
        old["time"] = entry["time"]
        # 更新摘要：空的 或 上次也是自動生成的（用戶未手動編輯）
        if not old.get("summary", "").strip() or old.get("summary_auto", False):
            old["summary"] = entry["summary"]
            old["summary_auto"] = True   # 標記為機器生成，可被下次覆蓋
    else:
        entry["summary_auto"] = True
        data["sessions"].insert(0, entry)

    # 保留最近 90 天（約 90*N 條）
    data["sessions"] = data["sessions"][:500]

    LOG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
