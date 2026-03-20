# -*- coding: utf-8 -*-
"""
pages/work_dashboard.py — 工作指揮室 v2.0
高質感 UI + 對話框新增任務 / 客戶
"""
import re
import uuid
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

from services import google_sheets as gs
from services.google_auth import is_authenticated
from services.chat_handler import parse_command


# ══════════════════════════════════════════════════════
# CSS Design System
# ══════════════════════════════════════════════════════
WORK_CSS = """
<style>
/* ── 全局字型 ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.work-dashboard * { font-family: 'Inter', sans-serif; }

/* ── 頁面標題 ── */
.wd-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
}
.wd-header h1 {
    font-size: 1.7rem;
    font-weight: 700;
    color: #1e293b;
    margin: 0;
}
.wd-date-badge {
    background: #f1f5f9;
    color: #64748b;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 500;
}

/* ── KPI 指標卡 ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 20px 0;
}
.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}
.kpi-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
.kpi-icon { font-size: 1.6rem; margin-bottom: 6px; }
.kpi-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #1e293b;
    line-height: 1;
}
.kpi-label {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 4px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── 合約狀態徽章 ── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
}
.badge-red    { background: #fee2e2; color: #b91c1c; }
.badge-amber  { background: #fef3c7; color: #92400e; }
.badge-green  { background: #dcfce7; color: #166534; }
.badge-indigo { background: #e0e7ff; color: #3730a3; }
.badge-gray   { background: #f1f5f9; color: #475569; }
.badge-blue   { background: #dbeafe; color: #1e40af; }

/* ── 優先級指示器 ── */
.priority-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.priority-high      { background: #ef4444; }
.priority-medium    { background: #f59e0b; }
.priority-low       { background: #10b981; }
.priority-scheduled { background: #8b5cf6; }

/* ── 客戶卡片 ── */
.client-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: border-color 0.2s, box-shadow 0.2s;
}
.client-card:hover {
    border-color: #94a3b8;
    box-shadow: 0 3px 12px rgba(0,0,0,0.08);
}
.client-name {
    font-size: 1rem;
    font-weight: 600;
    color: #1e293b;
}
.client-meta {
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: 3px;
}
.client-right { text-align: right; }
.client-value {
    font-size: 0.85rem;
    color: #475569;
    font-weight: 500;
}

/* ── 任務列表行 ── */
.task-row {
    background: #ffffff;
    border: 1px solid #f1f5f9;
    border-left: 4px solid transparent;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: border-left-color 0.2s;
}
.task-row.high      { border-left-color: #ef4444; }
.task-row.medium    { border-left-color: #f59e0b; }
.task-row.low       { border-left-color: #10b981; }
.task-row.scheduled { border-left-color: #8b5cf6; background: #faf5ff; }
.task-title {
    flex: 1;
    font-size: 0.88rem;
    font-weight: 500;
    color: #1e293b;
}
.task-client {
    font-size: 0.75rem;
    color: #64748b;
    background: #f8fafc;
    padding: 2px 8px;
    border-radius: 8px;
}
.task-due {
    font-size: 0.73rem;
    color: #94a3b8;
}
.task-due.overdue {
    color: #ef4444;
    font-weight: 600;
}
.task-confirmed { font-size: 0.75rem; }

/* ── 待辦列表行（暖色系，與任務明顯區分）── */
.todo-row {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-left: 4px solid #f59e0b;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}
.todo-row:hover { background: #fef9c3; }
.todo-check { font-size: 1rem; color: #d97706; }
.todo-title {
    font-size: 0.87rem;
    color: #78350f;
    font-weight: 500;
    flex: 1;
}
.todo-due {
    font-size: 0.73rem;
    color: #92400e;
    background: #fde68a;
    padding: 2px 7px;
    border-radius: 8px;
}
.todo-due.overdue {
    color: #fff;
    background: #ef4444;
    font-weight: 700;
}

/* ── 今日/本週摘要條 ── */
.summary-strip {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}
.summary-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 8px 14px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #334155;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    cursor: default;
}
.summary-chip .num { font-size: 1.1rem; font-weight: 800; }
.summary-chip.red   { border-color: #fca5a5; background: #fef2f2; color: #991b1b; }
.summary-chip.amber { border-color: #fcd34d; background: #fffbeb; color: #92400e; }
.summary-chip.blue  { border-color: #93c5fd; background: #eff6ff; color: #1e40af; }
.summary-chip.green { border-color: #86efac; background: #f0fdf4; color: #166534; }

/* ── 甘特圖區 ── */
.gantt-wrap { background: #fff; border-radius: 14px; padding: 12px; border: 1px solid #e2e8f0; }

/* ── 批次匯入區 ── */
.batch-preview-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: #f8fafc;
    border-radius: 8px;
    margin-bottom: 5px;
    font-size: 0.82rem;
}
.batch-date { color: #6366f1; font-weight: 700; min-width: 56px; }
.batch-title { flex: 1; color: #1e293b; }
.batch-client { color: #64748b; font-size: 0.75rem; }

/* ── 快速新增面板（頂部）── */
.add-panel-wrap {
    background: #fff;
    border: 1.5px solid #e2e8f0;
    border-radius: 16px;
    padding: 20px 24px 16px 24px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.add-panel-title {
    font-size: 0.78rem;
    font-weight: 700;
    color: #475569;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    margin-bottom: 14px;
}
.add-success {
    background: #f0fdf4;
    border-left: 3px solid #22c55e;
    border-radius: 0 10px 10px 0;
    padding: 10px 14px;
    font-size: 0.83rem;
    color: #166534;
    margin-top: 8px;
    white-space: pre-line;
}
.add-error {
    background: #fef2f2;
    border-left: 3px solid #ef4444;
    border-radius: 0 10px 10px 0;
    padding: 10px 14px;
    font-size: 0.83rem;
    color: #991b1b;
    margin-top: 8px;
}
/* ── 新增紀錄 ── */
.history-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-radius: 10px;
    background: #f8fafc;
    margin-bottom: 5px;
    font-size: 0.8rem;
    color: #334155;
}
.history-type {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    white-space: nowrap;
}
.history-task  { background: #dbeafe; color: #1e40af; }
.history-todo  { background: #fef3c7; color: #92400e; }
.history-client{ background: #dcfce7; color: #166534; }
.history-title { font-weight: 600; flex: 1; }
.history-meta  { color: #94a3b8; font-size: 0.73rem; white-space: nowrap; }

/* ── 區塊標題 ── */
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #334155;
    margin: 24px 0 12px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-count {
    background: #e2e8f0;
    color: #64748b;
    font-size: 0.72rem;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 600;
}
</style>
"""

