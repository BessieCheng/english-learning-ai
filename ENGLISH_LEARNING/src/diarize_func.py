# =============================================================
# diarize_func.py
# 功能：用 AssemblyAI 一次完成語音轉文字 + 說話者分離
# =============================================================

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv(".env.local")


def diarize(audio_path, whisper_result=None):
    """
    呼叫 AssemblyAI 同時完成：轉錄 + 說話者分離。
    whisper_result 參數保留相容性，實際不使用。
    回傳與舊版相同的 dict 格式，額外加上 transcript 欄位。
    """
    import assemblyai as aai

    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY 未設定，請在 .env.local 加入")

    aai.settings.api_key = api_key

    config = aai.TranscriptionConfig(
        speaker_labels=True,
        speaker_options=aai.SpeakerOptions(
            min_speakers_expected=2,
            max_speakers_expected=2,
            use_two_stage_clustering=True,
        ),
        language_code="en",
        speech_models=["universal-3-pro"]
    )

    transcriber = aai.Transcriber()
    result = transcriber.transcribe(audio_path, config=config)

    if result.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI 錯誤：{result.error}")

    # 把 AssemblyAI 的說話者 ID（"A", "B"...）對應到我們的標籤
    speakers_seen = []
    for utt in (result.utterances or []):
        if utt.speaker not in speakers_seen:
            speakers_seen.append(utt.speaker)

    id_map = {spk: chr(65 + i) for i, spk in enumerate(speakers_seen)}

    # 連續同一說話者的句子合併
    segments = []
    for utt in (result.utterances or []):
        label = id_map.get(utt.speaker, "A")
        if segments and segments[-1]["speaker"] == label:
            segments[-1]["text"] += " " + utt.text
        else:
            segments.append({"speaker": label, "text": utt.text})

    print(f"[AssemblyAI] 偵測到 {len(speakers_seen)} 位說話者，共 {len(segments)} 段")

    return {
        "transcript":      result.text or "",
        "speaker_count":   len(speakers_seen),
        "speaker_a_label": "Speaker A / 話者A / 說話者A",
        "speaker_b_label": "Speaker B / 話者B / 說話者B",
        "segments":        segments
    }


def _fallback(full_text):
    """API 無法使用時的後備（全文歸為 Speaker A）。"""
    return {
        "transcript":      full_text,
        "speaker_count":   1,
        "speaker_a_label": "Speaker A / 話者A / 說話者A",
        "speaker_b_label": "Speaker B / 話者B / 說話者B",
        "segments":        [{"speaker": "A", "text": full_text}]
    }
