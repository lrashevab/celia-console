# -*- coding: utf-8 -*-
"""
pages/content_studio.py — 內容工作室
素材庫 / 草稿工作台 / 內容日曆 / 成效追蹤
"""
import streamlit as st
from datetime import date, datetime, timedelta
from services.content_db import (
    add_idea, get_ideas, update_idea, delete_idea,
    add_draft, get_drafts, update_draft,
    add_schedule, get_schedule, update_schedule,
    upsert_performance, get_performance_summary,
)

STUDIO_CSS = """
<style>
/* ── 卡片 ── */
.idea-card {
    background: #fff;
    border: 1.5px solid #e2e8f0;
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: box-shadow 0.15s;
}
.idea-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.07); }
.idea-title { font-size: 0.95rem; font-weight: 700; color: #1e293b; }
.idea-meta  { font-size: 0.76rem; color: #64748b; margin-top: 4px; }
.idea-tag {
    display: inline-block;
    background: #f1f5f9;
    color: #475569;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.72rem;
    margin-right: 4px;
}

/* ── 狀態 badge ── */
.badge-new       { background:#dbeafe; color:#1e40af; border-radius:8px; padding:2px 9px; font-size:0.72rem; }
.badge-draft     { background:#fef9c3; color:#92400e; border-radius:8px; padding:2px 9px; font-size:0.72rem; }
.badge-ready     { background:#dcfce7; color:#166534; border-radius:8px; padding:2px 9px; font-size:0.72rem; }
.badge-published { background:#e0e7ff; color:#3730a3; border-radius:8px; padding:2px 9px; font-size:0.72rem; }
.badge-pending   { background:#fff7ed; color:#9a3412; border-radius:8px; padding:2px 9px; font-size:0.72rem; }

/* ── 日曆格 ── */
.cal-day {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 10px;
    padding: 8px;
    min-height: 90px;
    font-size: 0.78rem;
}
.cal-day.today { border-color: #6366f1; background: #eef2ff; }
.cal-post {
    background: #e0e7ff;
    color: #3730a3;
    border-radius: 6px;
    padding: 2px 6px;
    margin-bottom: 3px;
    font-size: 0.7rem;
    cursor: pointer;
}
.cal-post.xhs { background: #fee2e2; color: #991b1b; }

/* ── 平台 icon ── */
.plat-threads { color: #000; font-weight: 700; }
.plat-xhs     { color: #e60012; font-weight: 700; }
</style>
"""

CATEGORIES = ["生活", "工作", "AI", "學習", "觀察", "旅行", "美食", "其他"]
SOURCES     = ["生活觀察", "Claude日誌", "閱讀", "對話", "其他"]
STATUSES    = ["new", "developing", "used", "archived"]
STATUS_LABEL = {"new": "新靈感", "developing": "發展中", "used": "已使用", "archived": "封存"}
STATUS_BADGE = {"new": "badge-new", "developing": "badge-draft",
                "used": "badge-ready", "archived": "badge-published"}
DRAFT_STATUSES = ["draft", "ready", "scheduled", "published"]
DRAFT_LABEL    = {"draft": "草稿", "ready": "待發", "scheduled": "已排程", "published": "已發布"}


def _badge(status: str, mapping: dict = STATUS_BADGE) -> str:
    cls = mapping.get(status, "badge-new")
    label = STATUS_LABEL.get(status) or DRAFT_LABEL.get(status) or status
    return f'<span class="{cls}">{label}</span>'