# ── 合約狀態映射 ─────────────────────────────────────
CONTRACT_BADGE = {
    "未簽":   ("badge-red",    "未簽"),
    "洽談中": ("badge-amber",  "洽談中"),
    "已簽":   ("badge-green",  "已簽"),
    "執行中": ("badge-indigo", "執行中"),
    "已完成": ("badge-gray",   "已完成"),
    "暫停":   ("badge-blue",   "暫停"),
}
PRIORITY_CLASS = {"high": "high", "medium": "medium", "low": "low", "scheduled": "scheduled"}
TODAY = date.today()


def _contract_badge(status: str) -> str:
    cls, label = CONTRACT_BADGE.get(status, ("badge-gray", status or "—"))
    return f'<span class="badge {cls}">{label}</span>'


def _priority_dot(priority: str) -> str:
    p = priority.lower()
    if p == "scheduled":
        return '<span style="font-size:0.85rem;margin-right:4px" title="預訂日程">🗓</span>'
    cls = PRIORITY_CLASS.get(p, "medium")
    return f'<span class="priority-dot priority-{cls}"></span>'


def _due_class(due_str: str) -> str:
    try:
        due = date.fromisoformat(due_str)
        return "overdue" if due < TODAY else ""
    except Exception:
        return ""


def _account_tag(account: str) -> str:
    if account == "work":
        return '<span class="badge badge-indigo">🏢 工作</span>'
    return '<span class="badge badge-green">🏠 接案</span>'


# ══════════════════════════════════════════════════════
# 子元件：KPI 卡片
# ══════════════════════════════════════════════════════
def _render_kpi(clients_df, tasks_df, todos_df):
    open_tasks = tasks_df[tasks_df["status"].str.lower().isin(["open", "in-progress"])].shape[0]
    overdue_tasks = 0
    for _, row in tasks_df.iterrows():
        try:
            if date.fromisoformat(row.get("due_date", "")) < TODAY and row.get("status", "").lower() not in ("completed", "cancelled"):
                overdue_tasks += 1
        except Exception:
            pass

    unsigned_contracts = clients_df[clients_df["contract_status"].isin(["未簽", "洽談中"])].shape[0]
    open_todos = todos_df[todos_df["status"].str.lower() != "completed"].shape[0]

    kpi_html = f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-icon">👥</div>
        <div class="kpi-value">{clients_df.shape[0]}</div>
        <div class="kpi-label">客戶總數</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-icon">📋</div>
        <div class="kpi-value">{open_tasks}</div>
        <div class="kpi-label">進行中任務</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-icon">⚠️</div>
        <div class="kpi-value" style="color:{'#ef4444' if overdue_tasks > 0 else '#1e293b'}">{overdue_tasks}</div>
        <div class="kpi-label">逾期任務</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-icon">✅</div>
        <div class="kpi-value">{open_todos}</div>
        <div class="kpi-label">待辦事項</div>
    </div>
</div>
"""
    st.markdown(kpi_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 子元件：客戶卡片
# ══════════════════════════════════════════════════════
def _render_clients(clients_df: pd.DataFrame):
    if clients_df.empty:
        st.info("尚無客戶資料。在下方對話框輸入「新增客戶 [名稱]」來新增。")
        return

    total = clients_df.shape[0]
    st.markdown(
        f'<div class="section-title">👥 客戶總覽 <span class="section-count">{total} 位</span></div>',
        unsafe_allow_html=True,
    )

    for _, row in clients_df.iterrows():
        contract = row.get("contract_status", "—")
        account  = row.get("_account", "work")
        name     = row.get("name", "—")
        industry = row.get("industry", "—")
        contact  = row.get("contact", "—")
        value    = row.get("monthly_value", "—")

        st.markdown(f"""
<div class="client-card">
    <div>
        <div class="client-name">{name}</div>
        <div class="client-meta">{industry} · 聯絡：{contact}</div>
        <div style="margin-top:6px">{_contract_badge(contract)} {_account_tag(account)}</div>
    </div>
    <div class="client-right">
        <div class="client-value">月費 {value or '—'}</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 子元件：任務看板
