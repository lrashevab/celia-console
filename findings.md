# Life OS 環境健康報告

> 生成時間：2026-03-22
> 審查範圍：requirements.txt、.env.example、pages/ render()、TODO/NotImplementedError

---

## 1. requirements.txt — 套件版本鎖定狀態

**結論：⚠️ 所有套件使用 `>=` 而非精確版本鎖定，已安裝版本大幅超前最低要求。**

| 套件 | requirements.txt 要求 | 實際安裝版本 | 風險 |
|------|----------------------|-------------|------|
| streamlit | `>=1.32.0` | `1.55.0` | 中（跨大版本，API 可能異動） |
| google-auth | `>=2.28.0` | `2.49.1` | 低 |
| google-auth-oauthlib | `>=1.2.0` | `1.3.0` | 低 |
| google-auth-httplib2 | `>=0.2.0` | `0.3.0` | 低 |
| google-api-python-client | `>=2.120.0` | `2.193.0` | 低 |
| pandas | `>=2.2.0` | `2.3.3` | 低 |
| plotly | `>=5.20.0` | `6.6.0` | 中（跨大版本） |
| anthropic | `>=0.25.0` | `0.86.0` | 高（跨大版本，SDK 介面已大幅更動） |
| python-dotenv | `>=1.0.0` | `1.0.1` | 低 |

**建議行動**：執行 `pip freeze > requirements.txt` 鎖定當前環境，或改用 `==` 精確版本 + `pip-tools` 管理。

---

## 2. .env.example 變數完整性

**結論：⚠️ 缺少 2 個程式碼中實際使用的變數。**

### 已涵蓋（.env.example 有列、程式碼有用）

| 變數 | 使用位置 |
|------|---------|
| `ANTHROPIC_API_KEY` | `config/settings.py`, `services/meeting_processor.py`, `services/llm_client.py`, `services/content_generator.py` |
| `WORK_SPREADSHEET_ID` | `config/settings.py` → `ACCOUNTS["work"]["spreadsheet_id"]` |
| `WORK_CALENDAR_ID` | `config/settings.py` → `ACCOUNTS["work"]["calendar_id"]` |
| `PERSONAL_SPREADSHEET_ID` | `config/settings.py` → `ACCOUNTS["personal"]["spreadsheet_id"]` |
| `PERSONAL_CALENDAR_ID` | `config/settings.py` → `ACCOUNTS["personal"]["calendar_id"]` |
| `DIARY_LOCAL_PATH` | `config/settings.py` → `DIARY_PATH` |

### ❌ 缺少（程式碼有用、.env.example 未列）

| 缺少的變數 | 使用位置 | 說明 |
|-----------|---------|------|
| `GEMINI_API_KEY` | `config/settings.py`、`services/llm_client.py`、`services/content_generator.py` | LLM 主力（Gemini-first 策略），是核心功能變數 |
| `TAVILY_API_KEY` | `config/settings.py:TAVILY_API_KEY` | 文化雷達搜尋，settings.py 有讀取但目前無使用端 |

**建議行動**：補充 `.env.example`：
```
# Google Gemini（免費，LLM 主力）
GEMINI_API_KEY=AIzaSy...

# Tavily 搜尋（文化雷達）
TAVILY_API_KEY=tvly-...
```

---

## 3. pages/ render() 函式存在性

**結論：✅ 全部 6 個頁面皆可正常 import，且都有 render() 函式。**

| 檔案 | render() | import 狀態 |
|------|----------|-------------|
| `pages/home.py` | ✅ | ✅ OK |
| `pages/work_dashboard.py` | ✅ | ✅ OK |
| `pages/personal_dashboard.py` | ✅ | ✅ OK |
| `pages/content_studio.py` | ✅ | ✅ OK |
| `pages/meeting_page.py` | ✅ | ✅ OK |
| `pages/calendar_page.py` | ✅ | ✅ OK |

備注：`meeting_page` 和 `calendar_page` 未掛載於 `app.py` PAGES 路由，僅能透過直接呼叫 `render()` 存取。

---

## 4. TODO / NotImplementedError 位置

**結論：⚠️ 共 1 處 NotImplementedError（預期行為，有文件說明）。**

| 位置 | 類型 | 內容 |
|------|------|------|
| `services/xhs_pipeline.py:242–243` | `NotImplementedError` | `# TODO: 接入 XHS MCP`，`raise NotImplementedError("XHS API 尚未配置，請手動複製貼上發佈")` |

此為已知 stub，對應 Phase 2 規劃（XHS 半自動化）。呼叫方應 catch 此例外並顯示提示。

---

## 總結

| 項目 | 狀態 | 優先級 |
|------|------|--------|
| requirements.txt 版本鎖定 | ⚠️ 未鎖定 | 中 |
| .env.example 缺 `GEMINI_API_KEY` | ❌ 缺漏 | 高（影響 LLM 功能說明） |
| .env.example 缺 `TAVILY_API_KEY` | ⚠️ 缺漏 | 低（功能未接入） |
| pages render() 完整性 | ✅ 全數正常 | — |
| meeting_page / calendar_page 未掛載路由 | ⚠️ 孤兒頁面 | 低 |
| xhs_pipeline.py NotImplementedError | ⚠️ 已知 stub | Phase 2 |
