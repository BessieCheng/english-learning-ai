# 語音轉文字 — 使用 Groq Whisper API（免費，速度比 OpenAI 快 10 倍）
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def transcribe(audio_path):
    """
    呼叫 Groq Whisper API，回傳：
      - text: 完整逐字稿字串
      - segments: 每個片段含 start/end 時間戳（供 pyannote 合併用）
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=f,
            language="en",
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )

    segments = []
    for seg in (response.segments or []):
        segments.append({
            "start": seg["start"],
            "end":   seg["end"],
            "text":  seg["text"].strip()
        })

    return {
        "text":     response.text,
        "segments": segments
    }