# ══════════════════════════════════════════════════════
# Tab 1：素材庫
# ══════════════════════════════════════════════════════
def _render_ideas():
    st.subheader("💡 素材庫")

    # ── 快速新增 ──────────────────────────────────────
    with st.expander("➕ 新增靈感", expanded=st.session_state.get("ctx_idea_form_open", False)):
        c1, c2 = st.columns([3, 1])
        with c1:
            new_title = st.text_input("靈感標題 *", placeholder="一句話描述這個想法", key="new_idea_title")
        with c2:
            new_cat = st.selectbox("分類", CATEGORIES, key="new_idea_cat")

        new_content = st.text_area("展開說明（選填）", height=80, key="new_idea_content",
                                   placeholder="背景脈絡、為什麼有這個靈感、可能的發文角度...")
        c3, c4 = st.columns([2, 2])
        with c3:
            new_source = st.selectbox("來源", SOURCES, key="new_idea_source")
        with c4:
            new_tags_raw = st.text_input("標籤（逗號分隔）", key="new_idea_tags",
                                         placeholder="AI, 工作流, 生產力")

        if st.button("💾 儲存靈感", type="primary", key="save_idea_btn"):
            if new_title.strip():
                tags = [t.strip() for t in new_tags_raw.split(",") if t.strip()]
                idea_id = add_idea(new_title.strip(), new_content.strip(),
                                   new_cat, new_source, tags)
                st.success(f"✅ 靈感已儲存（{idea_id}）")
                st.session_state["ctx_idea_form_open"] = False
                st.rerun()
            else:
                st.warning("請填寫標題")

    st.divider()

    # ── 篩選 ─────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 2, 3])
    with fc1:
        filter_status = st.selectbox("狀態", ["全部"] + STATUSES,
                                     format_func=lambda x: "全部" if x == "全部" else STATUS_LABEL[x],
                                     key="idea_filter_status")
    with fc2:
        filter_cat = st.selectbox("分類", ["全部"] + CATEGORIES, key="idea_filter_cat")
    with fc3:
        search_q = st.text_input("搜尋", placeholder="關鍵字...", key="idea_search",
                                 label_visibility="collapsed")

    # ── 讀取資料 ──────────────────────────────────────
    ideas = get_ideas(status=None if filter_status == "全部" else filter_status)
    if filter_cat != "全部":
        ideas = [i for i in ideas if i["category"] == filter_cat]
    if search_q:
        q = search_q.lower()
        ideas = [i for i in ideas if q in i["title"].lower() or q in (i["content"] or "").lower()]

    st.caption(f"共 {len(ideas)} 筆靈感")

    if not ideas:
        st.info("還沒有靈感紀錄。按上方「➕ 新增靈感」開始！")
        return

    # ── 靈感列表 ──────────────────────────────────────
    for idea in ideas:
        iid = idea["id"]
        tags_html = "".join(f'<span class="idea-tag">{t}</span>' for t in idea["tags"])
        badge_html = _badge(idea["status"])

        with st.container():
            col_info, col_actions = st.columns([8, 2])
            with col_info:
                st.markdown(f"""
<div class="idea-card">
  <div class="idea-title">{idea['title']} &nbsp; {badge_html}</div>
  <div class="idea-meta">📁 {idea['category']} · 🔍 {idea['source']} · 🕐 {idea['created_at'][:10]}</div>
  {f'<div style="margin-top:6px;color:#475569;font-size:0.83rem">{idea["content"][:120]}{"…" if len(idea["content"] or "") > 120 else ""}</div>' if idea.get("content") else ""}
  <div style="margin-top:8px">{tags_html}</div>
</div>
""", unsafe_allow_html=True)

            with col_actions:
                st.markdown("<br><br>", unsafe_allow_html=True)
                # 生成草稿按鈕
                if st.button("✍️ 生成草稿", key=f"draft_from_{iid}", use_container_width=True):
                    st.session_state["ctx_generate_draft_idea_id"] = iid
                    st.session_state["ctx_generate_draft_idea_title"] = idea["title"]
                    st.session_state["ctx_generate_draft_idea_content"] = idea.get("content", "")
                    st.session_state["ctx_goto_tab"] = "draft"
                    st.rerun()

                # 狀態快速切換
                status_options = STATUSES
                cur_idx = status_options.index(idea["status"]) if idea["status"] in status_options else 0
                new_status = st.selectbox("狀態", status_options, index=cur_idx,
                                          format_func=lambda x: STATUS_LABEL[x],
                                          key=f"status_{iid}", label_visibility="collapsed")
                if new_status != idea["status"]:
                    update_idea(iid, status=new_status)
                    st.rerun()


