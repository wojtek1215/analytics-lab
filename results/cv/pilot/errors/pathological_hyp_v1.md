# Pathology impact — `cv27_pl_pilot`

**Rule:** `pathological_hyp_v1`

Pathology impact estimates how much catastrophic ASR collapse inflates the headline WER, while keeping those clips in the primary score for transparency.

- **Primary corpus WER** — headline (all clips).
- **Pathology-excluded WER** — sensitivity after dropping auto-flagged clips for that model only.
- **Pathology impact (pp)** — primary − pathology-excluded, in percentage points (positive ⇒ flagged collapses worsen the headline).

## Summary

| Model | Flagged / scored | Primary WER | Pathology-excluded WER | Pathology impact (pp) |
|---|---:|---:|---:|---:|
| `scribe_v2` | 0/40 | 5.9% | 5.9% | +0.00 |
| `whisper-large-v3-turbo` | 1/40 | 8.1% | 6.7% | +1.38 |

## Flagged clips

### `common_voice_pl_25378583` — `whisper-large-v3-turbo`

- **Reasons:** `repetition_loop`
- **Reference:** Chciałbym kiedyś zostać pilotem.
- **Hypothesis:** Cześć! Cześć! Cześć! Cześć!
