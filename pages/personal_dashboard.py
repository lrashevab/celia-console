# -*- coding: utf-8 -*-
"""
pages/personal_dashboard.py — 個人生活儀表板（硬隔離）
個人資料不與工作 context 交叉，AI 分析需明確授權
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import date, datetime

from services import google_sheets as gs
from services.google_auth import is_authenticated
from config.settings import DIARY_PATH


def render():
    st.title("🏠 個人生活中心")

    # ── 硬隔離提示 ───────────────────────────────────
    st.caption("🔒 個人模式：資料完全隔離，不與工作 context 共享")

    # ── 授權檢查 ─────────────────────────────────────
    if not is_authenticated("personal"):
        st.warning("⚠️ 個人帳號尚未授權 Google。")
        st.code("python3 -c \"from services.google_auth import get_credentials; get_credentials('personal')\"")
        st.info("授權後重新整理即可載入資料。")
        _render_demo_mode()
        return

    # ══════════════════════════════════════════════════
    # 載入所有個人資料
    # ══════════════════════════════════════════════════
    try:
        reading_df = gs.get_reading()
        fitness_df = gs.get_fitness()
        habits_df  = gs.get_habits()
        finance_df = gs.get_finance()
        goals_df   = gs.get_goals()
    except Exception as e:
        st.error(f"❌ 無法載入個人 Sheets：{e}")
        _render_demo_mode()
        return

    # ══════════════════════════════════════════════════
    # 頂部總覽指標
    # ══════════════════════════════════════════════════
    col1, col2, col3, col4 = st.columns(4)

    reading_pct = 0
    if not reading_df.empty:
        reading_df["pages_total"] = pd.to_numeric(reading_df["pages_total"], errors="coerce").fillna(0)
        reading_df["pages_read"]  = pd.to_numeric(reading_df["pages_read"],  errors="coerce").fillna(0)
        total_pages = reading_df["pages_total"].sum()
        read_pages  = reading_df["pages_read"].sum()
        reading_pct = int(read_pages / total_pages * 100) if total_pages > 0 else 0

    habit_rate = 0
    if not habits_df.empty:
        today_str = date.today().isoformat()
        today_habits = habits_df[habits_df["date"] == today_str]
        if not today_habits.empty:
            completed = today_habits["completed"].str.lower().isin(["true", "1", "yes", "✅"]).sum()
            habit_rate = int(completed / len(today_habits) * 100)

    with col1: st.metric("📚 閱讀進度", f"{reading_pct}%")
    with col2: st.metric("🏋️ 今日習慣", f"{habit_rate}%")
    with col3:
        if not goals_df.empty:
            goals_df["progress_pct"] = pd.to_numeric(goals_df["progress_pct"], errors="coerce").fillna(0)
            avg_goal = int(goals_df["progress_pct"].mean())
            st.metric("🎯 目標平均進度", f"{avg_goal}%")
        else:
            st.metric("🎯 目標平均進度", "—")
    with col4:
        if not finance_df.empty:
            finance_df["amount"] = pd.to_numeric(finance_df["amount"], errors="coerce").fillna(0)
            this_month = date.today().strftime("%Y-%m")
            month_expense = finance_df[
                (finance_df["date"].str.startswith(this_month)) &
                (finance_df["type"].str.lower() == "expense")
            ]["amount"].sum()
            st.metric("💰 本月支出", f"NT$ {int(month_expense):,}")
        else:
            st.metric("💰 本月支出", "—")

    st.divider()

    # ══════════════════════════════════════════════════
    # 閱讀進度
    # ══════════════════════════════════════════════════
    with st.expander("📚 閱讀進度", expanded=True):
        if reading_df.empty:
            st.info("Reading Sheet 尚無資料。")
        else:
            for _, row in reading_df.iterrows():
                total = float(row["pages_total"]) if row["pages_total"] else 0
                read  = float(row["pages_read"])  if row["pages_read"]  else 0
                pct   = read / total if total > 0 else 0
                st.markdown(f"**{row['book']}** — {row.get('author','')}")
                st.progress(pct, text=f"{int(read)}/{int(total)} 頁 ({int(pct*100)}%)")

    # ══════════════════════════════════════════════════
    # 習慣完成率（本週）
    # ══════════════════════════════════════════════════
    with st.expander("✅ 習慣追蹤（本週）", expanded=True):
        if habits_df.empty:
            st.info("Habits Sheet 尚無資料。")
        else:
            habits_df["completed_bool"] = habits_df["completed"].str.lower().isin(["true", "1", "yes", "✅"])
            pivot = habits_df.pivot_table(index="habit", columns="date", values="completed_bool", aggfunc="max")
            pivot = pivot.fillna(False)
            # 只顯示最近 7 天
            cols_sorted = sorted(pivot.columns)[-7:]
            pivot = pivot[cols_sorted]
            # 轉為視覺化字串
            display = pivot.applymap(lambda x: "✅" if x else "⬜")
            st.dataframe(display, use_container_width=True)

    # ══════════════════════════════════════════════════
    # 健身紀錄
    # ══════════════════════════════════════════════════
    with st.expander("🏋️ 健身紀錄", expanded=False):
        if fitness_df.empty:
            st.info("Fitness Sheet 尚無資料。")
        else:
            fitness_df["duration_min"] = pd.to_numeric(fitness_df["duration_min"], errors="coerce").fillna(0)
            fig = px.bar(
                fitness_df.tail(14),
                x="date", y="duration_min", color="activity",
                title="最近 14 天運動時長（分鐘）",
                labels={"duration_min": "時長（分鐘）", "date": "日期", "activity": "運動類型"},
            )
            st.plotly_chart(fig, use_container_width=True)

    # ══════════════════════════════════════════════════
    # 財務追蹤
    # ══════════════════════════════════════════════════
    with st.expander("💰 財務追蹤", expanded=False):
        if finance_df.empty:
            st.info("Finance Sheet 尚無資料。")
        else:
            finance_df["amount"] = pd.to_numeric(finance_df["amount"], errors="coerce").fillna(0)
            income  = finance_df[finance_df["type"].str.lower() == "income"]["amount"].sum()
            expense = finance_df[finance_df["type"].str.lower() == "expense"]["amount"].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("💵 總收入", f"NT$ {int(income):,}")
            c2.metric("💸 總支出", f"NT$ {int(expense):,}")
            c3.metric("💹 結餘", f"NT$ {int(income - expense):,}")

            # 支出分類圓餅圖
            expense_by_cat = finance_df[finance_df["type"].str.lower() == "expense"].groupby("category")["amount"].sum().reset_index()
            if not expense_by_cat.empty:
                fig = px.pie(expense_by_cat, values="amount", names="category", title="支出分類")
                st.plotly_chart(fig, use_container_width=True)

    # ══════════════════════════════════════════════════
    # 個人目標里程碑
    # ══════════════════════════════════════════════════
    with st.expander("🎯 個人目標", expanded=True):
        if goals_df.empty:
            st.info("Goals Sheet 尚無資料。")
        else:
            goals_df["progress_pct"] = pd.to_numeric(goals_df["progress_pct"], errors="coerce").fillna(0)
            for _, row in goals_df.iterrows():
                pct = float(row["progress_pct"]) / 100
                st.markdown(f"**{row['goal']}** `{row.get('category','')}` — 目標日：{row.get('target_date','')}")
                st.progress(min(pct, 1.0), text=f"{int(row['progress_pct'])}%")
                if row.get("milestones"):
                    st.caption(f"里程碑：{row['milestones']}")

    # ══════════════════════════════════════════════════
    # 私人日記（本地，絕不上傳 AI）
    # ══════════════════════════════════════════════════
    st.subheader("📔 私人日記")
    st.caption("🔒 本地存儲，不傳送至任何外部服務")

    diary_tab1, diary_tab2 = st.tabs(["✍️ 今日日記", "📂 過往記錄"])

    with diary_tab1:
        today_str = date.today().isoformat()
        diary_file = DIARY_PATH / f"{today_str}.md"
        existing = diary_file.read_text(encoding="utf-8") if diary_file.exists() else ""

        diary_content = st.text_area("今日日記（僅存本地）", value=existing, height=200)
        if st.button("💾 儲存日記"):
            diary_file.write_text(diary_content, encoding="utf-8")
            st.success(f"✅ 已儲存至 {diary_file}")

    with diary_tab2:
        diary_files = sorted(DIARY_PATH.glob("*.md"), reverse=True)[:10]
        if diary_files:
            selected = st.selectbox("選擇日期", [f.stem for f in diary_files])
            target = DIARY_PATH / f"{selected}.md"
            if target.exists():
                st.markdown(target.read_text(encoding="utf-8"))
        else:
            st.info("尚無日記記錄。")


def _render_demo_mode():
    """Demo 模式 — 顯示範例資料"""
    st.info("📊 Demo 模式（個人帳號未授權）")
    st.progress(0.65, text="📚《原子習慣》65% (195/300 頁)")
    st.progress(0.80, text="🎯 2026 存錢目標 80%")
    import plotly.express as px
    demo = pd.DataFrame({"類別": ["餐飲", "交通", "娛樂", "其他"], "金額": [8000, 3000, 2500, 1500]})
    fig = px.pie(demo, values="金額", names="類別", title="支出分類（Demo）")
    st.plotly_chart(fig, use_container_width=True)
