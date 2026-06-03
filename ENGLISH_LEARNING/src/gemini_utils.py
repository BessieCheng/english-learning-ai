import os
import json
import re
import time
from google import genai
from dotenv import load_dotenv

load_dotenv(".env.local")

MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]


def _extract_json(raw: str) -> dict:
    """從 Gemini 回應穩健萃取 JSON dict，處理 markdown 包裝、前綴文字、trailing comma。"""
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start:end + 1]
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)
    return json.loads(raw)


def _extract_json_array(raw: str) -> list:
    """從 Gemini 回應穩健萃取 JSON array，處理 markdown 包裝與 trailing comma。"""
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw).strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end > start:
        raw = raw[start:end + 1]
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)
    return json.loads(raw)


def call_gemini_json(prompt: str) -> dict:
    """呼叫 Gemini（多模型 + 重試），回傳解析後的 JSON dict。"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 未設定（請在 .env.local 或 Streamlit Secrets 設定）")
    client = genai.Client(api_key=api_key)
    last_err = None
    for model_name in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                return _extract_json(response.text.strip())
            except Exception as e:
                last_err = e
                err = str(e)
                if "404" in err or "NOT_FOUND" in err:
                    break
                elif any(c in err for c in ["503", "UNAVAILABLE", "429"]):
                    time.sleep(3 * (attempt + 1))
                else:
                    break
    raise RuntimeError(f"Gemini 查詢失敗：{last_err}")
