# -*- coding: utf-8 -*-
"""
pages/calendar_page.py — 行事曆管理
建立 Google Calendar 事件 + 查看即將到來的會議
"""
import streamlit as st
from datetime import date, datetime, timedelta

from services import google_calendar as gc
from services import google_sheets as gs
from services.google_auth import is_authenticated

TODAY = date.today()

CAL_CSS = """
<style>
/* ── 事件卡片 ── */
.cal-event-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left: 5px solid #6366f1;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 8px;
    display: flex;
    gap: 16px;
    align-items: flex-start;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: box-shadow 0.15s;
}
.cal-event-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.cal-event-date {
    min-width: 52px;
    text-align: center;
    background: #f1f5f9;
    border-radius: 10px;
    padding: 8px 4px;
}
.cal-event-day { font-size: 1.4rem; font-weight: 800; color: #1e293b; line-height: 1; }
.cal-event-month { font-size: 0.68rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
.cal-event-body { flex: 1; }
.cal-event-title { font-size: 0.92rem; font-weight: 700; color: #1e293b; }
.cal-event-meta  { font-size: 0.75rem; color: #94a3b8; margin-top: 3px; line-height: 1.6; }
.cal-event-link  { font-size: 0.75rem; color: #6366f1; text-decoration: none; }

/* ── 今天標記 ── */
.cal-today-badge {
    background: #ef4444;
    color: #fff;
    font-size: 0.65rem;
    padding: 1px 6px;
    border-radius: 8px;
    font-weight: 700;
    margin-left: 6px;
    vertical-align: middle;
}

/* ── 建立表單 ── */
.create-form-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 24px;
}

/* ── 空狀態 ── */
.empty-state {
    height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f8fafc;
    border-radius: 12px;
    border: 1px dashed #cbd5e1;
    text-align: center;
    color: #94a3b8;
}

/* ── 區塊標題 ── */
.section-head {
    font-size: 0.95rem;
    font-weight: 700;
    color: #334155;
    margin: 20px 0 12px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-count {
    background: #e2e8f0;
    color: #64748b;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 600;
}
</style>
"""

MONTH_ZH = ["", "一月", "二月", "三月", "四月", "五月", "六月",
            "七月", "八月", "九月", "十月", "十一月", "十二月"]


def _parse_event_dt(event: dict) -> tuple:
    """解析 Google Calendar 事件時間，回傳 (date, time_str)"""
    start = event.get("start", {})
    if "dateTime" in start:
        dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        # 轉台灣時間（UTC+8）
        dt = dt + timedelta(hours=8) if "Z" in start["dateTime"] else dt
        return dt.date(), dt.strftime("%H:%M")
    elif "date" in start:
        return date.fromisoformat(start["date"]), "整天"
    return TODAY, ""


# ══════════════════════════════════════════════════════
# 建立事件表單
# ══════════════════════════════════════════════════════
def _render_create_form():
    st.markdown('<div class="create-form-card">', unsafe_allow_html=True)
    st.markdown("**新增 Google Calendar 事件**")

    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("事件標題 *", placeholder="品牌陪跑會議 — 澄塘工事")
    with c2:
        event_date = st.date_input("日期 *", value=TODAY)

    c3, c4, c5 = st.columns(3)
    with c3:
        start_time = st.time_input("開始時間", value=datetime.strptime("10:00", "%H:%M").time())
    with c4:
        duration = st.selectbox("時長", [0.5, 1, 1.5, 2, 3, 4], index=1,
                                format_func=lambda x: f"{x} 小時")
    with c5:
        account = st.selectbox("帳號", ["work", "personal"],
                               format_func=lambda x: "🏢 工作" if x == "work" else "🏠 個人")

    location_input = st.text_input("地點（選填）", placeholder="台北辦公室 / Google Meet")
    attendees_input = st.text_input("與會者 email（逗號分隔，選填）",
                                    placeholder="client@example.com, colleague@company.com")
    description_input = st.text_area("說明（選填）", height=80,
                                     placeholder="會議議程、注意事項...")

    # 連結至既有會議記錄（選填）
    meetings_df = None
    try:
        meetings_df = gs.get_meetings(account="work")
    except Exception:
        pass

    linked_meeting = None
    if meetings_df is not None and not meetings_df.empty:
        meeting_options = ["（不連結）"] + [
            f"{row.get('date','')} · {row.get('title','')}" for _, row in meetings_df.iterrows()
        ]
        linked_idx = st.selectbox("連結至會議記錄（選填）", range(len(meeting_options)),
                                  format_func=lambda i: meeting_options[i])
        if linked_idx > 0:
            linked_meeting = meetings_df.iloc[linked_idx - 1]

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("📅 建立 Google Calendar 事件", type="primary", use_container_width=True):
        if not title.strip():
            st.warning("請填入事件標題。")
            return
        if not is_authenticated(account):
            st.error(f"{'工作' if account=='work' else '個人'}帳號尚未授權 Google。")
            return

        with st.spinner("建立中..."):
            try:
                attendees = [e.strip() for e in attendees_input.split(",") if e.strip() and "@" in e]
                desc_parts = []
                if description_input.strip():
                    desc_parts.append(description_input.strip())
                if location_input.strip():
                    desc_parts.append(f"📍 地點：{location_input.strip()}")
                if linked_meeting is not None:
                    desc_parts.append(f"📋 會議記錄：{linked_meeting.get('title','')}")

                event = gc.create_meeting_event(
                    title=title.strip(),
                    date_str=event_date.isoformat(),
                    start_time=start_time.strftime("%H:%M"),
                    duration_hours=duration,
                    attendees=attendees,
                    description="\n".join(desc_parts),
                    account=account,
                )
                cal_link = event.get("htmlLink", "")
                st.success("✅ Google Calendar 事件已建立！")
                if cal_link:
                    st.markdown(f"[→ 在 Google Calendar 查看]({cal_link})")
            except Exception as e:
                st.error(f"建立失敗：{e}")


