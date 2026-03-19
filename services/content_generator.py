# -*- coding: utf-8 -*-
"""
services/content_generator.py — 社群文章生成器（無需 API Key）
使用模板引擎 + 動態組裝，根據 Claude Code 活動資料生成 Threads / 小紅書文章

未來若有 ANTHROPIC_API_KEY，自動升級為 Claude API 生成（品質更高）
"""
import random
from datetime import datetime
from pathlib import Path


# ── 工具函數 ────────────────────────────────────────
def _clean_commit(commit: str) -> str:
    """去除 git hash，只留訊息"""
    parts = commit.split(" ", 1)
    return parts[1] if len(parts) > 1 else commit


def _extract_keywords(sessions: list) -> dict:
    """從 sessions 萃取關鍵資訊"""
    projects = list({s.get("project_name", "") for s in sessions if s.get("project_name")})
    summaries = [s.get("summary", "") for s in sessions if s.get("summary")]
    all_commits = []
    for s in sessions:
        all_commits.extend([_clean_commit(c) for c in s.get("recent_commits", [])[:2]])
    tags = []
    for s in sessions:
        tags.extend(s.get("tags", []))
    tags = list(dict.fromkeys(tags))  # 去重保序

    date_str = sessions[0].get("date", datetime.now().strftime("%Y-%m-%d")) if sessions else ""
    return {
        "projects": projects,
        "summaries": summaries,
        "commits": all_commits[:4],
        "tags": tags[:5],
        "date": date_str,
        "project_primary": projects[0] if projects else "個人專案",
        "multi_project": len(projects) > 1,
    }


# ── Threads 模板 ────────────────────────────────────
THREADS_OPENERS = [
    "今天又跟 AI 工作了一整天，說說我做了什麼 👇",
    "用 Claude Code 當協作夥伴已經變成我的日常了",
    "每天用 AI 做點什麼，是我給自己的功課",
    "不是在 build，就是在想要 build 什麼",
    "Claude Code 又幫我解決了一個卡了很久的問題",
]

THREADS_TRANSITIONS = [
    "今天主要在做",
    "這次的任務是",
    "花了大部分時間在",
    "重點放在",
]

THREADS_REFLECTIONS = [
    "你也在用 AI 提升工作流嗎？歡迎分享你的方式",
    "AI 工具真的讓我開始相信一個人也能做很多事",
    "每次 build 完都會想，下一個要做什麼",
    "慢慢覺得，會用 AI 的人和不會用的人差距會越來越大",
    "有在用 Claude Code 的朋友嗎？我們來聊聊",
]


def _generate_threads(kw: dict) -> str:
    opener = random.choice(THREADS_OPENERS)
    transition = random.choice(THREADS_TRANSITIONS)

    # 主體：用 summary 或 commits 組裝
    if kw["summaries"]:
        body = "。".join(kw["summaries"])
        if not body.endswith("。"):
            body += "。"
    elif kw["commits"]:
        body = "，".join(kw["commits"][:2]) + "。"
    else:
        body = f"在 {kw['project_primary']} 上做了一些進展。"

    # 專案提及
    if kw["multi_project"]:
        proj_line = f"同時跑了 {len(kw['projects'])} 個專案：{' / '.join(kw['projects'][:3])}。"
    else:
        proj_line = f"專案：{kw['project_primary']}。"

    reflection = random.choice(THREADS_REFLECTIONS)

    # hashtag（從 tags 轉換）
    tag_map = {
        "🌗 Life OS": "#LifeOS",
        "📊 Dashboard": "#Dashboard",
        "🔐 OAuth": "#GoogleOAuth",
        "🔌 MCP": "#MCPServer",
        "⚡ Skill": "#ClaudeSkill",
        "📢 廣告代理": "#MarTech",
        "🐍 腳本": "#Python",
        "🌐 API": "#API",
        "🚀 部署": "#Deploy",
        "🐛 修復": "#BugFix",
        "✨ 新功能": "#NewFeature",
        "💻 開發": "#SideProject",
    }
    hashtags = [tag_map.get(t, "") for t in kw["tags"] if tag_map.get(t)]
    if not hashtags:
        hashtags = ["#ClaudeCode", "#SideProject"]
    hashtags = list(dict.fromkeys(hashtags + ["#ClaudeCode", "#AI工作流"]))[:3]
    hashtag_str = " ".join(hashtags)

    return f"""{opener}

{transition}{proj_line}
{body}

{reflection}

{hashtag_str}"""


