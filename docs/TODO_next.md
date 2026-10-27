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

- [ ] Owner manually downloads Common Voice Scripted Speech 27.0 Polish from Mozilla Data Collective (accept terms; no rehost).
- [ ] Deterministic manifest with `seed=20261026`: **10 QA → 20–40 pilot** (frozen holdout 200 — do not peek while tuning).
- [ ] Run **local Whisper first** on the small pilot; score with frozen `pl_wer_normalized_v1` (+ report `pl_basic_v1` / `pl_numbers_v1` sensitivity + `taxonomy_v2`).
- [ ] ElevenLabs Scribe only with explicit budget approval + `--dry-run` beforehand.
- [ ] Identical audio and frozen protocol for both models; corpus WER = sum(edits)/sum(N); paired per-clip differences.
- [ ] For larger N, use appropriate paired uncertainty estimation (not applicable to N=1 smoke).
- [ ] Product framing: *when* Scribe is better/worse than Whisper for Polish (content vs format), not a single ranking.

## P3 — Optional future experiment (not primary accuracy)

- [ ] Scribe raw `text` vs `transcript_edit` / `edited_transcript` (post-processing), scored separately from primary ASR WER. See `docs/asr_inference_config_audit.md`.

## Explicit non-goals right now

- Do not treat `pl_numbers_v1` as primary.
- Do not overwrite `results/smoke/` or legacy `results/evaluation/smoke_*` artifacts.
- Do not expand number lexicon / brand lists against holdout / pilot errors (frozen `pl_wer_normalized_v1`).
- Do not run Common Voice or paid API batches as part of routine offline rescoring.
- Do not use review annotations to change primary WER.
