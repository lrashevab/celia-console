# -*- coding: utf-8 -*-
"""
pages/work_dashboard.py — 工作指揮室 v2.0
高質感 UI + 對話框新增任務 / 客戶
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime

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
.priority-high   { background: #ef4444; }
.priority-medium { background: #f59e0b; }
.priority-low    { background: #10b981; }

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
.task-row.high   { border-left-color: #ef4444; }
.task-row.medium { border-left-color: #f59e0b; }
.task-row.low    { border-left-color: #10b981; }
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

/* ── 待辦列表行 ── */
.todo-row {
    background: #f8fafc;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.todo-title {
    font-size: 0.87rem;
    color: #334155;
}
.todo-due {
    font-size: 0.73rem;
    color: #94a3b8;
}

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
PRIORITY_CLASS = {"high": "high", "medium": "medium", "low": "low"}
TODAY = date.today()


def _contract_badge(status: str) -> str:
    cls, label = CONTRACT_BADGE.get(status, ("badge-gray", status or "—"))
    return f'<span class="badge {cls}">{label}</span>'


def _priority_dot(priority: str) -> str:
    cls = PRIORITY_CLASS.get(priority.lower(), "medium")
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
            confirmed = row.get("confirmed_by_client", "FALSE")
            confirmed_icon = "✅" if str(confirmed).upper() == "TRUE" else "⏳"
            assigned = row.get("assigned_to", "") or "—"
            account  = row.get("_account", "work")

            st.markdown(f"""
<div class="task-row {pri}">
    <div>{_priority_dot(pri)}</div>
    <div class="task-title">{row.get('title','—')}</div>
    <span class="task-client">{row.get('client','—')}</span>
    {_account_tag(account)}
    <span class="badge badge-gray">指派：{assigned}</span>
    <span class="task-due {dcls}">📅 {due}</span>
    <span class="task-confirmed" title="客戶確認">{confirmed_icon}</span>
</div>
""", unsafe_allow_html=True)

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
        st.info("待辦清單是空的。在下方對話框輸入「新增待辦 [事項]」來新增。")
        return

    for _, row in open_df.iterrows():
        due  = row.get("due_date", "")
        dcls = _due_class(due)
        confirmed = row.get("confirmed_by_client", "FALSE")
        confirmed_icon = "✅" if str(confirmed).upper() == "TRUE" else ""
        account = row.get("_account", "work")

        st.markdown(f"""
<div class="todo-row">
    <div>
        <span class="todo-title">{row.get('title','—')}</span>
        {(' · ' + row.get('client','')) if row.get('client') else ''}
        &nbsp;{_account_tag(account)}
        {confirmed_icon}
    </div>
    <span class="todo-due {dcls}">📅 {due}</span>
</div>
""", unsafe_allow_html=True)


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
                # 從現有客戶清單取名稱供選擇（可手動輸入）
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
                    ["medium", "high", "low"],
                    format_func=lambda x: {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}[x],
                )

        # 連結區（每行一個，可貼多個）
        if add_type in ("任務", "待辦"):
            links_raw = st.text_area(
                "相關連結（每行一個，可不填）",
                placeholder="https://figma.com/xxx\nhttps://docs.google.com/yyy",
                height=72,
            )
        else:
            links_raw = ""

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
                row = [task_id, title.strip(), client, "client", "open", priority,
                       due_date.isoformat(), "Celia", links_str, "FALSE", ""]
                gs.append_task(row, account=account)
                _add_history("任務", title.strip(), client, due_date.isoformat(), now_str, account)

            elif add_type == "待辦":
                todo_id = f"D{uuid.uuid4().hex[:4].upper()}"
                row = [todo_id, title.strip(), client, "client", "open",
                       due_date.isoformat(), "Celia", links_str, "FALSE"]
                gs.append_todo(row, account=account)
                _add_history("待辦", title.strip(), client, due_date.isoformat(), now_str, account)

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


def _add_history(type_: str, title: str, client: str, due: str, created_at: str, account: str):
    if "add_history" not in st.session_state:
        st.session_state.add_history = []
    st.session_state.add_history.append({
        "type": type_, "title": title, "client": client,
        "due": due, "created_at": created_at, "account": "🏢" if account == "work" else "🏠",
    })


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

    st.markdown('<div class="cmd-bar-wrap">', unsafe_allow_html=True)
    _render_cmd_bar(demo_clients, demo_tasks, demo_todos)
    st.markdown('</div>', unsafe_allow_html=True)
    _render_kpi(demo_clients, demo_tasks, demo_todos)
    _render_clients(demo_clients)
    _render_tasks(demo_tasks)
    _render_todos(demo_todos)


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
        # 快速指令列（最頂部）
        st.markdown('<div class="cmd-bar-wrap">', unsafe_allow_html=True)
        _render_cmd_bar(clients_df, tasks_df, todos_df)
        st.markdown('</div>', unsafe_allow_html=True)

        _render_kpi(clients_df, tasks_df, todos_df)

        col_left, col_right = st.columns([1, 1], gap="large")
        with col_left:
            _render_clients(clients_df)
            _render_todos(todos_df)
        with col_right:
            _render_tasks(tasks_df)

    # ── Tab 2：行事曆 ────────────────────────────────
    with tab_calendar:
        from pages.calendar_page import render as cal_render
        cal_render()

    # ── Tab 3：會議記錄 ──────────────────────────────
    with tab_meeting:
        from pages.meeting_page import render as meeting_render
        meeting_render()
