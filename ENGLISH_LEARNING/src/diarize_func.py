import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv(".env.local")


def diarize(audio_path, whisper_result=None):
    """
    呼叫 AssemblyAI 同時完成：轉錄 + 說話者分離（自動偵測人數）。
    回傳與舊版相同的 dict 格式。
    """
    import assemblyai as aai

    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY 未設定，請在 .env.local 加入")

    aai.settings.api_key = api_key

    config = aai.TranscriptionConfig(
        speaker_labels=True,
        language_code="en",
        speech_models=["universal-3-pro"]
    )

    transcriber = aai.Transcriber()
    result = transcriber.transcribe(audio_path, config=config)

    if result.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI 錯誤：{result.error}")

    speakers_seen = []
    for utt in (result.utterances or []):
        if utt.speaker not in speakers_seen:
            speakers_seen.append(utt.speaker)

    id_map = {spk: chr(65 + i) for i, spk in enumerate(speakers_seen)}

    segments = []
    for utt in (result.utterances or []):
        label = id_map.get(utt.speaker, "A")
        if segments and segments[-1]["speaker"] == label:
            segments[-1]["text"] += " " + utt.text
        else:
            segments.append({"speaker": label, "text": utt.text})

    speaker_count = len(speakers_seen)
    print(f"[AssemblyAI] 偵測到 {speaker_count} 位說話者，共 {len(segments)} 段")

    return {
        "transcript":      result.text or "",
        "speaker_count":   speaker_count,
        "speaker_a_label": "Speaker A",
        "speaker_b_label": "Speaker B",
        "segments":        segments
    }


def _fallback(full_text):
    """API 無法使用時的後備（全文歸為 Speaker A）。"""
    return {
        "transcript":      full_text,
        "speaker_count":   1,
        "speaker_a_label": "Speaker A",
        "speaker_b_label": "Speaker B",
        "segments":        [{"speaker": "A", "text": full_text}]
    }
