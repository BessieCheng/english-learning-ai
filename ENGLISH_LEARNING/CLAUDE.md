# English Learning AI System - Project Rules

## 1. System Architecture & Tech Stack
- **Frontend/UI**: Streamlit (Python-based web framework)
- **Speech-to-Text**: OpenAI Whisper API
- **AI Analyst**: Anthropic Claude API (structured JSON responses)
- **Database**: SQLite (local storage for errors and vocabulary)
- **Review System**: Spaced Repetition System (SRS) based on SM-2 algorithm

## 2. Development Strategy (Strict Rules)
- **WIP = 1**: You must implement ONLY ONE module at a time. Do not move to the next phase until the current one is tested and working.
- **Incremental Steps**: Always build the core Python logic first, verify it in the terminal, and then wrap it into the Streamlit interface.
- **Simplicity**: Code must be beginner-friendly, clean, and well-commented since the user is a non-technical beginner.
- **Ask for Clarification**: If you encounter any ambiguity, missing API variables, or architectural choices, STOP and ask the user for confirmation. DO NOT make assumptions or decide on your own.

## 3. Core Modules Order
1. Phase 1: Audio File Upload & Whisper Transcription
2. Phase 2: Claude API Grammar & Pronunciation Analysis (Outputting JSON)
3. Phase 3: SQLite Database Integration (Saving data)
4. Phase 4: Streamlit Web UI Layout
5. Phase 5: SRS Vocabulary Daily Review System

## 4. Deployment & Git Workflow (MANDATORY)
- **所有更正都必須上雲端、推到 GitHub**：本 App 部署在 Streamlit Cloud，只會從 GitHub 更新。**禁止把任何修改只留在本地端**。每次改完一定要 `git commit` + `git push origin main`，雲端才會更新。
- **All fixes must reach the cloud**: After every edit, immediately `git commit` and `git push origin main`. Never leave changes local-only — Streamlit Cloud only redeploys from GitHub.
- **設計/視覺改動先給預覽再推**：UI、配色、版面、字體、按鈕樣式等視覺改動，先用 `design-preview` skill 產生靜態 HTML 截圖給使用者確認，OK 後再推（Streamlit 自身截圖不可靠）。
- **推之前先驗證**：用 `streamlit-verify` skill（`.claude/skills/streamlit-verify/verify.sh`）做語法＋啟動＋HTTP 200 檢查，再 commit + push。
- **`.env.local` / Secrets**：所有 API 密鑰放 `.env.local`，此檔必須在第一次 push 前加入 `.gitignore`，禁止使用裸露的 `.env`。腳本用 `load_dotenv(".env.local")`。Streamlit Cloud 金鑰在 Settings → Secrets 設定，除 GEMINI_API_KEY 外勿更動其他金鑰。

請用中文回答

## 5. CSS 修改規則（強制）
- **加 overflow:hidden / height 限制前**，先問自己「這個元素裡有沒有多行文字」，有則禁用
- **修 CSS 選擇器深度前**，確認同一結構在三個主題（zen / animal / bold）裡都有對應修正
- **CSS 改動必須用 design-preview 截圖驗證**，不能只靠 streamlit-verify HTTP 200

## 6. PostgreSQL 型別規則
- TIMESTAMPTZ 欄位從 psycopg2 回傳的是 **datetime 物件，不是字串**
- 凡是對時間欄位切片或格式化，必須先 `str(field or '')[:N]`，不能直接 `field[:N]`

## 7. 跨檔案介面修改規則
- 修改任何函式簽名（加/改/移除參數）後，必須同步更新所有呼叫端
- push 前執行 `bash .claude/skills/streamlit-verify/verify.sh`（已含函式簽名靜態驗證）

## 8. 部署後確認清單（push 完等 1-2 分鐘再執行）

**每次 push 後，請在 Streamlit Cloud 上點以下功能確認沒壞：**

| # | 頁面 | 操作 | 預期結果 |
|---|------|------|---------|
| 1 | 翻譯練習 | 點「問題を出す」/ 點「出題」 | 出現日文或中文題目，無錯誤訊息 |
| 2 | 今日單字 | 開啟單字清單，看每個單字下方 | 有日文或中文翻譯（非長段說明） |
| 3 | 新聞搜尋 | 展開「已儲存新聞」的一筆記錄 | 不出現 TypeError，顯示日期 |
| 4 | 上傳分析 | 確認頁面正常載入 | 無紅色錯誤框 |

**只在改動以下類型時才需要全部測：**
- 函式簽名改動 → 一定要測對應頁面
- CSS 改動 → 一定要看視覺是否正常
- 資料庫欄位相關 → 一定要測新聞、單字頁面
