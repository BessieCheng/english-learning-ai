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
- **`.env` / Secrets**：`.env` 不進 git；GEMINI_API_KEY 等金鑰在 Streamlit Cloud 的 Settings → Secrets 設定。除 GEMINI_API_KEY 外，勿更動其他金鑰。

請用中文回答
