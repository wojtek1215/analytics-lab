# TODO — next steps

Status: `polish_asr_eval_v2` / `pl_wer_normalized_v1` is **FROZEN** primary for new reports (2026-10-27). Legacy `pl_basic_v1` remains frozen for historical artifacts. `pl_numbers_v1` stays sensitivity-only.

## P1 — Freeze and audit v2

- [x] Implement `pl_wer_normalized_v1` + offline CLI `scripts/generate_smoke_report_v2.py`
- [x] Smoke v2 artifacts under `results/evaluation/v2/`
- [x] Smoke review annotations filled and owner-reviewed (`results/evaluation/v2/smoke_review_annotations.json`); documented in `docs/evaluation_protocol.md`
- [x] Freeze `pl_wer_normalized_v1` (no lexicon/brand expansion against holdout errors)
- [ ] Confirm unsupported/ambiguous cases on a small held-out sample during / after pilot scaling (without retuning the frozen normalizer)

## P2 — Alignment + error taxonomy (legacy v0)

- [x] Offline diagnostic: jiwer chunks with ref/hyp spans (`alignment.py`)
- [x] Tag edit mass: `number_format`, `proper_name`, `lexical`, `homophone`, `insertion_extra`, `ambiguous`
- [x] Smoke reports: `results/evaluation/smoke_alignment_pl_basic_v1.json`, `smoke_error_taxonomy.md`
- [x] Assert mass == S+D+I and cross-check primary JSON
- [ ] Manual audit of legacy `ambiguous` / `unclear` rows if still cited
- [x] Keep taxonomy exploratory; primary WER definition is versioned separately

## P2 — Common Voice pilot (next)

- [x] Owner manually downloads Common Voice Scripted Speech 27.0 Polish (`data/raw/cv-corpus-27.0-2026-09-11/pl/`; accept terms; no rehost).
- [x] Deterministic manifest `cv_test_speaker_disjoint_v1`, `seed=20261026`: **10 QA → 40 pilot → 200 holdout** (speaker-disjoint; see `docs/sampling_protocol.md`, `data/manifests/`).
- [x] Results tree `results/cv/{qa,pilot,holdout}/` with `hypotheses|metrics|errors|reports` (see `docs/results_layout.md`).
- [x] Run **local Whisper** on **qa (10)** → `results/cv/qa/hypotheses/whisper/` (`scripts/run_whisper_batch.py`; api_used=false).
- [x] Score qa + **error taxonomy** → `results/cv/qa/metrics|errors|reports/` (`scripts/evaluate_cohort.py`).
- [x] Pilot (40): Whisper + Scribe + offline score → `results/cv/pilot/` (Scribe 5.9% / Whisper 8.1% corpus WER).
- [x] Scribe batch CLI ready (`scripts/run_scribe_batch.py`; dry-run default; `--execute --i-accept-paid-api` gated).
- [x] ElevenLabs Scribe **live** qa(10) → `results/cv/qa/hypotheses/scribe/` (10/10 ok).
- [x] Review pilot hard cases (owner listen + Whisper/Scribe audit); exclusion/reporting/`pathological_hyp_v1` locked in `docs/evaluation_protocol.md` (2026-10-28).
- [x] Implement `pathological_hyp_v1` auto-flag in report/eval tooling (sensitivity table; does not change primary WER) — pilot rescored 2026-10-28 → `results/cv/pilot/errors/pathological_hyp_v1.{json,md}`.
- [x] Automated holdout audio preflight (2026-10-28): `scripts/preflight_cv_clips.py` → `results/cv/holdout/errors/preflight_audio.json` — **0 issues** on N=200 (pilot N=40 also 0).
- [ ] Holdout when methodology locked; paired CI for larger N.
- [ ] For larger N, use appropriate paired uncertainty estimation (not applicable to N=1 smoke).
- [ ] Product framing: *when* Scribe is better/worse than Whisper for Polish (**which error types**, content vs format), not a single ranking.

## P3 — Optional future experiment (not primary accuracy)

- [ ] Scribe raw `text` vs `transcript_edit` / `edited_transcript` (post-processing), scored separately from primary ASR WER. See `docs/asr_inference_config_audit.md`.

## Explicit non-goals right now

- Do not treat `pl_numbers_v1` as primary.
- Do not overwrite `results/smoke/` or legacy `results/evaluation/smoke_*` artifacts.
- Do not expand number lexicon / brand lists against holdout / pilot errors (frozen `pl_wer_normalized_v1`).
- Do not run Common Voice or paid API batches as part of routine offline rescoring.
- Do not use review annotations to change primary WER.