# ── 小紅書模板 ──────────────────────────────────────
XHS_TITLES = [
    "用 AI 打造個人系統 | 今天又推進了一步",
    "Claude Code 日記 | {project} 完成新進展",
    "一個人也能做大事 | AI 協作開發日常",
    "用 AI 當副駕駛 | 今日開發紀錄",
    "不會程式也能 build | 我的 AI 工作流",
]

XHS_PAINS = [
    "中間卡在授權流程一段時間，Google OAuth 的坑真的多",
    "debug 花了不少時間，但搞清楚原理之後就順了",
    "配置環境永遠是最煩的部分，但做完就爽了",
    "中間遇到一些奇怪的錯誤，問了 Claude 幾輪才解決",
]

XHS_HASHTAGS = [
    "#Claude #ClaudeCode #AI工具 #個人專案 #程式開發",
    "#AI工作流 #側計畫 #生產力工具 #Claude #開發日記",
    "#ClaudeCode #建構中 #AI協作 #個人系統 #程式學習",
]


def _generate_xiaohongshu(kw: dict) -> str:
    title_template = random.choice(XHS_TITLES)
    title = title_template.replace("{project}", kw["project_primary"])

    if kw["summaries"]:
        what_i_did = "；".join(kw["summaries"][:2])
    elif kw["commits"]:
        what_i_did = "，".join(kw["commits"][:2])
    else:
        what_i_did = f"持續推進 {kw['project_primary']} 的開發"

    discovery = "讓整個系統更完整了一點，自動化流程終於打通"
    if "OAuth" in str(kw["tags"]) or "oauth" in str(kw["commits"]).lower():
        discovery = "搞懂 Google OAuth 的完整流程，以後再也不怕授權問題了"
    elif "Dashboard" in str(kw["tags"]):
        discovery = "視覺化真的讓資訊更好消化，dashboard 讓工作狀態一目瞭然"

    pain = random.choice(XHS_PAINS)
    hashtag = random.choice(XHS_HASHTAGS)

    project_count = f"今天同時推進了 {len(kw['projects'])} 個專案" if kw["multi_project"] else f"今天專注在 {kw['project_primary']}"

    return f"""【{title}】

📌 今天做了什麼
{project_count}。{what_i_did}。

💡 最大收穫
{discovery}。

🤔 遇到的坑
{pain}。

✅ 今日結果
雖然看起來只是一小步，但每天累積真的會不一樣。用 AI 當協作夥伴之後，感覺一個人的產出可以頂以前的好幾倍。

如果你也在用 Claude Code 或其他 AI 工具，歡迎留言交流！

🏷️ {hashtag}"""


# ══════════════════════════════════════════════════
# 主要入口
# ══════════════════════════════════════════════════
def generate_social_post(sessions: list, format_type: str = "threads") -> str:
    """
    生成社群文章（無需 API Key，模板引擎）
    format_type: "threads" 或 "xiaohongshu"

    若環境有 ANTHROPIC_API_KEY 則自動升級為 Claude API 生成
    """
    if not sessions:
        return "沒有足夠的活動記錄來生成文章。"

    # 嘗試用 Claude API（若有 key）
    try:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            from config.settings import ANTHROPIC_API_KEY as cfg_key
            api_key = cfg_key
        if api_key and api_key.startswith("sk-ant"):
            return _generate_with_claude(sessions, format_type, api_key)
    except Exception:
        pass

    # Fallback：模板引擎
    kw = _extract_keywords(sessions)
    if format_type == "threads":
        return _generate_threads(kw)
    else:
        return _generate_xiaohongshu(kw)


def _generate_with_claude(sessions: list, format_type: str, api_key: str) -> str:
    """有 API Key 時使用 Claude API 生成（品質更高）"""
    import anthropic

    kw = _extract_keywords(sessions)
    context_lines = []
    for s in sessions:
        context_lines.append(f"專案：{s.get('project_name', '')}")
        if s.get("summary"):
            context_lines.append(f"摘要：{s['summary']}")
        if s.get("recent_commits"):
            context_lines.append(f"Commits：{' | '.join([_clean_commit(c) for c in s['recent_commits'][:2]])}")

    context = "\n".join(context_lines)
    client = anthropic.Anthropic(api_key=api_key)

    if format_type == "threads":
        system = "你是台灣科技工作者，分享今天用 Claude Code 做了什麼。口語、真實、150-250字繁體中文，結尾加 2-3 個 hashtag。"
    else:
        system = "你是小紅書創作者，分享 AI 工具使用心得。格式：標題 | 副標\n📌今天做了\n💡收穫\n🤔遇到的坑\n✅結果\n#hashtag×5。200-350字繁體中文。"

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": f"根據以下活動生成文章：\n\n{context}"}],
    )
    return resp.content[0].text
