# -*- coding: utf-8 -*-
"""
pages/calendar_page.py — 行事曆 v2.0
月 / 週 / 日 三種視圖 + 事件詳情面板
"""
import streamlit as st
import calendar
from datetime import date, datetime, timedelta
from collections import defaultdict

from services import google_calendar as gc
from services import google_sheets as gs
from services.google_auth import is_authenticated

TODAY = date.today()
WEEKDAY_ZH = ["一", "二", "三", "四", "五", "六", "日"]
MONTH_ZH   = ["", "一月", "二月", "三月", "四月", "五月", "六月",
              "七月", "八月", "九月", "十月", "十一月", "十二月"]

# 事件顏色池（依關鍵字自動配色）
EVENT_COLORS = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]

CAL_CSS = """
<style>
/* ── 全局 ── */
.cal-wrap { font-family: 'Inter', sans-serif; }

/* ── 導覽列 ── */
.cal-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding: 0 2px;
}
.cal-nav-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1e293b;
}
.cal-nav-sub { font-size: 0.78rem; color: #94a3b8; margin-left: 8px; }

/* ── 月視圖 ── */
.month-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    overflow: hidden;
    background: #f8fafc;
}
.month-weekhead {
    background: #f1f5f9;
    text-align: center;
    padding: 10px 4px;
    font-size: 0.72rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
}
.month-weekhead:last-child { border-right: none; }
.month-day {
    background: #fff;
    min-height: 96px;
    padding: 6px;
    border-right: 1px solid #f1f5f9;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: top;
    cursor: pointer;
    transition: background 0.1s;
}
.month-day:hover { background: #f8fafc; }
.month-day.other-month { background: #fafbfc; }
.month-day.today { background: #eff6ff; }
.month-day-num {
    font-size: 0.82rem;
    font-weight: 600;
    color: #475569;
    margin-bottom: 4px;
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
}
.month-day.today .month-day-num {
    background: #1e40af;
    color: #fff;
}
.month-day.other-month .month-day-num { color: #cbd5e1; }
.month-event-pill {
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: 6px;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
    display: block;
    color: #fff;
    font-weight: 500;
}
.month-more {
    font-size: 0.68rem;
    color: #94a3b8;
    margin-top: 2px;
}

/* ── 週視圖 ── */
.week-grid {
    display: grid;
    grid-template-columns: 48px repeat(7, 1fr);
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    overflow: hidden;
    background: #f8fafc;
}
.week-head-time { background: #f1f5f9; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; }
.week-head-day {
    background: #f1f5f9;
    text-align: center;
    padding: 10px 4px;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
}
.week-head-day:last-child { border-right: none; }
.week-head-weekday { font-size: 0.7rem; font-weight: 700; color: #64748b; text-transform: uppercase; }
.week-head-date {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1e293b;
    width: 34px;
    height: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    margin: 2px auto 0;
}
.week-head-day.today .week-head-date { background: #1e40af; color: #fff; }
.week-time-label {
    font-size: 0.65rem;
    color: #94a3b8;
    text-align: right;
    padding: 0 6px;
    height: 40px;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #f1f5f9;
    padding-top: 4px;
    background: #fafbfc;
}
.week-slot {
    height: 40px;
    border-right: 1px solid #f1f5f9;
    border-bottom: 1px solid #f1f5f9;
    padding: 1px 2px;
    background: #fff;
    vertical-align: top;
    position: relative;
}
.week-slot:last-child { border-right: none; }
.week-slot.today-col { background: #eff6ff; }
.week-event {
    font-size: 0.68rem;
    padding: 1px 4px;
    border-radius: 4px;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
    margin-bottom: 1px;
    font-weight: 500;
    line-height: 1.4;
}

/* ── 日視圖 ── */
.day-grid {
    display: grid;
    grid-template-columns: 56px 1fr;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    overflow: hidden;
}
.day-time-label {
    font-size: 0.68rem;
    color: #94a3b8;
    text-align: right;
    padding: 0 8px;
    height: 52px;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #f1f5f9;
    padding-top: 4px;
    background: #fafbfc;
}
.day-slot {
    height: 52px;
    border-bottom: 1px solid #f8fafc;
    padding: 2px 6px;
    background: #fff;
}
.day-event {
    font-size: 0.78rem;
    padding: 3px 8px;
    border-radius: 6px;
    color: #fff;
    display: block;
    margin-bottom: 2px;
    font-weight: 500;
    line-height: 1.5;
}

/* ── 事件詳情面板 ── */
.event-detail-panel {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}
.event-detail-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 12px;
}
.event-detail-row {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    margin-bottom: 8px;
    font-size: 0.84rem;
    color: #475569;
}
.event-detail-icon { color: #94a3b8; min-width: 18px; }
</style>
"""


