# Cohort: holdout (N=200)

**Manifest:** `data/manifests/cv27_pl_test_speaker_disjoint_v1_holdout.csv`  
**Purpose:** frozen final paired evaluation.

## Freeze rules

- Clip list is fixed in the sampling protocol (`cv_test_speaker_disjoint_v1`).
- Do not retune the normalizer, taxonomy rules, or sample after inspecting holdout ASR errors.
- Fill `hypotheses/`, `metrics/`, `errors/`, and `reports/` only when running the locked evaluation pass.
- Scribe batch requires explicit budget approval.

Error analysis here should **confirm** patterns seen in pilot, then feed `reports/decision_memo.md` (when written) — still with uncertainty and limitations stated.
