"""
快速測試腳本：不需要開啟 Streamlit，直接在終端機測試完整流程。
用法：python test_pipeline.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

AUDIO = "/Users/page/Downloads/No. 340 Bo-Ai 2nd Rd.m4a"

# ── Step 1: Transcribe ────────────────────────────────────────────
print("\n[1/3] Whisper 轉錄中...")
from transcribe_func import transcribe
result = transcribe(AUDIO)
print(f"  轉錄完成：{len(result['segments'])} 個片段")
print(f"  文字（前100字）：{result['text'][:100]}...")

# ── Step 2: Diarize ───────────────────────────────────────────────
print("\n[2/3] pyannote 說話者分離中（第一次執行會下載模型，需數分鐘）...")

# 模擬 @st.cache_resource：直接 import Pipeline
import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from pyannote.audio import Pipeline
hf_token = os.getenv("HUGGINGFACE_TOKEN")
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=hf_token)

import subprocess, tempfile
tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
tmp.close()
subprocess.run(
    ["/opt/homebrew/bin/ffmpeg", "-y", "-i", AUDIO,
     "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", tmp.name],
    check=True, capture_output=True
)

diarization = pipeline(tmp.name, num_speakers=2)
os.unlink(tmp.name)

annotation = getattr(diarization, "speaker_diarization", diarization)

speaker_turns = []
for turn, _, speaker_id in annotation.itertracks(yield_label=True):
    speaker_turns.append({"start": turn.start, "end": turn.end, "speaker": speaker_id})

all_ids = set(t["speaker"] for t in speaker_turns)
print(f"  偵測到說話者：{all_ids}  共 {len(speaker_turns)} 段")

# ── Step 3: Merge ────────────────────────────────────────────────
print("\n[3/3] 合併 Whisper + pyannote 結果...")
labeled = []
for seg in result["segments"]:
    mid = (seg["start"] + seg["end"]) / 2
    best = None
    for t in speaker_turns:
        if t["start"] <= mid <= t["end"]:
            best = t["speaker"]; break
    if best is None:
        best = max(speaker_turns, key=lambda t: min(seg["end"], t["end"]) - max(seg["start"], t["start"]), default={"speaker": "SPEAKER_00"})["speaker"]
    labeled.append({"speaker": best, "text": seg["text"]})

unique = list(dict.fromkeys(s["speaker"] for s in labeled))
id_map = {spk: chr(65+i) for i, spk in enumerate(unique)}

merged = []
for seg in labeled:
    label = id_map.get(seg["speaker"], "A")
    if merged and merged[-1]["speaker"] == label:
        merged[-1]["text"] += " " + seg["text"]
    else:
        merged.append({"speaker": label, "text": seg["text"]})

print(f"\n  結果（{len(merged)} 個說話者區塊）：")
for m in merged:
    print(f"  [{m['speaker']}] {m['text'][:80]}")

print("\n[完成] 說話者分離測試通過！")
