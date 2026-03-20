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
    """從 sessions 萃取關鍵資訊（含 challenge / insight / mood / post_angle）"""
    projects   = list({s.get("project_name", "") for s in sessions if s.get("project_name")})
    summaries  = [s.get("summary",    "") for s in sessions if s.get("summary")]
    challenges = [s.get("challenge",  "") for s in sessions if s.get("challenge")]
    insights   = [s.get("insight",    "") for s in sessions if s.get("insight")]
    moods      = [s.get("mood",       "") for s in sessions if s.get("mood")]
    angles     = [s.get("post_angle", "") for s in sessions if s.get("post_angle")]
    all_commits = []
    for s in sessions:
        all_commits.extend([_clean_commit(c) for c in s.get("recent_commits", [])[:2]])
    tags = []
    for s in sessions:
        tags.extend(s.get("tags", []))
    tags = list(dict.fromkeys(tags))

    date_str = sessions[0].get("date", datetime.now().strftime("%Y-%m-%d")) if sessions else ""
    return {
        "projects":        projects,
        "summaries":       summaries,
        "challenges":      challenges,
        "insights":        insights,
        "moods":           moods,
        "angles":          angles,
        "commits":         all_commits[:4],
        "tags":            tags[:5],
        "date":            date_str,
        "project_primary": projects[0] if projects else "個人專案",
        "multi_project":   len(projects) > 1,
    }


# ── Threads 模板 ────────────────────────────────────
# ── Threads Hook 公式庫（第一行才是關鍵）──────────
# 公式：[數字/反常識/情緒句] 讓人想點「更多」
def _build_threads_hook(kw: dict) -> str:
    """根據素材選最有張力的 Hook"""
    challenge = kw["challenges"][0] if kw["challenges"] else ""
    insight   = kw["insights"][0]   if kw["insights"]   else ""
    mood      = kw["moods"][0]      if kw["moods"]      else ""
    summary   = kw["summaries"][0]  if kw["summaries"]  else ""

    # 優先用「卡點 + 解決」結構（最有共鳴）
    if challenge and insight:
        return f"{challenge}。\n\n搞定了。原來{insight}"
    # 心情情緒型
    if "踩坑" in mood or "苦戰" in mood:
        return f"今天被 {kw['project_primary']} 搞了好幾個小時。\n\n但值得。"
    if "突破" in mood or "震撼" in mood:
        return f"今天有個讓我愣住的發現。\n\n關於 {kw['project_primary']}。"
    # 成就感型
    if "成就感" in mood:
        base = summary or f"{kw['project_primary']} 終於打通了"
        return f"{base}。\n\n一個人做到這步，我挺滿意的。"
    # fallback：成果型
    if summary:
        return f"今天用 Claude Code 做完了：{summary}\n\n記錄一下過程。"
    return f"用 AI 工作的第 N 天，{kw['project_primary']} 有新進展。"


def _generate_threads(kw: dict) -> str:
    hook = _build_threads_hook(kw)

    # 主體：故事弧 problem → struggle → solution → lesson
    body_parts = []
    if kw["summaries"]:
        body_parts.append(f"今天在做：{kw['summaries'][0]}")
    if kw["challenges"]:
        body_parts.append(f"卡住的地方：{kw['challenges'][0]}")
    if kw["insights"]:
        body_parts.append(f"搞懂了：{kw['insights'][0]}")
    if kw["multi_project"]:
        body_parts.append(f"同時跑著 {len(kw['projects'])} 個專案：{' / '.join(kw['projects'][:3])}")

    body = "\n\n".join(body_parts) if body_parts else f"在 {kw['project_primary']} 上推進了一步。"

    # 結尾互動句
    endings = [
        "你也遇過這種坑嗎？",
        "有在用 Claude Code 的嗎？來聊聊各自的用法。",
        "每天一小步，不知道哪天會突然跳一大步。",
        "AI 協作真的讓我覺得一個人也能做很多事。",
        "有什麼 AI 工具是你離不開的？",
    ]
    # 根據角度選結尾
    angle = kw["angles"][0] if kw["angles"] else ""
    if "工具" in angle:
        ending = "有什麼 AI 工具是你現在離不開的？"
    elif "學習" in angle:
        ending = "學 AI 工具最快的方式就是天天用它做真實的事。"
    else:
        ending = random.choice(endings)

    # hashtag
    tag_map = {
        "🌗 Life OS": "#LifeOS", "📊 Dashboard": "#Dashboard",
        "🔐 OAuth": "#GoogleOAuth", "🔌 MCP": "#MCPServer",
        "⚡ Skill": "#ClaudeSkill", "📢 廣告代理": "#MarTech",
        "🐍 腳本": "#Python", "🌐 API": "#API",
        "🚀 部署": "#Deploy", "🐛 修復": "#BugFix",
        "✨ 新功能": "#NewFeature", "💻 開發": "#SideProject",
    }
    hashtags = [tag_map[t] for t in kw["tags"] if t in tag_map]
    hashtags = list(dict.fromkeys(hashtags + ["#ClaudeCode", "#AI工作流"]))[:3]

    return f"""{hook}

{body}

{ending}

{' '.join(hashtags)}"""


