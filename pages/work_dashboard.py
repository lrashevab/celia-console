# -*- coding: utf-8 -*-
"""
pages/work_dashboard.py — 工作模式儀表板
顯示客戶、任務、待辦、會議；支援一鍵建立 Google Calendar
"""
import streamlit as st
import pandas as pd
from datetime import date

from services import google_sheets as gs
from services import google_calendar as gc
from services.meeting_processor import process_transcript, format_calendar_description
from services.google_auth import is_authenticated


# ── 樣式常數 ─────────────────────────────────────────
STATUS_COLOR = {
    "active": "🟢", "pending": "🟡", "completed": "✅",
    "cancelled": "❌", "on-hold": "🔵",
}
TASK_TYPE_ICON = {"internal": "🏠", "client": "👤", "external": "🌐"}


def _metric_card(label: str, value, delta=None):
    st.metric(label, value, delta)


def render():
    st.title("🏢 工作指揮室")

    # ── 授權檢查 ─────────────────────────────────────
    if not is_authenticated("work"):
        st.warning("⚠️ 工作帳號尚未授權 Google。請先完成 OAuth 設定。")
        st.code("# 在終端機執行以下指令完成首次授權\npython3 -c \"from services.google_auth import get_credentials; get_credentials('work')\"")
        st.stop()

    # ══════════════════════════════════════════════════
    # 頂部指標卡片
    # ══════════════════════════════════════════════════
    try:
        clients_df = gs.get_clients()
        tasks_df   = gs.get_tasks()
        todos_df   = gs.get_todos()
        meetings_df = gs.get_meetings()
    except Exception as e:
        st.error(f"❌ 無法讀取 Google Sheets：{e}")
        st.info("請確認 .env 中的 WORK_SPREADSHEET_ID 是否正確，以及 Sheets 分頁名稱是否符合設定。")
        _render_demo_mode()
        return

    active_clients = clients_df[clients_df["status"].str.lower() == "active"].shape[0]
    open_tasks     = tasks_df[tasks_df["status"].str.lower().isin(["open", "in-progress"])].shape[0]
    open_todos     = todos_df[todos_df["status"].str.lower() != "completed"].shape[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1: _metric_card("🏢 活躍客戶", active_clients)
    with col2: _metric_card("📋 進行中任務", open_tasks)
    with col3: _metric_card("✅ 待辦清單", open_todos)
    with col4: _metric_card("📅 本月會議", meetings_df.shape[0])

    st.divider()

    # ══════════════════════════════════════════════════
    # 客戶總覽
    # ══════════════════════════════════════════════════
    with st.expander("👥 客戶總覽", expanded=True):
        if clients_df.empty:
            st.info("Clients Sheet 目前無資料。")
        else:
            display = clients_df.copy()
            display["狀態"] = display["status"].map(lambda s: STATUS_COLOR.get(s.lower(), "⚪") + " " + s)
            st.dataframe(
                display[["name", "industry", "狀態", "contact", "created_date"]].rename(
                    columns={"name": "客戶名稱", "industry": "產業", "contact": "聯絡人", "created_date": "建立日期"}
                ),
                use_container_width=True, hide_index=True,
            )

    # ══════════════════════════════════════════════════
    # 任務總覽（三分類 Tab）
    # ══════════════════════════════════════════════════
    st.subheader("📋 任務管理")
    tab_all, tab_internal, tab_client, tab_external = st.tabs(["全部", "🏠 內部", "👤 客戶", "🌐 外發"])

    def _render_task_table(df: pd.DataFrame):
        if df.empty:
            st.info("此分類目前無任務。")
            return
        display = df.copy()
        display["類型"] = display["type"].map(lambda t: TASK_TYPE_ICON.get(t.lower(), "•") + " " + t)
        st.dataframe(
            display[["title", "client", "類型", "status", "due_date", "owner"]].rename(
                columns={"title": "任務", "client": "客戶", "status": "狀態", "due_date": "截止日", "owner": "負責人"}
            ),
            use_container_width=True, hide_index=True,
        )

    with tab_all:      _render_task_table(tasks_df)
    with tab_internal: _render_task_table(tasks_df[tasks_df["type"].str.lower() == "internal"])
    with tab_client:   _render_task_table(tasks_df[tasks_df["type"].str.lower() == "client"])
    with tab_external: _render_task_table(tasks_df[tasks_df["type"].str.lower() == "external"])

    st.divider()

    # ══════════════════════════════════════════════════
    # 待辦清單（三分類 Tab）
    # ══════════════════════════════════════════════════
    st.subheader("✅ 待辦事項")
    tab_t_all, tab_t_internal, tab_t_client, tab_t_external = st.tabs(["全部", "🏠 內部", "👤 與客戶", "🌐 外發"])

    def _render_todo_table(df: pd.DataFrame):
        if df.empty:
            st.info("此分類目前無待辦事項。")
            return
        for _, row in df.iterrows():
            done = row["status"].lower() == "completed"
            label = f"~~{row['title']}~~" if done else row["title"]
            col_a, col_b, col_c = st.columns([4, 2, 1])
            with col_a: st.markdown(label)
            with col_b: st.caption(f"截止：{row['due_date']}")
            with col_c: st.caption("✅" if done else "⏳")

    with tab_t_all:      _render_todo_table(todos_df)
    with tab_t_internal: _render_todo_table(todos_df[todos_df["type"].str.lower() == "internal"])
    with tab_t_client:   _render_todo_table(todos_df[todos_df["type"].str.lower() == "client"])
    with tab_t_external: _render_todo_table(todos_df[todos_df["type"].str.lower() == "external"])

    st.divider()

    # ══════════════════════════════════════════════════
    # 會議記錄 + 建立 Google Calendar
    # ══════════════════════════════════════════════════
    st.subheader("📅 會議記錄")

    with st.expander("➕ 新增會議記錄（貼上逐字稿）", expanded=False):
        raw_input = st.text_area(
            "貼入會議逐字稿或條列重點",
            height=200,
            placeholder="例：\n今天和 A 客戶討論 Q2 廣告計畫\n決定投放預算增加 20%\n小明負責下週五前提交素材\n...",
        )
        submit = st.button("🤖 AI 結構化 + 建立 Google Calendar")

        if submit and raw_input.strip():
            with st.spinner("Claude 正在分析會議內容..."):
                try:
                    meeting = process_transcript(raw_input)
                    st.success("✅ 結構化完成")
                    st.json(meeting)

                    desc = format_calendar_description(meeting)
                    event = gc.create_meeting_event(
                        title=meeting["title"],
                        date_str=meeting["date"],
                        start_time=meeting.get("start_time", "09:00"),
                        duration_hours=meeting.get("duration_hours", 1),
                        attendees=meeting.get("attendees", []),
                        description=desc,
                        account="work",
                    )
                    cal_link = event.get("htmlLink", "")
                    st.success(f"📅 Google Calendar 事件已建立 → [查看]({cal_link})")

                    # 建立 Action Item 提醒
                    for item in meeting.get("action_items", []):
                        if item.get("deadline"):
                            gc.create_action_item_reminder(
                                task=item["task"],
                                owner=item.get("owner", "?"),
                                deadline=item["deadline"],
                                account="work",
                            )
                    if meeting.get("action_items"):
                        st.info(f"📌 已為 {len(meeting['action_items'])} 個追蹤事項建立日曆提醒")

                    # 寫入 Sheets
                    import uuid
                    gs.append_meeting([
                        str(uuid.uuid4())[:8],
                        meeting["date"],
                        meeting.get("client", ""),
                        meeting["title"],
                        meeting.get("summary", ""),
                        cal_link,
                    ])

                except Exception as e:
                    st.error(f"❌ 處理失敗：{e}")

    # 顯示歷史會議
    if not meetings_df.empty:
        st.dataframe(
            meetings_df[["date", "client", "title", "summary"]].rename(
                columns={"date": "日期", "client": "客戶", "title": "主題", "summary": "摘要"}
            ),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("尚無會議記錄。")


def _render_demo_mode():
    """無法連線時顯示 Demo 資料"""
    st.info("📊 Demo 模式（無法連接 Google Sheets，顯示範例資料）")
    st.dataframe(pd.DataFrame({
        "客戶名稱": ["東區牙醫診所", "AppX SaaS", "Beauty Brand C"],
        "產業": ["醫療", "科技", "美妝"],
        "狀態": ["🟢 active", "🟡 pending", "🟢 active"],
        "聯絡人": ["陳醫師", "Kevin", "Lisa"],
    }), use_container_width=True, hide_index=True)
