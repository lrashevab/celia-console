# -*- coding: utf-8 -*-
"""
pages/home.py — Claude Code 指揮中心 v2.0
· 每日活動 Timeline（Stop hook 自動捕捉）
· 結構化紀錄：做了什麼 / 卡點 / 突破 / 心情 / 發文角度
· 一鍵生成 Threads / 小紅書：Hook 優先 + 平台原生邏輯
"""
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import defaultdict

LOG_FILE   = Path(__file__).parent.parent / "data" / "claude_log.json"
MEMORY_DIR = Path("/root/.claude/projects/-root/memory")

HOME_CSS = """
<style>
/* ── 情緒選擇器 ── */
.mood-row { display:flex; gap:10px; flex-wrap:wrap; margin:8px 0; }
.mood-chip {
    background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:20px;
    padding:5px 14px; font-size:0.85rem; cursor:pointer;
    transition:all 0.15s;
}
.mood-chip.selected { background:#6366f1; border-color:#6366f1; color:#fff; }
/* ── 發文預覽框 ── */
.post-preview {
    background:#fff;
    border:1.5px solid #e2e8f0;
    border-radius:14px;
    padding:18px 20px;
    margin:12px 0;
    font-size:0.88rem;
    line-height:1.7;
    color:#1e293b;
    white-space:pre-wrap;
    font-family:'Inter',sans-serif;
}
.post-preview .hook-line {
    font-size:1rem;
    font-weight:700;
    color:#1e293b;
    border-bottom:2px solid #6366f1;
    padding-bottom:4px;
    margin-bottom:12px;
}
/* ── 字數指示 ── */
.char-counter {
    font-size:0.72rem; color:#94a3b8;
    text-align:right; margin-top:4px;
}
.char-counter.warn { color:#f59e0b; }
.char-counter.over { color:#ef4444; font-weight:700; }
/* ── 標題卡片 ── */
.title-card {
    background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
    padding:10px 14px; margin-bottom:7px;
    display:flex; justify-content:space-between; align-items:center;
}
.title-card .title-text { font-size:0.87rem; font-weight:600; color:#1e293b; flex:1; }
.title-card .title-score { font-size:0.72rem; color:#6366f1; font-weight:700; }
/* ── 角度標籤 ── */
.angle-badge {
    display:inline-block; padding:2px 10px; border-radius:10px;
    font-size:0.72rem; font-weight:700;
}
.angle-learn  { background:#dbeafe; color:#1e40af; }
.angle-tool   { background:#dcfce7; color:#166534; }
.angle-diary  { background:#fef3c7; color:#92400e; }
.angle-collab { background:#f3e8ff; color:#7c3aed; }
/* ── 圖片提示 ── */
.img-prompt-box {
    background:#faf5ff; border:1px solid #e9d5ff; border-radius:10px;
    padding:12px 14px; font-size:0.82rem; color:#6b21a8; line-height:1.6;
    margin-top:8px;
}
/* ── session 卡片 ── */
.session-card {
    background:#fff; border:1px solid #e2e8f0; border-radius:14px;
    padding:16px 20px; margin-bottom:12px;
    box-shadow:0 1px 4px rgba(0,0,0,0.05);
}
.session-header {
    display:flex; justify-content:space-between; align-items:center;
    margin-bottom:10px;
}
.session-project { font-size:0.95rem; font-weight:700; color:#1e293b; }
.session-time { font-size:0.72rem; color:#94a3b8; }
.session-tag {
    display:inline-block; background:#f1f5f9; color:#475569;
    padding:2px 8px; border-radius:8px; font-size:0.7rem; margin-right:4px;
}
</style>
"""

MOOD_OPTIONS = [
    ("😤", "苦戰中"),
    ("😊", "順利"),
    ("🤯", "震撼"),
    ("😅", "踩坑"),
    ("💪", "有成就感"),
    ("🌀", "燒腦"),
    ("🎉", "突破"),
]