# ── 小紅書模板 ──────────────────────────────────────
def suggest_xhs_titles(sessions: list) -> list:
    """
    生成 3 個小紅書標題變體（A/B 測試用）
    回傳：[(標籤, 標題文字, 評分說明), ...]
    """
    kw = _extract_keywords(sessions)
    summary   = kw["summaries"][0]  if kw["summaries"]  else ""
    insight   = kw["insights"][0]   if kw["insights"]   else ""
    challenge = kw["challenges"][0] if kw["challenges"] else ""
    proj      = kw["project_primary"]

    titles = []

    # 公式 1：情緒/結果 | 身份 | 場景
    if insight:
        short = insight[:20].rstrip("，。")
        titles.append(("公式①", f"{short}，原來這麼簡單 | 設計師用 AI 接案日記", "情緒+結果型"))
    elif summary:
        short = summary[:18].rstrip("，。")
        titles.append(("公式①", f"用 AI {short} | 接案日記", "結果型"))
    else:
        titles.append(("公式①", f"用 AI 打造 {proj} | 一個人的開發日記", "結果型"))

    # 公式 2：數字 / 時間感
    if challenge:
        titles.append(("公式②", f"踩了 N 個坑才搞定的事 | {proj} 開發記錄", "踩坑共鳴型"))
    else:
        titles.append(("公式②", f"每天用 AI 工作是什麼感覺 | 第 N 天記錄", "日記連載型"))

    # 公式 3：身份認同 / 受眾呼喚
    titles.append(("公式③", f"不寫程式也能 build 這個 | Claude Code 真實使用心得", "受眾呼喚型"))

    return titles


