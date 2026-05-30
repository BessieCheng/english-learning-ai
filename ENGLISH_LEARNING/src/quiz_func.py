# =============================================================
# quiz_func.py
# 功能：AI 翻譯練習
#   - generate_quiz()：依多益程度，AI 生成一個中文句子
#   - grade_translation()：AI 批改使用者的英文翻譯
# 使用同 analyze_func 的 Gemini 呼叫模式（多模型 + 重試 + JSON 解析）
# =============================================================

import os
import json
import time
from google import genai
from dotenv import load_dotenv

# TOEIC 等級 → (CEFR, 風格描述) 對應，與新聞頁共用
from news_search import TOEIC_LEVELS

load_dotenv()

MODELS = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]


def _call_gemini_json(prompt):
    """呼叫 Gemini，回傳解析後的 JSON（dict）。多模型 + 重試。"""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    for model_name in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                raw = response.text.strip()
                if raw.startswith("```"):
                    raw = "\n".join(raw.split("\n")[1:-1])
                # 只取第一個 { ... } JSON 物件，避免尾部雜訊
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start != -1 and end > start:
                    raw = raw[start:end]
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


def generate_quiz(toeic_level_key):
    """
    依多益程度，AI 生成一個適合翻成英文的中文句子。
    回傳 dict：{"zh": "<中文句子>"}
    """
    cefr, style = TOEIC_LEVELS.get(toeic_level_key, ("B1-B2", "standard sentences"))
    prompt = f"""You are an English teacher creating a translation exercise.
The learner's level is CEFR {cefr} (target style: {style}).

Generate ONE natural Traditional Chinese sentence for the learner to translate INTO English.
Requirements:
- Difficulty must match {cefr}: vocabulary and grammar appropriate for that level.
- A single, self-contained sentence (not too long, 8-20 Chinese characters is ideal).
- Everyday or practical topic; avoid obscure idioms or proper nouns.
- Output Traditional Chinese (Taiwan), not Simplified.

Return ONLY a valid JSON object with no extra text:
{{
  "zh": "<the Traditional Chinese sentence>"
}}"""
    result = _call_gemini_json(prompt)
    if not result.get("zh"):
        raise RuntimeError("出題失敗：未取得題目。")
    return {"zh": result["zh"].strip()}


def grade_translation(source_zh, user_en, toeic_level_key):
    """
    批改使用者的英文翻譯。
    回傳 dict：
      {
        "correct": "<推薦英譯>",
        "score": <0-100>,
        "errors": [{"wrong": "...", "right": "...", "note": "..."}],
        "feedback": "<整體講評（繁體中文）>"
      }
    """
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
    {{"wrong": "<the learner's problematic part>", "right": "<corrected version>", "note": "<short explanation in Traditional Chinese>"}}
  ],
  "feedback": "<one or two sentences of overall feedback in Traditional Chinese>"
}}
If the translation is already perfect, return an empty "errors" array and a high score."""
    result = _call_gemini_json(prompt)
    # 容錯：確保欄位存在
    result.setdefault("correct", "")
    result.setdefault("score", 0)
    result.setdefault("errors", [])
    result.setdefault("feedback", "")
    return result
