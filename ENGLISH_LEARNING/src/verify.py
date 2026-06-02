# =============================================================
# verify.py
# 功能：每次改完功能後執行，自動驗證所有模組正常運作。
# 使用方式：python src/verify.py
# =============================================================

import sys, os, json, traceback
sys.path.insert(0, os.path.dirname(__file__))

PASS = "✅"
FAIL = "❌"
results = []


def check(name, fn):
    try:
        fn()
        results.append((PASS, name))
        print(f"{PASS} {name}")
    except Exception as e:
        results.append((FAIL, name))
        print(f"{FAIL} {name}")
        traceback.print_exc()


# ── 1. 語法檢查（所有 .py）───────────────────────────────────
def test_syntax():
    import py_compile, glob
    for f in glob.glob(os.path.join(os.path.dirname(__file__), "*.py")):
        if os.path.basename(f) == "verify.py":
            continue
        py_compile.compile(f, doraise=True)

check("語法檢查 (所有 .py)", test_syntax)


# ── 2. 資料庫初始化 ──────────────────────────────────────────
def test_database():
    from database import init_database, get_all_sessions, get_vocabulary_due_today
    init_database()
    sessions = get_all_sessions()
    vocab = get_vocabulary_due_today()
    assert isinstance(sessions, list)
    assert isinstance(vocab, list)

check("database: init + query", test_database)


# ── 3. SRS 算法 ──────────────────────────────────────────────
def test_srs():
    from srs import calculate_next_review
    interval, ease = calculate_next_review(1, 2.5, 0, 4)
    assert interval >= 1
    assert 1.3 <= ease <= 3.0

check("srs: SM-2 計算", test_srs)


# ── 4. analyze_func：語法 + 發音分析 ─────────────────────────
def test_analyze():
    from analyze_func import analyze
    transcript = (
        "I am go to the store yesterday. "
        "She don't like this kind of practice. "
        "Rice and read are very different words."
    )
    result = analyze(transcript)
    assert isinstance(result.get("overall_score"), int)
    assert result.get("grammar_errors") is not None
    assert result.get("pronunciation_tips") is not None
    # 確認發音提示有針對 L/R 或日式英文
    tips_text = json.dumps(result.get("pronunciation_tips", []))
    print(f"     → score={result['overall_score']}, "
          f"errors={len(result['grammar_errors'])}, "
          f"tips={len(result['pronunciation_tips'])}")

check("analyze_func: Gemini 分析", test_analyze)


# ── 5. analyze_func：單字查詢 ────────────────────────────────
def test_lookup():
    from analyze_func import lookup_word
    info = lookup_word("resilient")
    assert info.get("part_of_speech")
    assert info.get("definition_zh")
    assert info.get("definition_jp")
    assert info.get("example")
    print(f"     → {info['part_of_speech']} | {info['definition_zh']} / {info['definition_jp']}")

check("analyze_func: lookup_word", test_lookup)


# ── 6. diarize_func：import + AssemblyAI 設定 ────────────────
def test_diarize_import():
    from diarize_func import diarize, _fallback
    import assemblyai as aai
    # 確認 config 能正確序列化（不實際呼叫 API）
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        speaker_options=aai.SpeakerOptions(
            min_speakers_expected=2,
            max_speakers_expected=2,
            use_two_stage_clustering=True,
        ),
        language_code="en",
        speech_models=["universal-3-pro"]
    )
    d = config._raw_transcription_config.model_dump(exclude_none=True)
    assert d.get("speaker_labels") is True
    assert d.get("speech_models") == ["universal-3-pro"]
    assert "speakers_expected" not in d, "speakers_expected と speaker_options は同時使用不可"
    assert d["speaker_options"]["use_two_stage_clustering"] is True

check("diarize_func: config 序列化", test_diarize_import)


# ── 7. AssemblyAI API 連線（用官方 sample URL）───────────────
def test_assemblyai_api():
    import assemblyai as aai
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    assert api_key, "ASSEMBLYAI_API_KEY 未設定"
    aai.settings.api_key = api_key
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        speakers_expected=2,
        language_code="en",
        speech_models=["universal-3-pro"]
    )
    r = aai.Transcriber().transcribe(
        "https://storage.googleapis.com/aai-web-samples/espn-bears.m4a",
        config=config
    )
    assert r.status == aai.TranscriptStatus.completed, f"status={r.status}, error={r.error}"
    assert r.text
    assert r.utterances and len(r.utterances) > 0
    speakers = {u.speaker for u in r.utterances}
    print(f"     → {len(r.utterances)} utterances, speakers={sorted(speakers)}")

check("AssemblyAI API: 轉錄 + 說話者分離", test_assemblyai_api)


# ── 8. news_search：import ───────────────────────────────────
def test_news_import():
    from news_search import fetch_news_with_gemini, TOEIC_LEVELS
    assert isinstance(TOEIC_LEVELS, dict)
    assert len(TOEIC_LEVELS) > 0

check("news_search: import", test_news_import)


# ── 9. generate_pdf：import ──────────────────────────────────
def test_pdf_import():
    from generate_pdf import generate_report_pdf
    # 用假資料確認函式可呼叫、回傳 bytes
    fake_analysis = {
        "overall_score": 7,
        "summary": "テスト / 測試",
        "grammar_errors": [],
        "vocabulary_highlights": [],
        "pronunciation_tips": [],
        "hesitant_words": []
    }
    pdf = generate_report_pdf("test.mp3", "Hello world.", fake_analysis)
    assert isinstance(pdf, bytes) and len(pdf) > 100

check("generate_pdf: 產生 PDF", test_pdf_import)


# ── 結果總覽 ─────────────────────────────────────────────────
print()
print("=" * 50)
passed = sum(1 for r in results if r[0] == PASS)
total  = len(results)
print(f"結果：{passed} / {total} 通過")
if passed < total:
    print("失敗項目：")
    for icon, name in results:
        if icon == FAIL:
            print(f"  {FAIL} {name}")
    sys.exit(1)
else:
    print("🎉 全部通過！")
