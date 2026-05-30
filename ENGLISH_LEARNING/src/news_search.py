# =============================================================
# news_search.py
# 功能：用 Gemini + Google Search 找真實的英文新聞，
#       並整理成適合指定多益程度的學習格式。
# =============================================================

import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ── 多益分數對應的程度說明 ─────────────────────────────────────
TOEIC_LEVELS = {
    "TOEIC ≤ 350":     ("A1-A2", "very short simple sentences, basic everyday vocabulary"),
    "TOEIC 350–550":   ("A2-B1", "simple sentences, common vocabulary"),
    "TOEIC 550–700":   ("B1-B2", "standard news language, some complex sentences"),
    "TOEIC 700–850":   ("B2-C1", "formal news style, complex structures"),
    "TOEIC ≥ 850":     ("C1-C2", "professional news English, sophisticated vocabulary"),
}


def fetch_news_with_gemini(topic, toeic_level_key, count=3):
    """
    用 Gemini + Google Search 搜尋真實新聞，
    並整理成適合該程度學習者閱讀的格式。

    參數：
        topic           → 新聞主題（任何語言皆可）
        toeic_level_key → TOEIC_LEVELS 裡的 key
        count           → 要找幾篇（預設 3）

    回傳：list of dict（每篇包含 title、source、date、body、vocabulary）
    """
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    cefr, style_guide = TOEIC_LEVELS[toeic_level_key]

    prompt = f"""Search Google News for the latest {count} real news articles about: "{topic}"

For each article you find, rewrite the content in English suitable for a {cefr} level reader ({style_guide}).

Return ONLY a valid JSON array with no extra text or markdown:

[
  {{
    "title": "<original news headline>",
    "source": "<news source name, e.g. BBC, Reuters, CNN>",
    "date": "<publication date if available, format YYYY-MM-DD>",
    "body": "<article content rewritten at {cefr} English level, 100-200 words, English only>",
    "vocabulary": [
      {{
        "word": "<key word from the article>",
        "definition": "<simple English definition suitable for {cefr} level>",
        "example": "<short example sentence>"
      }}
    ],
    "word_glossary": {{
      "<every meaningful word in the body (nouns, verbs, adjectives, adverbs — skip articles/prepositions like the/a/in/of)>": {{
        "jp": "<Japanese translation, 1-4 characters>",
        "zh": "<Traditional Chinese translation, 1-4 characters>"
      }}
    }}
  }}
]

Include 3-5 vocabulary items per article. All body text must be in English only.
The word_glossary must cover all content words (nouns, verbs, adjectives, adverbs) in the body."""

    # 依序嘗試的模型（主要 → 備用）
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]

    last_error = None
    raw = None

    for model_name in models_to_try:
        for attempt in range(3):   # 每個模型最多重試 3 次
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                raw = response.text.strip()
                break   # 成功就跳出重試迴圈
            except Exception as e:
                last_error = e
                error_str = str(e)
                if "404" in error_str or "NOT_FOUND" in error_str:
                    break  # 此模型不可用，直接跳下一個
                elif "503" in error_str or "UNAVAILABLE" in error_str or "429" in error_str:
                    time.sleep(3 * (attempt + 1))
                    continue
                else:
                    raise
        if raw:
            break   # 某個模型成功了，跳出外層迴圈

    if raw is None:
        raise Exception(f"Gemini 伺服器忙碌中，請稍後再試。/ サーバーが混雑しています。しばらくしてからお試しください。\n({last_error})")

    # Gemini sometimes wraps JSON in markdown code blocks — strip them
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])

    # Sometimes there is trailing content after the JSON array — extract just the array
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start != -1 and end > start:
        raw = raw[start:end]

    return json.loads(raw)
