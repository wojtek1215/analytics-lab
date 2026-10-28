# Sampling protocol — Common Voice Polish test split

**Protocol id:** `cv_test_speaker_disjoint_v1`  
**Seed:** `20261026`  
**Manifest version:** `1.0.0`  
**Status:** frozen for qa / pilot / holdout assignment (2026-10-27)

This document defines how clips are selected **before** any ASR scoring on Common Voice. The selection code lives in `src/asr_benchmark/sampling/cv_manifest.py` and is invoked by `scripts/build_cv_manifest.py`.

## Why `test.tsv` (not full `validated.tsv`)

| File | Role in this project |
|---|---|
| `test.tsv` | **Source pool** for qa / pilot / holdout (~10k clips, Mozilla official test split) |
| `validated.tsv` | Full validated pool; overlaps train/dev/test — **not** used for sampling |
| `train.tsv` / `dev.tsv` | Unused for the paired Scribe vs Whisper evaluation sets |
| `clips/` | Local MP3 storage (gitignored under `data/raw/`; never re-hosted) |

Using Mozilla’s `test` split avoids training-split leakage and keeps the sample comparable to other CV-test evaluations, without claiming identity with prior papers’ releases or normalizers.

## Local corpus expected layout

```text
data/raw/cv-corpus-27.0-2026-09-11/pl/
  test.tsv
  clip_durations.tsv
  clips/*.mp3
```

Audio and full TSV dumps stay private/local. Published artifacts are **manifests only** (paths, hashed client ids already present in CV, sentences that are CC0 scripted prompts).

## Selection algorithm (must stay stable)

1. Load `test.tsv` with required columns: `client_id`, `path`, `sentence_id`, `sentence`.
2. Optionally join `clip_durations.tsv` on `path` / `clip`.
3. **Filters** (documented counts are written into the manifest):
   - drop rows missing required fields
   - drop duplicate `path`
   - drop rows whose `clips/<path>` file is missing (`require_audio=True` by default)
   - drop non-positive / missing duration when `require_positive_duration=True` (default)
4. Sort eligible clips by **`path` ascending**.
5. **One clip per `client_id`:** keep the first clip for each speaker in that path order (reduces speaker domination; maximizes speaker diversity).
6. Sort that speaker pool again by `path` ascending.
7. Shuffle with `random.Random(20261026).shuffle(pool)` (Python stdlib MT19937).
8. Assign contiguous slices:
   - `qa` = `pool[0:10]`
   - `pilot` = `pool[10:50]`
   - `holdout` = `pool[50:250]`
9. Assert empty overlaps of `client_id` and `path` across the three splits.

No LLM, no quality-based rejection after seeing model errors, no holdout-driven re-sampling.

## Outputs

Written under `data/manifests/` (no audio bytes):

| Artifact | Purpose |
|---|---|
| `cv27_pl_test_speaker_disjoint_v1.json` | Full provenance + all selected clips |
| `…_qa.csv` / `…_pilot.csv` / `…_holdout.csv` | Split lists for batch runners |
| `…_all.csv` | Combined table |
| `…_report.md` | Human-readable filter stats and overlap check |

Each clip record includes `clip_id`, `path`, `audio_relative`, `client_id`, `sentence_id`, `sentence`, votes, `duration_ms`, and `sentence_sha256`.

## How to reproduce

```bash
# From repository root (requires local CV extract under data/raw/)
uv run python scripts/build_cv_manifest.py \
  --corpus-dir data/raw/cv-corpus-27.0-2026-09-11/pl \
  --output-dir data/manifests

uv run pytest tests/test_cv_manifest.py
```

Re-running with the same corpus files and seed must yield the **same ordered `path` lists**. The manifest stores `split_tsv_sha256` (and durations sha256 when present) so corpus drift is detectable.

## Usage rules after sampling

| Split | Allowed use |
|---|---|
| `qa` (10) | Wire Whisper + offline scorer; fix I/O bugs |
| `pilot` (40) | Development metrics, error taxonomy practice, budget checks |
| `holdout` (200) | **Frozen** final paired evaluation only after methodology lock |

Do **not** change the normalizer (`pl_wer_normalized_v1`) or re-draw samples after inspecting holdout ASR errors. If a bug forces a resampling, bump the protocol id and document the reason.

## Explicit non-goals

- Physically moving or copying MP3s out of `clips/`
- Sampling from `validated.tsv` for the primary study sets
- Paid ElevenLabs calls as part of manifest construction
- Identifying speakers beyond the anonymized `client_id` already in Common Voice
