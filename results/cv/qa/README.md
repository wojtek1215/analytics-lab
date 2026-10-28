# Cohort: qa (N=10)

**Manifest:** `data/manifests/cv27_pl_test_speaker_disjoint_v1_qa.csv`  
**Purpose:** end-to-end pipeline check (Whisper → offline metrics → error taxonomy).

## Status

| Step | Status |
|---|---|
| Whisper hypotheses | **Done** (10/10) via `scripts/run_whisper_batch.py` |
| Scribe hypotheses | **Done** (10/10) via `run_scribe_batch.py --execute --i-accept-paid-api` |
| Metrics + error taxonomy | Next |

## Artifacts

| Path | Contents |
|---|---|
| `hypotheses/whisper/*.txt` | Local Whisper hypotheses |
| `hypotheses/_meta/whisper/` | Per-clip latency/status + `batch_summary.json` |
| `hypotheses/scribe/*.txt` | Only after dry-run + budget approval |
| `metrics/` | Per-clip + corpus WER/CER |
| `errors/` | Alignments, taxonomy summary, hard-case write-up |
| `reports/comparison.md` | Short metrics + failure-mode summary |

No methodology changes based on these 10 clips alone.