ANGLE_OPTIONS = {
    "📚 學習成長": "learn",
    "🔧 工具推薦": "tool",
    "📖 開發日記": "diary",
    "🤝 AI 協作": "collab",
}


# ── 資料讀寫 ────────────────────────────────────────
def load_sessions() -> list:
    if not LOG_FILE.exists():
        return []
    try:
        return json.loads(LOG_FILE.read_text(encoding="utf-8")).get("sessions", [])
    except Exception:
        return []


def save_sessions(sessions: list):
    LOG_FILE.write_text(
        json.dumps({"sessions": sessions}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def load_projects() -> list:
    projects = []
    root = Path("/root")
    sessions = load_sessions()
    for claude_md in sorted(root.glob("*/CLAUDE.md")):
        proj_dir  = claude_md.parent
        name_line = claude_md.read_text(encoding="utf-8").splitlines()[0]
        name      = name_line.lstrip("#").strip()[:50]
        proj_sess = [s for s in sessions if s.get("project_path") == str(proj_dir)]
        projects.append({
            "name":        name,
            "path":        str(proj_dir),
            "last_active": proj_sess[0]["date"] if proj_sess else "—",
            "sessions":    len(proj_sess),
        })
    return projects


def generate_article(sessions: list, format_type: str) -> str:
    try:
        from services.content_generator import generate_social_post
        return generate_social_post(sessions, format_type)
    except ImportError:
        return "(content_generator 尚未載入)"
    except Exception as e:
        return f"生成失敗：{e}"


# ── 欄位標籤 ─────────────────────────────────────────
def _field_label(icon: str, label: str, hint: str = "") -> str:
    hint_html = f' <span style="font-size:0.7rem;color:#94a3b8">— {hint}</span>' if hint else ""
    return f'<span style="font-size:0.78rem;font-weight:700;color:#475569">{icon} {label}{hint_html}</span>'


def _char_counter(text: str, limit: int) -> str:
    n   = len(text)
    cls = "over" if n > limit else ("warn" if n > limit * 0.85 else "")
    return f'<div class="char-counter {cls}">{n} / {limit} 字</div>'


# ══════════════════════════════════════════════════════
# 主渲染
# ══════════════════════════════════════════════════════
def render():
    st.markdown(HOME_CSS, unsafe_allow_html=True)
    st.title("🤖 Claude Code 指揮中心")
    st.caption("AI 工作流 × 個人成長 × 內容輸出 — 一站管理")

    sessions = load_sessions()
    today_str = date.today().isoformat()
    week_ago  = (date.today() - timedelta(days=7)).isoformat()

    today_sessions = [s for s in sessions if s.get("date") == today_str]
    week_sessions  = [s for s in sessions if s.get("date", "") >= week_ago]
    published      = [s for s in sessions if s.get("published")]
    projects       = load_projects()

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("🗓️ 今日 sessions",  len(today_sessions))
    with col2: st.metric("📅 本週 sessions",  len(week_sessions))
    with col3: st.metric("📁 進行中專案",      len(projects))
    with col4: st.metric("📤 已發布文章",      len(published))

    st.divider()

    tab_projects, tab_timeline, tab_content = st.tabs([
        "📁 進行中專案", "📅 每日活動紀錄", "✍️ 生成文章",
    ])

    # ════════════════ Tab 1：專案總覽 ════════════════
    with tab_projects:
        st.subheader("Claude Code 進行中專案")
        if not projects:
            st.info("尚未偵測到任何專案（需有 CLAUDE.md 的目錄）")
        else:
            for p in projects:
                with st.container(border=True):
                    ca, cb, cc = st.columns([4, 2, 1])
                    with ca:
                        st.markdown(f"**{p['name']}**")
                        st.caption(p["path"])
                    with cb: st.caption(f"最後活躍：{p['last_active']}")
                    with cc: st.caption(f"{p['sessions']} sessions")

    # ════════════════ Tab 2：每日活動紀錄 ════════════
    with tab_timeline:
        st.subheader("每日 Claude 活動紀錄")
        st.caption("填得越詳細，AI 生成的文章越有靈魂。")

        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            filter_days = st.selectbox("顯示範圍",
                ["今天", "最近 7 天", "最近 30 天", "全部"], index=1)
        with col_f2:
            all_projects = list({s.get("project_name", "") for s in sessions})
            filter_proj  = st.multiselect("篩選專案", all_projects)

        cutoff_map = {
            "今天": today_str,
            "最近 7 天": week_ago,
            "最近 30 天": (date.today() - timedelta(days=30)).isoformat(),
            "全部": "2000-01-01",
        }
        cutoff   = cutoff_map[filter_days]
        filtered = [
            s for s in sessions
            if s.get("date", "") >= cutoff
            and (not filter_proj or s.get("project_name", "") in filter_proj)
        ]

        if not filtered:
            st.info("此時間範圍內無活動記錄。完成第一次 Claude Code 對話後自動記錄。")
            if st.button("➕ 手動新增一筆紀錄（測試）"):
                from scripts.log_session import build_entry
                entry = build_entry("/root/life-os", "manual_test")
                entry["summary"] = "手動測試紀錄"
                sessions.insert(0, entry)
                save_sessions(sessions)
                st.rerun()
        else:
            by_date = defaultdict(list)
            for s in filtered:
                by_date[s.get("date", "unknown")].append(s)

            for day in sorted(by_date.keys(), reverse=True):
                st.markdown(f"### 📅 {day}")
                for idx, s in enumerate(by_date[day]):
                    sid = s.get("id", f"{day}_{idx}")

                    with st.expander(
                        f"**{s.get('project_name','未知專案')}**  `{s.get('time','')}`  "
                        f"{'✅已發布' if s.get('published') else '📝 未發布'}",
                        expanded=(day == today_str)
                    ):
                        # ── tags ──
                        tags = s.get("tags", [])
                        if tags:
                            st.markdown(
                                " ".join(f'<span class="session-tag">{t}</span>' for t in tags),
                                unsafe_allow_html=True
                            )
                            st.markdown("")

                        # ── commits（收合）──
                        commits = s.get("recent_commits", [])
                        if commits:
                            with st.expander("📝 Commits"):
                                for c in commits:
                                    st.code(c, language="text")

                        st.divider()

                        # ── AI 初稿按鈕 ──────────────────────────
                        draft_key = f"drafted_{sid}_{idx}"
                        col_ai, col_hint = st.columns([2, 5])
                        with col_ai:
                            if st.button("🤖 AI 幫我初稿", key=f"draft_btn_{sid}_{idx}",
                                         help="根據 commits 和異動檔案，自動填寫下方欄位（可再修改）"):
                                with st.spinner("分析中..."):
                                    try:
                                        from services.content_generator import draft_session_fields
                                        draft = draft_session_fields(s)
                                    except Exception as e:
                                        draft = {}
                                        st.error(f"初稿失敗：{e}")
                                if draft:
                                    # 把結果寫入 session_state，對應各 widget 的 key
                                    if draft.get("summary"):
                                        st.session_state[f"sum_{sid}_{idx}"] = draft["summary"]
                                    if draft.get("challenge"):
                                        st.session_state[f"chl_{sid}_{idx}"] = draft["challenge"]
                                    if draft.get("insight"):
                                        st.session_state[f"ins_{sid}_{idx}"] = draft["insight"]
                                    # mood / angle：只在欄位尚未填寫時覆蓋
                                    if draft.get("mood") and not s.get("mood"):
                                        mood_options = [f"{e} {l}" for e, l in MOOD_OPTIONS]
                                        if draft["mood"] in mood_options:
                                            st.session_state[f"mood_{sid}_{idx}"] = draft["mood"]
                                    if draft.get("post_angle") and not s.get("post_angle"):
                                        if draft["post_angle"] in list(ANGLE_OPTIONS.keys()):
                                            st.session_state[f"ang_{sid}_{idx}"] = draft["post_angle"]
                                    st.session_state[draft_key] = True
                                    st.rerun()
                        with col_hint:
                            if st.session_state.get(draft_key):
                                st.success("✅ 初稿已填入，請確認並調整後再發文")
                            else:
                                st.caption("沒有 API Key 時會用 commits 規則萃取；有 API Key 會更準")

                        st.markdown("**✏️ 填寫發文素材**（讓 AI 生成有靈魂的文章）")

                        # ── ① 做了什麼 ──
                        st.markdown(_field_label("①", "今天做了什麼",
                            "一句話描述成果，不用技術術語"), unsafe_allow_html=True)
                        new_summary = st.text_area(
                            "summary", label_visibility="collapsed",
                            value=s.get("summary", ""),
                            placeholder="例：終於把 Google OAuth 串接完成，可以用工作帳號登入拿資料了",
                            height=80,
                            key=f"sum_{sid}_{idx}",
                        )
                        st.markdown(_char_counter(new_summary, 100), unsafe_allow_html=True)

                        # ── ② 遇到的卡點 ──
                        st.markdown(_field_label("②", "遇到什麼卡點 / 踩了什麼坑",
                            "越具體越好，這是最有共鳴的部分"), unsafe_allow_html=True)
                        new_challenge = st.text_area(
                            "challenge", label_visibility="collapsed",
                            value=s.get("challenge", ""),
                            placeholder="例：OAuth scope 少填了 calendar.readonly，找了 2 小時才發現",
                            height=70,
                            key=f"chl_{sid}_{idx}",
                        )

                        # ── ③ 最大突破 ──
                        st.markdown(_field_label("③", "最大的突破或領悟",
                            "讀者想帶走的那一句話"), unsafe_allow_html=True)
                        new_insight = st.text_area(
                            "insight", label_visibility="collapsed",
                            value=s.get("insight", ""),
                            placeholder="例：原來 Google API 的 scope 要先在 OAuth 同意畫面裡加，不是在程式裡加",
                            height=70,
                            key=f"ins_{sid}_{idx}",
                        )

                        # ── ④ 心情 ──
                        st.markdown(_field_label("④", "今天的心情"), unsafe_allow_html=True)
                        mood_options = [f"{e} {l}" for e, l in MOOD_OPTIONS]
                        current_mood = s.get("mood", "")
                        mood_idx = mood_options.index(current_mood) if current_mood in mood_options else None
                        new_mood = st.radio(
                            "mood", mood_options,
                            index=mood_idx,
                            horizontal=True,
                            label_visibility="collapsed",
                            key=f"mood_{sid}_{idx}",
                        )

                        # ── ⑤ 發文角度 ──
                        st.markdown(_field_label("⑤", "發文角度",
                            "決定寫給誰看、用什麼口吻"), unsafe_allow_html=True)
                        angle_keys = list(ANGLE_OPTIONS.keys())
                        current_angle = s.get("post_angle", "")
                        angle_idx = angle_keys.index(current_angle) if current_angle in angle_keys else 0
                        new_angle = st.selectbox(
                            "angle", angle_keys,
                            index=angle_idx,
                            label_visibility="collapsed",
                            key=f"ang_{sid}_{idx}",
                        )

                        # ── ⑥ 是否適合公開 ──
                        new_shareable = st.checkbox(
                            "✅ 這個工作內容適合公開發文",
                            value=s.get("shareable", True),
                            key=f"sha_{sid}_{idx}",
                        )

                        # ── 儲存 ──
                        changed = (
                            new_summary  != s.get("summary", "") or
                            new_challenge != s.get("challenge", "") or
                            new_insight  != s.get("insight", "") or
                            new_mood     != s.get("mood", "") or
                            new_angle    != s.get("post_angle", "") or
                            new_shareable != s.get("shareable", True)
                        )
                        if changed:
                            s["summary"]      = new_summary
                            s["challenge"]    = new_challenge
                            s["insight"]      = new_insight
                            s["mood"]         = new_mood
                            s["post_angle"]   = new_angle
                            s["shareable"]    = new_shareable
                            s["summary_auto"] = False
                            save_sessions(sessions)

    # ════════════════ Tab 3：生成文章 ════════════════
    with tab_content:
        st.subheader("✍️ 生成 Threads / 小紅書文章")

        available_dates = sorted(
            {s.get("date", "") for s in sessions if s.get("date")}, reverse=True
        )
        if not available_dates:
            st.info("尚無活動記錄，無法生成文章。")
            return

        # ── 選擇日期 + 格式 ──
        c1, c2 = st.columns([2, 2])
        with c1:
            selected_date = st.selectbox("選擇日期", available_dates)
        with c2:
            format_type = st.radio(
                "發布平台",
                ["🧵 Threads", "📕 小紅書"],
                horizontal=True,
            )

        day_sessions = [
            s for s in sessions
            if s.get("date") == selected_date and s.get("shareable", True)
        ]

        if not day_sessions:
            st.warning("此日無適合公開的紀錄（請在活動紀錄中勾選「適合公開發文」）。")
            return

        # ── 素材完整度評估 ──
        completeness_checks = {
            "做了什麼": any(s.get("summary") for s in day_sessions),
            "遇到的卡點": any(s.get("challenge") for s in day_sessions),
            "最大突破": any(s.get("insight") for s in day_sessions),
            "心情標記": any(s.get("mood") for s in day_sessions),
            "發文角度": any(s.get("post_angle") for s in day_sessions),
        }
        filled = sum(completeness_checks.values())
        quality_pct = int(filled / len(completeness_checks) * 100)

        st.markdown(f"**素材完整度：{quality_pct}%**")
        quality_cols = st.columns(len(completeness_checks))
        for i, (label, ok) in enumerate(completeness_checks.items()):
            with quality_cols[i]:
                st.markdown(
                    f"{'✅' if ok else '⬜'} {label}",
                    help=f"{'已填寫' if ok else '未填寫，生成品質會下降'}",
                )
        if quality_pct < 60:
            st.warning("建議先在「每日活動紀錄」補充更多素材，生成品質會更高。")

        st.divider()

        # ── 平台說明 ──
        is_threads = "Threads" in format_type

        if is_threads:
            with st.expander("💡 Threads 發文邏輯", expanded=False):
                st.markdown("""
**Threads 演算法關鍵：第一行決定一切**

- Feed 只顯示前 ~80 字，沒點開就不算曝光
- 最佳 Hook 公式：`[數字/反常識/情緒句]` + 停頓 → 讓人想點「更多」
- 範例：「花了 3 小時找一個少打的字。不後悔，因為我終於搞懂了 OAuth。」
- hashtag 在 Threads 效果不如 IG，1-2 個就夠
- 結尾問句互動率高（「你也遇過這種坑嗎？」）
                """)
        else:
            with st.expander("💡 小紅書發文邏輯", expanded=False):
                st.markdown("""
**小紅書轉化漏斗：封面圖 → 標題 → 第一屏**

- 標題公式（擇一）：
  - `[情緒/結果] | [身份] | [場景]`：「AI 幫我一週做完一個月的事 | 設計師 | 接案日記」
  - `[數字] 個我用 AI [動詞] 的方法`
  - `為什麼我開始每天用 Claude Code 記錄`
- 正文結構：📌 今天做了 → 💡 最大收穫 → 🤔 踩的坑 → ✅ 結語 → #hashtag
- hashtag 分層：行業標籤 2 個 + 泛話題 2 個 + 情境 1 個
- 封面圖建議：截圖 + 大字標題（比純文字封面高 3-5 倍點擊）
                """)

        # ── 語調選擇 ──
        tone_options = {
            "輕鬆日常": "casual",
            "教學深度": "educational",
            "成長反思": "reflective",
            "真實踩坑": "authentic",
        }
        tone = st.radio(
            "語調風格",
            list(tone_options.keys()),
            index=0,
            horizontal=True,
            help="影響文章的切入角度與用語風格",
        )

        # ── 預覽輸入素材 ──
        with st.expander("📋 今日素材預覽（生成時會用到這些）"):
            for s in day_sessions:
                st.markdown(f"**{s.get('project_name','—')}**")
                cols = st.columns(2)
                with cols[0]:
                    st.caption(f"做了什麼：{s.get('summary','—')}")
                    st.caption(f"卡點：{s.get('challenge','—')}")
                with cols[1]:
                    st.caption(f"突破：{s.get('insight','—')}")
                    st.caption(f"心情：{s.get('mood','—')} | 角度：{s.get('post_angle','—')}")
                st.divider()

        # ── 生成 ──
        if st.button("🤖 生成文章草稿", type="primary"):
            with st.spinner("生成中..."):
                fmt     = "threads" if is_threads else "xiaohongshu"
                article = generate_article(day_sessions, fmt)

            st.success("✅ 草稿完成")

            # ── Threads：Hook 分析 ──
            if is_threads:
                lines = article.strip().split("\n")
                hook_line = next((l for l in lines if l.strip()), "")
                char_count = len(article)
                counter_cls = "over" if char_count > 500 else ("warn" if char_count > 400 else "")

                st.markdown("**🎣 第一行（Hook）預覽**")
                st.markdown(
                    f'<div class="post-preview"><div class="hook-line">{hook_line}</div>'
                    f'<span style="color:#94a3b8;font-size:0.8rem">— Feed 只顯示到這裡 —</span></div>',
                    unsafe_allow_html=True
                )
                st.markdown(f'<div class="char-counter {counter_cls}">{char_count} / 500 字</div>',
                            unsafe_allow_html=True)

            # ── 小紅書：標題建議 ──
            else:
                st.markdown("**📝 標題建議（A/B 測試用，擇一）**")
                try:
                    from services.content_generator import suggest_xhs_titles
                    titles = suggest_xhs_titles(day_sessions)
                except Exception:
                    titles = []
                if titles:
                    for t_label, t_text, t_score in titles:
                        st.markdown(
                            f'<div class="title-card">'
                            f'<span class="title-text">{t_text}</span>'
                            f'<span class="title-score">{t_label} {t_score}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("（標題建議需補充更多素材）")

                # 封面圖提示
                st.markdown("**🖼️ 封面圖製作提示**")
                insight = next((s.get("insight", "") for s in day_sessions if s.get("insight")), "")
                summary = next((s.get("summary", "") for s in day_sessions if s.get("summary")), "")
                img_text = insight or summary or "AI 協作開發日記"
                st.markdown(
                    f'<div class="img-prompt-box">'
                    f'建議截圖：Dashboard 畫面 / 程式碼片段 / 終端機輸出<br>'
                    f'大字標題（用 Canva 疊加）：「{img_text[:30]}」<br>'
                    f'配色建議：深色背景 + 紫/藍漸層 + 白色大字（科技感）'
                    f'</div>',
                    unsafe_allow_html=True
                )

            # ── 完整草稿 ──
            st.markdown("**📄 完整草稿**")
            st.text_area(
                "文章草稿（可直接複製貼上）",
                value=article,
                height=320,
                label_visibility="collapsed",
            )

            # ── 標記發布 ──
            if st.button("✅ 標記為已發布"):
                for s in day_sessions:
                    s["published"] = True
                save_sessions(sessions)
                st.success("已標記！")
                st.rerun()
