import os
import json
import psycopg2
import psycopg2.extras
import psycopg2.pool
from contextlib import contextmanager
from datetime import date
from dotenv import load_dotenv

load_dotenv(".env.local")

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL 未設定，請在 .env.local 加入")
        if "sslmode" not in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 10, url)
    return _pool


@contextmanager
def get_db():
    """從連線池取得連線，成功自動 commit，失敗自動 rollback，離開後歸還連線。"""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def init_database():
    """初始化資料庫：建立所有需要的資料表與索引（已存在則跳過）。"""
    with get_db() as conn:
        cur = _cur(conn)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id              SERIAL PRIMARY KEY,
                audio_file      TEXT    NOT NULL,
                transcript      TEXT    NOT NULL,
                score           INTEGER,
                summary         TEXT,
                analysis_json   TEXT,
                diarized_json   TEXT,
                reference_title TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS grammar_errors (
                id          SERIAL PRIMARY KEY,
                session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                original    TEXT    NOT NULL,
                correction  TEXT    NOT NULL,
                explanation TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id              SERIAL PRIMARY KEY,
                session_id      INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                word            TEXT    NOT NULL,
                part_of_speech  TEXT,
                definition      TEXT,
                example         TEXT,
                source          TEXT    DEFAULT 'vocabulary',
                next_review     DATE    DEFAULT CURRENT_DATE,
                interval_days   INTEGER DEFAULT 1,
                ease_factor     REAL    DEFAULT 2.5,
                review_count    INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_vocabulary_word_lower
            ON vocabulary (LOWER(word))
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS translation_quiz (
                id            SERIAL PRIMARY KEY,
                toeic_level   TEXT,
                source_zh     TEXT    NOT NULL,
                user_en       TEXT    NOT NULL,
                correct_en    TEXT,
                score         INTEGER,
                feedback_json TEXT,
                created_at    TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS saved_news (
                id         SERIAL PRIMARY KEY,
                title      TEXT NOT NULL,
                source     TEXT,
                date_str   TEXT,
                body       TEXT,
                vocab_json TEXT,
                saved_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.close()
    print("✅ 資料庫初始化完成（Supabase PostgreSQL）")


def save_session(audio_file, transcript, analysis, diarized=None, reference_title=None):
    """把一次完整的分析結果存入資料庫，所有 INSERT 在同一交易中，回傳 session_id。"""
    with get_db() as conn:
        cur = _cur(conn)

        cur.execute("""
            INSERT INTO sessions (audio_file, transcript, score, summary, analysis_json, diarized_json, reference_title)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            audio_file,
            transcript,
            analysis.get("overall_score"),
            analysis.get("summary"),
            json.dumps(analysis, ensure_ascii=False),
            json.dumps(diarized, ensure_ascii=False) if diarized else None,
            reference_title,
        ))
        session_id = cur.fetchone()["id"]

        for err in analysis.get("grammar_errors", []):
            cur.execute("""
                INSERT INTO grammar_errors (session_id, original, correction, explanation)
                VALUES (%s, %s, %s, %s)
            """, (session_id, err.get("original"), err.get("correction"), err.get("explanation")))

        def _word_exists(word):
            cur.execute("SELECT 1 FROM vocabulary WHERE LOWER(word) = LOWER(%s) LIMIT 1", (word,))
            return cur.fetchone() is not None

        for v in analysis.get("vocabulary_highlights", []):
            if v.get("word") and not _word_exists(v["word"]):
                cur.execute("""
                    INSERT INTO vocabulary (session_id, word, part_of_speech, definition, example, source)
                    VALUES (%s, %s, %s, %s, %s, 'vocabulary')
                """, (session_id, v.get("word"), v.get("part_of_speech"), v.get("definition"), v.get("example")))

        for tip in analysis.get("pronunciation_tips", []):
            if isinstance(tip, dict) and tip.get("example"):
                word = tip["example"].split()[0].strip(".,!?\"'():").lower()
                if word and not _word_exists(word):
                    # definition 留空，待自動查詞義補填；發音說明存入 example
                    pron_note = tip.get("tip", "")
                    pron_ex   = tip.get("example", "")
                    combined  = f"{pron_note} [{pron_ex}]" if pron_ex else pron_note
                    cur.execute("""
                        INSERT INTO vocabulary (session_id, word, definition, example, source)
                        VALUES (%s, %s, %s, %s, 'pronunciation')
                    """, (session_id, word, None, combined))

        for hw in analysis.get("hesitant_words", []):
            if hw.get("word") and not _word_exists(hw["word"]):
                cur.execute("""
                    INSERT INTO vocabulary (session_id, word, part_of_speech, definition, example, source)
                    VALUES (%s, %s, %s, %s, %s, 'hesitant')
                """, (session_id, hw.get("word"), hw.get("part_of_speech"), hw.get("definition", ""), hw.get("example", "")))

        cur.close()

    print(f"💾 已存入資料庫（Session ID: {session_id}）")
    return session_id


def get_all_sessions():
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
    return rows


def delete_session(session_id):
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        cur.close()


def save_translation_quiz(toeic_level, source_zh, user_en, correct_en, score, feedback_json):
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("""
            INSERT INTO translation_quiz (toeic_level, source_zh, user_en, correct_en, score, feedback_json)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (toeic_level, source_zh, user_en, correct_en, score, feedback_json))
        quiz_id = cur.fetchone()["id"]
        cur.close()
    return quiz_id


def get_all_translation_quiz():
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("SELECT * FROM translation_quiz ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
    return rows


def delete_translation_quiz(quiz_id):
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("DELETE FROM translation_quiz WHERE id = %s", (quiz_id,))
        cur.close()


def add_vocabulary_manually(word, definition, example="", part_of_speech=""):
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("SELECT 1 FROM vocabulary WHERE LOWER(word) = LOWER(%s) LIMIT 1", (word.strip(),))
        if cur.fetchone():
            cur.close()
            return
        cur.execute("""
            INSERT INTO vocabulary (session_id, word, part_of_speech, definition, example, source)
            VALUES (NULL, %s, %s, %s, %s, 'manual')
        """, (word.strip(), part_of_speech.strip() or None, definition.strip(), example.strip()))
        cur.close()


def get_vocabulary_due_today():
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("""
            SELECT * FROM vocabulary
            WHERE next_review <= CURRENT_DATE
            ORDER BY next_review ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
    return rows


def save_news_article(title, source, date_str, body, vocab_json=""):
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("""
            INSERT INTO saved_news (title, source, date_str, body, vocab_json)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, source, date_str, body, vocab_json))
        cur.close()


def get_saved_news():
    try:
        with get_db() as conn:
            cur = _cur(conn)
            cur.execute("SELECT * FROM saved_news ORDER BY saved_at DESC")
            rows = [dict(r) for r in cur.fetchall()]
            cur.close()
        return rows
    except psycopg2.errors.UndefinedTable:
        return []
    except Exception as e:
        print(f"[get_saved_news] 查詢失敗：{e}")
        return []


def delete_saved_news(news_id):
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("DELETE FROM saved_news WHERE id = %s", (news_id,))
        cur.close()


def get_all_vocabulary():
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("""
            SELECT v.*, s.reference_title
            FROM vocabulary v
            LEFT JOIN sessions s ON v.session_id = s.id
            ORDER BY v.id DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
    return rows


def delete_vocabulary(vocab_id):
    with get_db() as conn:
        cur = _cur(conn)
        cur.execute("DELETE FROM vocabulary WHERE id = %s", (vocab_id,))
        cur.close()
