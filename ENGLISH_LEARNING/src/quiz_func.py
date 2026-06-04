from news_search import TOEIC_LEVELS
from gemini_utils import call_gemini_json

_VERSION = "2"  # bump to force Streamlit Cloud recompile


def generate_quiz(toeic_level_key, lang="zh"):
    """依多益程度，AI 生成一個適合翻成英文的句子。
    lang='zh' → 繁體中文題；lang='ja' → 日文題。
    回傳 dict：{"text": "...", "lang": lang}
    """
    cefr, style = TOEIC_LEVELS.get(toeic_level_key, ("B1-B2", "standard sentences"))
    if lang == "ja":
        lang_instruction = "Generate ONE natural Japanese sentence (日本語) for the learner to translate INTO English."
        lang_req = "- Output in Japanese (日本語). A single sentence, 15-40 characters."
        json_key = "ja"
    else:
        lang_instruction = "Generate ONE natural Traditional Chinese sentence for the learner to translate INTO English."
        lang_req = "- Output Traditional Chinese (Taiwan), not Simplified. 8-20 Chinese characters."
        json_key = "zh"

    prompt = f"""You are an English teacher creating a translation exercise.
The learner's level is CEFR {cefr} (target style: {style}).

{lang_instruction}
Requirements:
- Difficulty must match {cefr}: vocabulary and grammar appropriate for that level.
- A single, self-contained sentence (not too long).
- Everyday or practical topic; avoid obscure idioms or proper nouns.
- {lang_req}

Return ONLY a valid JSON object with no extra text:
{{
  "{json_key}": "<the sentence>"
}}"""
    result = call_gemini_json(prompt)
    sentence = result.get(json_key, "")
    if not sentence:
        raise RuntimeError("出題失敗：未取得題目。")
    return {"text": sentence.strip(), "lang": lang, "zh": sentence.strip() if lang == "zh" else "", "ja": sentence.strip() if lang == "ja" else ""}


def grade_translation(source_zh, user_en, toeic_level_key):
    """批改使用者的英文翻譯，回傳分數、錯誤列表、講評。"""
    cefr, _ = TOEIC_LEVELS.get(toeic_level_key, ("B1-B2", ""))
    prompt = f"""You are an English teacher grading a Chinese-to-English translation.
Learner level: CEFR {cefr}.

Chinese sentence (the prompt):
{source_zh}

Learner's English translation:
{user_en}

Grade it. Consider grammar, word choice, naturalness, and whether the meaning matches.
Be encouraging but precise. Give the corrections a learner at {cefr} can understand.

Return ONLY a valid JSON object with no extra text:
{{
  "correct": "<one recommended natural English translation>",
  "score": <integer 0-100>,
  "errors": [
    {{"wrong": "<the learner's problematic part>", "right": "<corrected version>", "note": "<short explanation in BOTH Japanese AND Traditional Chinese, format: 'Japanese説明。/ 中文說明。'>"}}
  ],
  "feedback": "<one or two sentences of overall feedback in BOTH Japanese AND Traditional Chinese, format: 'Japanese講評。/ 中文講評。'>"
}}
If the translation is already perfect, return an empty "errors" array and a high score."""
    result = call_gemini_json(prompt)
    result.setdefault("correct", "")
    result.setdefault("score", 0)
    result.setdefault("errors", [])
    result.setdefault("feedback", "")
    return result