# ══════════════════════════════════════════════════════
# 工具函數
# ══════════════════════════════════════════════════════
def _parse_event(event: dict) -> dict:
    """解析 Google Calendar 事件，回傳標準化 dict"""
    start = event.get("start", {})
    end   = event.get("end",   {})
    all_day = "date" in start and "dateTime" not in start

    if all_day:
        ev_date  = date.fromisoformat(start["date"])
        ev_time  = ""
        ev_end   = ""
        end_date = date.fromisoformat(end.get("date", start["date"]))
    else:
        dt_start = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        dt_end   = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
        ev_date  = dt_start.date()
        ev_time  = dt_start.strftime("%H:%M")
        ev_end   = dt_end.strftime("%H:%M")
        end_date = dt_end.date()

    return {
        "id":          event.get("id", ""),
        "title":       event.get("summary", "（無標題）"),
        "date":        ev_date,
        "end_date":    end_date,
        "time":        ev_time,
        "end_time":    ev_end,
        "all_day":     all_day,
        "location":    event.get("location", ""),
        "description": event.get("description", ""),
        "link":        event.get("htmlLink", ""),
        "attendees":   [a.get("email", "") for a in event.get("attendees", [])],
    }


def _event_color(idx: int) -> str:
    return EVENT_COLORS[idx % len(EVENT_COLORS)]


def _events_by_date(events: list) -> dict:
    """events → {date: [event_dict, ...]}"""
    result = defaultdict(list)
    for i, ev in enumerate(events):
        parsed = _parse_event(ev)
        parsed["_color"] = _event_color(i)
        result[parsed["date"]].append(parsed)
    return result


# ══════════════════════════════════════════════════════
# 月視圖
# ══════════════════════════════════════════════════════
def _render_month(ev_map: dict, anchor_date: date) -> str:
    year, month = anchor_date.year, anchor_date.month
    cal = calendar.monthcalendar(year, month)

    # 週標題
    heads = "".join(f'<div class="month-weekhead">{d}</div>' for d in WEEKDAY_ZH)
    cells = ""

    for week in cal:
        for day_num in week:
            if day_num == 0:
                cells += '<div class="month-day other-month"><div class="month-day-num"></div></div>'
                continue
            d = date(year, month, day_num)
            cls = "month-day"
            if d == TODAY:
                cls += " today"

            events_today = ev_map.get(d, [])
            pills = ""
            for ev in events_today[:3]:
                time_prefix = f"{ev['time']} " if ev["time"] else ""
                title_short = (ev["title"])[:14]
                pills += (f'<span class="month-event-pill" '
                          f'style="background:{ev["_color"]}">'
                          f'{time_prefix}{title_short}</span>')
            if len(events_today) > 3:
                pills += f'<div class="month-more">+{len(events_today)-3} 更多</div>'

            cells += f"""
<div class="{cls}">
  <div class="month-day-num">{day_num}</div>
  {pills}
</div>"""

    return f'<div class="month-grid">{heads}{cells}</div>'