# ══════════════════════════════════════════════════════
# 即將到來的事件列表
# ══════════════════════════════════════════════════════
def _render_upcoming(days: int, account: str):
    events = []
    if is_authenticated(account):
        try:
            events = gc.list_upcoming_events(days=days, account=account)
        except Exception as e:
            st.warning(f"無法讀取行事曆：{e}")
    else:
        st.info(f"{'工作' if account=='work' else '個人'}帳號尚未授權，無法讀取行事曆。")
        return

    if not events:
        st.markdown("""
<div class="empty-state">
  <div>
    <div style="font-size:2rem;margin-bottom:8px">📭</div>
    <div style="font-size:0.84rem">未來 {days} 天沒有排定的行程</div>
  </div>
</div>""".replace("{days}", str(days)), unsafe_allow_html=True)
        return

    # 按日期分組
    from collections import defaultdict
    by_date = defaultdict(list)
    for ev in events:
        ev_date, ev_time = _parse_event_dt(ev)
        by_date[ev_date].append((ev_time, ev))

    st.markdown(f'<div class="section-head">📅 未來 {days} 天行程 <span class="section-count">{len(events)} 件</span></div>',
                unsafe_allow_html=True)

    for ev_date in sorted(by_date.keys()):
        is_today = ev_date == TODAY
        date_label = f"{ev_date.month}/{ev_date.day}"
        today_badge = '<span class="cal-today-badge">今天</span>' if is_today else ""

        st.markdown(f'<div style="font-size:0.78rem;font-weight:700;color:#64748b;margin:16px 0 6px 0">'
                    f'{ev_date.strftime("%Y-%m-%d")} {today_badge}</div>', unsafe_allow_html=True)

        for ev_time, ev in sorted(by_date[ev_date]):
            title_ev = ev.get("summary", "（無標題）")
            html_link = ev.get("htmlLink", "")
            location_ev = ev.get("location", "")
            desc_ev = (ev.get("description") or "")[:80]

            meta_parts = []
            if ev_time != "整天":
                meta_parts.append(f"⏰ {ev_time}")
            if location_ev:
                meta_parts.append(f"📍 {location_ev}")
            meta_str = " &nbsp;·&nbsp; ".join(meta_parts)

            link_html = f'<a class="cal-event-link" href="{html_link}" target="_blank">→ 查看</a>' if html_link else ""

            st.markdown(f"""
<div class="cal-event-card">
  <div class="cal-event-date">
    <div class="cal-event-day">{ev_date.day}</div>
    <div class="cal-event-month">{MONTH_ZH[ev_date.month]}</div>
  </div>
  <div class="cal-event-body">
    <div class="cal-event-title">{title_ev} {link_html}</div>
    <div class="cal-event-meta">{meta_str}</div>
    {f'<div style="font-size:0.78rem;color:#64748b;margin-top:4px">{desc_ev}</div>' if desc_ev else ''}
  </div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 主渲染
# ══════════════════════════════════════════════════════
def render():
    st.markdown(CAL_CSS, unsafe_allow_html=True)

    st.markdown("""
<h1 style="font-size:1.7rem;font-weight:700;color:#1e293b;margin:0 0 4px 0">🗓 行事曆</h1>
<p style="color:#94a3b8;font-size:0.83rem;margin:0 0 20px 0">
  建立 Google Calendar 事件 ｜ 查看即將到來的行程
</p>
""", unsafe_allow_html=True)

    tab_create, tab_upcoming = st.tabs(["➕ 建立事件", "📅 即將到來"])

    with tab_create:
        _render_create_form()

    with tab_upcoming:
        col_days, col_account, col_refresh = st.columns([1, 1, 1])
        with col_days:
            days = st.selectbox("查看範圍", [7, 14, 30], format_func=lambda d: f"未來 {d} 天")
        with col_account:
            account = st.selectbox("帳號", ["work", "personal"],
                                   format_func=lambda x: "🏢 工作" if x == "work" else "🏠 個人",
                                   key="cal_account")
        with col_refresh:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 重新整理", use_container_width=True):
                st.rerun()

        _render_upcoming(days, account)
