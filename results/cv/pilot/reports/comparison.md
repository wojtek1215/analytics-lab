# Cohort comparison — `cv27_pl_pilot`

- **Protocol:** `polish_asr_eval_v2` / eval `2.0.0`
- **Primary metric:** WER after `pl_wer_normalized_v1`
- **Clips in manifest:** 40
- **Missing hypotheses:** 0
- **Offline only:** `api_used=False`, `asr_inference_performed=False`

## Corpus WER / CER

| Model | Basic WER | Numbers WER | **Normalized WER** | Norm CER | Norm S/D/I | N_words |
|---|---:|---:|---:|---:|---:|---:|
| `scribe_v2` | 5.9% | 5.9% | **5.9%** | 2.6% | 14/1/1 | 271 |
| `whisper-large-v3-turbo` | 8.5% | 7.8% | **8.1%** | 4.3% | 16/5/1 | 271 |

## Error taxonomy (primary profile)

Edit mass by automatic `taxonomy_v2` category (does **not** change WER).

### `scribe_v2` — total edit mass 16

| Category | Edit mass |
|---|---:|
| `unclear` | 10 |
| `lexical_substitution` | 2 |
| `morphology` | 2 |
| `deletion` | 1 |
| `insertion` | 1 |

Impact: `content_difference`=5, `undetermined`=11

### `whisper-large-v3-turbo` — total edit mass 22

| Category | Edit mass |
|---|---:|
| `unclear` | 9 |
| `deletion` | 3 |
| `lexical_substitution` | 3 |
| `morphology` | 3 |
| `number_format` | 3 |
| `insertion` | 1 |

Impact: `content_difference`=9, `equivalent_formatting`=3, `undetermined`=10

## Pathology impact

Pathology impact estimates how much catastrophic ASR collapse inflates the headline WER, while keeping those clips in the primary score for transparency.

Auto-flag rule `pathological_hyp_v1` does **not** change primary WER. Details: [`../errors/pathological_hyp_v1.md`](../errors/pathological_hyp_v1.md).

| Model | Flagged / scored | Primary WER | Pathology-excluded WER | Pathology impact (pp) |
|---|---:|---:|---:|---:|
| `scribe_v2` | 0/40 | 5.9% | 5.9% | +0.00 |
| `whisper-large-v3-turbo` | 1/40 | 8.1% | 6.7% | +1.38 |

## Hard cases

See [`../errors/hard_cases.md`](../errors/hard_cases.md) for clip-level examples (where models fail most).

## Limitations

- N = 40 QA clips; not a population estimate.
- Holdout must not guide methodology changes.
- Taxonomy labels are auto-inferred until human review.
- Pathological auto-flags are heuristic; primary metrics keep all clips.
