#!/usr/bin/env python3
"""
backend-test — 後台測試 ENGLISH_LEARNING 功能的執行腳本。
不需要開瀏覽器，直接呼叫 Gemini / DB，回傳結果給 Claude 判斷。

使用方式（從 ENGLISH_LEARNING/ 目錄執行）：
    python .claude/skills/backend-test/run.py quiz_grade "中文句子" "使用者英文翻譯"
    python .claude/skills/backend-test/run.py quiz_gen
    python .claude/skills/backend-test/run.py vocab_lookup "word"
    python .claude/skills/backend-test/run.py db_check
"""
import sys
import json
import os
from dotenv import load_dotenv

load_dotenv(".env.local")
sys.path.insert(0, "src")

PASS = True
def fail(msg):
    global PASS
    PASS = False
    print(f"❌ {msg}")

def ok(msg):
    print(f"✅ {msg}")

def check_bilingual(text, label):
    """驗證文字是 '日文 / 中文' 格式，不含英文。"""
    if not text:
        fail(f"{label}: 空白")
        return
    # 接受 " / " 或 "/ "（日文句號後直接接斜線）
    sep = " / " if " / " in text else ("/ " if "/ " in text else None)
    if not sep:
        fail(f"{label}: 缺少分隔符 → {text[:80]}")
        return
    parts = text.split(sep, 1)
    ja_part = parts[0].strip()
    zh_part = parts[1].strip()
    # 簡單偵測：日文部分不應是純英文（有日文字元才算日文）
    has_ja = any('぀' <= c <= 'ヿ' or '一' <= c <= '鿿' for c in ja_part)
    has_zh = any('一' <= c <= '鿿' for c in zh_part)
    if not has_ja:
        fail(f"{label} 日文部分不含日文字元: {ja_part[:60]}")
    elif not has_zh:
        fail(f"{label} 中文部分不含中文字元: {zh_part[:60]}")
    else:
        ok(f"{label} 雙語格式正確")
        print(f"   日: {ja_part[:60]}")
        print(f"   中: {zh_part[:60]}")


cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

# ── quiz_grade：測試批改功能 ─────────────────────────────────────────
if cmd == "quiz_grade":
    source = sys.argv[2] if len(sys.argv) > 2 else "因近期大雨，北部部分道路暫時封閉。"
    answer = sys.argv[3] if len(sys.argv) > 3 else "Due to heavy rain, some roads in the north are temporarily closed."
    level  = sys.argv[4] if len(sys.argv) > 4 else "TOEIC 550-700"

    print(f"\n[quiz_grade] 題目: {source}")
    print(f"[quiz_grade] 回答: {answer}\n")

    from quiz_func import grade_translation
    result = grade_translation(source, answer, level)

    score = result.get("score", 0)
    ok(f"分數: {score}/100") if isinstance(score, int) else fail(f"分數格式錯誤: {score}")

    errors = result.get("errors", [])
    ok(f"錯誤修正: {len(errors)} 條")
    for i, e in enumerate(errors[:3]):
        check_bilingual(e.get("note", ""), f"  errors[{i}].note")

    check_bilingual(result.get("feedback", ""), "feedback")

# ── quiz_gen：測試出題功能 ─────────────────────────────────────────
elif cmd == "quiz_gen":
    lang = sys.argv[2] if len(sys.argv) > 2 else "zh"
    level = sys.argv[3] if len(sys.argv) > 3 else "TOEIC 550-700"

    print(f"\n[quiz_gen] lang={lang}, level={level}\n")

    from quiz_func import generate_quiz
    q = generate_quiz(level, lang=lang)

    zh = q.get("zh", "")
    ja = q.get("ja", "")
    text = q.get("text", "")

    ok(f"中文題: {zh}") if zh else fail("中文題: 空白")
    ok(f"日文題: {ja}") if ja else fail("日文題: 空白")
    ok(f"主題目 ({lang}): {text}") if text else fail("主題目: 空白")

# ── vocab_lookup：測試單字查詢 ─────────────────────────────────────
elif cmd == "vocab_lookup":
    word = sys.argv[2] if len(sys.argv) > 2 else "resilient"
    print(f"\n[vocab_lookup] 查詢: {word}\n")

    from analyze_func import lookup_word
    info = lookup_word(word)

    jp_def = info.get("definition_jp", "")
    zh_def = info.get("definition_zh", "")
    ok(f"日文: {jp_def}") if jp_def else fail("日文定義: 空白")
    ok(f"中文: {zh_def}") if zh_def else fail("中文定義: 空白")
    ok(f"詞性: {info.get('part_of_speech','')}")

# ── db_check：測試資料庫連線 ───────────────────────────────────────
elif cmd == "db_check":
    print("\n[db_check]\n")
    from database import get_saved_news, get_all_vocabulary, get_all_translation_quiz
    news = get_saved_news()
    ok(f"saved_news: {len(news)} 筆，saved_at 型別 {type(news[0]['saved_at']).__name__ if news else 'N/A'}")
    vocab = get_all_vocabulary()
    ok(f"vocabulary: {len(vocab)} 筆")
    quizzes = get_all_translation_quiz()
    ok(f"translation_quiz: {len(quizzes)} 筆")

else:
    print(__doc__)

print()
print("✅ 全部通過" if PASS else "❌ 有失敗項目")
sys.exit(0 if PASS else 1)
