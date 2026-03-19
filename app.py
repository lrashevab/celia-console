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
/* 側邊欄模式切換按鈕加大 */
section[data-testid="stSidebar"] .stSelectbox > div > div {
    font-size: 1.1rem;
    font-weight: bold;
}
/* 指標卡片 */
[data-testid="stMetricValue"] { font-size: 2rem !important; }
/* 硬隔離警告條 */
.isolation-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 側邊欄
# ══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🌗 Life OS")
    st.caption("工作 × 個人 雙模式管理系統")
    st.divider()

    # 模式切換
    mode = st.selectbox(
        "切換模式",
        ["🤖 Claude Code 指揮中心", "🏢 工作（廣告行銷）", "🏠 個人生活"],
        key="mode_selector",
    )

    # 隔離狀態顯示
    if "Claude" in mode:
        st.info("🤖 Claude Code 指揮中心")
        st.caption("活動記錄 × 專案總覽 × 內容輸出")
    elif "工作" in mode:
        st.success("🟢 工作模式 — 工作帳號")
        st.caption("資料來源：Google Sheets（工作帳號）")
    else:
        st.info("🔵 個人模式 — 個人帳號")
        st.caption("資料來源：Google Sheets（個人帳號）\n📔 日記：本地存儲")

    st.divider()

    # 模式切換警告（防止 context 混淆）
    prev_mode = st.session_state.get("_prev_mode", mode)
    if prev_mode != mode:
        st.warning("⚠️ 切換模式中...\n\n前一個模式的資料已清除。")
        # 清除可能殘留的 session 資料
        for key in list(st.session_state.keys()):
            if key not in ("mode_selector", "_prev_mode"):
                del st.session_state[key]
    st.session_state["_prev_mode"] = mode

    st.divider()
    st.markdown("### ⚡ 快速指令")
    st.code("/meeting  — 建立會議記錄\n/life-sync — 同步個人目標", language="bash")
    st.caption("在 Claude Code 終端機輸入")

    st.divider()
    st.markdown("### 🔐 帳號狀態")
    try:
        from services.google_auth import is_authenticated
        work_ok = is_authenticated("work")
        pers_ok = is_authenticated("personal")
        st.write(f"工作帳號：{'✅' if work_ok else '❌ 未授權'}")
        st.write(f"個人帳號：{'✅' if pers_ok else '❌ 未授權'}")
    except Exception:
        st.write("帳號狀態：讀取中...")


# ══════════════════════════════════════════════════════
# 主內容區域 — 依模式切換
# ══════════════════════════════════════════════════════
if "Claude" in mode:
    from pages.home import render as home_render
    home_render()
elif "工作" in mode:
    from pages.work_dashboard import render as work_render
    work_render()
else:
    from pages.personal_dashboard import render as personal_render
    personal_render()