# ══════════════════════════════════════════════════════
# 週視圖
# ══════════════════════════════════════════════════════
def _render_week(ev_map: dict, week_start: date, hours=(7, 22)) -> str:
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    # 週頭
    heads = '<div class="week-head-time"></div>'
    for d in week_days:
        today_cls = " today" if d == TODAY else ""
        heads += f"""
<div class="week-head-day{today_cls}">
  <div class="week-head-weekday">{WEEKDAY_ZH[d.weekday()]}</div>
  <div class="week-head-date">{d.day}</div>
</div>"""

    # 時間槽
    rows = ""
    for hour in range(hours[0], hours[1]):
        rows += f'<div class="week-time-label">{hour:02d}:00</div>'
        for d in week_days:
            today_cls = " today-col" if d == TODAY else ""
            evs_here = [e for e in ev_map.get(d, [])
                        if e["time"] and int(e["time"].split(":")[0]) == hour]
            inner = ""
            for ev in evs_here:
                t = (ev["title"])[:12]
                inner += (f'<span class="week-event" style="background:{ev["_color"]}">'
                          f'{ev["time"]} {t}</span>')
            rows += f'<div class="week-slot{today_cls}">{inner}</div>'

    return f'<div class="week-grid">{heads}{rows}</div>'


# ══════════════════════════════════════════════════════
# 日視圖
# ══════════════════════════════════════════════════════
def _render_day(ev_map: dict, day: date, hours=(7, 22)) -> str:
    events_today = ev_map.get(day, [])
    rows = ""
    for hour in range(hours[0], hours[1]):
        evs = [e for e in events_today
               if e["time"] and int(e["time"].split(":")[0]) == hour]
        inner = ""
        for ev in evs:
            t = ev["title"]
            time_range = f"{ev['time']}–{ev['end_time']}" if ev["end_time"] else ev["time"]
            inner += (f'<span class="day-event" style="background:{ev["_color"]}">'
                      f'{time_range} {t}</span>')
        # 整天事件
        all_day_evs = [e for e in events_today if e["all_day"] and hour == hours[0]]
        if hour == hours[0]:
            for ev in all_day_evs:
                inner += (f'<span class="day-event" style="background:{ev["_color"]}">'
                          f'整天 {ev["title"]}</span>')
        rows += f'<div class="day-time-label">{hour:02d}:00</div><div class="day-slot">{inner}</div>'

    return f'<div class="day-grid">{rows}</div>'


