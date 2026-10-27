# analytics-lab

Independent technical lab for speech recognition (ASR) evaluation experiments,
with an initial focus on Polish-language smoke tests and reproducible offline
scoring.

## Local setup

```bash
cp .env.example .env
# Edit .env locally. Never commit real secrets or private recordings.

uv sync
```

Requires Python 3.14+ (see `.python-version`).

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

Raw audio and reference transcripts under `data/raw/` stay local by default.
Provide your own licensed fixtures before running the smoke evaluator.
