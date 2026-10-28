# Holdout audio preflight — 2026-10-28

**Status:** OK (no automated issues)

| Field | Value |
|---|---|
| Script | `scripts/preflight_cv_clips.py` |
| Manifest | `data/manifests/cv27_pl_test_speaker_disjoint_v1_holdout.csv` |
| Machine report | [`preflight_audio.json`](preflight_audio.json) |
| Clips checked | 200 |
| Clips with issues | 0 |
| Issue rows | 0 |
| Gates | file present; size ≥ 1 byte; `duration_ms` ≥ 200; `ffprobe` readable |

This is technical audio QC only. It does **not** validate that spoken content matches the Common Voice sentence (`ref_ne_audio` requires human listen). See `docs/evaluation_protocol.md`.
