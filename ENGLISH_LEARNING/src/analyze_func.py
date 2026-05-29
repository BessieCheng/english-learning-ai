# Gemini 分析的核心函式，供 app.py 和 pipeline.py 共用
import os
import json
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

MODELS = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]


def lookup_word(word):
    """
    用 Gemini 查詢單字的詞性、中日文定義、例句。
    回傳 dict：part_of_speech, definition_zh, definition_jp, example
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"""Look up the English word or phrase "{word}".
Return ONLY a valid JSON object with no extra text:
{{
  "part_of_speech": "<noun / verb / adjective / adverb / phrase / idiom>",
  "definition_zh": "<Traditional Chinese definition, concise 2-8 characters>",
  "definition_jp": "<Japanese definition, concise 2-8 characters>",
  "example": "<one natural English example sentence using this word>"
}}"""

    for model_name in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                raw = response.text.strip()
                if raw.startswith("```"):
                    raw = "\n".join(raw.split("\n")[1:-1])
                return json.loads(raw)
            except Exception as e:
                err = str(e)
                if "404" in err or "NOT_FOUND" in err:
                    break
                elif any(c in err for c in ["503", "UNAVAILABLE", "429"]):
                    time.sleep(3 * (attempt + 1))
                else:
                    raise
    raise RuntimeError("Gemini 查詢失敗，請稍後再試。")


def analyze(transcript, diarized=None, reference_text=None):
    """
    呼叫 Gemini API，分析逐字稿並回傳 dict 格式的分析結果。

    參數：
        transcript → 原始逐字稿（字串）
        diarized   → 話者分離結果（dict，可選）。若有提供，
                     文法錯誤會標注是哪位說話者的錯誤。
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # 話者分離結果があれば、ラベル付きのテキストを作成
    if diarized and diarized.get("segments"):
        label_a = diarized.get("speaker_a_label", "Speaker A")
        label_b = diarized.get("speaker_b_label", "Speaker B")
        labeled_lines = []
        for seg in diarized["segments"]:
            label = label_a if seg["speaker"] == "A" else label_b
            labeled_lines.append(f"[{label}]: {seg['text']}")
        transcript_for_analysis = "\n".join(labeled_lines)
        speaker_instruction = (
            f'The conversation has two speakers: "{label_a}" and "{label_b}". '
            f'In grammar_errors, add a "speaker" field ("A" or "B") to indicate who made each error. '
            f'In pronunciation_tips, identify non-native pronunciation issues for BOTH speakers — '
            f'add a "speaker" field ("A" or "B") to each tip based on who made the error.'
        )
    else:
        transcript_for_analysis = transcript
        speaker_instruction = (
            'Add a "speaker" field with value "A" to all grammar_errors. '
            'In pronunciation_tips, identify non-native pronunciation issues and add a "speaker" field ("A") to each tip.'
        )

    reference_section = ""
    if reference_text:
        reference_section = f"""
The speakers were reading the following article aloud. Compare their speech against this original text to identify specific words they mispronounced, skipped, added, or struggled with. Prioritize errors that deviate from the article.

Original article:
\"\"\"{reference_text}\"\"\"
"""

    prompt = f"""You are an English pronunciation coach specializing in helping Japanese and Taiwanese learners of English.
{speaker_instruction}
{reference_section}

Analyze the following transcript and return ONLY a valid JSON object with no extra text, no markdown formatting, no code blocks.

Focus especially on these common Japanese/Taiwanese English pronunciation patterns when filling in pronunciation_tips:
- L/R confusion (e.g. "right" → "light", "rice" → "lice")
- TH sounds pronounced as S, Z, D, or T (e.g. "think" → "sink", "this" → "dis")
- V/B confusion (e.g. "very" → "bery")
- Adding extra vowels between consonants or at word endings (e.g. "desk" → "de-su-ku", "bed" → "be-do")
- Breaking up consonant clusters (e.g. "stream" → "su-to-ri-mu")
- Pitch accent instead of English stress accent
- Short/long vowel confusion (e.g. "ship"/"sheep", "live"/"leave")
- Silent letters pronounced (e.g. "know" → pronouncing the K)
- -tion ending as "shi-on" instead of "shun"
- W pronounced as V or B
- Flat intonation (no natural sentence stress or rhythm)
Even if the transcript only shows spelling, infer likely pronunciation mistakes based on the words used and the speaker's apparent background.

The JSON must follow this exact structure:
{{
  "overall_score": <integer 1-10>,
  "summary": "<one sentence overall assessment written in BOTH Japanese AND Traditional Chinese, format: 'Japanese文。/ 中文。'>",
  "grammar_errors": [
    {{
      "speaker": "<'A' or 'B'>",
      "original": "<problematic phrase>",
      "correction": "<corrected version>",
      "explanation": "<explanation written in BOTH Japanese AND Traditional Chinese, format: 'Japanese説明。/ 中文說明。'>"
    }}
  ],
  "vocabulary_highlights": [
    {{
      "word": "<useful word>",
      "part_of_speech": "<e.g. noun / verb / adjective / adverb / phrase>",
      "definition": "<definition written in BOTH Japanese AND Traditional Chinese, format: 'Japanese意味 / 中文定義'>",
      "example": "<example sentence in English>"
    }}
  ],
  "pronunciation_tips": [
    {{
      "speaker": "<'A' or 'B'>",
      "tip": "<specific Japanese/Taiwanese pronunciation issue found, written in BOTH Japanese AND Traditional Chinese — include HOW to fix it, format: 'Japaneseヒント。/ 中文提示。'>",
      "example": "<the actual word or phrase likely mispronounced, with correct IPA or description, e.g. 'rice → /raɪs/, not /laɪs/'>"
    }}
  ],
  "hesitant_words": [
    {{
      "speaker": "<'A' or 'B'>",
      "word": "<word the speaker visibly hesitated on, repeated, or struggled to recall>",
      "part_of_speech": "<e.g. noun / verb / adjective / adverb / phrase>",
      "definition": "<definition written in BOTH Japanese AND Traditional Chinese, format: 'Japanese意味 / 中文定義'>",
      "example": "<correct natural example sentence in English>"
    }}
  ]
}}

Transcript:
\"\"\"{transcript_for_analysis}\"\"\"
"""

    raw = None
    for model_name in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                raw = response.text.strip()
                break
            except Exception as e:
                err_str = str(e)
                if any(code in err_str for code in ["404", "NOT_FOUND"]):
                    break  # 此模型不可用，直接跳下一個
                elif any(code in err_str for code in ["503", "UNAVAILABLE", "429"]):
                    time.sleep(3 * (attempt + 1))
                else:
                    raise
        if raw:
            break

    if not raw:
        raise RuntimeError("Gemini が全モデルで失敗しました。しばらく待ってから再試行してください。")
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])

    return json.loads(raw)
