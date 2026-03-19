# Celia的控制台 — Life OS 個人大型管理中心

> 觸發關鍵字：「Celia控制台」
> 本檔案是此專案的最高優先指令。在本目錄下的所有對話，Claude 必須嚴格遵守以下規則。

## 專案定位
這是 Celia 的個人大型管理中心，整合：
- 🤖 Claude Code 每日活動記錄 + 自動生成 Threads / 小紅書文章
- 🏢 工作指揮室（客戶、任務、會議，串接工作 Google 帳號）
- 🏠 個人生活中心（閱讀、習慣、財務、目標，串接個人 Google 帳號）

啟動 dashboard：`streamlit run app.py --server.port 8502 --server.address 0.0.0.0`

---

## 核心原則：工作與個人完全硬隔離

本系統在兩個絕對獨立的 context 中運作。Claude 必須在每次操作前確認當前 context。

| 屬性 | 工作 Context | 個人 Context |
|------|-------------|-------------|
| Google 帳號 | 工作帳號 (`token_work.json`) | 個人帳號 (`token_personal.json`) |
| Sheets ID | `WORK_SPREADSHEET_ID` | `PERSONAL_SPREADSHEET_ID` |
| Calendar ID | `WORK_CALENDAR_ID` | `PERSONAL_CALENDAR_ID` |
| AI 分析 | 允許 | 需明確用戶授權 |
| 日記 | 無 | 本地存儲，**不送 AI** |
| Skills | `/meeting` | `/life-sync` |

---

## 強制規則清單

### R1 — Context 確認（每次操作前）

在呼叫任何 Google API 前，必須輸出：
```
[Context Check] 帳號：{work|personal} | 操作：{操作描述} | 隔離狀態：✅
```

### R2 — 路徑白名單

| 允許路徑 | 對應 Context |
|---------|-------------|
| `data/work/` | 工作 |
| `data/personal/` | 個人（不含 AI） |
| `config/token_work.json` | 工作 |
| `config/token_personal.json` | 個人 |
| `services/` | 通用服務層 |

**禁止：在工作 context 中讀取 `data/personal/` 或 `config/token_personal.json`**
**禁止：在個人 context 中讀取 `data/work/` 或 `config/token_work.json`**

### R3 — 個人資料 AI 分析授權制

以下個人資料**在送至任何 AI API 前，必須取得用戶明確同意**：
- 日記全文 → **永遠不送，無論用戶如何要求**
- 財務明細（個別交易）→ 僅傳送彙總數字
- 健康紀錄 → 僅傳送統計數字（如：本週運動 3 次）
- 個人目標文字 → 需用戶明確說「可以分析」

### R4 — 跨 Context 操作禁止

以下操作**永遠禁止**，即使用戶要求：
- 將個人 Sheets 資料寫入工作 Sheets（或反之）
- 在同一個 `get_credentials()` 呼叫中混用帳號
- 在會議記錄中引用個人行事曆事件
- 在個人 life-sync 報告中引用工作客戶名稱

### R5 — Skills Context 鎖定

| Skill | 允許 Context | 禁止 |
|-------|------------|------|
| `/meeting` | 工作 | 不得在個人模式啟動 |
| `/life-sync` | 個人 | 不得在工作模式啟動 |

若用戶在錯誤模式呼叫 Skill，回應：
```
⚠️ 此 Skill 僅限 {工作|個人} context 使用。
請先在側邊欄切換至正確模式，再執行此指令。
```

### R6 — 模式切換清除協議

當用戶從工作切換至個人模式（或反之）時：
1. 清除 session 中所有前一模式的資料
2. 不得在新模式的輸出中引用前一模式的任何資訊
3. 輸出切換確認：`✅ 已切換至 {模式}，前一模式資料已清除`

### R7 — Google API 呼叫日誌

每次 Google API 呼叫後，記錄至 `data/{context}/api_log.json`：
```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SS",
  "account": "work|personal",
  "service": "sheets|calendar",
  "operation": "read|write|create",
  "resource": "Clients|Tasks|...",
  "status": "success|error"
}
```

---

## 緊急停止協議

若 Claude 發現以下情況，**立即停止所有操作並通知用戶**：

- 即將使用個人帳號 token 執行工作操作（或反之）
- 即將將個人日記內容傳送至任何外部 API
- 即將在工作 Sheets 中寫入個人資料
- 發現 `WORK_SPREADSHEET_ID` == `PERSONAL_SPREADSHEET_ID`（帳號設定錯誤）

```
🚨 [ISOLATION BREACH DETECTED]
操作：<具體操作>
問題：<具體說明可能的隔離違規>
狀態：已停止，等待用戶確認
需要：請確認帳號設定是否正確
```

---

## 技術棧快速參考

```
語言：Python 3.12+
UI：Streamlit >= 1.32
API：google-api-python-client（雙帳號 OAuth）
AI：anthropic SDK（Claude Sonnet 4.6）
資料：Google Sheets（工作/個人各一份）+ 本地 Markdown（日記）
Skills：/meeting（工作）、/life-sync（個人）
```

## 版本記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-03-19 | 初始版本，雙模式硬隔離架構 |