def _generate_xiaohongshu(kw: dict) -> str:
    """小紅書：結構化五段式（📌💡🤔✅🏷️）"""

    # 標題（選最適合的一個）
    titles = suggest_xhs_titles([])  # fallback
    title = titles[0][1] if titles else f"用 AI 推進 {kw['project_primary']}"
    # 用實際 kw 覆蓋
    if kw["insights"]:
        short = kw["insights"][0][:20].rstrip("，。")
        title = f"{short}，原來這麼簡單 | 設計師 AI 工作日記"
    elif kw["summaries"]:
        title = f"用 AI {kw['summaries'][0][:18].rstrip('，。')} | 接案日記"

    # 📌 今天做了什麼
    if kw["summaries"]:
        what = "；".join(kw["summaries"][:2])
    elif kw["commits"]:
        what = "，".join(kw["commits"][:2])
    else:
        what = f"持續推進 {kw['project_primary']}"
    proj_context = (
        f"今天同時推進了 {len(kw['projects'])} 個專案：{' / '.join(kw['projects'][:3])}"
        if kw["multi_project"] else f"今天專注在 {kw['project_primary']}"
    )

    # 💡 最大收穫
    if kw["insights"]:
        discovery = kw["insights"][0]
    elif "OAuth" in str(kw["tags"]):
        discovery = "搞懂 Google OAuth 的完整流程，以後再也不怕授權問題了"
    elif "Dashboard" in str(kw["tags"]):
        discovery = "視覺化真的讓資訊更好消化，dashboard 讓工作狀態一目瞭然"
    else:
        discovery = "每次做完一塊，系統就又完整了一點"

    # 🤔 遇到的坑
    if kw["challenges"]:
        pain = kw["challenges"][0]
    else:
        pain = "環境配置永遠是最煩的部分，但搞定之後就爽了"

    # 心情標記
    mood_str = f"今天心情：{kw['moods'][0]}" if kw["moods"] else ""

    # hashtag 分層：行業 + 泛話題 + 情境
    tag_map = {
        "🌗 Life OS": "#個人系統", "📊 Dashboard": "#Dashboard開發",
        "🔐 OAuth": "#GoogleAPI", "🔌 MCP": "#MCPServer",
        "📢 廣告代理": "#MarTech", "🐍 腳本": "#Python開發",
        "🌐 API": "#API串接", "🚀 部署": "#自動化部署",
        "🐛 修復": "#Debug日記", "✨ 新功能": "#功能上線",
    }
    industry_tags = [tag_map[t] for t in kw["tags"] if t in tag_map][:2]
    broad_tags    = ["#ClaudeCode", "#AI工作流"]
    context_tags  = ["#接案日記", "#設計師日常"]
    all_tags = " ".join(list(dict.fromkeys(industry_tags + broad_tags + context_tags))[:5])

    return f"""【{title}】

📌 今天做了什麼
{proj_context}。{what}。

💡 最大收穫
{discovery}。

🤔 遇到的坑
{pain}。

✅ 今日小結
{mood_str}
雖然看起來只是一小步，但每天累積真的不一樣。用 AI 當協作夥伴之後，感覺一個人的產出能頂以前好幾倍。

如果你也在用 Claude Code 或其他 AI 工具，歡迎留言分享你的用法！

🏷️ {all_tags}"""


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
    """有 API Key 時使用 Claude API 生成（品質更高，使用結構化素材）"""
    import anthropic

    kw = _extract_keywords(sessions)

    # 組裝結構化素材（比直接丟 commits 有效得多）
    context_parts = []
    for s in sessions:
        parts = [f"【專案】{s.get('project_name', '')}"]
        if s.get("summary"):    parts.append(f"【做了什麼】{s['summary']}")
        if s.get("challenge"):  parts.append(f"【遇到的坑】{s['challenge']}")
        if s.get("insight"):    parts.append(f"【最大突破】{s['insight']}")
        if s.get("mood"):       parts.append(f"【心情】{s['mood']}")
        if s.get("post_angle"): parts.append(f"【發文角度】{s['post_angle']}")
        context_parts.append("\n".join(parts))

    context = "\n\n---\n\n".join(context_parts)
    client  = anthropic.Anthropic(api_key=api_key)

    if format_type == "threads":
        system = """你是台灣的設計師/接案工作者，每天用 Claude Code 做開發，在 Threads 上分享真實工作狀態。

寫作規則：
1. 第一行是 HOOK，必須讓人想點「更多」。公式：[踩坑/突破/數字/反常識] + 短暫停頓。絕對不用「今天又跟 AI 工作了一整天」這種廢話開頭。
2. 故事弧：坑/挑戰 → 過程 → 結果/學到的 → 給讀者的問句
3. 口語、真實，有點自我嘲解，不賣弄技術
4. 150-300 字繁體中文
5. 結尾一句互動問句，不要 "歡迎分享" 這種無聊的
6. 最後 2-3 個 hashtag（不要塞滿）"""
    else:
        system = """你是在小紅書分享 AI 工作流的設計師，受眾是 25-35 歲的設計師/接案族。

寫作規則：
1. 標題用公式：[情緒/結果] | [身份] | [場景]，要讓人一眼就想點進來
2. 正文結構嚴格遵守：📌今天做了 → 💡最大收穫（要具體，不是廢話） → 🤔遇到的坑（細節！） → ✅今日小結
3. 200-350 字繁體中文，emoji 分段讓人好讀
4. 最後 5 個 hashtag 分三層：行業標籤×2 + 泛話題×2 + 情境×1
5. 結尾問句引導留言互動
6. 不說「一個人可以頂以前好幾倍」這種空話，要具體說做了什麼"""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=700,
        system=system,
        messages=[{"role": "user", "content": f"根據以下活動素材生成文章：\n\n{context}"}],
    )
    return resp.content[0].text
