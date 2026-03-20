# -*- coding: utf-8 -*-
"""
app.py — Life OS 主入口
雙模式切換：工作（廣告行銷）/ 個人生活
硬隔離：兩個 context 絕不共享資料
"""
import streamlit as st

# ── 頁面設定 ─────────────────────────────────────────
st.set_page_config(
    page_title="Life OS",
    page_icon="🌗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局樣式 ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── 隱藏 Streamlit 預設頁面導覽（pages/ 自動生成的連結） ── */
[data-testid="stSidebarNav"] { display: none !important; }
/* 隱藏頂部 Deploy 按鈕與 header */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }

/* ── 側邊欄底色 ── */
section[data-testid="stSidebar"] {
    background: #0f172a;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 20px;
}
section[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}
section[data-testid="stSidebar"] h2 {
    color: #f8fafc !important;
    font-weight: 700;
}
section[data-testid="stSidebar"] .stDivider { border-color: #2d3748; }

/* ── 導覽按鈕 ── */
.nav-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 0.9rem;
    font-weight: 500;
    color: #94a3b8;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    margin-bottom: 4px;
    text-decoration: none;
}
.nav-btn:hover { background: #1e293b; color: #f1f5f9; }
.nav-btn.active {
    background: #1e40af;
    color: #fff !important;
    font-weight: 700;
}
.nav-icon { font-size: 1.1rem; width: 22px; text-align: center; }

/* ── 帳號狀態 ── */
.acct-status {
    font-size: 0.78rem;
    padding: 3px 0;
    color: #64748b;
}

/* ── 全域元件 ── */
[data-testid="stMetricValue"] { font-size: 2rem !important; }
[data-testid="stExpander"] { border: 1px solid #e2e8f0; border-radius: 14px; }
.stButton > button { border-radius: 10px; font-weight: 600; font-size: 0.85rem; }
[data-testid="stChatInput"] { border-radius: 16px !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 側邊欄
# ══════════════════════════════════════════════════════
PAGES = [
    ("🤖", "Claude 指揮中心", "claude"),
    ("🏢", "工作指揮室",     "work"),
    ("📅", "會議記錄",       "meeting"),
    ("🏠", "個人生活",       "personal"),
]

# 初始化當前頁面
if "current_page" not in st.session_state:
    st.session_state.current_page = "claude"

with st.sidebar:
    # ── 系統標題 ──────────────────────────────────────
    st.markdown("""
<div style="padding:16px 4px 12px 4px">
  <div style="font-size:1.3rem;font-weight:800;color:#f8fafc;letter-spacing:-0.02em">
    🌗 Celia 控制台
  </div>
  <div style="font-size:0.72rem;color:#475569;margin-top:3px">
    Life OS · 工作 × 個人
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── 導覽按鈕 ──────────────────────────────────────
    st.markdown('<div style="font-size:0.68rem;font-weight:700;color:#475569;letter-spacing:0.08em;margin-bottom:8px">導覽</div>', unsafe_allow_html=True)

    for icon, label, page_id in PAGES:
        is_active = st.session_state.current_page == page_id
        btn_style = (
            "background:#1e40af;color:#fff;border:none;border-radius:10px;"
            "padding:10px 14px;width:100%;text-align:left;font-size:0.9rem;"
            "font-weight:700;cursor:pointer;margin-bottom:4px;display:block"
        ) if is_active else (
            "background:transparent;color:#94a3b8;border:none;border-radius:10px;"
            "padding:10px 14px;width:100%;text-align:left;font-size:0.9rem;"
            "font-weight:500;cursor:pointer;margin-bottom:4px;display:block"
        )
        if st.button(f"{icon}  {label}", key=f"nav_{page_id}", use_container_width=True):
            # 切換時清除舊 session 資料
            prev = st.session_state.current_page
            if prev != page_id:
                for k in [k for k in st.session_state if k not in ("current_page",)]:
                    del st.session_state[k]
                st.session_state.current_page = page_id
                st.rerun()

    st.divider()

    # ── 帳號狀態 ──────────────────────────────────────
    st.markdown('<div style="font-size:0.68rem;font-weight:700;color:#475569;letter-spacing:0.08em;margin-bottom:8px">帳號狀態</div>', unsafe_allow_html=True)
    try:
        from services.google_auth import is_authenticated
        work_ok = is_authenticated("work")
        pers_ok = is_authenticated("personal")
        w_icon = "🟢" if work_ok else "🔴"
        p_icon = "🟢" if pers_ok else "🔴"
        st.markdown(f'<div class="acct-status">{w_icon} 工作帳號</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="acct-status">{p_icon} 個人帳號</div>', unsafe_allow_html=True)
    except Exception:
        st.markdown('<div class="acct-status">⏳ 讀取中...</div>', unsafe_allow_html=True)

    st.divider()

    # ── 快速指令提示 ──────────────────────────────────
    st.markdown('<div style="font-size:0.68rem;font-weight:700;color:#475569;letter-spacing:0.08em;margin-bottom:8px">Claude Code 指令</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.75rem;color:#64748b;line-height:1.8">/meeting — 建立會議記錄<br>/work-start — 每日開工<br>/life-sync — 同步個人目標</div>', unsafe_allow_html=True)

# 取得當前頁面
mode = st.session_state.current_page


# ══════════════════════════════════════════════════════
# 主內容區域 — 依模式切換
# ══════════════════════════════════════════════════════
if mode == "claude":
    from pages.home import render as home_render
    home_render()
elif mode == "work":
    from pages.work_dashboard import render as work_render
    work_render()
elif mode == "meeting":
    from pages.meeting_page import render as meeting_render
    meeting_render()
else:
    from pages.personal_dashboard import render as personal_render
    personal_render()
