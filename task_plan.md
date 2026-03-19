# Task Plan — Life OS 雙模式自動化管理系統

## Goal
建立一個 Streamlit 儀表板，切換工作（廣告行銷）與個人生活模式，串接雙 Google 帳號，完全硬隔離。

## Architecture Decision
- 單一 app.py + sidebar 切換模式
- 工作帳號 / 個人帳號各自 OAuth token
- /meeting skill → 工作 context only
- /life-sync skill → 個人 context only
- 個人資料 AI 分析需明確授權

## Phases

### Phase 1 — Infrastructure [complete]
- [x] 建立目錄結構
- [x] task_plan.md / findings.md / progress.md
- [ ] CLAUDE.md Standing Orders
- [ ] requirements.txt
- [ ] .env.example

### Phase 2 — Google Auth 雙帳號 [in_progress]
- [ ] services/google_auth.py — 統一 OAuth 入口，支援 work/personal
- [ ] config/settings.py — Sheets ID、Calendar ID 設定

### Phase 3 — Services Layer []
- [ ] services/google_sheets.py — 讀取 Work Sheets（Clients/Tasks/ToDos/Meetings）
- [ ] services/google_calendar.py — 建立 / 讀取 Google Calendar 事件
- [ ] services/meeting_processor.py — 逐字稿 → 結構化 → 寫入 Calendar

### Phase 4 — Work Dashboard []
- [ ] pages/work_dashboard.py
  - 客戶數總覽卡片
  - 任務表格（internal/external/client 分類）
  - 待辦清單（三類型 tab）
  - 會議記錄輸入 + 一鍵建立 Google Calendar

### Phase 5 — Personal Dashboard []
- [ ] pages/personal_dashboard.py
  - 閱讀進度、健身紀錄、習慣完成率
  - 財務追蹤（收支圖）
  - 個人目標里程碑
  - 私人日記摘要（本地，不送 AI）

### Phase 6 — Skills []
- [ ] .claude/skills/meeting/SKILL.md
- [ ] .claude/skills/life-sync/SKILL.md

### Phase 7 — CLAUDE.md []
- [ ] 專屬 Standing Orders，強制 context 隔離

### Phase 8 — Claude Code 管理中心升級 [in_progress]
**目標**：入口頁 + 每日活動記錄 + 自動內容生成（Threads / 小紅書）

- [x] P8-1：`data/claude_log.json` + `scripts/log_session.py`（Stop hook 腳本）
- [x] P8-2：設定 Stop hook（`~/.claude/settings.json` hooks.Stop）
- [x] P8-3：`pages/home.py`（專案卡片 + 活動 timeline + 生成文章 tab）
- [x] P8-4：`services/content_generator.py`（模板引擎，無需 API Key）
- [x] P8-5：整合 `app.py`（新增 Claude Code 指揮中心入口）
- [x] P8-6：Stop hook 自動摘要升級（今日 commits + task_plan phases + changed_files）

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| OOB OAuth 已棄用 | 1 | 改用 localhost redirect + 手動貼 URL |
