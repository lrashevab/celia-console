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
with open("static/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 側邊欄
# ══════════════════════════════════════════════════════
PAGES = [
    ("🤖", "Claude 指揮中心", "claude"),
    ("🏢", "工作指揮室",      "work"),
    ("🏠", "個人生活",        "personal"),
    ("📱", "內容工作室",      "studio"),
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
            prev = st.session_state.current_page
            if prev != page_id:
                # 只清除 ctx_ 開頭的 context 資料，保留 ui_ 開頭的 UI 偏好與 widget 狀態
                for k in [k for k in st.session_state if k.startswith("ctx_")]:
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
    except ImportError:
        st.markdown('<div class="acct-status">⚠️ 服務未設定</div>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.markdown('<div class="acct-status">🔴 Token 不存在</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="acct-status">❌ 讀取失敗: {type(e).__name__}</div>', unsafe_allow_html=True)

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
elif mode == "studio":
    from pages.content_studio import render as studio_render
    studio_render()
else:
    from pages.personal_dashboard import render as personal_render
    personal_render()
