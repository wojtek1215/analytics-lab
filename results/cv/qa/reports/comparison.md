# Cohort comparison — `cv27_pl_qa`

- **Protocol:** `polish_asr_eval_v2` / eval `2.0.0`
- **Primary metric:** WER after `pl_wer_normalized_v1`
- **Clips in manifest:** 10
- **Missing hypotheses:** 0
- **Offline only:** `api_used=False`, `asr_inference_performed=False`

## Corpus WER / CER

| Model | Basic WER | Numbers WER | **Normalized WER** | Norm CER | Norm S/D/I | N_words |
|---|---:|---:|---:|---:|---:|---:|
| `scribe_v2` | 4.3% | 4.3% | **4.3%** | 1.6% | 3/0/0 | 69 |
| `whisper-large-v3-turbo` | 17.4% | 17.4% | **17.4%** | 4.4% | 8/1/3 | 69 |

## Error taxonomy (primary profile)

Edit mass by automatic `taxonomy_v2` category (does **not** change WER).

### `scribe_v2` — total edit mass 3

| Category | Edit mass |
|---|---:|
| `morphology` | 2 |
| `lexical_substitution` | 1 |

Impact: `content_difference`=3

### `whisper-large-v3-turbo` — total edit mass 12

| Category | Edit mass |
|---|---:|
| `lexical_substitution` | 4 |
| `morphology` | 4 |
| `insertion` | 3 |
| `deletion` | 1 |

Impact: `content_difference`=9, `undetermined`=3

## Hard cases

See [`../errors/hard_cases.md`](../errors/hard_cases.md) for clip-level examples (where models fail most).

## Limitations

- N = 10 QA clips; not a population estimate.
- Holdout must not guide methodology changes.
- Taxonomy labels are auto-inferred until human review.
