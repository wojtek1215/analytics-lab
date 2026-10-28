# Common Voice results (`results/cv/`)

Paired Scribe vs Whisper outputs for the frozen sample  
`cv_test_speaker_disjoint_v1` (`seed=20261026`). See `docs/results_layout.md` and `docs/sampling_protocol.md`.

| Cohort | N | Path | Status |
|---|---:|---|---|
| qa | 10 | [`qa/`](qa/) | Scaffold ready — run Whisper next |
| pilot | 40 | [`pilot/`](pilot/) | Scaffold ready — after qa |
| holdout | 200 | [`holdout/`](holdout/) | Scaffold ready — **do not use for methodology tuning** |

Legacy owner smoke remains under `results/smoke/` and `results/evaluation/` (immutable).

**Project emphasis:** cohort reports must include an **error narrative** (`errors/hard_cases.md` + taxonomy), not only WER tables.
