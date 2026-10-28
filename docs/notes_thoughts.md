# Notes & thoughts — open questions for follow-up

Living scratchpad for methodology decisions and suspicious findings.  
Not a frozen protocol; not a publication claim. Hand this file + linked artifacts to the next agent/model session when continuing the CV benchmark.

**Normative lock (2026-10-28):** clip exclusion, reporting layers, glossary, and `pathological_hyp_v1` live in [`docs/evaluation_protocol.md`](evaluation_protocol.md) — use that file, not this scratchpad, as the source of truth.

**Holdout audio preflight (2026-10-28):** ran `scripts/preflight_cv_clips.py` on holdout N=200 → [`results/cv/holdout/errors/preflight_audio.json`](../results/cv/holdout/errors/preflight_audio.json) — **OK** (`n_clips_with_issues=0`). Also noted in `results/cv/holdout/README.md`.

**`pathological_hyp_v1` (2026-10-28):** implemented in eval; pilot offline rescore → [`results/cv/pilot/errors/pathological_hyp_v1.md`](../results/cv/pilot/errors/pathological_hyp_v1.md). Whisper flagged 1/40 (`25378583` repetition); Scribe 0/40. Primary WER unchanged (8.1% / 5.9%); Whisper **pathology-excluded WER** ≈ 6.7% → **pathology impact** ≈ +1.4 pp on the headline. Normative wording in `docs/evaluation_protocol.md` (scorecard-ready row: *Pathology impact*).

**Related report:** [`results/cv/pilot/errors/hard_cases.md`](../results/cv/pilot/errors/hard_cases.md)  
**Cohort:** pilot N=40 (`cv27_pl_test_speaker_disjoint_v1`, seed `20261026`)  
**Primary metric:** WER after `pl_wer_normalized_v1`

---

## 2026-10-28 — Owner audio audit of two worst pilot clips

### Human check (owner)

Owner listened to audio vs Common Voice `sentence` reference for:

| clip_id | Audio path | Reference |
|---|---|---|
| `common_voice_pl_25378583` | `data/raw/cv-corpus-27.0-2026-09-11/pl/clips/common_voice_pl_25378583.mp3` | Chciałbym kiedyś zostać pilotem. |
| `common_voice_pl_32077476` | `data/raw/cv-corpus-27.0-2026-09-11/pl/clips/common_voice_pl_32077476.mp3` | Rząd w Hanoi jednostronnie dysponuje mieniem kościoła wbrew wcześniejszym umowom |

**Finding:** audio **matches** the reference text. Recordings are **not the cleanest**, but content is correct. Therefore these are **not** “bad CV labels / wrong sentence” exclusions under a ref≠audio rule.

### Model outputs (from hard_cases.md)

**`common_voice_pl_25378583`**

- Scribe WER 75%: *Chciałbym kiedyś zatańczyć z Piotrem.* (wrong content, still Polish sentence-shaped)
- Whisper large-v3-turbo WER 100%: **`Cześć! Cześć! Cześć! Cześć!`** — looks like a **repetition / greeting hallucination**, not a near-miss of “pilotem”

**`common_voice_pl_32077476`**

- Both models fail badly (names / foreign toponym + church lexicon); Whisper WER 60%, Scribe 90% on this clip
- Still “attempted transcription”, not pure looped garbage like the `Cześć!` case

---

## 2026-10-28 — Whisper + Scribe audit re-run (executed)

**Artifacts:** [`results/cv/pilot/audit/summary.md`](../results/cv/pilot/audit/summary.md), `batch_summary.json`, Whisper dirs `audit/{baseline,temp0,no_condition}/`, Scribe dir `audit/scribe/`  
**Runner:** `scripts/run_whisper_hard_case_audit.py` (`--whisper`; later `--no-whisper --scribe --i-accept-paid-api`)  
**Manifest:** `data/manifests/cv27_pl_pilot_hard_case_audit_2.csv`  
**Guardrail:** pilot hypothesis SHA-1 unchanged (Whisper **and** Scribe); pilot WER **not** recomputed.

### Findings

| Clip | Whisper audit | Scribe audit |
|---|---|---|
| `25378583` | **Unstable wrong** (≠ frozen `Cześć! ×4`, ≠ ref; mixed-script trash; ablations fail) | Frozen pilot wrong (*zatańczyć z Piotrem*); **audit matches reference** → transient miss |
| `32077476` | **Identical** to frozen pilot (stable hard miss) | Still wrong; mild jitter vs frozen (*Żalycha*/*Żalcha*, *dyskutuje*/*dysponuje*) |

