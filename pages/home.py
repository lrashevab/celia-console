# -*- coding: utf-8 -*-
"""
pages/home.py — Life OS 入口頁
· Claude Code 進行中專案總覽
· 每日活動 Timeline（自動捕捉自 Stop hook）
· 一鍵生成 Threads / 小紅書文章
"""
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import defaultdict

LOG_FILE = Path(__file__).parent.parent / "data" / "claude_log.json"
MEMORY_DIR = Path("/root/.claude/projects/-root/memory")


# ── 讀取活動紀錄 ────────────────────────────────────
def load_sessions() -> list:
    if not LOG_FILE.exists():
        return []
    try:
        data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        return data.get("sessions", [])
    except Exception:
        return []


def save_sessions(sessions: list):
    LOG_FILE.write_text(
        json.dumps({"sessions": sessions}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ── 讀取進行中專案（從 memory + git） ──────────────
def load_projects() -> list:
    projects = []

    # 掃描 /root 下有 CLAUDE.md 的目錄
    root = Path("/root")
    for claude_md in sorted(root.glob("*/CLAUDE.md")):
        proj_dir = claude_md.parent
        name_line = claude_md.read_text(encoding="utf-8").splitlines()[0]
        name = name_line.lstrip("#").strip()[:50]

        # 最後活躍時間（從 log）
        sessions = load_sessions()
        proj_sessions = [s for s in sessions if s.get("project_path") == str(proj_dir)]
        last_active = proj_sessions[0]["date"] if proj_sessions else "—"
        session_count = len(proj_sessions)

        projects.append({
            "name": name,
            "path": str(proj_dir),
            "last_active": last_active,
            "sessions": session_count,
        })

    return projects


# ── 生成文章（呼叫 content_generator） ─────────────
def generate_article(sessions: list, format_type: str) -> str:
    try:
        from services.content_generator import generate_social_post
        return generate_social_post(sessions, format_type)
    except ImportError:
        return "(content_generator 尚未載入)"
    except Exception as e:
        return f"生成失敗：{e}"


# ══════════════════════════════════════════════════
# 主渲染函數
# ══════════════════════════════════════════════════
def render():
    st.title("🤖 Claude Code 指揮中心")
    st.caption("你的 AI 工作流 × 個人成長 × 內容輸出一站管理")

    sessions = load_sessions()

    # ── 頂部指標 ────────────────────────────────────
    today_str = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    today_sessions = [s for s in sessions if s.get("date") == today_str]
    week_sessions  = [s for s in sessions if s.get("date", "") >= week_ago]
    published      = [s for s in sessions if s.get("published")]
    projects       = load_projects()

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("🗓️ 今日 sessions", len(today_sessions))
    with col2: st.metric("📅 本週 sessions", len(week_sessions))
    with col3: st.metric("📁 進行中專案", len(projects))
    with col4: st.metric("📤 已發布文章", len(published))

    st.divider()

    # ══════════════════════════════════════════════
    # Tab 分頁
    # ══════════════════════════════════════════════
    tab_projects, tab_timeline, tab_content = st.tabs([
        "📁 進行中專案", "📅 每日活動紀錄", "✍️ 生成文章"
    ])

    # ── Tab 1：專案總覽 ──────────────────────────
    with tab_projects:
        st.subheader("Claude Code 進行中專案")
        if not projects:
            st.info("尚未偵測到任何專案（需有 CLAUDE.md 的目錄）")
        else:
            for p in projects:
                with st.container(border=True):
                    col_a, col_b, col_c = st.columns([4, 2, 1])
                    with col_a:
                        st.markdown(f"**{p['name']}**")
                        st.caption(p['path'])
                    with col_b:
                        st.caption(f"最後活躍：{p['last_active']}")
                    with col_c:
                        st.caption(f"{p['sessions']} sessions")

    # ── Tab 2：每日活動 Timeline ─────────────────
    with tab_timeline:
        st.subheader("每日 Claude 活動紀錄")

        # 日期篩選
        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            filter_days = st.selectbox("顯示範圍", ["今天", "最近 7 天", "最近 30 天", "全部"], index=1)
        with col_f2:
            all_projects = list({s.get("project_name", "") for s in sessions})
            filter_proj = st.multiselect("篩選專案", all_projects, default=[])

        # 計算日期範圍
        if filter_days == "今天":
            cutoff = today_str
        elif filter_days == "最近 7 天":
            cutoff = week_ago
        elif filter_days == "最近 30 天":
            cutoff = (date.today() - timedelta(days=30)).isoformat()
        else:
            cutoff = "2000-01-01"

        filtered = [
            s for s in sessions
            if s.get("date", "") >= cutoff
            and (not filter_proj or s.get("project_name", "") in filter_proj)
        ]

        if not filtered:
            st.info("此時間範圍內無活動記錄。完成第一次 Claude Code 對話後自動記錄。")
            # 手動新增示範
            if st.button("➕ 手動新增一筆紀錄（測試）"):
                from scripts.log_session import build_entry
                import os
                entry = build_entry("/root/life-os", "manual_test")
                entry["summary"] = "手動測試紀錄"
                sessions.insert(0, entry)
                save_sessions(sessions)
                st.rerun()
        else:
            # 依日期分組顯示
            by_date = defaultdict(list)
            for s in filtered:
                by_date[s.get("date", "unknown")].append(s)

            for day in sorted(by_date.keys(), reverse=True):
                st.markdown(f"### 📅 {day}")
                for idx, s in enumerate(by_date[day]):
                    with st.container(border=True):
                        col_a, col_b = st.columns([5, 2])
                        with col_a:
                            st.markdown(f"**{s.get('project_name', '未知專案')}**  `{s.get('time', '')}`")
                            tags = s.get("tags", [])
                            if tags:
                                st.caption(" · ".join(tags))

                            # 最近 commits
                            commits = s.get("recent_commits", [])
                            if commits:
                                with st.expander("📝 最近 commits"):
                                    for c in commits:
                                        st.code(c, language="text")

                            # 摘要（可編輯）
                            summary_key = f"summary_{day}_{idx}_{s.get('id','')[:8]}"
                            new_summary = st.text_input(
                                "今日摘要（可選填，用於生成文章）",
                                value=s.get("summary", ""),
                                key=summary_key,
                                placeholder="例：完成了 Google OAuth 串接，修復了 token 過期問題...",
                            )
                            if new_summary != s.get("summary", ""):
                                s["summary"] = new_summary
                                s["summary_auto"] = False  # 用戶已編輯，不再被 hook 覆蓋
                                save_sessions(sessions)

                        with col_b:
                            pub_icon = "✅ 已發布" if s.get("published") else "📤 未發布"
                            st.caption(pub_icon)

    # ── Tab 3：生成文章 ──────────────────────────
    with tab_content:
        st.subheader("✍️ 一鍵生成 Threads / 小紅書文章")

        # 選擇要生成的日期
        available_dates = sorted({s.get("date", "") for s in sessions if s.get("date")}, reverse=True)
        if not available_dates:
            st.info("尚無活動記錄，無法生成文章。")
            return

        selected_date = st.selectbox("選擇日期", available_dates)
        format_type   = st.radio("格式", ["Threads（短文）", "小紅書（圖文）"], horizontal=True)

        day_sessions = [s for s in sessions if s.get("date") == selected_date]
        st.caption(f"此日有 {len(day_sessions)} 筆 session，涵蓋：{', '.join(s.get('project_name','') for s in day_sessions)}")

        # 預覽輸入
        with st.expander("📋 原始資料預覽"):
            for s in day_sessions:
                st.markdown(f"- **{s.get('project_name')}**：{s.get('summary') or '（無摘要）'}")
                if s.get("recent_commits"):
                    st.caption("commits: " + " | ".join(s["recent_commits"][:2]))

        # 生成
        if st.button("🤖 生成文章草稿", type="primary"):
            with st.spinner("Claude 正在生成..."):
                fmt = "threads" if "Threads" in format_type else "xiaohongshu"
                article = generate_article(day_sessions, fmt)

            st.success("✅ 草稿生成完成")
            st.text_area("文章草稿（可直接複製）", value=article, height=300)

            col_copy, col_mark = st.columns(2)
            with col_mark:
                if st.button("✅ 標記為已發布"):
                    for s in day_sessions:
                        s["published"] = True
                    save_sessions(sessions)
                    st.success("已標記！")
                    st.rerun()