# ══════════════════════════════════════════════════════
# 草稿來源 1：從 Claude 日誌生成
# ══════════════════════════════════════════════════════
def _render_from_claude_log():
    import json as _json
    from pathlib import Path
    LOG_FILE = Path(__file__).parent.parent / "data" / "claude_log.json"

    st.markdown("**📅 從 Claude 日誌生成草稿**")
    st.caption("把今天的工作紀錄（commits、突破、心情）直接轉成貼文素材。")

    try:
        sessions = _json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
    except Exception:
        sessions = []

    available_dates = sorted({s.get("date","") for s in sessions if s.get("date")}, reverse=True)
    if not available_dates:
        st.info("尚無 Claude 活動紀錄，請先到「Claude 指揮中心」完成幾次工作再回來。")
        return

    c1, c2 = st.columns([2, 2])
    with c1:
        sel_date = st.selectbox("選擇日期", available_dates, key="log_sel_date")
    with c2:
        fmt = st.radio("平台", ["🧵 Threads", "📕 小紅書"], horizontal=True, key="log_fmt")

    day_sessions = [s for s in sessions if s.get("date") == sel_date and s.get("shareable", True)]
    if not day_sessions:
        st.warning("此日無可公開的紀錄（請在 Claude 指揮中心勾選「適合公開發文」）。")
        return

    tone = st.selectbox("語調", ["自然口語", "專業分享", "輕鬆幽默", "激勵正能量"], key="log_tone")

    if st.button("🤖 生成草稿", type="primary", key="log_gen_btn"):
        with st.spinner("生成中..."):
            from services.content_generator import generate_social_post
            fmt_key = "threads" if "Threads" in fmt else "xiaohongshu"
            content = generate_social_post(day_sessions, fmt_key)
        draft_id = add_draft(
            title=f"{sel_date} 日誌{'Threads' if 'Threads' in fmt else 'XHS'}",
            content_threads=content if "Threads" in fmt else "",
            content_xhs=content if "小紅書" in fmt else "",
            platform="threads" if "Threads" in fmt else "xhs",
        )
        st.success(f"✅ 草稿已儲存（{draft_id}），到下方草稿列表查看。")
        st.session_state["ctx_log_generated_content"] = content
        st.rerun()

    if st.session_state.get("ctx_log_generated_content"):
        st.text_area("生成結果（可複製）", value=st.session_state["ctx_log_generated_content"],
                     height=260, key="log_result_area")


