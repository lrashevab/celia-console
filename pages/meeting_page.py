# -*- coding: utf-8 -*-
"""
pages/meeting_page.py — 會議記錄中心 v3.0
職責：填表 → 存入 Google Sheets（Meetings tab）
行事曆建立移至 calendar_page.py
"""
import streamlit as st
import pandas as pd
import uuid
from datetime import date

from services import google_sheets as gs
from services.meeting_processor import process_transcript

TODAY = date.today()

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
MEETING_CSS = """
<style>
/* ── 標準表單預覽（仿實體表格） ── */
.mtg-doc {
    background: #fff;
    border: 2px solid #1e293b;
    border-radius: 4px;
    font-size: 0.87rem;
    overflow: hidden;
    margin-bottom: 16px;
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
}
.mtg-header-cell {
    padding: 9px 14px;
    border-right: 1px solid #cbd5e1;
    border-bottom: 1px solid #cbd5e1;
    display: flex;
    gap: 8px;
}
.mtg-header-cell:nth-child(even) { border-right: none; }
.mtg-cell-label {
    font-weight: 700;
    color: #475569;
    white-space: nowrap;
    min-width: 72px;
    font-size: 0.76rem;
}
.mtg-cell-value { color: #1e293b; font-size: 0.85rem; line-height: 1.5; }
.mtg-agenda-bar {
    background: #f1f5f9;
    padding: 8px 14px;
    font-weight: 700;
    color: #334155;
    border-bottom: 1px solid #cbd5e1;
    font-size: 0.82rem;
}
.mtg-agenda-value { color: #1e40af; font-weight: 500; margin-left: 6px; }
.mtg-topics-header {
    display: grid;
    grid-template-columns: 150px 1fr;
    background: #f8fafc;
    border-bottom: 1px solid #cbd5e1;
}
.mtg-col-head {
    padding: 7px 12px;
    font-weight: 700;
    font-size: 0.75rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-right: 1px solid #cbd5e1;
}
.mtg-col-head:last-child { border-right: none; }
.mtg-topic-row {
    display: grid;
    grid-template-columns: 150px 1fr;
    border-bottom: 1px solid #f1f5f9;
}
.mtg-topic-row:last-child { border-bottom: none; }
.mtg-topic-name {
    padding: 12px;
    font-weight: 700;
    color: #1e293b;
    border-right: 1px solid #e2e8f0;
    background: #fafbfc;
    font-size: 0.84rem;
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
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.meeting-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.meeting-card-title { font-size: 0.95rem; font-weight: 700; color: #1e293b; }
.meeting-card-meta  { font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }

/* ── 模式徽章 ── */
.badge-ai    { background:#dcfce7;color:#166534;padding:3px 10px;border-radius:12px;font-size:0.72rem;font-weight:700 }
.badge-rules { background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:12px;font-size:0.72rem;font-weight:700 }
.badge-manual{ background:#e0e7ff;color:#3730a3;padding:3px 10px;border-radius:12px;font-size:0.72rem;font-weight:700 }
</style>
"""