### Closed vs still open

1. **Re-run as separate audit?** — **Done** for **both** Whisper and Scribe on the same two clips.
2. **Bug vs model?** — Still points away from path wiring. Whisper: decode instability on `25378583`. Scribe: can recover that clip on retry; Hanoi clip remains hard for both.
3. **Known Whisper hallucinations?** — Strengthened (unstable pathological hyps + non-PL script junk).
4. **Exclusion rules?** — Unchanged: do **not** exclude for wrong reference.
5. **Impact on pilot numbers** — Keep clips in primary WER; narrative should contrast Whisper instability vs Scribe transient miss on `25378583`, and shared hard failure on `32077476`.
6. **Holdout checklist** — Dual-system audit for these clips is **done**; remaining checklist items still open.

---

## Open questions (remaining)

1. ~~Re-run as a separate audit?~~ → done 2026-10-28 for Whisper **and** Scribe (see above).
2. ~~Fresh Whisper / temp0 / no_condition on `25378583`?~~ → done; none recover reference. ~~Scribe re-run?~~ → done; recovers reference on this clip. Optional later: non-turbo Whisper size comparison.
3. **Are Whisper hallucinations like this known?**  
   Yes in public discussion: Whisper can emit **repeated words/phrases**, especially on **short / noisy / Common Voice–like** clips; community threads discuss repetition loops, silence-related hallucinations, and occasional disappearance on **retry**. Larger models are **not** hallucination-free.  
   Audit adds: even when the exact `Cześć!` string does not repeat, this clip still yields **run-to-run divergent garbage** — still model-side, not proof of miswired paths.

4. **Exclusion rules?**  
   Owner confirmation ⇒ **do not exclude** these clips for “wrong reference”.  
   Optional later policy (must be written before holdout if used): flag **pathological hypotheses** (e.g. high repetition / high script mix) for qualitative reporting while **keeping** them in primary WER, or report WER **with and without** auto-detected hallucination clips as sensitivity—not silent deletion.

5. **Impact on pilot numbers**  
   One Whisper catastrophe on a 4-word clip inflates corpus WER a lot (small N_words). Before holdout 200: decide whether to report **corpus WER + distribution / hard-case narrative**, and whether a **hallucination / repetition detector** is part of the error story (product-relevant for local Whisper).

6. **Before holdout 200 checklist (still open)**  
   - Written exclusion criteria (ref≠audio, silence, corrupt file)—**not** “high WER”  
   - Freeze models + `pl_wer_normalized_v1`  
   - Dry-run Scribe budget on 200  
   - Whisper first locally  
   - ~~Optional: diagnostic re-run of `25378583` (and maybe `32077476`) documented as audit-only~~ → done

---

## Suggested next actions

| Priority | Action | Why |
|---|---|---|
| ~~P0~~ | ~~Separate Whisper + Scribe audit re-run~~ | **Done** → `results/cv/pilot/audit/` |
| P1 | Keep clips in pilot metrics; document Whisper instability vs Scribe transient miss (`25378583`) and shared hard fail (`32077476`) | Honesty + product-relevant failure modes |
| P2 | Optional non-turbo Whisper size check on `25378583` only | Isolate turbo-specific behavior (not required for holdout) |
| P3 | Do **not** retune normalizer on these errors | Frozen `pl_wer_normalized_v1` |

---

## Pointers

- Hard cases: `results/cv/pilot/errors/hard_cases.md`
- Pilot comparison: `results/cv/pilot/reports/comparison.md`
- Hypotheses: `results/cv/pilot/hypotheses/{whisper,scribe}/<clip_id>.txt`
- Manifest row: `data/manifests/cv27_pl_test_speaker_disjoint_v1_pilot.csv`
- Hard-case audit: `results/cv/pilot/audit/summary.md`
- Audit manifest: `data/manifests/cv27_pl_pilot_hard_case_audit_2.csv`
- Whisper batch config (language=pl): `scripts/run_whisper_batch.py` / `src/asr_benchmark/inference/whisper_batch.py`
- Audit runner: `scripts/run_whisper_hard_case_audit.py`
