# 語音轉文字 — 使用 Groq Whisper API（免費，速度快）
# 僅作為 AssemblyAI 失敗時的備用方案
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(".env.local")

def transcribe(audio_path):
    """呼叫 Groq Whisper API，回傳逐字稿字串。"""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=f,
            language="en",
        )

    return {"text": response.text}
