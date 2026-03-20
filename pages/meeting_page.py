# -*- coding: utf-8 -*-
"""
pages/meeting_page.py — 會議記錄中心 v1.0
貼入逐字稿 → AI/規則結構化 → 建立 Google Calendar → 存入 Sheets
"""
import streamlit as st
import pandas as pd
import uuid
from datetime import date, datetime

from services import google_sheets as gs
from services import google_calendar as gc
from services.meeting_processor import process_transcript, format_calendar_description
from services.google_auth import is_authenticated


# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
MEETING_CSS = """
<style>
/* ── 會議卡片 ── */
.meeting-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left: 5px solid #6366f1;
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.meeting-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.1); }
.meeting-title {
    font-size: 1rem;
    font-weight: 700;
    color: #1e293b;
}
.meeting-meta {
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: 4px;
}
.meeting-summary {
    font-size: 0.85rem;
    color: #475569;
    margin-top: 10px;
    line-height: 1.6;
}

/* ── 結構化預覽 ── */
.struct-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
}
.struct-section {
    margin-bottom: 14px;
}
.struct-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #94a3b8;
    margin-bottom: 4px;
}
.struct-value {
    font-size: 0.88rem;
    color: #1e293b;
    font-weight: 500;
}
.action-item-row {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 6px;
}
.action-owner {
    font-size: 0.75rem;
    font-weight: 700;
    background: #e0e7ff;
    color: #3730a3;
    padding: 2px 8px;
    border-radius: 10px;
    white-space: nowrap;
}
.action-deadline {
    font-size: 0.73rem;
    color: #94a3b8;
    margin-left: auto;
    white-space: nowrap;
}

/* ── 模式徽章 ── */
.mode-ai    { background: #dcfce7; color: #166534; }
.mode-rules { background: #fef3c7; color: #92400e; }

/* ── 輸入區 ── */
.input-hint {
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: -8px;
    margin-bottom: 12px;
}
</style>
"""


