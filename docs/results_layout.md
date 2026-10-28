# Results layout — Common Voice cohorts

**Goal of this project (product analytics framing):** not only *who has lower WER*, but **where each model fails** (error types, examples, content vs format) so a developer can decide when Scribe vs local Whisper is worth it for Polish.

Owner smoke (`results/smoke/`, `results/evaluation/`) stays untouched. New CV work uses **`results/cv/`** only.

## Top-level map

```text
data/manifests/                          # frozen clip lists (no audio)
  cv27_pl_test_speaker_disjoint_v1*.csv

results/cv/
  README.md                              # this tree’s index
  qa/          # N=10  — pipeline + error-analysis dry run
  pilot/       # N=40  — development metrics + taxonomy practice
  holdout/     # N=200 — frozen final paired eval (no methodology peek)
```

Each cohort directory has the **same** internal shape:

```text
results/cv/<cohort>/
  README.md
  hypotheses/
    whisper/                 # one .txt per clip_id (model output)
    scribe/                  # filled only after budget approval
    _meta/                   # optional JSON: latency, model revision, status
  metrics/
    per_clip.csv             # WER/CER/S/D/I per clip × model × profile
    corpus.json              # corpus WER = sum(edits)/sum(N)
  errors/                    # FIRST-CLASS deliverable (not optional)
    alignment.csv            # jiwer ops with ref/hyp spans
    taxonomy_summary.json    # mass by taxonomy_v2 category × model
    hard_cases.md            # curated examples: where models fail most
    review_annotations.json  # optional human labels (never change WER)
  reports/
    comparison.md            # metrics + error narrative for the cohort
```

## Why separate qa / pilot / holdout folders

| Cohort | Role | Error-analysis use |
|---|---|---|
| **qa** | Wire I/O, scorer, taxonomy export | Sanity-check that failure modes are readable |
| **pilot** | Tune *reporting* and example selection only | Draft “where models fail” story; **do not** retune `pl_wer_normalized_v1` |
| **holdout** | One-shot final paired scores | Confirm patterns; freeze decision memo |

Speaker-disjoint manifests live in `data/manifests/`; results folders never re-sample clips.

## Metrics vs errors (both required)

| Artifact | Answers |
|---|---|
| `metrics/corpus.json` | How large is the gap? (WER/CER, paired) |
| `errors/alignment.csv` + `taxonomy_summary.json` | Which edit types dominate (numbers already normalized away, residual lexical/homophone/insertion/…)? |
| `errors/hard_cases.md` | Concrete Polish examples a PM can read |
| `reports/comparison.md` | Combined: magnitude + failure modes + limitations |

Primary scores stay on frozen `pl_wer_normalized_v1`. Taxonomy and reviews **never** rescale WER; they explain remaining edits.

## Naming

- Hypothesis file: `hypotheses/<model>/<clip_id>.txt` where `clip_id` matches the manifest (e.g. `common_voice_pl_20621575.txt`).
- Do not overwrite owner `results/smoke/`.
- Do not store API keys, raw HTTP headers, or Common Voice MP3s under `results/`.

## Next implementation steps

1. Whisper batch writer → `results/cv/qa/hypotheses/whisper/`.
2. Offline scorer + `taxonomy_v2` → `metrics/` + `errors/` for qa.
3. Repeat for pilot; holdout only after methodology lock + explicit Scribe approval for paid side.