# ══════════════════════════════════════════════════════
# 渲染：標準會議記錄表單預覽
# ══════════════════════════════════════════════════════
def _render_meeting_doc(m: dict):
    mode = m.get("mode", "rules")
    if mode == "ai":
        badge = '<span class="badge-ai">🤖 AI 解析</span>'
    elif mode == "manual":
        badge = '<span class="badge-manual">✏️ 手動填寫</span>'
    else:
        badge = '<span class="badge-rules">📝 規則解析</span>'

    topics = m.get("topics", [])
    topics_html = ""
    for t in topics:
        content = (t.get("content") or "").replace("<", "&lt;").replace(">", "&gt;")
        topics_html += f"""
<div class="mtg-topic-row">
  <div class="mtg-topic-name">{t.get('topic','—')}</div>
  <div class="mtg-topic-content">{content}</div>
</div>"""

    if not topics_html:
        topics_html = ('<div class="mtg-topic-row">'
                       '<div class="mtg-topic-name">—</div>'
                       '<div class="mtg-topic-content">（尚無議題內容）</div></div>')

    st.markdown(f"""
<div style="display:flex;justify-content:flex-end;margin-bottom:6px">{badge}</div>
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
    會議 Agenda<span class="mtg-agenda-value">{m.get('agenda','—')}</span>
  </div>
  <div class="mtg-topics-header">
    <div class="mtg-col-head">項目</div>
    <div class="mtg-col-head">內容</div>
  </div>
  {topics_html}
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 渲染：手動填寫表單
# ══════════════════════════════════════════════════════
def _render_manual_form():
    c1, c2 = st.columns(2)
    with c1:
        theme = st.text_input("Meeting theme（會議主題）*", placeholder="澄塘工事品牌陪跑第二次訪談")
    with c2:
        mdate = st.text_input("Meeting Date *", value=TODAY.strftime("%Y/%m/%d"))

    c3, c4 = st.columns(2)
    with c3:
        client_att = st.text_input("客戶出席", placeholder="莊理事長")
    with c4:
        location = st.text_input("會議地點", placeholder="台北辦公室")

    c5, c6 = st.columns(2)
    with c5:
        internal_att = st.text_input("與會同仁", value="Celia")
    with c6:
        recorder = st.text_input("會議記錄", value="Celia")

    agenda = st.text_input("會議 Agenda（議程標題）", placeholder="品牌陪跑第二次訪談")

    st.markdown("**議題項目**")
    if "manual_topics" not in st.session_state:
        st.session_state.manual_topics = [{"topic": "", "content": ""}]

    remove_idx = None
    for i, t in enumerate(st.session_state.manual_topics):
        ca, cb, cc = st.columns([2, 5, 1])
        with ca:
            new_topic = st.text_input("項目", value=t["topic"], key=f"mt_{i}", placeholder="業務模式")
        with cb:
            new_content = st.text_area("內容", value=t["content"], key=f"mc_{i}", height=80, placeholder="說明內容...")
        with cc:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑", key=f"del_{i}"):
                remove_idx = i
        st.session_state.manual_topics[i] = {"topic": new_topic, "content": new_content}

    if remove_idx is not None:
        st.session_state.manual_topics.pop(remove_idx)
        st.rerun()

    if st.button("＋ 新增議題", use_container_width=False):
        st.session_state.manual_topics.append({"topic": "", "content": ""})
        st.rerun()

    st.markdown("---")
    if st.button("👁 預覽表單", type="primary", use_container_width=True):
        st.session_state["parsed_meeting"] = {
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
        st.rerun()


# ══════════════════════════════════════════════════════
# 儲存到 Google Sheets
# ══════════════════════════════════════════════════════
def _save_to_sheets(m: dict):
    raw_date = m.get("meeting_date", TODAY.isoformat()).replace("/", "-")
    topics_summary = "\n".join(
        f"【{t['topic']}】{t['content'][:120]}" for t in m.get("topics", [])
    )
    action_summary = "; ".join(
        f"[{a.get('owner','?')}] {a.get('task','')}"
        for a in m.get("action_items", [])
    )
    row = [
        str(uuid.uuid4())[:8],
        raw_date,
        m.get("client_attendees", ""),
        m.get("meeting_theme", ""),
        m.get("internal_attendees", ""),
        topics_summary,
        action_summary,
        "",  # calendar_link（從行事曆頁填入）
    ]
    gs.append_meeting(row, account="work")


# ══════════════════════════════════════════════════════
# 歷史記錄
# ══════════════════════════════════════════════════════
def _show_history(meetings_df: pd.DataFrame):
    if meetings_df.empty:
        st.info("尚無會議記錄。在「新增」頁籤建立第一筆。")
        return
    try:
        meetings_df = meetings_df.sort_values("date", ascending=False)
    except Exception:
        pass

    search = st.text_input("🔍 搜尋", placeholder="客戶名稱或會議主題...", label_visibility="collapsed")
    if search:
        mask = (
            meetings_df.get("title", pd.Series(dtype=str)).str.contains(search, case=False, na=False) |
            meetings_df.get("client", pd.Series(dtype=str)).str.contains(search, case=False, na=False)
        )
        meetings_df = meetings_df[mask]

    st.markdown(f'<div style="font-size:0.78rem;color:#94a3b8;margin-bottom:12px">{len(meetings_df)} 筆記錄</div>',
                unsafe_allow_html=True)

    for _, row in meetings_df.iterrows():
        cal_link = row.get("calendar_link", "")
        cal_html = (f'&nbsp;<a href="{cal_link}" target="_blank" style="color:#6366f1;font-size:0.73rem">'
                    f'📅 行事曆</a>') if cal_link else ""
        summary_text = (row.get("summary", "") or "")[:150]
        st.markdown(f"""
<div class="meeting-card">
  <div class="meeting-card-title">{row.get('title','—')}{cal_html}</div>
  <div class="meeting-card-meta">
    📅 {row.get('date','—')} &nbsp;·&nbsp; 👤 {row.get('client','—')} &nbsp;·&nbsp;
    ✍️ {row.get('attendees','')}
  </div>
  <div style="font-size:0.82rem;color:#475569;margin-top:8px;line-height:1.6">{summary_text}</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 主渲染
# ══════════════════════════════════════════════════════
def render():
    st.markdown(MEETING_CSS, unsafe_allow_html=True)

    st.markdown("""
<h1 style="font-size:1.7rem;font-weight:700;color:#1e293b;margin:0 0 4px 0">📋 會議記錄</h1>
<p style="color:#94a3b8;font-size:0.83rem;margin:0 0 20px 0">
  填寫會議記錄 → 存入 Google Sheets ｜ 行事曆管理請至「🗓 行事曆」
</p>
""", unsafe_allow_html=True)

    # 讀取歷史
    meetings_df = pd.DataFrame()
    try:
        meetings_df = gs.get_meetings(account="work")
    except Exception:
        pass

    tab_paste, tab_manual, tab_history = st.tabs(["📋 貼入逐字稿", "✏️ 手動填寫", "📁 歷史記錄"])

    # ── Tab 1：貼入逐字稿 ──────────────────────────────
    with tab_paste:
        col_in, col_out = st.columns([1, 1], gap="large")

        with col_in:
            st.caption("直接複製會議記錄文字（含 header 欄位）貼入，AI 自動填入表單")
            raw = st.text_area(
                label="會議內容",
                height=320,
                placeholder=(
                    "Meeting theme    澄塘工事品牌陪跑會議    Meeting Date    2025/6/23\n"
                    "客戶出席    莊理事長    會議地點    辦公室\n"
                    "與會同仁    Sharon, Celia    會議記錄    Celia\n\n"
                    "會議Agenda    品牌陪跑第二次訪談\n"
                    "項目    內容\n\n"
                    "業務模式\n"
                    "》現況：...\n"
                    "》未來目標：..."
                ),
                label_visibility="collapsed",
            )
            if st.button("🔍 解析並產出表單", type="primary", use_container_width=True):
                if raw.strip():
                    with st.spinner("解析中..."):
                        try:
                            result = process_transcript(raw)
                            st.session_state["parsed_meeting"] = result
                        except Exception as e:
                            st.error(f"解析失敗：{e}")
                else:
                    st.warning("請先貼入內容。")

        with col_out:
            if "parsed_meeting" in st.session_state:
                m = st.session_state["parsed_meeting"]
                _render_meeting_doc(m)

                col_save, col_clear = st.columns(2)
                with col_save:
                    if st.button("💾 存入 Google Sheets", type="primary", use_container_width=True):
                        with st.spinner("寫入中..."):
                            try:
                                _save_to_sheets(m)
                                st.success("✅ 已存入 Google Sheets！")
                                st.session_state.pop("parsed_meeting", None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"寫入失敗：{e}")
                with col_clear:
                    if st.button("🗑 清除重填", use_container_width=True):
                        st.session_state.pop("parsed_meeting", None)
                        st.rerun()
            else:
                st.markdown("""
<div style="height:280px;display:flex;align-items:center;justify-content:center;
            background:#f8fafc;border-radius:12px;border:1px dashed #cbd5e1">
  <div style="text-align:center;color:#94a3b8">
    <div style="font-size:2.5rem;margin-bottom:10px">📋</div>
    <div style="font-size:0.84rem">貼入內容 → 點「解析」<br>表單預覽在這裡</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Tab 2：手動填寫 ────────────────────────────────
    with tab_manual:
        col_form, col_prev = st.columns([1, 1], gap="large")

        with col_form:
            _render_manual_form()

        with col_prev:
            if "parsed_meeting" in st.session_state:
                m = st.session_state["parsed_meeting"]
                _render_meeting_doc(m)
                if st.button("💾 存入 Google Sheets", type="primary", use_container_width=True,
                             key="save_manual"):
                    with st.spinner("寫入中..."):
                        try:
                            _save_to_sheets(m)
                            st.success("✅ 已存入 Google Sheets！")
                            st.session_state.pop("parsed_meeting", None)
                            st.session_state.pop("manual_topics", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"寫入失敗：{e}")
            else:
                st.markdown("""
<div style="height:280px;display:flex;align-items:center;justify-content:center;
            background:#f8fafc;border-radius:12px;border:1px dashed #cbd5e1">
  <div style="text-align:center;color:#94a3b8">
    <div style="font-size:2.5rem;margin-bottom:10px">✏️</div>
    <div style="font-size:0.84rem">填完後點「預覽表單」<br>確認無誤再存入</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Tab 3：歷史記錄 ────────────────────────────────
    with tab_history:
        col_r = st.columns([1, 5])[0]
        with col_r:
            if st.button("🔄 重新整理"):
                st.rerun()
        _show_history(meetings_df)
