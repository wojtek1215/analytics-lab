# Cohort: holdout (N=200)

**Manifest:** `data/manifests/cv27_pl_test_speaker_disjoint_v1_holdout.csv`  
**Purpose:** frozen final paired evaluation.

## Freeze rules

- Clip list is fixed in the sampling protocol (`cv_test_speaker_disjoint_v1`).
- Do not retune the normalizer, taxonomy rules, or sample after inspecting holdout ASR errors.
- Fill `hypotheses/`, `metrics/`, `errors/`, and `reports/` only when running the locked evaluation pass.
- Scribe batch requires explicit budget approval.

Error analysis here should **confirm** patterns seen in pilot, then feed `reports/decision_memo.md` (when written) — still with uncertainty and limitations stated.

## Audio preflight (2026-10-28) — OK

Automated technical QC only (missing / 0-byte / unreadable / tiny `duration_ms`). Does **not** check ref↔audio content.

| Item | Value |
|---|---|
| Command | `uv run python scripts/preflight_cv_clips.py --manifest data/manifests/cv27_pl_test_speaker_disjoint_v1_holdout.csv --json-out results/cv/holdout/errors/preflight_audio.json` |
| Report | [`errors/preflight_audio.json`](errors/preflight_audio.json) |
| Result | **Pass:** `n_clips=200`, `n_clips_with_issues=0`, `n_issue_rows=0` |

Same check on pilot (`…_pilot.csv`, N=40) also returned 0 issues (no separate JSON saved).
