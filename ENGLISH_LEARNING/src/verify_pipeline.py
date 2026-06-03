#!/usr/bin/env python3
"""
verify_pipeline.py
一鍵確認音檔上傳核心流程各模組是否正常運作。
執行方式：python src/verify_pipeline.py
"""

import sys
import os
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(__file__))

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []


def check(name, fn):
    print(f"\n── {name} ──")
    try:
        fn()
        print(f"  {PASS}")
        results.append((name, True, None))
    except Exception as e:
        print(f"  {FAIL}")
        traceback.print_exc()
        results.append((name, False, str(e)))


# ── Mock 資料（共用）────────────────────────────────────────────
MOCK_ANALYSIS = {
    "overall_score": 7,
    "summary": "Good effort. / 良い努力です。",
    "grammar_errors": [
        {"speaker": "A", "original": "I go yesterday",
         "correction": "I went yesterday", "explanation": "Past tense required."}
    ],
    "vocabulary_highlights": [
        {"word": "purchase", "part_of_speech": "verb",
         "definition": "to buy / 買う", "example": "I purchased a new book."}
    ],
    "pronunciation_tips": [
        {"speaker": "B", "tip": "L/R confusion / L/R混同",
         "example": "rice → /raɪs/, not /laɪs/"}
    ],
    "hesitant_words": [
        {"speaker": "A", "word": "although", "part_of_speech": "conjunction",
         "definition": "雖然 / けれども",
         "example": "Although it rained, we went out."}
    ],
}
MOCK_DIARIZED = {
    "transcript": "I go to store yesterday.",
    "speaker_count": 2,
    "speaker_a_label": "Speaker A",
    "speaker_b_label": "Speaker B",
    "segments": [
        {"speaker": "A", "text": "I go to store yesterday."},
        {"speaker": "B", "text": "Oh really? What did you buy?"},
    ],
}


# ── 1. Database ──────────────────────────────────────────────────
def test_database():
    import database

    orig_path = database.DB_PATH
    database.DB_PATH = tempfile.mktemp(suffix=".db")
    try:
        database.init_database()

        session_id = database.save_session(
            "test.mp3", "I go to store yesterday.",
            MOCK_ANALYSIS, diarized=MOCK_DIARIZED
        )
        assert isinstance(session_id, int) and session_id > 0

        sessions = database.get_all_sessions()
        assert any(s["id"] == session_id for s in sessions), "session 未找到"

        vocab = database.get_all_vocabulary()
        words = [v["word"] for v in vocab]
        assert "purchase" in words, "vocabulary_highlights 未存入"
        assert "although" in words, "hesitant_words 未存入"

        database.delete_session(session_id)
        assert not any(s["id"] == session_id for s in database.get_all_sessions()), "刪除失敗"

        print("  → init / save / query / hesitant_words / delete: OK")
    finally:
        if os.path.exists(database.DB_PATH):
            os.unlink(database.DB_PATH)
        database.DB_PATH = orig_path


# ── 2. PDF 生成 ──────────────────────────────────────────────────
def test_pdf():
    from generate_pdf import generate_report_pdf

    pdf_bytes = generate_report_pdf(
        "test_audio.mp3", "Test transcript.",
        MOCK_ANALYSIS, diarized=MOCK_DIARIZED
    )
    assert isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 1000, \
        f"PDF 太小（{len(pdf_bytes)} bytes），可能生成失敗"
    print(f"  → 生成成功：{len(pdf_bytes):,} bytes")


# ── 3. Gemini 分析（微量 API 呼叫）──────────────────────────────
def test_analyze():
    from dotenv import load_dotenv
    load_dotenv(".env.local")

    if not os.getenv("GEMINI_API_KEY"):
        raise EnvironmentError("GEMINI_API_KEY 未設定（請確認 .env.local）")

    from analyze_func import analyze
    result = analyze("I go to the store yesterday and buyed some apple.")

    assert isinstance(result, dict), "回傳值應為 dict"
    for key in ("overall_score", "grammar_errors", "vocabulary_highlights",
                "pronunciation_tips", "hesitant_words"):
        assert key in result, f"缺少欄位：{key}"

    print(f"  → score: {result.get('overall_score')}/10")
    print(f"  → grammar_errors: {len(result.get('grammar_errors', []))} 筆")
    print(f"  → vocabulary_highlights: {len(result.get('vocabulary_highlights', []))} 筆")
    print(f"  → pronunciation_tips: {len(result.get('pronunciation_tips', []))} 筆")
    print(f"  → hesitant_words: {len(result.get('hesitant_words', []))} 筆")


# ── 執行 ─────────────────────────────────────────────────────────
print("=" * 52)
print("verify_pipeline.py — 音檔上傳流程核心檢查")
print("=" * 52)

check("1. Database（init / save / query / delete）", test_database)
check("2. PDF 生成（generate_report_pdf）", test_pdf)
check("3. Gemini 分析（analyze，微量 API 呼叫）", test_analyze)

print("\n" + "=" * 52)
passed = sum(1 for _, ok, _ in results if ok)
for name, ok, err in results:
    print(f"  {'✅' if ok else '❌'}  {name}")
    if err:
        print(f"       原因：{err}")

print(f"\n結果：{passed}/{len(results)} 通過")
sys.exit(0 if passed == len(results) else 1)