# ══════════════════════════════════════════════════════
# 事件詳情面板
# ══════════════════════════════════════════════════════
def _render_detail(ev: dict):
    color = ev.get("_color", "#6366f1")
    time_str = f"{ev['time']}–{ev['end_time']}" if ev["time"] and ev["end_time"] else (ev["time"] or "整天")
    attendees_str = ", ".join(ev["attendees"][:5]) if ev["attendees"] else "—"

    link_html = (f'<a href="{ev["link"]}" target="_blank" '
                 f'style="color:#6366f1;font-size:0.8rem">→ 在 Google Calendar 查看</a>'
                 ) if ev["link"] else ""

    rows = [
        ("📅", f"{ev['date']} {time_str}"),
        ("📍", ev["location"] or "—"),
        ("👥", attendees_str),
    ]
    rows_html = ""
    for icon, val in rows:
        rows_html += f'<div class="event-detail-row"><span class="event-detail-icon">{icon}</span><span>{val}</span></div>'

    desc = (ev.get("description") or "").replace("\n", "<br>")

    st.markdown(f"""
<div class="event-detail-panel">
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:14px">
    <div style="width:4px;height:40px;background:{color};border-radius:4px"></div>
    <div class="event-detail-title">{ev['title']}</div>
  </div>
  {rows_html}
  {f'<div style="font-size:0.82rem;color:#64748b;margin-top:10px;line-height:1.7;border-top:1px solid #f1f5f9;padding-top:10px">{desc}</div>' if desc else ''}
  <div style="margin-top:12px">{link_html}</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 建立事件表單
# ══════════════════════════════════════════════════════
def _render_create_form():
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

    location_i = st.text_input("地點（選填）", placeholder="台北辦公室")
    attendees_i = st.text_input("與會者 email（逗號分隔，選填）")
    desc_i = st.text_area("說明（選填）", height=80)

    if st.button("📅 建立行事曆事件", type="primary", use_container_width=True):
        if not title.strip():
            st.warning("請填入事件標題。")
            return
        if not is_authenticated(account):
            st.error(f"{'工作' if account=='work' else '個人'}帳號尚未授權 Google。")
            return
        with st.spinner("建立中..."):
            try:
                attendees = [e.strip() for e in attendees_i.split(",") if "@" in e]
                event = gc.create_meeting_event(
                    title=title.strip(),
                    date_str=event_date.isoformat(),
                    start_time=start_time.strftime("%H:%M"),
                    duration_hours=duration,
                    attendees=attendees,
                    description="\n".join(filter(None, [desc_i, f"📍 {location_i}" if location_i else ""])),
                    account=account,
                )
                cal_link = event.get("htmlLink", "")
                st.success("✅ 行事曆事件已建立！")
                if cal_link:
                    st.markdown(f"[→ 在 Google Calendar 查看]({cal_link})")
                st.session_state["cal_needs_refresh"] = True
            except Exception as e:
                st.error(f"建立失敗：{e}")


# ══════════════════════════════════════════════════════
# 主渲染
# ══════════════════════════════════════════════════════
def render():
    st.markdown(CAL_CSS, unsafe_allow_html=True)

    st.markdown("""
<h1 style="font-size:1.7rem;font-weight:700;color:#1e293b;margin:0 0 20px 0">🗓 行事曆</h1>
""", unsafe_allow_html=True)

    tab_view, tab_create = st.tabs(["📅 行事曆視圖", "➕ 建立事件"])

    # ──────────────────────────────────────────────────
    # Tab 1：行事曆視圖
    # ──────────────────────────────────────────────────
    with tab_view:
        # ── 控制列 ──────────────────────────────────
        ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 1, 1, 1])

        with ctrl1:
            view_mode = st.radio("視圖", ["月", "週", "日"],
                                 horizontal=True, label_visibility="collapsed")
        with ctrl2:
            account = st.selectbox("帳號", ["work", "personal"],
                                   format_func=lambda x: "🏢 工作" if x == "work" else "🏠 個人",
                                   key="cal_account_view",
                                   label_visibility="collapsed")
        with ctrl3:
            if "cal_anchor" not in st.session_state:
                st.session_state.cal_anchor = TODAY
            if st.button("◀ 上一頁", use_container_width=True):
                a = st.session_state.cal_anchor
                if view_mode == "月":
                    # 上個月
                    m = a.month - 1 if a.month > 1 else 12
                    y = a.year if a.month > 1 else a.year - 1
                    st.session_state.cal_anchor = a.replace(year=y, month=m, day=1)
                elif view_mode == "週":
                    st.session_state.cal_anchor = a - timedelta(weeks=1)
                else:
                    st.session_state.cal_anchor = a - timedelta(days=1)
                st.rerun()
        with ctrl4:
            c_today, c_next = st.columns(2)
            with c_today:
                if st.button("今天", use_container_width=True):
                    st.session_state.cal_anchor = TODAY
                    st.rerun()
            with c_next:
                if st.button("▶ 下一頁", use_container_width=True):
                    a = st.session_state.cal_anchor
                    if view_mode == "月":
                        m = a.month + 1 if a.month < 12 else 1
                        y = a.year if a.month < 12 else a.year + 1
                        st.session_state.cal_anchor = a.replace(year=y, month=m, day=1)
                    elif view_mode == "週":
                        st.session_state.cal_anchor = a + timedelta(weeks=1)
                    else:
                        st.session_state.cal_anchor = a + timedelta(days=1)
                    st.rerun()

        anchor = st.session_state.cal_anchor

        # ── 標題 ────────────────────────────────────
        if view_mode == "月":
            title_str = f"{anchor.year} 年 {MONTH_ZH[anchor.month]}"
        elif view_mode == "週":
            week_start = anchor - timedelta(days=anchor.weekday())
            week_end   = week_start + timedelta(days=6)
            title_str  = f"{week_start.month}/{week_start.day} – {week_end.month}/{week_end.day}"
        else:
            title_str = f"{anchor.year}/{anchor.month:02d}/{anchor.day:02d} 週{WEEKDAY_ZH[anchor.weekday()]}"

        st.markdown(f'<div style="font-size:1.1rem;font-weight:700;color:#1e293b;margin:8px 0 14px 0">{title_str}</div>',
                    unsafe_allow_html=True)

        # ── 取得事件 ─────────────────────────────────
        events_raw = []
        if is_authenticated(account):
            try:
                # 根據視圖範圍決定取幾天的事件
                if view_mode == "月":
                    fetch_days = 45
                elif view_mode == "週":
                    fetch_days = 14
                else:
                    fetch_days = 3
                events_raw = gc.list_upcoming_events(days=fetch_days, account=account)
            except Exception as e:
                st.warning(f"無法讀取行事曆：{e}")
        else:
            st.info(f"{'工作' if account=='work' else '個人'}帳號尚未授權 Google。")

        ev_map = _events_by_date(events_raw)

        # ── 渲染視圖 ─────────────────────────────────
        col_cal, col_detail = st.columns([3, 1])

        with col_cal:
            if view_mode == "月":
                html = _render_month(ev_map, anchor)
            elif view_mode == "週":
                ws = anchor - timedelta(days=anchor.weekday())
                html = _render_week(ev_map, ws)
            else:
                html = _render_day(ev_map, anchor)

            st.markdown(html, unsafe_allow_html=True)

            # 日期選擇器（點擊某天看詳情）
            st.markdown("---")
            st.caption("選擇日期查看當天事件詳情 👇")
            selected_date = st.date_input("選擇日期", value=anchor,
                                          label_visibility="collapsed",
                                          key="cal_selected_date")

        # ── 事件詳情面板 ─────────────────────────────
        with col_detail:
            st.markdown(f"""
<div style="font-size:0.88rem;font-weight:700;color:#334155;margin-bottom:12px">
📌 {selected_date.month}/{selected_date.day} 的事件
</div>""", unsafe_allow_html=True)

            day_events = ev_map.get(selected_date, [])

            if not day_events:
                st.markdown("""
<div style="text-align:center;color:#94a3b8;padding:30px 10px;
            background:#f8fafc;border-radius:12px;border:1px dashed #e2e8f0">
  <div style="font-size:1.8rem;margin-bottom:8px">📭</div>
  <div style="font-size:0.78rem">當天沒有行程</div>
</div>""", unsafe_allow_html=True)
            else:
                for i, ev in enumerate(day_events):
                    # 摘要按鈕
                    time_str = ev["time"] or "整天"
                    btn_label = f"{time_str} · {ev['title'][:16]}"
                    if st.button(btn_label, key=f"ev_btn_{selected_date}_{i}", use_container_width=True):
                        st.session_state["cal_selected_event"] = ev

                # 顯示選中的事件詳情
                if "cal_selected_event" in st.session_state:
                    sel = st.session_state["cal_selected_event"]
                    if sel.get("date") == selected_date:
                        st.markdown("---")
                        _render_detail(sel)

    # ──────────────────────────────────────────────────
    # Tab 2：建立事件
    # ──────────────────────────────────────────────────
    with tab_create:
        _render_create_form()
