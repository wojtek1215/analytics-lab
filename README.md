# analytics-lab

Independent technical lab for speech recognition (ASR) evaluation experiments,
with an initial focus on Polish-language smoke tests and reproducible offline
scoring.

## Local setup

```bash
cp .env.example .env
# Edit .env locally. Never commit real secrets or private recordings.

# Core evaluation + tests
uv sync --group dev

# Optional: local smoke transcription (Whisper MLX + ElevenLabs)
uv sync --group dev --group smoke
```

Requires Python 3.14+ (see `.python-version`).

## What runs where

| Piece | Where | Notes |
|---|---|---|
| `data/raw/` audio + reference | **Local only** (gitignored) | Your recording; not published by default |
| `.env` / API keys | **Local only** | Use `.env.example` as a template |
| `results/` hypotheses & reports | **Local** unless you deliberately publish them | Produced by smoke/eval scripts |
| `src/asr_benchmark/` + offline scripts | **GitHub** | Scoring code; no API calls |
| `scripts/smoke_test.py` | **GitHub (code only)** | Needs local audio + key to run |
| `.github/workflows/ci.yml` | **GitHub Actions** | Installs core+dev deps and runs `pytest` |

GitHub CI does **not** run Whisper/Scribe, does **not** read your `.env`, and does
**not** use `data/raw/`. It only checks that the evaluation unit tests pass.

## Offline evaluation

Scoring uses saved hypotheses only (no STT API calls). Protocol:
[docs/evaluation_protocol.md](docs/evaluation_protocol.md).

```bash
uv run pytest
uv run python scripts/evaluate_smoke.py \
  --reference data/raw/test_pl_reference.txt \
  --scribe results/smoke/scribe.txt \
  --whisper results/smoke/whisper.txt \
  --output results/evaluation
```

## Local smoke transcription (optional)

```bash
# Requires data/raw/test_pl.m4a and ELEVENLABS_API_KEY in .env
uv run --group smoke python scripts/smoke_test.py
```

Outputs: `results/smoke/whisper.txt` and `results/smoke/scribe.txt`.
