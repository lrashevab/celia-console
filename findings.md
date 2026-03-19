# Findings — Life OS

## 用戶需求確認 (2026-03-19)

### Google 帳號策略
- 工作帳號 ≠ 個人帳號 → 需雙 OAuth credential
- 統一方式：各自存 `config/token_work.json` / `config/token_personal.json`
- 可在同一個 Streamlit app 管理，session_state 區分帳號

### 資料來源
- 工作：Google Sheets（工作帳號）
- 個人：Google Sheets（個人帳號）+ 本地 Markdown（日記，不上雲）

### 工作指標需求
- 客戶數、pipeline 狀態
- 任務項目：分 internal / client / external 三類
- 代辦事項（與客戶、內部、外發）
- 會議紀錄 + Google Calendar 日程建立

### 個人指標需求（全部）
- 閱讀進度、健身紀錄、習慣完成率
- 財務追蹤、個人目標里程碑、私人日記摘要

### /meeting 模式
- 輸入：貼上逐字稿或條列重點
- 輸出：結構化 JSON → Google Calendar 事件 + 追蹤事項

### 隔離強度
- Level C 硬隔離：個人資料絕不進工作 context
- 個人資料 AI 分析需明確用戶授權

### Sheets Schema（Work）
- Clients: client_id, name, status, contact, industry, created_date
- Tasks: task_id, client, title, type, status, due_date, owner
- ToDos: todo_id, type(internal/client/external), title, due_date, status
- Meetings: meeting_id, date, client, title, calendar_link

### Sheets Schema（Personal）
- Reading: book, pages_total, pages_read, status
- Fitness: date, activity, duration_min
- Habits: date, habit, completed
- Finance: date, category, type(income/expense), amount
- Goals: goal, category, target_date, progress_pct
