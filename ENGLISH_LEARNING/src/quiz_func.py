from news_search import TOEIC_LEVELS
from gemini_utils import call_gemini_json

_VERSION = "3"


def generate_quiz(toeic_level_key, lang="zh"):
    """依多益程度，AI 生成一個適合翻成英文的句子，並同時附上另一語言的對照翻譯。
    lang='zh' → 主題為繁體中文，附日文對照；lang='ja' → 主題為日文，附中文對照。
    回傳 dict：{"text": str, "lang": str, "zh": str, "ja": str}
    """
    cefr, style = TOEIC_LEVELS.get(toeic_level_key, ("B1-B2", "standard sentences"))

    prompt = f"""You are an English teacher creating a translation exercise.
The learner's level is CEFR {cefr} (target style: {style}).

Generate ONE natural sentence for the learner to translate INTO English.
The PRIMARY language is {"Traditional Chinese (繁體中文)" if lang == "zh" else "Japanese (日本語)"}.
Also provide the translation of that sentence in the other language.

Requirements:
- Difficulty matches CEFR {cefr}.
- A single, self-contained sentence. Everyday or practical topic.
- Traditional Chinese: 8-20 characters (Taiwan style, not Simplified).
- Japanese: 15-40 characters.

Return ONLY a valid JSON object with no extra text:
{{
  "zh": "<Traditional Chinese sentence>",
  "ja": "<Japanese sentence (same meaning)>"
}}"""
    result = call_gemini_json(prompt)
    zh = (result.get("zh") or "").strip()
    ja = (result.get("ja") or "").strip()
    if not zh or not ja:
        raise RuntimeError("出題失敗：未取得題目。")
    text = zh if lang == "zh" else ja
    return {"text": text, "lang": lang, "zh": zh, "ja": ja}


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
