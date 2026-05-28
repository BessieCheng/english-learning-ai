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
