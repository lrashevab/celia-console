# -*- coding: utf-8 -*-
"""
pages/meeting_page.py — 會議記錄中心 v2.0
對應 Celia 標準會議記錄模板格式
Header（6格）+ 議題表格（項目/內容）
"""
import streamlit as st
import pandas as pd
import uuid
from datetime import date

from services import google_sheets as gs
from services import google_calendar as gc
from services.meeting_processor import process_transcript, format_calendar_description
from services.google_auth import is_authenticated

TODAY = date.today()

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
MEETING_CSS = """
<style>
/* ── 會議記錄預覽表單（仿實體表格） ── */
.mtg-doc {
    background: #fff;
    border: 2px solid #1e293b;
    border-radius: 4px;
    font-family: 'Inter', '微軟正黑體', sans-serif;
    font-size: 0.88rem;
    margin: 8px 0 20px 0;
    overflow: hidden;
}
.mtg-title-bar {
    background: #1e293b;
    color: #fff;
    text-align: center;
    padding: 10px 16px;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.mtg-header-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    border-bottom: 1px solid #cbd5e1;
}
.mtg-header-cell {
    padding: 8px 12px;
    border-right: 1px solid #cbd5e1;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    gap: 8px;
    align-items: flex-start;
}
.mtg-header-cell:nth-child(even) { border-right: none; }
.mtg-cell-label {
    font-weight: 700;
    color: #475569;
    white-space: nowrap;
    min-width: 72px;
    font-size: 0.78rem;
}
.mtg-cell-value {
    color: #1e293b;
    font-size: 0.85rem;
    line-height: 1.5;
}
.mtg-agenda-bar {
    background: #f1f5f9;
    padding: 8px 14px;
    font-weight: 700;
    color: #334155;
    border-bottom: 1px solid #cbd5e1;
    font-size: 0.82rem;
    letter-spacing: 0.03em;
}
.mtg-agenda-value {
    color: #1e40af;
    font-weight: 500;
    margin-left: 8px;
}
.mtg-topics-header {
    display: grid;
    grid-template-columns: 160px 1fr;
    background: #f8fafc;
    border-bottom: 1px solid #cbd5e1;
}
.mtg-col-head {
    padding: 7px 12px;
    font-weight: 700;
    font-size: 0.78rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-right: 1px solid #cbd5e1;
}
.mtg-col-head:last-child { border-right: none; }
.mtg-topic-row {
    display: grid;
    grid-template-columns: 160px 1fr;
    border-bottom: 1px solid #f1f5f9;
}
.mtg-topic-row:last-child { border-bottom: none; }
.mtg-topic-name {
    padding: 12px;
    font-weight: 700;
    color: #1e293b;
    border-right: 1px solid #e2e8f0;
    background: #fafbfc;
    font-size: 0.85rem;
    vertical-align: top;
}
.mtg-topic-content {
    padding: 12px 14px;
    color: #334155;
    font-size: 0.84rem;
    line-height: 1.75;
    white-space: pre-wrap;
}

/* ── 歷史卡片 ── */
.meeting-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left: 5px solid #6366f1;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    cursor: pointer;
}
.meeting-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.1); border-left-color: #4f46e5; }
.meeting-card-title { font-size: 0.95rem; font-weight: 700; color: #1e293b; }
.meeting-card-meta  { font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }

/* ── 模式徽章 ── */
.badge-ai    { background:#dcfce7;color:#166534;padding:3px 10px;border-radius:12px;font-size:0.72rem;font-weight:700 }
.badge-rules { background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:12px;font-size:0.72rem;font-weight:700 }

/* ── 動作按鈕 ── */
.action-row { display:flex; gap:8px; flex-wrap:wrap; margin-top:16px; }
</style>
"""