# ══════════════════════════════════════════════════════
def _render_tasks(tasks_df: pd.DataFrame):
    if tasks_df.empty:
        st.info("尚無任務資料。在下方對話框輸入「新增任務 [名稱] 給 [客戶]」來新增。")
        return

    open_df  = tasks_df[tasks_df["status"].str.lower().isin(["open", "in-progress"])]
    done_df  = tasks_df[tasks_df["status"].str.lower().isin(["completed", "cancelled"])]

    # 先依優先級排序
    priority_order = {"high": 0, "medium": 1, "low": 2}
    open_df = open_df.copy()
    open_df["_pri"] = open_df["priority"].str.lower().map(priority_order).fillna(1)
    open_df = open_df.sort_values(["_pri", "due_date"])

    total = len(open_df)
    st.markdown(
        f'<div class="section-title">📋 任務看板 <span class="section-count">{total} 件進行中</span></div>',
        unsafe_allow_html=True,
    )

    tab_open, tab_done = st.tabs(["🔄 進行中", "✅ 已完成"])

    with tab_open:
        if open_df.empty:
            st.info("目前沒有進行中的任務。")
        for _, row in open_df.iterrows():
            pri   = row.get("priority", "medium").lower()
            due   = row.get("due_date", "")
            dcls  = _due_class(due)
            assigned = row.get("assigned_to", "") or "—"
            account  = row.get("_account", "work")
            item_id  = row.get("id", "")
            is_editing = st.session_state.get(f"editing_{item_id}", False)

            col_card, col_btn = st.columns([9, 1])
            with col_card:
                st.markdown(f"""
<div class="task-row {pri}">
    <div>{_priority_dot(pri)}</div>
    <div class="task-title">{row.get('title','—')}</div>
    <span class="task-client">{row.get('client','—')}</span>
    {_account_tag(account)}
    <span class="badge badge-gray">👤 {assigned}</span>
    <span class="task-due {dcls}">📅 {due}</span>
</div>
""", unsafe_allow_html=True)
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("✏️", key=f"edit_btn_task_{item_id}", help="編輯", use_container_width=True):
                    st.session_state[f"editing_{item_id}"] = not is_editing
                    st.rerun()

            if is_editing:
                _render_edit_form(row, "tasks")

    with tab_done:
        if done_df.empty:
            st.info("尚無已完成任務。")
        for _, row in done_df.iterrows():
            st.markdown(f"""
<div class="task-row" style="opacity:0.6">
    <div class="task-title">~~{row.get('title','—')}~~</div>
    <span class="task-client">{row.get('client','—')}</span>
    <span class="badge badge-gray">{row.get('status','—')}</span>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 子元件：待辦清單
# ══════════════════════════════════════════════════════
def _render_todos(todos_df: pd.DataFrame):
    open_df = todos_df[todos_df["status"].str.lower() != "completed"]
    total = len(open_df)

    st.markdown(
        f'<div class="section-title">✅ 待辦清單 <span class="section-count">{total} 件</span></div>',
        unsafe_allow_html=True,
    )

    if open_df.empty:
        st.info("待辦清單是空的。使用頂部快速新增面板 → 待辦。")
        return

    for _, row in open_df.iterrows():
        due     = row.get("due_date", "")
        dcls    = _due_class(due)
        client_str = f" · {row.get('client','')}" if row.get("client") else ""
        account = row.get("_account", "work")
        item_id = row.get("id", "")
        is_editing = st.session_state.get(f"editing_{item_id}", False)

        col_card, col_btn = st.columns([9, 1])
        with col_card:
            st.markdown(f"""
<div class="todo-row">
    <span class="todo-check">☐</span>
    <span class="todo-title">{row.get('title','—')}{client_str}</span>
    {_account_tag(account)}
    <span class="todo-due {dcls}">📅 {due}</span>
</div>
""", unsafe_allow_html=True)
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✏️", key=f"edit_btn_todo_{item_id}", help="編輯", use_container_width=True):
                st.session_state[f"editing_{item_id}"] = not is_editing
                st.rerun()

        if is_editing:
            _render_edit_form(row, "todos")


# ══════════════════════════════════════════════════════
# 子元件：快速新增面板（頂部結構化表單）
# ══════════════════════════════════════════════════════
def _render_cmd_bar(clients_df, tasks_df, todos_df):
    st.markdown('<div class="add-panel-title">⚡ 快速新增</div>', unsafe_allow_html=True)

    # ── 類型切換（表單外，切換立即生效）──────────────
    if "add_type" not in st.session_state:
        st.session_state.add_type = "任務"

    type_cols = st.columns(3)
    type_labels = ["任務", "待辦", "客戶"]
    for i, label in enumerate(type_labels):
        with type_cols[i]:
            active = st.session_state.add_type == label
            btn_style = "primary" if active else "secondary"
            if st.button(f"{'✅ ' if label == '任務' else '📝 ' if label == '待辦' else '👤 '}{label}",
                         key=f"type_btn_{label}", type=btn_style, use_container_width=True):
                st.session_state.add_type = label
                st.rerun()

    add_type = st.session_state.add_type
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 表單欄位 ──────────────────────────────────────
    with st.form("add_item_form", clear_on_submit=True):

        # 第一行：名稱 + 帳號
        c1, c2 = st.columns([4, 1])
        with c1:
            title = st.text_input(
                f"{'任務名稱' if add_type == '任務' else '待辦事項' if add_type == '待辦' else '客戶名稱'} *",
                placeholder="例：Q2 廣告提案、確認合約、ACME 品牌",
            )
        with c2:
            account = st.selectbox("帳號", ["work", "personal"],
                                   format_func=lambda x: "🏢 工作" if x == "work" else "🏠 接案")

        if add_type in ("任務", "待辦"):
            # 第二行：客戶 + 截止日期 + 優先級
            c3, c4, c5 = st.columns([2, 2, 1])
            with c3:
                existing = [""] + sorted(clients_df["name"].dropna().unique().tolist()) if not clients_df.empty else [""]
                client_select = st.selectbox("客戶（可選）", existing)
                if client_select == "":
                    client_manual = st.text_input("或手動輸入客戶", placeholder="客戶名稱")
                    client = client_manual.strip()
                else:
                    client = client_select
            with c4:
                due_date = st.date_input("截止日期", value=TODAY)
            with c5:
                priority = st.selectbox(
                    "優先",
                    ["medium", "high", "low", "scheduled"],
                    format_func=lambda x: {
                        "high": "🔴 高", "medium": "🟡 中",
                        "low": "🟢 低", "scheduled": "🗓 預訂日程"
                    }[x],
                )

            # 第三行：負責人 + 連結
            c6, c7 = st.columns([2, 3])
            with c6:
                assigned_to = st.text_input("負責人", value="Celia",
                                            placeholder="Celia / 外發設計師 / 廠商名稱")
            with c7:
                links_raw = st.text_area(
                    "相關連結（每行一個，可不填）",
                    placeholder="https://figma.com/xxx\nhttps://docs.google.com/yyy",
                    height=68,
                )
            # 備註
            notes_input = st.text_input("備註（可選）", placeholder="補充說明、特殊注意事項...")
        else:
            assigned_to = "Celia"
            links_raw = ""
            notes_input = ""

        # 備註（可選）
        if add_type == "客戶":
            c6, c7 = st.columns(2)
            with c6:
                industry = st.text_input("產業", placeholder="美妝 / 科技 / 餐飲...")
            with c7:
                contact = st.text_input("聯絡人", placeholder="王小明")
            contract = st.selectbox("合約狀態", ["未簽", "洽談中", "已簽", "執行中", "暫停", "已完成"])

        submitted = st.form_submit_button(
            f"✅ 新增{'任務' if add_type == '任務' else '待辦' if add_type == '待辦' else '客戶'}",
            type="primary", use_container_width=True,
        )

    # ── 處理送出 ──────────────────────────────────────
    if submitted and title and title.strip():
        import uuid
        links = [l.strip() for l in links_raw.splitlines() if l.strip().startswith("http")]
        links_str = ", ".join(links)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        error_msg = None

        try:
            if add_type == "任務":
                task_id = f"T{uuid.uuid4().hex[:4].upper()}"
                # notes = links + 備註（以換行分隔）
                notes_combined = "\n".join(filter(None, [links_str, notes_input.strip()]))
                row = [task_id, title.strip(), client, "client", "open", priority,
                       due_date.isoformat(), "Celia", assigned_to.strip(), "FALSE", notes_combined]
                gs.append_task(row, account=account)
                _add_history("任務", title.strip(), client, due_date.isoformat(), now_str, account,
                             assigned_to=assigned_to.strip(), notes=notes_combined, item_id=task_id)

            elif add_type == "待辦":
                todo_id = f"D{uuid.uuid4().hex[:4].upper()}"
                notes_combined = "\n".join(filter(None, [links_str, notes_input.strip()]))
                row = [todo_id, title.strip(), client, "client", "open",
                       due_date.isoformat(), assigned_to.strip(), notes_combined, "FALSE"]
                gs.append_todo(row, account=account)
                _add_history("待辦", title.strip(), client, due_date.isoformat(), now_str, account,
                             assigned_to=assigned_to.strip(), notes=notes_combined, item_id=todo_id)

            elif add_type == "客戶":
                client_id = f"C{uuid.uuid4().hex[:4].upper()}"
                row = [client_id, title.strip(), industry if add_type == "客戶" else "", "",
                       contact if add_type == "客戶" else "", "",
                       contract if add_type == "客戶" else "未簽",
                       "work" if account == "work" else "freelance",
                       "", TODAY.isoformat(), ""]
                from services.google_sheets import _append_row
                from services.google_auth import get_sheets_service
                from config.settings import ACCOUNTS
                svc = get_sheets_service(account)
                sid = ACCOUNTS[account]["spreadsheet_id"]
                _append_row(svc, sid, "Clients", row)
                _add_history("客戶", title.strip(), "", "", now_str, account)

        except Exception as e:
            error_msg = str(e)

        if error_msg:
            st.markdown(f'<div class="add-error">⚠️ 寫入失敗：{error_msg}<br>請確認 Google Sheets 連線正常</div>',
                        unsafe_allow_html=True)
        else:
            detail = f"截止：{due_date.isoformat()}" if add_type in ("任務", "待辦") else ""
            if links:
                detail += f"  ·  {len(links)} 個連結"
            st.markdown(
                f'<div class="add-success">✅ 已新增{add_type}：<b>{title.strip()}</b><br>'
                f'{detail}</div>',
                unsafe_allow_html=True,
            )
            st.rerun()

    # ── 新增紀錄 ──────────────────────────────────────
    history = st.session_state.get("add_history", [])
    if history:
        st.markdown('<div style="font-size:0.75rem;font-weight:700;color:#94a3b8;'
                    'letter-spacing:0.06em;margin:16px 0 8px 0">最近新增紀錄</div>',
                    unsafe_allow_html=True)
        for h in reversed(history[-10:]):
            type_cls = {"任務": "history-task", "待辦": "history-todo", "客戶": "history-client"}.get(h["type"], "history-task")
            meta_parts = []
            if h.get("client"):
                meta_parts.append(h["client"])
            if h.get("due"):
                meta_parts.append(f"截止 {h['due']}")
            meta_parts.append(h["account"])
            meta_str = " · ".join(meta_parts)
            st.markdown(f"""
<div class="history-row">
  <span class="history-type {type_cls}">{h['type']}</span>
  <span class="history-title">{h['title']}</span>
  <span class="history-meta">{meta_str}</span>
  <span class="history-meta">{h['created_at']}</span>
</div>""", unsafe_allow_html=True)


def _add_history(type_: str, title: str, client: str, due: str, created_at: str, account: str,
                 assigned_to: str = "Celia", notes: str = "", item_id: str = ""):
    if "add_history" not in st.session_state:
        st.session_state.add_history = []
    st.session_state.add_history.append({
        "type": type_, "title": title, "client": client,
        "due": due, "created_at": created_at,
        "account_raw": account,
        "account": "🏢" if account == "work" else "🏠",
        "assigned_to": assigned_to, "notes": notes, "id": item_id,
    })


# ══════════════════════════════════════════════════════
# 今日 / 本週摘要條
# ══════════════════════════════════════════════════════
def _render_daily_summary(tasks_df: pd.DataFrame, todos_df: pd.DataFrame):
    today_str = TODAY.isoformat()
    week_end  = (TODAY + timedelta(days=6)).isoformat()

    overdue, today_tasks, week_tasks = [], [], []
    for _, row in tasks_df.iterrows():
        if row.get("status", "").lower() in ("completed", "cancelled"):
            continue
        due = row.get("due_date", "")
        try:
            d = date.fromisoformat(due)
            if d < TODAY:
                overdue.append(row)
            elif due == today_str:
                today_tasks.append(row)
            elif due <= week_end:
                week_tasks.append(row)
        except Exception:
            pass

    open_todos = todos_df[todos_df["status"].str.lower() != "completed"] if not todos_df.empty else pd.DataFrame()

    chips = []
    if overdue:
        chips.append(f'<div class="summary-chip red"><span class="num">{len(overdue)}</span> 件逾期</div>')
    chips.append(f'<div class="summary-chip {"amber" if today_tasks else "green"}"><span class="num">{len(today_tasks)}</span> 件今日截止</div>')
    chips.append(f'<div class="summary-chip blue"><span class="num">{len(week_tasks)}</span> 件本週到期</div>')
    chips.append(f'<div class="summary-chip amber"><span class="num">{len(open_todos)}</span> 件待辦未完成</div>')

    st.markdown(f'<div class="summary-strip">{"".join(chips)}</div>', unsafe_allow_html=True)

    # 展開今日細節
    all_today = today_tasks + overdue
    if all_today:
        with st.expander(f"📌 今日需關注（{len(all_today)} 件）", expanded=False):
            for row in all_today:
                is_over = row.get("due_date", "") < today_str
                tag = "🔴 逾期" if is_over else "📅 今日"
                pri = row.get("priority", "medium")
                pri_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(pri, "🟡")
                st.markdown(
                    f"{pri_icon} **{row.get('title','—')}** — {row.get('client','—')} `{tag}`"
                )


# ══════════════════════════════════════════════════════
# 甘特圖
# ══════════════════════════════════════════════════════
def _render_gantt(tasks_df: pd.DataFrame):
    import plotly.express as px

    df = tasks_df[tasks_df["status"].str.lower().isin(["open", "in-progress"])].copy()
    if df.empty:
        st.info("沒有進行中的任務可顯示。")
        return

    rows = []
    for _, row in df.iterrows():
        try:
            due = date.fromisoformat(row.get("due_date", ""))
        except Exception:
            continue
        # 開始日：取今天和「截止前 7 天」的較晚者，確保不早於今天太多
        start = max(TODAY - timedelta(days=14), due - timedelta(days=6))
        rows.append({
            "任務": row.get("title", "—")[:24],
            "客戶": row.get("client", "—"),
            "開始": pd.Timestamp(start),
            "截止": pd.Timestamp(due),
            "優先": row.get("priority", "medium"),
            "狀態": row.get("status", "open"),
        })

    if not rows:
        st.info("無有效截止日期的任務。")
        return

    gdf = pd.DataFrame(rows)
    color_map = {"high": "#ef4444", "medium": "#f59e0b", "low": "#10b981"}

    fig = px.timeline(
        gdf, x_start="開始", x_end="截止", y="任務",
        color="優先", color_discrete_map=color_map,
        hover_data=["客戶", "狀態"],
        labels={"優先": "優先級"},
    )
    fig.update_yaxes(autorange="reversed")
    # add_vline 需要字串格式，不接受 pd.Timestamp
    fig.add_vline(
        x=TODAY.isoformat(), line_dash="dash",
        line_color="#6366f1", line_width=2,
        annotation_text="今天", annotation_position="top left",
    )
    fig.update_layout(
        height=max(220, len(rows) * 46 + 80),
        paper_bgcolor="white", plot_bgcolor="#f8fafc",
        margin=dict(l=0, r=10, t=30, b=0),
        font=dict(family="Inter, sans-serif", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════
# 批次時程匯入
# ══════════════════════════════════════════════════════
def _parse_timeline_text(text: str) -> list:
    """解析多行時程文字 → [{date, title, client, assigned_to}, ...]
    支援格式：
      M/D (週X) 任務描述 @負責人
      M/D 任務描述給客戶 @負責人
    """
    items = []
    year = TODAY.year
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # 格式：M/D (週X) 描述  或  M/D 描述
        m = re.match(r"(\d{1,2})[/月](\d{1,2})(?:\s*\([^)]*\))?\s+(.+)", line)
        if not m:
            continue
        try:
            month, day, desc = int(m.group(1)), int(m.group(2)), m.group(3).strip()
            task_date = date(year, month, day)
        except (ValueError, OverflowError):
            continue
        # 解析 @負責人（在描述末尾）
        assigned_to = ""
        am = re.search(r"@([\w\u4e00-\u9fff]+)", desc)
        if am:
            assigned_to = am.group(1)
            desc = desc[:am.start()].strip()
        # 解析客戶：「給XX」
        client = ""
        cm = re.search(r"給([^\s，,。（(＆&@]+)", desc)
        if cm:
            client = cm.group(1).strip()
        items.append({"date": task_date, "title": desc, "client": client, "assigned_to": assigned_to})
    return items


def _render_batch_import(clients_df: pd.DataFrame):
    st.markdown("**📥 批次匯入時程**")
    st.caption(
        "每行格式：`M/D (週X) 任務描述 @負責人`　　"
        "例：`3/26 (四) 視覺風格方向提案給宇光森 @Celia`\n\n"
        "（`@負責人` 可省略，省略時套用下方統一負責人設定）"
    )

    raw = st.text_area(
        "貼入時程文字",
        placeholder=(
            "3/26 (四) 視覺風格方向提案給宇光森 @Celia\n"
            "3/27 (五) 宇光森提供給客戶\n"
            "3/30 (一) 客戶回饋\n"
            "4/2 (四) 第一次設計提案提供給宇光森＆宇光森給予回饋 @設計師"
        ),
        height=150,
        label_visibility="collapsed",
    )

    col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 1])
    with col_a:
        existing = ["（由描述自動判斷）"] + sorted(clients_df["name"].dropna().unique().tolist()) if not clients_df.empty else ["（由描述自動判斷）"]
        default_client = st.selectbox("統一指定客戶（可選）", existing, key="batch_client")
    with col_b:
        default_assigned = st.text_input("統一負責人", value="Celia",
                                         placeholder="Celia / 外發設計師",
                                         key="batch_assigned",
                                         help="若行內已寫 @負責人 則以行內為準")
    with col_c:
        default_priority = st.selectbox(
            "優先級",
            ["scheduled", "medium", "high", "low"],
            format_func=lambda x: {
                "scheduled": "🗓 預訂日程", "high": "🔴 高",
                "medium": "🟡 中", "low": "🟢 低"
            }[x],
            key="batch_priority",
        )
    with col_d:
        batch_account = st.selectbox("帳號", ["work", "personal"],
                                     format_func=lambda x: "🏢 工作" if x == "work" else "🏠 接案",
                                     key="batch_account")

    if not raw.strip():
        return

    items = _parse_timeline_text(raw)
    if not items:
        st.warning("無法解析，請確認格式（每行需以 M/D 開頭）。")
        return

    # 預覽
    st.markdown(f"**解析結果（{len(items)} 筆）**")
    for it in items:
        client_show = (default_client if default_client != "（由描述自動判斷）" else it.get("client", "")) or "—"
        person_show = it.get("assigned_to") or default_assigned or "Celia"
        st.markdown(f"""
<div class="batch-preview-row">
  <span class="batch-date">{it['date'].strftime('%m/%d')}</span>
  <span class="batch-title">{it['title']}</span>
  <span class="batch-client">👤 {person_show} · 🏢 {client_show}</span>
</div>""", unsafe_allow_html=True)

    if st.button("✅ 全部匯入為任務", type="primary", use_container_width=True, key="batch_submit"):
        success, fail = 0, 0
        for it in items:
            client = (default_client if default_client != "（由描述自動判斷）" else it.get("client", ""))
            person = it.get("assigned_to") or default_assigned or "Celia"
            task_id = f"T{uuid.uuid4().hex[:4].upper()}"
            row = [task_id, it["title"], client, "client", "open",
                   default_priority, it["date"].isoformat(), "Celia", person, "FALSE", ""]
            try:
                gs.append_task(row, account=batch_account)
                success += 1
            except Exception:
                fail += 1
        if success:
            st.success(f"✅ 已匯入 {success} 筆任務！{f'（{fail} 筆失敗）' if fail else ''}")
            st.rerun()
        else:
            st.error("匯入失敗，請確認 Google Sheets 連線。")


# ══════════════════════════════════════════════════════
# 任務區（清單 / 甘特圖 / 批次匯入）
# ══════════════════════════════════════════════════════
def _render_tasks_with_views(tasks_df: pd.DataFrame, todos_df: pd.DataFrame, clients_df: pd.DataFrame):
    # ── 本日/本週摘要 ──────────────────────────────
    _render_daily_summary(tasks_df, todos_df)

    # ── 視圖切換 ───────────────────────────────────
    view_tab, gantt_tab, todo_tab = st.tabs([
        "📋 任務清單", "📊 甘特圖", "✅ 待辦事項"
    ])

    with view_tab:
        _render_tasks(tasks_df)

    with gantt_tab:
        st.markdown('<div class="gantt-wrap">', unsafe_allow_html=True)
        try:
            _render_gantt(tasks_df)
        except Exception as e:
            st.warning(f"甘特圖無法顯示：{e}")
        st.markdown('</div>', unsafe_allow_html=True)

    with todo_tab:
        _render_todos(todos_df)


# ══════════════════════════════════════════════════════
# Inline 編輯表單
# ══════════════════════════════════════════════════════
def _render_edit_form(row: pd.Series, sheet_key: str):
    """展開 inline 編輯表單，儲存後更新 Google Sheets"""
    item_id  = row.get("id", "")
    account  = row.get("_account", "work")
    status_opts   = ["open", "in-progress", "completed", "cancelled"]
    priority_opts = ["medium", "high", "low"]

    with st.form(f"edit_{sheet_key}_{item_id}", clear_on_submit=False):
        ea, eb = st.columns([3, 1])
        with ea:
            new_title = st.text_input("名稱", value=row.get("title", ""))
        with eb:
            cur_status = row.get("status", "open")
            new_status = st.selectbox("狀態", status_opts,
                                      index=status_opts.index(cur_status) if cur_status in status_opts else 0)

        ec, ed, ee = st.columns([2, 2, 1])
        with ec:
            new_client = st.text_input("客戶", value=row.get("client", ""))
        with ed:
            new_assigned = st.text_input("負責人", value=row.get("assigned_to", ""))
        with ee:
            if sheet_key == "tasks":
                priority_opts_ext = ["medium", "high", "low", "scheduled"]
                cur_pri = row.get("priority", "medium")
                new_priority = st.selectbox(
                    "優先", priority_opts_ext,
                    index=priority_opts_ext.index(cur_pri) if cur_pri in priority_opts_ext else 0,
                    format_func=lambda x: {
                        "high": "🔴 高", "medium": "🟡 中",
                        "low": "🟢 低", "scheduled": "🗓 預訂日程"
                    }[x],
                )
            else:
                new_priority = None

        ef, eg = st.columns([2, 3])
        with ef:
            try:
                due_val = date.fromisoformat(row.get("due_date", TODAY.isoformat()))
            except Exception:
                due_val = TODAY
            new_due = st.date_input("截止日期", value=due_val)
        with eg:
            new_notes = st.text_area("備註 / 連結", value=row.get("notes", ""), height=68)

        cs, cc = st.columns(2)
        with cs:
            saved = st.form_submit_button("💾 儲存", type="primary", use_container_width=True)
        with cc:
            cancelled = st.form_submit_button("✖ 取消", use_container_width=True)

    if cancelled:
        st.session_state.pop(f"editing_{item_id}", None)
        st.rerun()

    if saved and new_title.strip():
        fields = {
            "title": new_title.strip(),
            "client": new_client.strip(),
            "assigned_to": new_assigned.strip(),
            "due_date": new_due.isoformat(),
            "status": new_status,
            "notes": new_notes.strip(),
        }
        if new_priority:
            fields["priority"] = new_priority
        try:
            ok = gs.update_row_by_id(item_id, sheet_key, fields, account=account)
            if ok:
                st.success("✅ 已更新！")
                st.session_state.pop(f"editing_{item_id}", None)
                st.rerun()
            else:
                st.error(f"找不到 ID={item_id} 的項目，請確認 Sheets 資料。")
        except Exception as e:
            st.error(f"更新失敗：{e}")


def _find_matching_tasks(tasks_df, todos_df, hint: str) -> str:
    """在任務和待辦中搜尋符合 hint 的項目"""
    results = []
    for df, label in [(tasks_df, "任務"), (todos_df, "待辦")]:
        matches = df[df["title"].str.contains(hint, case=False, na=False)]
        for _, row in matches.iterrows():
            results.append(f"- {label}：**{row['title']}** ({row.get('client','—')})")
    if not results:
        return f"\n\n找不到包含「{hint}」的任務，請確認名稱是否正確。"
    return "\n\n找到以下相關項目：\n" + "\n".join(results) + "\n\n請到 Google Sheets 手動標記完成，或告訴我精確名稱。"


def _build_today_summary(tasks_df, todos_df) -> str:
    """建立今日任務摘要"""
    today_str = TODAY.isoformat()

    overdue, due_today, upcoming = [], [], []
    for _, row in tasks_df.iterrows():
        if row.get("status", "").lower() in ("completed", "cancelled"):
            continue
        due = row.get("due_date", "")
        try:
            d = date.fromisoformat(due)
            item = f"• **{row['title']}** — {row.get('client','—')}"
            if d < TODAY:
                overdue.append(item + f" ⚠️ 逾期（{due}）")
            elif due == today_str:
                due_today.append(item)
            else:
                upcoming.append(item + f"（{due}）")
        except Exception:
            upcoming.append(f"• {row['title']}")

    parts = [f"📅 今天是 {today_str}\n"]
    if overdue:
        parts.append(f"🔴 **逾期任務（{len(overdue)} 件）**\n" + "\n".join(overdue))
    if due_today:
        parts.append(f"📋 **今天截止（{len(due_today)} 件）**\n" + "\n".join(due_today))
    if upcoming:
        parts.append(f"⏳ **即將到來**\n" + "\n".join(upcoming[:5]))
    if not overdue and not due_today and not upcoming:
        parts.append("🎉 今天沒有待辦任務，好好休息！")
    return "\n\n".join(parts)


# ══════════════════════════════════════════════════════
# Demo 模式（Google Sheets 無法連線時）
# ══════════════════════════════════════════════════════
def _render_demo():
    st.info("📊 示範模式（Google Sheets 連線失敗，顯示範例資料）")

    demo_clients = pd.DataFrame({
        "name": ["客戶 A", "客戶 B", "客戶 C", "客戶 D"],
        "industry": ["美妝", "科技", "餐飲", "教育"],
        "contract_status": ["執行中", "洽談中", "已簽", "未簽"],
        "_account": ["work", "work", "personal", "personal"],
        "contact": ["Lisa", "Kevin", "王經理", "陳老師"],
        "monthly_value": ["50,000", "80,000", "30,000", "—"],
    })
    demo_tasks = pd.DataFrame({
        "title": ["Q2 廣告提案", "品牌識別系統", "菜單設計", "課程大綱"],
        "client": ["客戶 A", "客戶 B", "客戶 C", "客戶 D"],
        "status": ["in-progress", "open", "open", "open"],
        "priority": ["high", "medium", "low", "medium"],
        "due_date": [TODAY.isoformat(), "2026-04-01", "2026-04-15", "2026-05-01"],
        "assigned_to": ["Celia", "Celia", "設計師", "Celia"],
        "confirmed_by_client": ["FALSE", "FALSE", "TRUE", "FALSE"],
        "_account": ["work", "work", "personal", "personal"],
    })
    demo_todos = pd.DataFrame({
        "title": ["寄送合約給客戶 A", "確認客戶 B 提案時間"],
        "client": ["客戶 A", "客戶 B"],
        "status": ["open", "open"],
        "due_date": [TODAY.isoformat(), "2026-03-25"],
        "confirmed_by_client": ["FALSE", "FALSE"],
        "_account": ["work", "work"],
    })

    with st.expander("⚡ 快速新增 / 批次匯入", expanded=True):
        qadd_tab, qbatch_tab = st.tabs(["📝 逐筆新增", "📥 批次匯入"])
        with qadd_tab:
            _render_cmd_bar(demo_clients, demo_tasks, demo_todos)
        with qbatch_tab:
            _render_batch_import(demo_clients)
    _render_kpi(demo_clients, demo_tasks, demo_todos)
    col_l, col_r = st.columns([4, 6], gap="large")
    with col_l:
        _render_clients(demo_clients)
    with col_r:
        _render_tasks_with_views(demo_tasks, demo_todos, demo_clients)


# ══════════════════════════════════════════════════════
# 主渲染函數
# ══════════════════════════════════════════════════════
def render():
    # 注入 CSS
    st.markdown(WORK_CSS, unsafe_allow_html=True)

    # 頁面標題
    weekday_map = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekday_map[TODAY.weekday()]
    st.markdown(f"""
<div class="work-dashboard wd-header">
    <h1>🏢 工作指揮室</h1>
    <span class="wd-date-badge">📅 {TODAY.isoformat()} 週{weekday}</span>
</div>
""", unsafe_allow_html=True)

    # ── 授權檢查 ─────────────────────────────────────
    if not is_authenticated("work") and not is_authenticated("personal"):
        st.warning("⚠️ Google 帳號尚未授權。請先完成 OAuth 設定。")
        st.code("python3 -c \"from services.google_auth import get_credentials; get_credentials('work')\"")

    # ── 讀取資料 ─────────────────────────────────────
    try:
        work_clients   = gs.get_clients(account="work")
        work_tasks     = gs.get_tasks(account="work")
        work_todos     = gs.get_todos(account="work")
    except Exception:
        work_clients = pd.DataFrame()
        work_tasks   = pd.DataFrame()
        work_todos   = pd.DataFrame()

    try:
        pers_clients = gs.get_clients(account="personal")
        pers_tasks   = gs.get_tasks(account="personal")
        pers_todos   = gs.get_todos(account="personal")
    except Exception:
        pers_clients = pd.DataFrame()
        pers_tasks   = pd.DataFrame()
        pers_todos   = pd.DataFrame()

    all_clients = pd.concat([work_clients, pers_clients], ignore_index=True)
    all_tasks   = pd.concat([work_tasks, pers_tasks], ignore_index=True)
    all_todos   = pd.concat([work_todos, pers_todos], ignore_index=True)

    # 如果完全無資料，顯示 demo
    if all_clients.empty and all_tasks.empty and all_todos.empty:
        _render_demo()
        return

    # ── 篩選控制 ─────────────────────────────────────
    col_filter1, col_filter2 = st.columns([1, 3])
    with col_filter1:
        account_filter = st.selectbox(
            "帳號",
            ["全部", "🏢 工作", "🏠 接案"],
            label_visibility="collapsed",
        )
    with col_filter2:
        st.markdown("<br>", unsafe_allow_html=True)

    if "工作" in account_filter:
        clients_df = work_clients
        tasks_df   = work_tasks
        todos_df   = work_todos
    elif "接案" in account_filter:
        clients_df = pers_clients
        tasks_df   = pers_tasks
        todos_df   = pers_todos
    else:
        clients_df = all_clients
        tasks_df   = all_tasks
        todos_df   = all_todos

    # ── 頂層三分頁 ──────────────────────────────────
    tab_overview, tab_calendar, tab_meeting = st.tabs([
        "📊 總覽", "🗓 行事曆", "📋 會議記錄"
    ])

    # ── Tab 1：總覽 ──────────────────────────────────
    with tab_overview:
        # 快速新增面板（可收合）
        with st.expander("⚡ 快速新增 / 批次匯入", expanded=st.session_state.get("add_panel_open", True)):
            st.session_state["add_panel_open"] = True
            qadd_tab, qbatch_tab = st.tabs(["📝 逐筆新增", "📥 批次匯入"])
            with qadd_tab:
                _render_cmd_bar(clients_df, tasks_df, todos_df)
            with qbatch_tab:
                _render_batch_import(clients_df)

        _render_kpi(clients_df, tasks_df, todos_df)

        col_left, col_right = st.columns([4, 6], gap="large")
        with col_left:
            _render_clients(clients_df)
        with col_right:
            _render_tasks_with_views(tasks_df, todos_df, clients_df)

    # ── Tab 2：行事曆 ────────────────────────────────
    with tab_calendar:
        from pages.calendar_page import render as cal_render
        cal_render()

    # ── Tab 3：會議記錄 ──────────────────────────────
    with tab_meeting:
        from pages.meeting_page import render as meeting_render
        meeting_render()
