---
name: life-sync
description: >
  個人 context 專屬（個人 Google 帳號，已透過 MCP 連線）。整合個人目標、
  習慣清單與私人資料庫，產出本週個人執行計畫。
  TRIGGER: 用戶說「同步個人目標」「更新習慣」「個人週計畫」或 /life-sync。
  AI 分析個人資料前需明確授權。
user-invocable: true
allowed-tools: "Bash, Read, Write"
---

# /life-sync — 個人生活同步

> ⚠️ 本 skill 僅在個人 context 執行。不得讀取工作 Sheets 或工作 Calendar。
> ⚠️ AI 分析個人資料前，必須取得用戶明確同意。

## 使用方式

- `/life-sync` → 讀取個人 Sheets，產出本週生活執行計畫
- `/life-sync goals` → 僅更新目標進度
- `/life-sync habits` → 僅顯示習慣達成狀況

## 執行步驟

### Step 0：Context 確認

```
⚠️ 即將進入個人 context。
本次操作將讀取您的個人 Google Sheets（個人帳號）。
資料不會與工作 context 共享。
確認繼續？(y/n)
```

等待用戶回覆 y 再繼續。

### Step 1：讀取個人資料

```bash
cd /root/life-os
python3 -c "
from services.google_sheets import get_reading, get_habits, get_goals, get_fitness, get_finance
import json

data = {
    'reading': get_reading().to_dict('records'),
    'habits_today': get_habits().tail(7).to_dict('records'),
    'goals': get_goals().to_dict('records'),
    'fitness_week': get_fitness().tail(7).to_dict('records'),
}
print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
" 2>/dev/null
```

### Step 2：AI 分析（需用戶授權）

詢問用戶：
```
是否允許 AI 分析您的個人目標與習慣資料，產出建議？
（財務明細與日記內容不會送出）
(y/n)
```

若用戶同意，產出以下分析：

```
📊 本週個人狀態報告

📚 閱讀：[進度摘要]
🏋️ 運動：[本週次數與時長]
✅ 習慣達成率：[%]
💰 本月財務：[收支概況，無明細]
🎯 目標進度：[里程碑狀態]

本週建議行動：
1. [具體建議1]
2. [具體建議2]
3. [具體建議3]
```

### Step 3：更新目標進度

若用戶想更新進度，詢問：
```
哪個目標需要更新進度？（輸入目標名稱與新進度 %）
```

```bash
# 更新 Goals Sheet（示例）
cd /root/life-os
python3 -c "
# TODO: 用戶提供的目標名稱與進度
print('請在 Google Sheets 中手動更新，或提供 API 寫入指令')
"
```

### Step 4：私人日記（本地，絕不送 AI）

```bash
# 列出本地日記
ls /root/life-os/data/personal/diary/ 2>/dev/null || echo "（尚無日記）"
```

日記摘要僅顯示條數與最近日期，內容絕不送出至任何 API。

## 安全規則

- 僅使用 `account='personal'` 呼叫 Google API
- 不得讀取 `config/token_work.json`
- 日記檔案（`data/personal/diary/`）內容不得傳送至 AI API
- 財務明細（各筆交易）不得傳送至 AI，僅傳送彙總數字
- 健康數據不得傳送至第三方服務