# ══════════════════════════════════════════════════════
# 渲染：標準會議記錄表單預覽
# ══════════════════════════════════════════════════════
def _render_meeting_doc(m: dict):
    mode_cls   = "badge-ai"    if m.get("mode") == "ai"    else "badge-rules"
    mode_label = "🤖 AI 解析" if m.get("mode") == "ai"    else "📝 規則解析"

    topics = m.get("topics", [])
    topics_html = ""
    for t in topics:
        content_escaped = (t.get("content") or "").replace("<", "&lt;").replace(">", "&gt;")
        topics_html += f"""
<div class="mtg-topic-row">
  <div class="mtg-topic-name">{t.get('topic','—')}</div>
  <div class="mtg-topic-content">{content_escaped}</div>
</div>"""

    if not topics_html:
        topics_html = '<div class="mtg-topic-row"><div class="mtg-topic-name">—</div><div class="mtg-topic-content">（尚無議題內容）</div></div>'

    st.markdown(f"""
<div style="display:flex;justify-content:flex-end;margin-bottom:8px">
  <span class="{mode_cls}">{mode_label}</span>
</div>

<div class="mtg-doc">
  <div class="mtg-title-bar">會議記錄 Meeting Minutes</div>

  <div class="mtg-header-grid">
    <div class="mtg-header-cell">
      <span class="mtg-cell-label">Meeting theme</span>
      <span class="mtg-cell-value">{m.get('meeting_theme','—')}</span>
    </div>
    <div class="mtg-header-cell">
      <span class="mtg-cell-label">Meeting Date</span>
      <span class="mtg-cell-value">{m.get('meeting_date','—')}</span>
    </div>
    <div class="mtg-header-cell">
      <span class="mtg-cell-label">客戶出席</span>
      <span class="mtg-cell-value">{m.get('client_attendees','—')}</span>
    </div>
    <div class="mtg-header-cell">
      <span class="mtg-cell-label">會議地點</span>
      <span class="mtg-cell-value">{m.get('location','—') or '—'}</span>
    </div>
    <div class="mtg-header-cell">
      <span class="mtg-cell-label">與會同仁</span>
      <span class="mtg-cell-value">{m.get('internal_attendees','—')}</span>
    </div>
    <div class="mtg-header-cell">
      <span class="mtg-cell-label">會議記錄</span>
      <span class="mtg-cell-value">{m.get('recorder','Celia')}</span>
    </div>
  </div>

  <div class="mtg-agenda-bar">
    會議 Agenda <span class="mtg-agenda-value">{m.get('agenda','—')}</span>
  </div>

  <div class="mtg-topics-header">
    <div class="mtg-col-head">項目</div>
    <div class="mtg-col-head">內容</div>
  </div>

  {topics_html}
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 渲染：手動填寫表單（逐欄位輸入）
# ══════════════════════════════════════════════════════
def _render_manual_form():
    st.markdown("**直接填寫表單**")

    c1, c2 = st.columns(2)
    with c1:
        theme = st.text_input("Meeting theme（會議主題）", placeholder="澄塘工事品牌陪跑第二次訪談")
    with c2:
        mdate = st.text_input("Meeting Date", value=TODAY.strftime("%Y/%m/%d"), placeholder="2025/6/23")

    c3, c4 = st.columns(2)
    with c3:
        client_att = st.text_input("客戶出席", placeholder="莊理事長")
    with c4:
        location = st.text_input("會議地點", placeholder="台北辦公室")

    c5, c6 = st.columns(2)
    with c5:
        internal_att = st.text_input("與會同仁", placeholder="宇光森 Sharon, Celia", value="Celia")
    with c6:
        recorder = st.text_input("會議記錄", value="Celia")

    agenda = st.text_input("會議 Agenda", placeholder="品牌陪跑第二次訪談")

    # ── 動態議題列表 ─────────────────────────────────
    st.markdown("**議題項目**")
    if "manual_topics" not in st.session_state:
        st.session_state.manual_topics = [{"topic": "", "content": ""}]

    topics_to_remove = []
    for i, t in enumerate(st.session_state.manual_topics):
        st.markdown(f"*議題 {i+1}*")
        tc1, tc2 = st.columns([1, 3])
        with tc1:
            new_topic = st.text_input(f"項目", value=t["topic"], key=f"mtopic_{i}", placeholder="業務模式")
        with tc2:
            new_content = st.text_area(f"內容", value=t["content"], key=f"mcontent_{i}", height=100,
                                       placeholder="說明內容...")
        st.session_state.manual_topics[i] = {"topic": new_topic, "content": new_content}

        col_del = st.columns([5, 1])[1]
        with col_del:
            if st.button("🗑", key=f"del_topic_{i}", help="刪除此議題"):
                topics_to_remove.append(i)

    for i in reversed(topics_to_remove):
        st.session_state.manual_topics.pop(i)

    if st.button("＋ 新增議題項目", use_container_width=False):
        st.session_state.manual_topics.append({"topic": "", "content": ""})
        st.rerun()

    # 組裝結果
    manual_meeting = {
        "meeting_theme": theme,
        "meeting_date": mdate,
        "client_attendees": client_att,
        "location": location,
        "internal_attendees": internal_att,
        "recorder": recorder,
        "agenda": agenda,
        "topics": [t for t in st.session_state.manual_topics if t["topic"] or t["content"]],
        "action_items": [],
        "mode": "manual",
    }

    if st.button("👁 預覽表單", type="primary", use_container_width=True):
        st.session_state["parsed_meeting"] = manual_meeting
        st.rerun()


# ══════════════════════════════════════════════════════
# 歷史記錄列表
# ══════════════════════════════════════════════════════
def _show_history(meetings_df: pd.DataFrame):
    if meetings_df.empty:
        st.info("尚無會議記錄。在「新增」頁籤建立第一筆。")
        return

    try:
        meetings_df = meetings_df.sort_values("date", ascending=False)
    except Exception:
        pass

    search = st.text_input("🔍 搜尋客戶或主題", placeholder="輸入關鍵字...", label_visibility="collapsed")
    if search:
        mask = (
            meetings_df.get("title", pd.Series(dtype=str)).str.contains(search, case=False, na=False) |
            meetings_df.get("client", pd.Series(dtype=str)).str.contains(search, case=False, na=False)
        )
        meetings_df = meetings_df[mask]

    for _, row in meetings_df.iterrows():
        cal_link = row.get("calendar_link", "")
        link_html = (f' &nbsp;<a href="{cal_link}" target="_blank" '
                     f'style="color:#6366f1;font-size:0.73rem">📅 行事曆</a>') if cal_link else ""
        st.markdown(f"""
<div class="meeting-card">
  <div class="meeting-card-title">{row.get('title','—')}{link_html}</div>
  <div class="meeting-card-meta">
    📅 {row.get('date','—')} &nbsp;·&nbsp; 👤 {row.get('client','—')}
  </div>
  <div style="font-size:0.82rem;color:#475569;margin-top:8px;line-height:1.6">
    {(row.get('summary','') or '')[:200]}
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 主渲染
# ══════════════════════════════════════════════════════
def render():
    st.markdown(MEETING_CSS, unsafe_allow_html=True)

    st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:2px">
  <h1 style="font-size:1.7rem;font-weight:700;color:#1e293b;margin:0">📅 會議記錄中心</h1>
</div>
<p style="color:#94a3b8;font-size:0.83rem;margin:0 0 20px 0">
  貼入逐字稿 / 手動填寫 → 自動產出標準表單 → 建立 Google Calendar
</p>
""", unsafe_allow_html=True)

    # 讀取歷史
    meetings_df = pd.DataFrame()
    try:
        meetings_df = gs.get_meetings(account="work")
    except Exception:
        pass

    tab_paste, tab_manual, tab_history = st.tabs(["📋 貼入逐字稿", "✏️ 手動填寫", "📁 歷史記錄"])

    # ──────────────────────────────────────────────────
    # Tab 1：貼入逐字稿
    # ──────────────────────────────────────────────────
    with tab_paste:
        col_in, col_out = st.columns([1, 1], gap="large")

        with col_in:
            st.markdown("**貼入會議內容**")
            st.caption("支援：逐字稿、條列重點、含表格的文字複製")

            raw = st.text_area(
                label="會議內容",
                height=300,
                placeholder=(
                    "範例：\n"
                    "Meeting theme    澄塘工事品牌陪跑會議    Meeting Date    2025/6/23\n"
                    "客戶出席    莊理事長    會議地點    台北辦公室\n"
                    "與會同仁    Sharon, Celia    會議記錄    Celia\n\n"
                    "會議Agenda    品牌陪跑第二次訪談\n\n"
                    "業務模式\n"
                    "》現況：四大業務...\n"
                    "》未來：持續深化..."
                ),
                label_visibility="collapsed",
            )

            if st.button("🔍 解析並產出表單", type="primary", use_container_width=True):
                if raw.strip():
                    with st.spinner("解析中..."):
                        try:
                            result = process_transcript(raw)
                            st.session_state["parsed_meeting"] = result
                            st.session_state.pop("manual_topics", None)
                        except Exception as e:
                            st.error(f"解析失敗：{e}")
                else:
                    st.warning("請先貼入會議內容。")

        with col_out:
            st.markdown("**標準會議記錄表單**")
            if "parsed_meeting" in st.session_state:
                m = st.session_state["parsed_meeting"]
                _render_meeting_doc(m)
                _render_save_buttons(m)
            else:
                st.markdown("""
<div style="height:260px;display:flex;align-items:center;justify-content:center;
            background:#f8fafc;border-radius:12px;border:1px dashed #cbd5e1">
  <div style="text-align:center;color:#94a3b8">
    <div style="font-size:2rem;margin-bottom:8px">📋</div>
    <div style="font-size:0.84rem">解析後，表單預覽會顯示在這裡</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────
    # Tab 2：手動填寫
    # ──────────────────────────────────────────────────
    with tab_manual:
        col_form, col_prev = st.columns([1, 1], gap="large")

        with col_form:
            _render_manual_form()

        with col_prev:
            st.markdown("**表單預覽**")
            if "parsed_meeting" in st.session_state:
                m = st.session_state["parsed_meeting"]
                _render_meeting_doc(m)
                _render_save_buttons(m)
            else:
                st.markdown("""
<div style="height:260px;display:flex;align-items:center;justify-content:center;
            background:#f8fafc;border-radius:12px;border:1px dashed #cbd5e1">
  <div style="text-align:center;color:#94a3b8">
    <div style="font-size:2rem;margin-bottom:8px">✏️</div>
    <div style="font-size:0.84rem">填完後點「預覽表單」顯示在這裡</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────
    # Tab 3：歷史記錄
    # ──────────────────────────────────────────────────
    with tab_history:
        col_r = st.columns([1, 5])[0]
        with col_r:
            if st.button("🔄 重新整理"):
                st.rerun()
        _show_history(meetings_df)


# ══════════════════════════════════════════════════════
# 儲存按鈕（Calendar + Sheets）
# ══════════════════════════════════════════════════════
def _render_save_buttons(m: dict):
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        cal_ok = is_authenticated("work")
        if st.button("📅 建立 Google Calendar", use_container_width=True, disabled=not cal_ok):
            with st.spinner("建立中..."):
                try:
                    # 日期格式統一 YYYY-MM-DD
                    raw_date = m.get("meeting_date", TODAY.isoformat()).replace("/", "-")
                    desc = format_calendar_description(m)
                    event = gc.create_meeting_event(
                        title=m.get("meeting_theme", "會議"),
                        date_str=raw_date,
                        start_time="10:00",
                        duration_hours=1,
                        attendees=[],
                        description=desc,
                        account="work",
                    )
                    cal_link = event.get("htmlLink", "")
                    st.session_state["parsed_meeting"]["cal_link"] = cal_link
                    st.success("✅ Calendar 事件已建立")
                    if cal_link:
                        st.markdown(f"[→ 查看行事曆]({cal_link})")
                    # Action item 提醒
                    for item in m.get("action_items", []):
                        if item.get("deadline"):
                            gc.create_action_item_reminder(
                                task=item["task"],
                                owner=item.get("owner", "?"),
                                deadline=item["deadline"],
                                account="work",
                            )
                except Exception as e:
                    st.error(f"建立失敗：{e}")
        if not cal_ok:
            st.caption("⚠️ 需要工作帳號授權")

    with col2:
        if st.button("💾 存入 Google Sheets", use_container_width=True):
            with st.spinner("寫入中..."):
                try:
                    cal_link = m.get("cal_link", "")
                    topics_summary = " | ".join(
                        f"{t['topic']}: {t['content'][:60]}"
                        for t in m.get("topics", [])
                    )
                    action_summary = "; ".join(
                        f"[{a.get('owner','?')}] {a.get('task','')}"
                        for a in m.get("action_items", [])
                    )
                    raw_date = m.get("meeting_date", TODAY.isoformat()).replace("/", "-")
                    row = [
                        str(uuid.uuid4())[:8],
                        raw_date,
                        m.get("client_attendees", ""),
                        m.get("meeting_theme", ""),
                        m.get("internal_attendees", ""),
                        topics_summary,
                        action_summary,
                        cal_link,
                    ]
                    gs.append_meeting(row, account="work")
                    st.success("✅ 已存入 Sheets")
                    st.session_state.pop("parsed_meeting", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"寫入失敗：{e}")

    with col3:
        if st.button("🗑 清除重填", use_container_width=True):
            st.session_state.pop("parsed_meeting", None)
            st.session_state.pop("manual_topics", None)
            st.rerun()
