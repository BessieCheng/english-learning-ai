# =============================================================
# database.py
# 功能：建立 SQLite 資料庫，並提供存入、查詢分析結果的功能。
#       SQLite 是一種輕量的本機資料庫，不需要安裝任何伺服器，
#       所有資料都存在一個 .db 檔案裡。
# 使用方式：在終端機執行 → python src/database.py
# =============================================================

import sqlite3    # Python 內建的 SQLite 套件，不需要額外安裝
import json
import os
from datetime import datetime, date

# ── 資料庫檔案的存放路徑 ──────────────────────────────────────
# 資料庫檔案會建立在專案根目錄，叫做 english_learning.db
DB_PATH = "english_learning.db"


def get_connection():
    """建立並回傳資料庫連線。"""
    # connect() 會自動建立檔案（如果不存在的話）
    conn = sqlite3.connect(DB_PATH)
    # row_factory 讓查詢結果可以用欄位名稱來存取（像字典一樣）
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """
    初始化資料庫：建立所有需要的資料表。
    如果資料表已存在，就不會重複建立（IF NOT EXISTS）。
    """
    conn = get_connection()
    cursor = conn.cursor()  # cursor 是用來執行 SQL 指令的工具

    # ── 建立 sessions 表（每次分析的主記錄）──────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            audio_file      TEXT    NOT NULL,
            transcript      TEXT    NOT NULL,
            score           INTEGER,
            summary         TEXT,
            analysis_json   TEXT,
            diarized_json   TEXT,
            created_at      TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)
    # 舊資料庫升級：若缺欄位則補上
    for col in ("analysis_json", "diarized_json"):
        try:
            cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col} TEXT")
        except Exception:
            pass
    # 欄位說明：
    # id         → 自動編號（每筆記錄的唯一識別碼）
    # audio_file → 音檔名稱
    # transcript → Whisper 轉出的逐字稿
    # score      → Gemini 給的整體評分（1-10）
    # summary    → Gemini 的分析總結
    # created_at → 記錄建立時間

    # ── 建立 grammar_errors 表（文法錯誤記錄）────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grammar_errors (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            original    TEXT    NOT NULL,
            correction  TEXT    NOT NULL,
            explanation TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    # session_id → 對應到哪一次 session（外鍵關聯）

    # ── 建立 vocabulary 表（單字本，含 SRS 欄位）─────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER,
            word            TEXT    NOT NULL,
            part_of_speech  TEXT,
            definition      TEXT,
            example         TEXT,
            source          TEXT    DEFAULT 'vocabulary',
            next_review     TEXT    DEFAULT (date('now', 'localtime')),
            interval_days   INTEGER DEFAULT 1,
            ease_factor     REAL    DEFAULT 2.5,
            review_count    INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    # 舊資料庫升級：補缺少的欄位
    for col, default in [("source", "'vocabulary'"), ("part_of_speech", "NULL")]:
        try:
            cursor.execute(f"ALTER TABLE vocabulary ADD COLUMN {col} TEXT DEFAULT {default}")
        except Exception:
            pass

    # 修復舊版 session_id NOT NULL 問題：若 session_id 不允許 NULL 就重建表
    cursor.execute("PRAGMA table_info(vocabulary)")
    col_info = {row[1]: row[3] for row in cursor.fetchall()}  # name: notnull(1=NOT NULL)
    if col_info.get("session_id", 0) == 1:
        cursor.execute("ALTER TABLE vocabulary RENAME TO vocabulary_old")
        cursor.execute("""
            CREATE TABLE vocabulary (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      INTEGER,
                word            TEXT    NOT NULL,
                part_of_speech  TEXT,
                definition      TEXT,
                example         TEXT,
                source          TEXT    DEFAULT 'vocabulary',
                next_review     TEXT    DEFAULT (date('now', 'localtime')),
                interval_days   INTEGER DEFAULT 1,
                ease_factor     REAL    DEFAULT 2.5,
                review_count    INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        cursor.execute("""
            INSERT INTO vocabulary
                (id, session_id, word, part_of_speech, definition, example,
                 source, next_review, interval_days, ease_factor, review_count)
            SELECT
                id, session_id, word, part_of_speech, definition, example,
                source, next_review, interval_days, ease_factor, review_count
            FROM vocabulary_old
        """)
        cursor.execute("DROP TABLE vocabulary_old")

    conn.commit()
    conn.close()
    print(f"✅ 資料庫初始化完成：{DB_PATH}")


def save_session(audio_file, transcript, analysis, diarized=None):
    """
    把一次完整的分析結果存入資料庫。

    參數：
        audio_file  → 音檔名稱（字串）
        transcript  → 逐字稿（字串）
        analysis    → Gemini 分析結果（字典，來自 analyze.py）

    回傳：
        session_id  → 這筆記錄的 ID（整數）
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ── 步驟 1：存入主記錄（sessions 表）─────────────────────
    cursor.execute("""
        INSERT INTO sessions (audio_file, transcript, score, summary, analysis_json, diarized_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        audio_file,
        transcript,
        analysis.get("overall_score"),
        analysis.get("summary"),
        json.dumps(analysis, ensure_ascii=False),
        json.dumps(diarized, ensure_ascii=False) if diarized else None
    ))
    # ? 是佔位符號，防止 SQL Injection 安全漏洞
    # lastrowid 取得剛插入那筆資料的 ID
    session_id = cursor.lastrowid

    # ── 步驟 2：存入文法錯誤（grammar_errors 表）──────────────
    errors = analysis.get("grammar_errors", [])
    for err in errors:
        cursor.execute("""
            INSERT INTO grammar_errors (session_id, original, correction, explanation)
            VALUES (?, ?, ?, ?)
        """, (
            session_id,
            err.get("original"),
            err.get("correction"),
            err.get("explanation")
        ))

    # ── 步驟 3：存入單字（vocabulary 表）─────────────────────
    vocab_list = analysis.get("vocabulary_highlights", [])
    for v in vocab_list:
        cursor.execute("""
            INSERT INTO vocabulary (session_id, word, part_of_speech, definition, example, source)
            VALUES (?, ?, ?, ?, ?, 'vocabulary')
        """, (session_id, v.get("word"), v.get("part_of_speech"), v.get("definition"), v.get("example")))

    # ── 步驟 4：發音錯誤單字 ──────────────────────────────────
    for tip in analysis.get("pronunciation_tips", []):
        if isinstance(tip, dict) and tip.get("example"):
            word = tip["example"].split()[0].strip(".,!?\"'():").lower()
            if word:
                cursor.execute("""
                    INSERT INTO vocabulary (session_id, word, definition, example, source)
                    VALUES (?, ?, ?, ?, 'pronunciation')
                """, (session_id, word, tip.get("tip", ""), tip.get("example", "")))

    # ── 步驟 5：猶豫單字 ─────────────────────────────────────
    for hw in analysis.get("hesitant_words", []):
        if hw.get("word"):
            cursor.execute("""
                INSERT INTO vocabulary (session_id, word, part_of_speech, definition, example, source)
                VALUES (?, ?, ?, ?, ?, 'hesitant')
            """, (session_id, hw.get("word"), hw.get("part_of_speech"), hw.get("definition", ""), hw.get("example", "")))

    conn.commit()
    conn.close()

    print(f"💾 已存入資料庫（Session ID: {session_id}）")
    return session_id


def get_all_sessions():
    """
    查詢所有歷史分析記錄，由新到舊排序。
    回傳：list of dict
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    # 把每筆記錄轉成普通的字典，方便使用
    return [dict(row) for row in rows]


def delete_session(session_id):
    """
    刪除指定 session 及其所有相關的文法錯誤和單字記錄。
    參數：session_id → 要刪除的記錄 ID
    """
    conn = get_connection()
    cursor = conn.cursor()
    # 先刪除子表的關聯資料，再刪除主記錄
    cursor.execute("DELETE FROM grammar_errors WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM vocabulary WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def add_vocabulary_manually(word, definition, example="", part_of_speech=""):
    """手動新增單字到單字本。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO vocabulary (session_id, word, part_of_speech, definition, example, source)
        VALUES (NULL, ?, ?, ?, ?, 'manual')
    """, (word.strip(), part_of_speech.strip() or None, definition.strip(), example.strip()))
    conn.commit()
    conn.close()


def get_vocabulary_due_today():
    """
    查詢今天需要複習的單字（next_review <= 今天）。
    回傳：list of dict
    """
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()  # 取得今天日期，格式：YYYY-MM-DD
    cursor.execute("""
        SELECT * FROM vocabulary
        WHERE next_review <= ?
        ORDER BY next_review ASC
    """, (today,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_news_article(title, source, date_str, body, vocab_json=""):
    """儲存一篇新聞文章。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_news (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            source     TEXT,
            date_str   TEXT,
            body       TEXT,
            vocab_json TEXT,
            saved_at   TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    cursor.execute("""
        INSERT INTO saved_news (title, source, date_str, body, vocab_json)
        VALUES (?, ?, ?, ?, ?)
    """, (title, source, date_str, body, vocab_json))
    conn.commit()
    conn.close()


def get_saved_news():
    """回傳所有已儲存新聞，由新到舊。"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM saved_news ORDER BY saved_at DESC")
        rows = cursor.fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(row) for row in rows]


def delete_saved_news(news_id):
    """刪除指定新聞。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM saved_news WHERE id = ?", (news_id,))
    conn.commit()
    conn.close()


def get_all_vocabulary():
    """
    查詢單字本所有單字，依加入時間由新到舊排序。
    回傳：list of dict
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vocabulary ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_vocabulary(vocab_id):
    """刪除指定單字。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vocabulary WHERE id = ?", (vocab_id,))
    conn.commit()
    conn.close()

