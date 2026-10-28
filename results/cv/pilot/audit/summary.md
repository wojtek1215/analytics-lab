# Pilot hard-case audit (Whisper + Scribe)

**Date:** 2026-10-28  
**Purpose:** Diagnostic re-transcription only. Does **not** overwrite pilot hypotheses or change frozen pilot WER.  
**Manifest:** `data/manifests/cv27_pl_pilot_hard_case_audit_2.csv`  
**Runner:** `scripts/run_whisper_hard_case_audit.py` (`--whisper` / `--scribe --i-accept-paid-api`)  
**Machine summaries:** `batch_summary.json`, `whisper_batch_summary.json` (if present), `scribe_batch_summary.json`

Owner previously confirmed both clips: audio matches Common Voice reference (not wrong-label exclusions).

---

## Side-by-side

### `common_voice_pl_25378583`

Reference: *Chciałbym kiedyś zostać pilotem.*

| Source | Text |
|---|---|
| Frozen pilot Whisper | Cześć! Cześć! Cześć! Cześć! |
| Audit Whisper `baseline` | Jecha od tego logicznego ze şu |
| Audit Whisper `temp0` | Kaj algum kele za te piłotami? |
| Audit Whisper `no_condition` | Jecha od tego logicznego ze şu |
| Frozen pilot Scribe | Chciałbym kiedyś zatańczyć z Piotrem. |
| Audit Scribe | Chciałbym kiedyś zostać pilotem |

**Same-session Whisper note:** An earlier baseline attempt (before an ablation clip-filter fix) also produced `Zapraszam kilka réussimeno 115 Naw польз PRE 되면` — further evidence of run-to-run instability (non-Polish / mixed-script trash).

**Verdict**

- **Whisper:** pathological and **unstable**. Fresh calls stay wrong; often emit non-Polish characters / mixed scripts; never recovered the reference in this audit. Ablations did not help.
- **Scribe:** frozen pilot was a near-miss Polish sentence (*zatańczyć z Piotrem*); **audit re-run matches the reference** (minus final period). So this clip is **not a stable Scribe failure** — treat the pilot error as a **transient / non-deterministic** miss, not a systematic product defect on this utterance.

### `common_voice_pl_32077476`

Reference: *Rząd w Hanoi jednostronnie dysponuje mieniem kościoła wbrew wcześniejszym umowom*

| Source | Text |
|---|---|
| Frozen pilot Whisper | Urząd w kanali jednostronny, wspomnienia imieniem Kościoława wbrew wcześniejszym umowom. |
| Audit Whisper `baseline` | Urząd w kanali jednostronny, wspomnienia imieniem Kościoława wbrew wcześniejszym umowom. |
| Frozen pilot Scribe | Żalycha nowi widno stronę dyskutuje imieniem puścił, brak wcześniejszym umową |
| Audit Scribe | Żalcha nowi widno stronę dysponuje imieniem puścił, brak wcześniejszym umową |

**Verdict**

- **Whisper:** **bit-identical** to frozen pilot → stable hard lexicon / toponym miss.
- **Scribe:** still badly wrong; audit text is **close but not identical** to frozen pilot (*Żalycha*→*Żalcha*, *dyskutuje*→*dysponuje*). Stable **as a hard failure**, with mild output jitter — not a recovery to reference.

---

## Cross-system conclusions

1. Same audio + confirmed labels → failures are **model-side**, not CV ref≠audio exclusions.
2. On the short “pilotem” clip, systems diverge sharply: Whisper → unstable multilingual garbage / loops; Scribe → can be correct on retry after a wrong pilot hyp.
3. On the Hanoi / church lexicon clip, **both** systems fail in a mostly stable way; Whisper more reproducible bit-for-bit.
4. Non-Polish script characters in Whisper audit outputs are consistent with known Whisper decode collapse on short/noisy clips, not with a Polish reference problem.
5. Keep both clips in primary pilot WER; use this folder for qualitative / sensitivity narrative only.

---

## Guardrail check

Pilot hypothesis SHA-1 unchanged after Whisper + Scribe audit writes:

- `results/cv/pilot/hypotheses/whisper/common_voice_pl_25378583.txt` → `22299a2b7c6d6d66251c627577110e566bd3bb3a`
- `results/cv/pilot/hypotheses/whisper/common_voice_pl_32077476.txt` → `00988e19c8ebf671a47e4b22190e079eaee91924`
- `results/cv/pilot/hypotheses/scribe/common_voice_pl_25378583.txt` → `6076341bc0cf59b955c2d4b9179181b2ceb0e356`
- `results/cv/pilot/hypotheses/scribe/common_voice_pl_32077476.txt` → `4dfa0ec502a5af4558b220a9bf5c5e7f8b8ce81b`

Pilot corpus WER / comparison reports were **not** recomputed. Scribe audit used ~9.6 s audio (~$0.0006 public-list estimate).
