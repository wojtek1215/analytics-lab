# Cohort: pilot (N=40)

**Manifest:** `data/manifests/cv27_pl_test_speaker_disjoint_v1_pilot.csv`  
**Purpose:** development scoring and the first serious **error-pattern** draft (still speaker-disjoint from qa/holdout).

## Status (2026-10-28)

| Step | Status |
|---|---|
| Whisper hypotheses | **Done** (40/40) |
| Scribe hypotheses | **Done** (40/40) |
| Offline metrics + errors | **Done** → `reports/comparison.md`, `errors/hard_cases.md` |

Primary corpus WER (`pl_wer_normalized_v1`, 271 words): Scribe **5.9%**, Whisper turbo **8.1%**.

Do **not** expand `pl_wer_normalized_v1` against pilot errors. Do **not** peek at holdout ASR results while changing protocol.