# ══════════════════════════════════════════════════════
# 草稿來源 2：爆款 Pipeline（從 home.py 搬移）
# ══════════════════════════════════════════════════════
def _render_xhs_pipeline():
    from services.xhs_pipeline import step1_research, step2_generate_stream, step3_format, step4_publish_package
    import os, json as _json

    st.markdown("**🔥 小紅書爆款 Pipeline**")
    st.caption("4 步驟：搜尋熱點 → AI 撰文 → 格式適配 → 發佈準備")

    from services.llm_client import active_provider, provider_label
    has_llm    = active_provider() is not None
    has_tavily = bool(os.environ.get("TAVILY_API_KEY", ""))

    with st.expander("⚙️ 環境狀態", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(provider_label())
        with c2: st.markdown(f"{'✅' if has_tavily else '⚠️'} Tavily {'已設定' if has_tavily else '未設定'}")
        with c3: st.markdown("✅ 封面圖（Pollinations.ai 免費）")

    col_topic, col_days = st.columns([4, 2])
    with col_topic:
        topic = st.text_input("主題 / 關鍵字", placeholder="例：設計師用 AI 提升效率", key="boom_topic")
    with col_days:
        search_days = st.selectbox("搜尋範圍", [7, 14, 30], index=1, key="boom_days",
                                   format_func=lambda d: f"最近 {d} 天")

    manual_ref = ""
    if not has_tavily:
        with st.expander("📋 手動貼入參考資料"):
            manual_ref = st.text_area("參考資料", height=100, key="boom_manual_ref")

    run_btn = st.button("🚀 開始生成", type="primary", disabled=not topic or not has_llm, key="boom_run")

    if not run_btn:
        return

    # Step 1
    with st.spinner("Step 1：搜尋熱點資料..."):
        if has_tavily:
            research = step1_research(topic, search_days)
        else:
            research = {"articles": [{"title": "手動資料", "url": "", "content": manual_ref, "score": 1}]
                        if manual_ref else [], "images": [], "query": topic, "source": "manual"}

    if research.get("error"):
        st.error(f"搜尋失敗：{research['error']}")
        return
    st.success(f"✅ Step 1 完成：找到 {len(research.get('articles', []))} 篇資料")

    # Step 2
    full_article = ""
    with st.spinner("Step 2：AI 撰文中..."):
        article_ph = st.empty()
        try:
            for chunk in step2_generate_stream(topic, research):
                full_article += chunk
                if len(full_article) % 40 == 0:
                    article_ph.markdown(full_article + " ▌")
            article_ph.markdown(full_article)
        except Exception as e:
            st.error(f"撰文失敗：{e}")
            return
    st.success("✅ Step 2 完成")

    # Step 3 & 4
    with st.spinner("Step 3-4：格式化 + 發佈準備..."):
        formatted = step3_format(full_article, research.get("images", []))
        package   = step4_publish_package(formatted)
    st.success("✅ Step 3-4 完成")

    st.divider()
    st.markdown(f"### {formatted['title'] or '（標題待填）'}")
    st.markdown("**話題標籤：** " + "  ".join(f"`#{t}`" for t in formatted["topics"]))

    # 封面圖
    from services.image_generator import build_xhs_prompt, generate_cover_variants, MODELS
    with st.expander("🖼️ 封面圖生成", expanded=True):
        cv1, cv2, cv3 = st.columns([3, 2, 2])
        with cv1:
            cover_prompt_in = st.text_input("圖片描述（留空自動）", key="boom_cover_prompt")
        with cv2:
            cover_style = st.selectbox("風格", ["modern","warm","bold","minimal"],
                                       format_func=lambda s: {"modern":"🔵 科技感","warm":"🟠 生活感",
                                                               "bold":"🔴 大字報","minimal":"⚪ 極簡"}[s],
                                       key="boom_cover_style")
        with cv3:
            cover_model = st.selectbox("模型", list(MODELS.keys()), format_func=lambda k: MODELS[k], key="boom_model")
            cover_count = st.number_input("張數", 1, 4, 2, key="boom_count")

        if st.button("🎨 生成封面", key="boom_gen_cover"):
            prompt = cover_prompt_in or build_xhs_prompt(formatted["title"], topic, formatted["topics"][:3], cover_style)
            with st.spinner("生成中..."):
                urls = generate_cover_variants(prompt, count=cover_count, model=cover_model)
            for i, url in enumerate(urls):
                try:
                    st.image(url, caption=f"封面 {i+1}", use_container_width=True)
                except Exception:
                    st.markdown(f"[封面 {i+1}]({url})")

    edited = st.text_area("完整文章（可編輯）", value=formatted["content"], height=360,
                           label_visibility="collapsed", key="boom_final")

    # 儲存為草稿
    if st.button("💾 儲存為草稿", key="boom_save_draft"):
        draft_id = add_draft(title=formatted["title"][:40], content_xhs=edited, platform="xhs")
        st.success(f"✅ 已儲存草稿（{draft_id}）")

    with st.expander("📋 JSON 輸出"):
        dp = {k: v for k, v in package.items() if k != "meta"}
        dp["content"] = edited
        st.code(_json.dumps(dp, ensure_ascii=False, indent=2), language="json")


# ══════════════════════════════════════════════════════
# Tab 2：草稿工作台
# ══════════════════════════════════════════════════════
def _render_drafts():
    st.subheader("✍️ 草稿工作台")

    auto_idea_id      = st.session_state.pop("ctx_generate_draft_idea_id", None)
    auto_idea_title   = st.session_state.pop("ctx_generate_draft_idea_title", "")
    auto_idea_content = st.session_state.pop("ctx_generate_draft_idea_content", "")

    src_tab_idea, src_tab_log, src_tab_boom = st.tabs([
        "💡 從靈感/主題生成", "📅 從 Claude 日誌生成", "🔥 爆款 Pipeline"
    ])

    with src_tab_idea:
        ideas = get_ideas()
        idea_options = {"（不綁定靈感，直接輸入）": None} | {f"{i['title']} ({i['id']})": i["id"] for i in ideas}
        sel_label = st.selectbox("來自靈感庫（選填）", list(idea_options.keys()),
                                 key="draft_idea_select",
                                 index=list(idea_options.values()).index(auto_idea_id)
                                 if auto_idea_id in idea_options.values() else 0)
        selected_idea_id = idea_options[sel_label]
        topic = st.text_input("主題 / 靈感一句話",
                              value=auto_idea_title if auto_idea_id else "",
                              key="draft_topic",
                              placeholder="例：用 AI 一天做完以前一週的工作")
        extra = st.text_area("補充說明（選填）", value=auto_idea_content if auto_idea_id else "",
                             height=70, key="draft_extra",
                             placeholder="卡點、突破、想傳達的核心觀點...")
        c1, c2 = st.columns(2)
        with c1:
            platforms = st.multiselect("生成平台", ["Threads", "小紅書"],
                                       default=["Threads", "小紅書"], key="draft_platforms")
        with c2:
            tone = st.selectbox("語調", ["自然口語", "專業分享", "輕鬆幽默", "激勵正能量"], key="draft_tone")

        if st.button("🚀 AI 幫我生成草稿", type="primary", key="gen_draft_btn"):
            if not topic.strip():
                st.warning("請填寫主題")
            elif not platforms:
                st.warning("請選擇至少一個平台")
            else:
                with st.spinner("生成中..."):
                    content_t, content_x = _generate_drafts(topic, extra, tone, platforms)
                draft_id = add_draft(
                    idea_id=selected_idea_id,
                    platform="both" if len(platforms) == 2 else platforms[0].lower(),
                    title=topic[:40],
                    content_threads=content_t,
                    content_xhs=content_x,
                )
                if selected_idea_id:
                    update_idea(selected_idea_id, status="developing")
                st.success(f"✅ 草稿已儲存（{draft_id}）")
                st.rerun()

    with src_tab_log:
        _render_from_claude_log()

    with src_tab_boom:
        _render_xhs_pipeline()

    st.divider()

    # ── 草稿列表 ──────────────────────────────────────
    df1, df2 = st.columns([2, 2])
    with df1:
        filter_ds = st.selectbox("狀態篩選", ["全部"] + DRAFT_STATUSES,
                                 format_func=lambda x: "全部" if x == "全部" else DRAFT_LABEL[x],
                                 key="draft_filter")
    drafts = get_drafts(status=None if filter_ds == "全部" else filter_ds)
    st.caption(f"共 {len(drafts)} 份草稿")

    if not drafts:
        st.info("還沒有草稿，按上方「AI 幫我生成草稿」開始！")
        return

    for d in drafts:
        did = d["id"]
        with st.expander(
            f"**{d['title'] or '（無標題）'}**  —  "
            f"{DRAFT_LABEL.get(d['status'], d['status'])}  ·  {d['updated_at'][:10]}",
            expanded=False
        ):
            tab_t, tab_x, tab_action = st.tabs(["🧵 Threads", "📕 小紅書", "⚙️ 操作"])

            with tab_t:
                new_ct = st.text_area("Threads 內容", value=d["content_threads"],
                                      height=180, key=f"ct_{did}")
                if st.button("💾 儲存", key=f"save_ct_{did}"):
                    update_draft(did, content_threads=new_ct)
                    st.success("已儲存")

            with tab_x:
                new_title = st.text_input("小紅書標題", value=d["title"], key=f"xt_{did}")
                new_cx = st.text_area("小紅書正文", value=d["content_xhs"],
                                      height=180, key=f"cx_{did}")
                if st.button("💾 儲存", key=f"save_cx_{did}"):
                    update_draft(did, title=new_title, content_xhs=new_cx)
                    st.success("已儲存")

            with tab_action:
                # 狀態
                cur_idx = DRAFT_STATUSES.index(d["status"]) if d["status"] in DRAFT_STATUSES else 0
                new_ds = st.selectbox("草稿狀態", DRAFT_STATUSES, index=cur_idx,
                                      format_func=lambda x: DRAFT_LABEL[x],
                                      key=f"ds_{did}")
                if new_ds != d["status"]:
                    update_draft(did, status=new_ds)
                    st.rerun()

                st.divider()

                # 排程
                st.markdown("**📅 加入排程**")
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    sched_plat = st.selectbox("平台", ["threads", "xhs"],
                                              format_func=lambda x: "Threads" if x == "threads" else "小紅書",
                                              key=f"sp_{did}")
                with sc2:
                    sched_date = st.date_input("發文日期", value=date.today() + timedelta(days=1),
                                               key=f"sd_{did}")
                with sc3:
                    sched_time = st.time_input("時間", value=datetime.strptime("10:00", "%H:%M").time(),
                                               key=f"st_{did}")

                if st.button("📅 加入排程", key=f"add_sched_{did}"):
                    sched_dt = f"{sched_date} {sched_time.strftime('%H:%M:%S')}"
                    sched_id = add_schedule(did, sched_plat, sched_dt)
                    update_draft(did, status="scheduled")
                    st.success(f"✅ 已排程（{sched_id}）")
                    st.rerun()


def _generate_drafts(topic: str, extra: str, tone: str, platforms: list) -> tuple[str, str]:
    """呼叫 LLM 生成雙平台草稿"""
    try:
        from services.llm_client import generate

        tone_map = {
            "自然口語": "口語化、像在跟朋友說話",
            "專業分享": "有條理、有觀點、適合分享給同行",
            "輕鬆幽默": "有點自嘲、幽默、輕鬆",
            "激勵正能量": "有能量感、激勵、真實",
        }
        tone_desc = tone_map.get(tone, "自然口語")
        context = f"主題：{topic}"
        if extra:
            context += f"\n補充：{extra}"

        content_t = ""
        content_x = ""

        if "Threads" in platforms:
            sys_t = f"""你是一位在 Threads 上經營個人品牌的創作者，語調：{tone_desc}。
寫作規則：
1. 第一行是 HOOK，讓人想繼續看。公式：[情緒/數字/反常識] + 短停頓
2. 150-280 字繁體中文，自然段落
3. 結尾一句互動問句，不要「歡迎分享」這種廢話
4. 最多 3 個 hashtag，放最後
只回傳貼文內容，不要任何說明。"""
            content_t = generate(sys_t, f"根據以下資訊寫一篇 Threads 貼文：\n{context}", max_tokens=600)

        if "小紅書" in platforms:
            sys_x = f"""你是在小紅書分享生活與工作的創作者，語調：{tone_desc}，受眾是 25-35 歲。
寫作規則：
1. 第一行是標題：[情緒詞] + [結果] | [場景]，吸引點擊
2. 正文結構：📌做了什麼 → 💡最大收穫 → 🤔遇到的坑 → ✅今日小結
3. 200-320 字繁體中文，emoji 分段
4. 最後 5 個 hashtag，不要重複
只回傳完整貼文（含標題），不要任何說明。"""
            content_x = generate(sys_x, f"根據以下資訊寫一篇小紅書貼文：\n{context}", max_tokens=700)

        return content_t, content_x
    except Exception as e:
        fallback = f"關於「{topic}」的草稿（AI 生成失敗：{e}）"
        return fallback, fallback


# ══════════════════════════════════════════════════════
# Tab 3：內容日曆
# ══════════════════════════════════════════════════════
def _render_calendar():
    st.subheader("📅 內容日曆")

    today = date.today()
    # 週起始（週一）
    week_start = today - timedelta(days=today.weekday())

    c1, c2 = st.columns([3, 1])
    with c1:
        view = st.radio("檢視", ["本週", "下週", "本月"], horizontal=True, key="cal_view")
    with c2:
        if st.button("➕ 快速排程", key="quick_sched"):
            st.session_state["ctx_goto_tab"] = "draft"

    if view == "本週":
        start = week_start
        end   = week_start + timedelta(days=6)
    elif view == "下週":
        start = week_start + timedelta(days=7)
        end   = week_start + timedelta(days=13)
    else:
        start = today.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)

    scheds = get_schedule(from_date=start.isoformat(), to_date=end.isoformat())

    # 依日期分組
    by_date: dict[str, list] = {}
    for s in scheds:
        d = s["scheduled_at"][:10]
        by_date.setdefault(d, []).append(s)

    # 週視圖
    if view in ["本週", "下週"]:
        days = [start + timedelta(days=i) for i in range(7)]
        weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
        cols = st.columns(7)
        for i, (col, day) in enumerate(zip(cols, days)):
            with col:
                is_today = day == today
                day_scheds = by_date.get(day.isoformat(), [])
                posts_html = ""
                for s in day_scheds:
                    plat_cls = "xhs" if s["platform"] == "xhs" else ""
                    plat_icon = "📕" if s["platform"] == "xhs" else "🧵"
                    title = (s.get("title") or "草稿")[:10]
                    posts_html += f'<div class="cal-post {plat_cls}">{plat_icon} {title}</div>'

                day_cls = "cal-day today" if is_today else "cal-day"
                st.markdown(f"""
<div class="{day_cls}">
  <div style="font-weight:700;color:{'#6366f1' if is_today else '#334155'};margin-bottom:6px">
    週{weekday_names[i]} {day.day}
  </div>
  {posts_html if posts_html else '<div style="color:#cbd5e1;font-size:0.7rem">無排程</div>'}
</div>
""", unsafe_allow_html=True)
    else:
        # 月視圖：列表形式
        if not scheds:
            st.info(f"本月（{start.strftime('%Y/%m')}）尚無排程。")
        for s in scheds:
            plat = "Threads" if s["platform"] == "threads" else "小紅書"
            status_color = "#16a34a" if s["status"] == "published" else "#d97706"
            st.markdown(f"""
<div style="border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px;margin-bottom:8px;display:flex;align-items:center;gap:12px">
  <div style="font-weight:700;color:#334155;min-width:60px">{s['scheduled_at'][:10]}</div>
  <div style="color:#6366f1">{plat}</div>
  <div style="flex:1;color:#1e293b">{s.get('title') or '（無標題）'}</div>
  <div style="color:{status_color};font-size:0.8rem">{s['status']}</div>
</div>
""", unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 排程詳細")

    if not scheds:
        st.info("這個時間範圍內沒有排程。")
        return

    for s in scheds:
        sid = s["id"]
        plat_label = "Threads" if s["platform"] == "threads" else "小紅書"
        with st.expander(
            f"{'🧵' if s['platform']=='threads' else '📕'} {plat_label}  ·  "
            f"{s['scheduled_at'][:16]}  ·  {s.get('title','草稿')[:20]}",
            expanded=False
        ):
            content = s.get("content_threads") if s["platform"] == "threads" else s.get("content_xhs")
            if content:
                st.text_area("貼文內容", value=content, height=150,
                             key=f"cal_content_{sid}", disabled=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                new_status = st.selectbox("狀態", ["pending", "published", "failed", "cancelled"],
                                          index=["pending", "published", "failed", "cancelled"].index(
                                              s["status"]) if s["status"] in ["pending", "published", "failed", "cancelled"] else 0,
                                          key=f"cal_status_{sid}",
                                          format_func=lambda x: {"pending":"待發","published":"已發布",
                                                                   "failed":"失敗","cancelled":"取消"}[x])
            with c2:
                post_url = st.text_input("貼文連結（發布後填入）", value=s.get("post_url",""),
                                         key=f"cal_url_{sid}")
            with c3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 更新", key=f"cal_save_{sid}"):
                    update_schedule(sid, status=new_status, post_url=post_url,
                                    published_at=datetime.now().isoformat() if new_status == "published" else None)
                    st.success("已更新")
                    st.rerun()


# ══════════════════════════════════════════════════════
# Tab 4：成效追蹤
# ══════════════════════════════════════════════════════
def _render_performance():
    st.subheader("📊 成效追蹤")

    summary = get_performance_summary()
    if summary:
        cols = st.columns(len(summary))
        for col, plat_data in zip(cols, summary):
            plat = "Threads" if plat_data["platform"] == "threads" else "小紅書"
            with col:
                st.metric(f"{plat} 總觸及", f"{plat_data['total_reach']:,}")
                st.metric("貼文數", plat_data["post_count"])
                st.metric("總按讚", plat_data["total_likes"])
        st.divider()

    st.markdown("**手動回填成效數字**")

    published_scheds = get_schedule()
    published = [s for s in published_scheds if s["status"] == "published"]

    if not published:
        st.info("尚無已發布的貼文。發布後回來填入成效數字，讓 AI 幫你分析哪種內容最有效。")
        return

    for s in published:
        sid = s["id"]
        plat_label = "Threads" if s["platform"] == "threads" else "小紅書"
        with st.expander(f"{'🧵' if s['platform']=='threads' else '📕'} {plat_label} · {s.get('title','')[:20]} · {s.get('published_at','')[:10]}"):
            pc1, pc2, pc3, pc4 = st.columns(4)
            with pc1:
                likes = st.number_input("按讚", min_value=0, key=f"perf_likes_{sid}")
            with pc2:
                comments = st.number_input("留言", min_value=0, key=f"perf_comments_{sid}")
            with pc3:
                reposts = st.number_input("轉發/收藏", min_value=0, key=f"perf_reposts_{sid}")
            with pc4:
                reach = st.number_input("觸及", min_value=0, key=f"perf_reach_{sid}")

            if st.button("💾 儲存成效", key=f"save_perf_{sid}"):
                upsert_performance(sid, s["platform"],
                                   likes=likes, comments=comments,
                                   reposts=reposts, reach=reach)
                st.success("已儲存")
                st.rerun()


# ══════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════
def render():
    st.markdown(STUDIO_CSS, unsafe_allow_html=True)
    st.markdown("""
<div style="padding:8px 0 20px 0">
  <h1 style="font-size:1.8rem;font-weight:800;color:#1e293b;margin:0">📱 內容工作室</h1>
  <div style="color:#64748b;font-size:0.85rem;margin-top:4px">靈感 → 草稿 → 排程 → 成效追蹤</div>
</div>
""", unsafe_allow_html=True)

    # Tab 跳轉（從素材庫點「生成草稿」時）
    default_tab = 1 if st.session_state.get("ctx_goto_tab") == "draft" else 0
    if "ctx_goto_tab" in st.session_state:
        del st.session_state["ctx_goto_tab"]

    tab_ideas, tab_drafts, tab_cal, tab_perf = st.tabs([
        "💡 素材庫", "✍️ 草稿工作台", "📅 內容日曆", "📊 成效追蹤"
    ])

    with tab_ideas:
        _render_ideas()
    with tab_drafts:
        _render_drafts()
    with tab_cal:
        _render_calendar()
    with tab_perf:
        _render_performance()
