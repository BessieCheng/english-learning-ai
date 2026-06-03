import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from gemini_utils import MODELS, _extract_json_array

load_dotenv(".env.local")

TOEIC_LEVELS = {
    "TOEIC ≤ 350":     ("A1-A2", "very short simple sentences, basic everyday vocabulary"),
    "TOEIC 350–550":   ("A2-B1", "simple sentences, common vocabulary"),
    "TOEIC 550–700":   ("B1-B2", "standard news language, some complex sentences"),
    "TOEIC 700–850":   ("B2-C1", "formal news style, complex structures"),
    "TOEIC ≥ 850":     ("C1-C2", "professional news English, sophisticated vocabulary"),
}


def fetch_news_with_gemini(topic, toeic_level_key, count=3):
    """
    用 Gemini + Google Search 搜尋真實新聞，整理成適合該程度學習者閱讀的格式。
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

    import time
    last_error = None
    raw = None

    for model_name in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                raw = response.text.strip()
                break
            except Exception as e:
                last_error = e
                error_str = str(e)
                if "404" in error_str or "NOT_FOUND" in error_str:
                    break
                elif "503" in error_str or "UNAVAILABLE" in error_str or "429" in error_str:
                    time.sleep(3 * (attempt + 1))
                    continue
                else:
                    raise
        if raw:
            break

    if raw is None:
        raise Exception(
            f"Gemini 伺服器忙碌中，請稍後再試。/ サーバーが混雑しています。\n({last_error})"
        )

    return _extract_json_array(raw)
