#!/usr/bin/env python3
"""Local smoke transcription: Whisper (MLX) + ElevenLabs Scribe v2.

Requires a local audio file and (for Scribe) ELEVENLABS_API_KEY in .env.
Does not upload anything to GitHub; writes hypotheses under results/smoke/.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import mlx_whisper
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "data/raw/test_pl.m4a"
OUTPUT = ROOT / "results/smoke"
OUTPUT.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

if not AUDIO.is_file():
    raise FileNotFoundError(
        f"Missing local audio fixture: {AUDIO}. "
        "Place a licensed recording at this path (not committed by default)."
    )

# 1. Whisper (local MLX)
print("Running Whisper...")
start = time.perf_counter()

whisper = mlx_whisper.transcribe(
    str(AUDIO),
    path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
    language="pl",
    verbose=False,
)

whisper_seconds = time.perf_counter() - start
(OUTPUT / "whisper.txt").write_text(whisper["text"].strip(), encoding="utf-8")

# 2. ElevenLabs Scribe v2 (API)
print("Running Scribe v2...")
api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    raise RuntimeError("Missing ELEVENLABS_API_KEY in .env")

start = time.perf_counter()

with AUDIO.open("rb") as audio_file:
    response = requests.post(
        "https://api.elevenlabs.io/v1/speech-to-text",
        headers={"xi-api-key": api_key},
        data={
            "model_id": "scribe_v2",
            "language_code": "pl",
            "tag_audio_events": "false",
        },
        files={"file": ("test_pl.m4a", audio_file, "audio/mp4")},
        timeout=180,
    )

response.raise_for_status()
scribe = response.json()
scribe_seconds = time.perf_counter() - start

(OUTPUT / "scribe.txt").write_text(scribe["text"].strip(), encoding="utf-8")

print("\n=== WHISPER ===")
print(whisper["text"])
print(f"Elapsed: {whisper_seconds:.2f} s")

print("\n=== SCRIBE V2 ===")
print(scribe["text"])
print(f"Elapsed: {scribe_seconds:.2f} s")