# ══════════════════════════════════════════════════════
# 子元件：結構化預覽
# ══════════════════════════════════════════════════════
def _show_structured(m: dict):
    mode_cls   = "mode-ai" if m.get("mode") == "ai" else "mode-rules"
    mode_label = "🤖 Claude AI 解析" if m.get("mode") == "ai" else "📝 規則解析（備援）"

    st.markdown(f"""
<div class="struct-box">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
    <span style="font-size:1.1rem;font-weight:700;color:#1e293b">📋 {m.get('title','—')}</span>
    <span class="badge {mode_cls}" style="padding:3px 10px;border-radius:12px;font-size:0.72rem;font-weight:700">{mode_label}</span>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px">
    <div class="struct-section">
      <div class="struct-label">日期</div>
      <div class="struct-value">📅 {m.get('date','—')}</div>
    </div>
    <div class="struct-section">
      <div class="struct-label">時間</div>
      <div class="struct-value">⏰ {m.get('start_time','—')}（{m.get('duration_hours',1)}小時）</div>
    </div>
    <div class="struct-section">
      <div class="struct-label">客戶</div>
      <div class="struct-value">👤 {m.get('client','—') or '—'}</div>
    </div>
  </div>

  <div class="struct-section">
    <div class="struct-label">出席者</div>
    <div class="struct-value">{' · '.join(m.get('attendees', [])) or '—'}</div>
  </div>

  <div class="struct-section" style="margin-top:12px">
    <div class="struct-label">會議摘要</div>
    <div class="struct-value" style="line-height:1.7">{m.get('summary','—')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # 決策
    if m.get("decisions"):
        st.markdown("**✅ 決策事項**")
        for d in m["decisions"]:
            st.markdown(f"- {d}")

    # Action Items
    if m.get("action_items"):
        st.markdown("**📌 待追蹤事項**")
        for item in m["action_items"]:
            st.markdown(f"""
<div class="action-item-row">
  <span class="action-owner">{item.get('owner','?')}</span>
  <span style="font-size:0.87rem;color:#334155">{item.get('task','')}</span>
  <span class="action-deadline">📅 {item.get('deadline','TBD')}</span>
</div>
""", unsafe_allow_html=True)

    if m.get("next_meeting"):
        st.info(f"🗓 下次會議：{m['next_meeting']}")


# ══════════════════════════════════════════════════════
# 子元件：歷史會議列表
# ══════════════════════════════════════════════════════
def _show_history(meetings_df: pd.DataFrame):
    if meetings_df.empty:
        st.info("尚無會議記錄。在上方貼入逐字稿來新增第一筆。")
        return

    # 依日期降冪排列
    try:
        meetings_df = meetings_df.sort_values("date", ascending=False)
    except Exception:
        pass

    st.markdown(
        f'<div style="font-size:1rem;font-weight:700;color:#334155;margin-bottom:12px">'
        f'📁 歷史記錄 <span style="background:#e2e8f0;color:#64748b;font-size:0.72rem;'
        f'padding:2px 8px;border-radius:10px;font-weight:600">{len(meetings_df)} 筆</span></div>',
        unsafe_allow_html=True,
    )

    for _, row in meetings_df.iterrows():
        cal_link = row.get("calendar_link", "")
        link_html = f'<a href="{cal_link}" target="_blank" style="font-size:0.75rem;color:#6366f1">📅 查看行事曆</a>' if cal_link else ""
        client = row.get("client", "—") or "—"
        summary = row.get("summary", "") or row.get("title", "")

        st.markdown(f"""
<div class="meeting-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div class="meeting-title">{row.get('title','—')}</div>
      <div class="meeting-meta">📅 {row.get('date','—')} &nbsp;·&nbsp; 👤 {client} &nbsp;·&nbsp; {row.get('attendees','')}</div>
    </div>
    <div>{link_html}</div>
  </div>
  <div class="meeting-summary">{summary}</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 主渲染
# ══════════════════════════════════════════════════════
def render():
    st.markdown(MEETING_CSS, unsafe_allow_html=True)

    today_str = date.today().isoformat()

    st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
  <h1 style="font-size:1.7rem;font-weight:700;color:#1e293b;margin:0">📅 會議記錄中心</h1>
  <span style="background:#f1f5f9;color:#64748b;padding:4px 12px;border-radius:20px;font-size:0.78rem;font-weight:500">工作 context 專屬</span>
</div>
<p style="color:#94a3b8;font-size:0.85rem;margin-top:0">貼入逐字稿或條列重點 → AI 自動結構化 → 建立 Google Calendar 事件</p>
""", unsafe_allow_html=True)

    # ── 讀取歷史記錄 ─────────────────────────────────
    meetings_df = pd.DataFrame()
    try:
        meetings_df = gs.get_meetings(account="work")
    except Exception:
        pass

    # ══════════════════════════════════════════════════
    # Tab 1：新增會議  |  Tab 2：歷史記錄
    # ══════════════════════════════════════════════════
    tab_new, tab_history = st.tabs(["➕ 新增會議記錄", "📁 歷史記錄"])

    # ── Tab 1：新增 ───────────────────────────────────
    with tab_new:
        col_input, col_preview = st.columns([1, 1], gap="large")

        with col_input:
            st.markdown("**貼入會議內容**")
            st.markdown('<div class="input-hint">支援：逐字稿、條列重點、中英混合</div>', unsafe_allow_html=True)

            raw = st.text_area(
                label="會議內容",
                height=280,
                placeholder=(
                    "範例：\n"
                    "2026/3/20 與客戶A討論Q2廣告提案\n"
                    "出席：Celia、客戶A王經理\n\n"
                    "決定：投放預算增加20%\n"
                    "確認：4月初上線\n\n"
                    "Celia 負責 3/25前提交創意稿\n"
                    "王經理 負責 確認TA資料\n\n"
                    "下次開會：下週四"
                ),
                label_visibility="collapsed",
            )

            # 客戶補填（可選）
            client_override = st.text_input("客戶名稱（選填，可從逐字稿自動識別）", placeholder="例：客戶A")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                parse_btn = st.button("🔍 解析會議內容", use_container_width=True, type="primary")
            with col_btn2:
                clear_btn = st.button("🗑 清空", use_container_width=True)

            if clear_btn:
                st.session_state.pop("parsed_meeting", None)
                st.rerun()

        with col_preview:
            st.markdown("**結構化預覽**")

            # 解析按鈕
            if parse_btn and raw.strip():
                with st.spinner("正在解析中..."):
                    try:
                        result = process_transcript(raw)
                        if client_override.strip():
                            result["client"] = client_override.strip()
                        st.session_state["parsed_meeting"] = result
                        st.session_state["meeting_raw"] = raw
                    except Exception as e:
                        st.error(f"解析失敗：{e}")
            elif parse_btn and not raw.strip():
                st.warning("請先貼入會議內容。")

            # 顯示預覽
            if "parsed_meeting" in st.session_state:
                m = st.session_state["parsed_meeting"]
                _show_structured(m)

                st.divider()

                # ── 建立行事曆 + 寫入 Sheets ──────────
                col_cal, col_sheet = st.columns(2)

                with col_cal:
                    cal_enabled = is_authenticated("work")
                    if st.button(
                        "📅 建立 Google Calendar 事件",
                        use_container_width=True,
                        disabled=not cal_enabled,
                        type="primary",
                    ):
                        with st.spinner("建立行事曆事件..."):
                            try:
                                desc = format_calendar_description(m)
                                event = gc.create_meeting_event(
                                    title=m["title"],
                                    date_str=m["date"],
                                    start_time=m.get("start_time", "10:00"),
                                    duration_hours=m.get("duration_hours", 1),
                                    attendees=m.get("attendees", []),
                                    description=desc,
                                    account="work",
                                )
                                cal_link = event.get("htmlLink", "")
                                st.session_state["parsed_meeting"]["cal_link"] = cal_link
                                st.success("✅ 行事曆事件已建立！")
                                if cal_link:
                                    st.markdown(f"[→ 在 Google Calendar 查看]({cal_link})")

                                # Action Item 提醒
                                for item in m.get("action_items", []):
                                    if item.get("deadline"):
                                        gc.create_action_item_reminder(
                                            task=item["task"],
                                            owner=item.get("owner", "?"),
                                            deadline=item["deadline"],
                                            account="work",
                                        )
                                if m.get("action_items"):
                                    st.info(f"📌 已為 {len(m['action_items'])} 個追蹤事項建立提醒")
                            except Exception as e:
                                st.error(f"行事曆建立失敗：{e}")
                    if not cal_enabled:
                        st.caption("⚠️ 需要工作帳號 Google 授權")

                with col_sheet:
                    if st.button("💾 存入 Google Sheets", use_container_width=True):
                        with st.spinner("寫入記錄..."):
                            try:
                                cal_link = st.session_state["parsed_meeting"].get("cal_link", "")
                                row = [
                                    str(uuid.uuid4())[:8],
                                    m.get("date", today_str),
                                    m.get("client", ""),
                                    m.get("title", ""),
                                    " · ".join(m.get("attendees", [])),
                                    m.get("summary", ""),
                                    "; ".join(
                                        f"[{a.get('owner','?')}] {a.get('task','')}"
                                        for a in m.get("action_items", [])
                                    ),
                                    cal_link,
                                ]
                                gs.append_meeting(row, account="work")
                                st.success("✅ 已存入 Google Sheets！")
                                # 清空 session
                                st.session_state.pop("parsed_meeting", None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"寫入失敗：{e}")
            else:
                st.markdown("""
<div style="height:220px;display:flex;align-items:center;justify-content:center;
            background:#f8fafc;border-radius:12px;border:1px dashed #cbd5e1">
  <div style="text-align:center;color:#94a3b8">
    <div style="font-size:2rem;margin-bottom:8px">📋</div>
    <div style="font-size:0.85rem">貼入內容後點「解析」<br>結構化結果會顯示在這裡</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Tab 2：歷史 ───────────────────────────────────
    with tab_history:
        col_refresh, col_search = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 重新整理"):
                st.rerun()
        with col_search:
            search = st.text_input("搜尋客戶或主題", placeholder="輸入關鍵字...", label_visibility="collapsed")

        if search and not meetings_df.empty:
            mask = (
                meetings_df.get("title", pd.Series(dtype=str)).str.contains(search, case=False, na=False) |
                meetings_df.get("client", pd.Series(dtype=str)).str.contains(search, case=False, na=False) |
                meetings_df.get("summary", pd.Series(dtype=str)).str.contains(search, case=False, na=False)
            )
            meetings_df = meetings_df[mask]

        _show_history(meetings_df)
