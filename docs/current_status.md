# Current status — analytics-lab

**Date:** 2026-10-27  
**Scope:** smoke evaluation frozen; Common Voice sampling manifests generated.

## Environment

| Item | Observed |
|---|---|
| Project root | `/projects/analytics-lab/analytics-lab` |
| Python | 3.14.9 (`.python-version`: `3.14`) |
| Package manager | `uv`; `.venv` present |
| Audio tooling | FFmpeg available |
| Secrets | `.env` present (gitignored); do not print values |
| Common Voice | Local extract `data/raw/cv-corpus-27.0-2026-09-11/pl/` (gitignored) |

## Frozen evaluation

- Primary protocol: `polish_asr_eval_v2` / normalizer `pl_wer_normalized_v1` (see `docs/evaluation_protocol.md`).
- Owner smoke clip rescored under `results/evaluation/v2/` (N=1; not an independent holdout).

## Common Voice sampling (2026-10-27)

| Item | Value |
|---|---|
| Protocol | `cv_test_speaker_disjoint_v1` |
| Seed | `20261026` |
| Source | `test.tsv` (not full `validated.tsv`) |
| Pool | 10 094 eligible → 2 514 speakers (one clip/client) |
| Splits | qa 10 / pilot 40 / holdout 200 (disjoint clients & paths) |
| Duration (250 clips) | ≈ 23.1 minutes |
| Docs | `docs/sampling_protocol.md` |
| Artifacts | `data/manifests/cv27_pl_test_speaker_disjoint_v1*` |
| CLI | `uv run python scripts/build_cv_manifest.py …` |

Audio stays in `clips/`; manifests list paths only. Re-run of the CLI reproduces identical path lists.

## Results layout

Scaffold under `results/cv/{qa,pilot,holdout}/` — each with `hypotheses/`, `metrics/`, `errors/`, `reports/`.  
Documented in `docs/results_layout.md`. **Error analysis is first-class** (taxonomy + hard cases), not a side note to WER.

## Whisper qa batch (2026-10-27)

- CLI: `uv run python scripts/run_whisper_batch.py`
- Model: `mlx-community/whisper-large-v3-turbo`, language `pl`
- Output: `results/cv/qa/hypotheses/whisper/` (10/10 ok) + `_meta/whisper/`
- **API spend: 0**

## Scribe qa batch (2026-10-27)

- CLI: `uv run --env-file .env python scripts/run_scribe_batch.py --execute --i-accept-paid-api`
- 10/10 ok → `results/cv/qa/hypotheses/scribe/` (~7.6 s wall; ~0.6–1.0 s/clip)
- Same audio set as Whisper qa

## QA cohort score (2026-10-27)

Offline `scripts/evaluate_cohort.py` on N=10 (`pl_wer_normalized_v1`, corpus WER):

| Model | WER | CER | S/D/I | N_words |
|---|---:|---:|---:|---:|
| scribe_v2 | 4.3% | 1.6% | 3/0/0 | 69 |
| whisper-large-v3-turbo | 17.4% | 4.4% | 8/1/3 | 69 |

Reports: `results/cv/qa/reports/comparison.md`, hard cases: `results/cv/qa/errors/hard_cases.md`.  
N=10 is pipeline QA only — not a population claim.

## Next action

1. Optional: spot-check hard cases against audio; then Whisper (+ later Scribe) on **pilot 40**.
2. Do not inspect holdout ASR results while changing methodology.
