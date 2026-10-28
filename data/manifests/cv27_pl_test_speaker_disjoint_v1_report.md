# Sampling report — `cv_test_speaker_disjoint_v1`

- **Manifest file:** `cv27_pl_test_speaker_disjoint_v1.json`
- **Manifest version:** `1.0.0`
- **Seed:** `20261026`
- **RNG:** `python.random.Random.shuffle`
- **Dataset:** `cv-corpus-27.0-2026-09-11` / locale `pl`
- **Source split:** `test.tsv` (sha256 `76fb82bfa286dc516f6c0b496710b25bb45c11521128b493b107804d734104a0`)

## Requested sample sizes

| Split | N | Purpose |
|---|---:|---|
| qa | 10 | Pipeline / data QA |
| pilot | 40 | Development scoring |
| holdout | 200 | Frozen final evaluation (do not peek while tuning) |

## Filter and pool statistics

| Stage | Count |
|---|---:|
| Source rows | 10094 |
| Missing required fields | 0 |
| Duplicate path | 0 |
| Audio missing | 0 |
| Non-positive duration | 0 |
| Eligible clips | 10094 |
| Unique clients (eligible) | 2514 |
| Dropped for one-clip-per-client | 7580 |
| Speaker pool (shuffled) | 2514 |

## Duration (selected clips)

- Clips with duration: 250
- Total duration: 1386924 ms (23.115 minutes)

## Overlap check

All client and path overlap lists must be empty.

```json
{
  "qa_pilot_clients": [],
  "qa_holdout_clients": [],
  "pilot_holdout_clients": [],
  "qa_pilot_paths": [],
  "qa_holdout_paths": [],
  "pilot_holdout_paths": []
}
```

## Reproducibility

```bash
uv run python scripts/build_cv_manifest.py \
  --corpus-dir data/raw/cv-corpus-27.0-2026-09-11/pl \
  --output-dir data/manifests
```

Identical inputs + seed must reproduce byte-identical clip path lists.
Do not retune selection after inspecting holdout ASR errors.
