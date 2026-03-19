---
name: meeting
description: >
  工作 context 專屬（celia@sirius-brand.com）。接收會議逐字稿或重點條列，
  使用 Claude 結構化後自動建立 Google Calendar 事件與追蹤事項。
  在 Claude Code 對話中直接使用 MCP Calendar/Gmail 工具操作工作帳號。
  TRIGGER: 用戶說「開會記錄」「會議摘要」「幫我記錄這次會議」或 /meeting。
user-invocable: true
allowed-tools: "Bash, Read, Write"
---

# /meeting — 會議記錄自動化（工作帳號：celia@sirius-brand.com）

> ⚠️ 本 skill 僅在工作 context 執行。
> 📅 Calendar 操作使用 MCP Google Calendar 工具（已連線工作帳號）。
> ✉️ 摘要寄送使用 MCP Gmail 工具。

## 執行流程

### Step 1：確認 Context

```
[Context Check] 帳號：celia@sirius-brand.com（工作）| 隔離狀態：✅
```

### Step 2：請用戶貼上逐字稿

```
請貼上會議逐字稿或條列重點。格式不限，可以是：
- 完整逐字稿
- 條列重點（決策、待辦、參與者）
- 簡短備忘
```

### Step 3：Claude 結構化分析

收到逐字稿後，自行分析並產出以下結構（繁體中文）：

```json
{
  "title": "會議主題（10字以內）",
  "date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "duration_hours": 1,
  "attendees": ["參與者1", "參與者2"],
  "client": "客戶名稱（若為內部會議則填 internal）",
  "summary": "三句話摘要",
  "decisions": ["決策1", "決策2"],
  "action_items": [
    {"task": "任務", "owner": "負責人", "deadline": "YYYY-MM-DD"}
  ]
}
```

確認後繼續下一步。

### Step 4：建立 Google Calendar 事件（MCP）

使用 `gcal_create_event` MCP 工具：

```
calendar_id: celia@sirius-brand.com
summary: [meeting.title]
start: [date]T[start_time]:00+08:00
end: [date]T[end_time]:00+08:00（依 duration_hours 計算）
description:
  📋 [summary]

  ✅ 決策：
  • [decisions]

  📌 追蹤事項：
  • [owner] — [task]（截止：[deadline]）
attendees: [attendees]
```

### Step 5：為每個 Action Item 建立提醒事件（MCP）

對每個 action_item，使用 `gcal_create_event` 建立全天事件：

```
summary: 📌 [owner] — [task]
start: [deadline]（全天事件）
end: [deadline]
description: 來自會議：[meeting.title]
```

### Step 6：產出摘要給用戶

```
✅ 會議記錄完成

📋 主題：[title]
📅 [date] [start_time]（[duration_hours] 小時）
👥 [attendees]
🏷️ 客戶：[client]

摘要：[summary]

決策事項：
• [decision]

追蹤事項（已加入 Calendar 提醒）：
• [owner] — [task]（截止：[deadline]）

📅 主要事件已加入 celia@sirius-brand.com 行事曆
```

### Step 7（選用）：寄出會議摘要 Gmail 草稿

若用戶想寄出摘要，使用 `gmail_create_draft` MCP 工具：

```
to: [attendees emails]
subject: [會議記錄] [title] — [date]
body: 完整結構化摘要
```

## 安全規則

- 所有 MCP 工具操作的是工作帳號（celia@sirius-brand.com）
- 不得讀取 data/personal/ 目錄
- 不得呼叫個人 Gmail 草稿工具寄送工作會議記錄
- 若 MCP Calendar 操作失敗，退回 Python 腳本模式並告知用戶
