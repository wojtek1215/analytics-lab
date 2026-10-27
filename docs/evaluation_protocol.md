# Evaluation protocol — Polish ASR smoke / corpus scoring

This document covers two versioned protocols:

| Protocol | Primary metric | Evaluation code | Status |
|---|---|---|---|
| Legacy (v1) | WER after `pl_basic_v1` | `1.0.0` | Frozen; historical smoke reports immutable |
| `polish_asr_eval_v2` | WER after `pl_wer_normalized_v1` | `2.0.0` | Current primary for new reports |

Secondary metrics under v2 include legacy `wer_pl_basic_v1`, sensitivity `wer_pl_numbers_v1`, and CER under the matching profiles.

## Scope

Both protocols score **already produced** hypotheses against a frozen reference. They do not call STT models or the ElevenLabs API.

## `pl_basic_v1` normalizer

Applied identically to reference and hypothesis:

1. Unicode **NFC**
2. **`casefold`** (case-insensitive)
3. Protect decimal separators between digits (`97,5`, `97.5`) so they are not treated as word breaks
4. Replace every Unicode punctuation character (category `P*`) with a space — including quotes, commas used as clause separators, hyphens, and apostrophes
5. Collapse whitespace and strip ends
6. Restore protected decimal separators

**Preserved:** Polish diacritics, digit characters.  
**Not done:** LLM rewriting, synonym maps, equating `2026` with spelled-out Polish numbers, model-specific fixes.

### Implications (intentional)

| Example | Effect under `pl_basic_v1` |
|---|---|
| `„Zażółć gęślą jaźń!”` vs `zażółć gęślą jaźń` | WER = 0, CER = 0 |
| `łaska` vs `laska` | error (diacritic is semantic) |
| `2026` vs `dwa tysiące dwudziesty szósty` | error (digits ≠ words) |
| `GPT-6` | tokens `gpt` + `6` |
| `ChatGPT` vs `chat GPT` | one token vs two → edit cost |

## `pl_numbers_v1` — sensitivity profile (not primary)

Optional normalizer for **digit↔word format sensitivity**. Primary headline scores stay on `pl_basic_v1`. Smoke rescoring CLI defaults to `pl_basic_v1` and must not switch primary without an explicit protocol change.

### Pipeline

1. Run full `pl_basic_v1`
2. Unify digit decimals: `97.5` → `97,5`
3. Rewrite **covered** spelled cardinals / year-like ordinal phrases to digits (deterministic lexicon + parser)
4. Rewrite `… przecinek …` decimals to `N,M` (e.g. `dziewięćdziesiąt siedem przecinek pięć` → `97,5`)

Use via `compute_metrics(..., normalization_version="pl_numbers_v1")` only for paired sensitivity tables.

### Covered (v1)

- Integers and simple compounds roughly in `0–999` plus thousands via `tysiąc` / `tysiące` / `tysięcy`
- Year-like readings such as `dwa tysiące dwudziesty szósty` / `… dwudziestym szóstym` → `2026`
- Digit forms already present (`120`, `97,5`)

### Explicit limitations (Polish inflection)

- Common **case/gender forms** of covered number words are collapsed to the same digit (`dwudziesty` ≈ `dwudziestym` → `20`). That **hides morphological errors inside number phrases** on purpose: this profile asks “same quantity, different surface form?”, not “correct Polish declension?”.
- **Out of scope:** complex dates, mixed alphanumerics, currencies as values, fractions beyond `przecinek`, ordinals used as non-numeric discourse, uncovered inflectional variants, multi-word quantities the parser does not recognize (left as words → still cost WER).
- Never tune the lexicon against holdout ASR errors. Extend only with versioned tests.

### Aggregation guard

`aggregate_corpus` rejects mixed `normalization_version` **or** mixed `evaluation_version` so sensitivity and primary rows cannot be silently pooled.

## WER / CER definitions

- **WER** = `(S + D + I) / N_words_ref` on whitespace-tokenized normalized text.
- **CER** = `(S + D + I) / N_chars_ref` on characters of the normalized string, **including spaces**.
- Edit counts come from `jiwer.process_words` / `jiwer.process_characters` with **tokenize-only** transforms (no second pass of case/punct stripping).
- Empty reference after normalization → validation error (`EmptyReferenceError`), never WER = 0 by silence.

## Aggregation

- **Corpus WER/CER** = sum of edit operations / sum of reference units across clips.
- Do **not** report an unweighted mean of per-clip percentages as the headline score.
- Pair models only on the same `clip_id` + shared reference + same `normalization_version` and `evaluation_version`.

## Smoke inputs (read-only)

| Role | Path |
|---|---|
| Audio | `data/raw/test_pl.m4a` |
| Reference | `data/raw/test_pl_reference.txt` |
| Scribe hypothesis | `results/smoke/scribe.txt` |
| Whisper hypothesis | `results/smoke/whisper.txt` |
| Rescored outputs | `results/evaluation/smoke_pl_basic_v1.json`, `smoke_comparison.md` |

Historical plan notes (Scribe WER 10.3% / CER 2.4%; Whisper WER 20.7% / CER 6.4%) were **not** produced by this repository. Under `pl_basic_v1` the smoke rescore is higher (see `results/evaluation/smoke_comparison.md`), mainly because digit↔word expansions count as errors and because the earlier notes had no checked-in normalizer. Do not rewrite `results/smoke/`.

## Alignment + error taxonomy (`taxonomy_v0`)

Exploratory diagnostics on top of primary `pl_basic_v1` WER. **Does not change** headline metrics.

1. `align_words` uses the same jiwer `WORD_TRANSFORM` as WER and exposes S/D/I chunks with ref/hyp token spans.
2. Unit of accounting = **token edit mass** (`edit_mass` sums to `S+D+I`).
3. Chunk tags: `number_format`, `proper_name`, `lexical`, `homophone` (closed list: `morze`/`może`), `insertion_extra` (optional note `hallucination_trailing`), `ambiguous`.
4. `content_impact`: `format_only` | `content_changing` | `unclear` — heuristic, not semantic ground truth.
5. One jiwer chunk can mix error types → prefer `ambiguous` over forced single-label purity.

Outputs (read-only w.r.t. smoke hypotheses):

- `results/evaluation/smoke_alignment_pl_basic_v1.json`
- `results/evaluation/smoke_error_taxonomy.md`

```bash
uv run python scripts/diagnose_smoke_errors.py
```

Cross-checks against `smoke_pl_basic_v1.json` when present. Auxiliary column: whole-clip `pl_numbers_v1` WER (sensitivity only).

### What to automate later (Common Voice)

Automate early: alignment export, mass assert vs S/D/I, number-lexicon signal, trailing-insert candidates, per-clip JSON.  
Keep semi-manual: final `ambiguous` labels, new homophones, brand-list growth, semantic “did meaning change?” for complex substitutions.

## How to run

```bash
# From the repository root
uv run pytest

# Legacy v1 rescore (writes results/evaluation/smoke_*)
uv run python scripts/evaluate_smoke.py \
  --reference data/raw/test_pl_reference.txt \
  --scribe results/smoke/scribe.txt \
  --whisper results/smoke/whisper.txt \
  --output results/evaluation
uv run python scripts/diagnose_smoke_errors.py

# Protocol v2 offline report (writes only results/evaluation/v2/)
uv run python scripts/generate_smoke_report_v2.py
```

## Known Polish limitations (legacy + shared)

- Homophones (`morze` / `może`) are distinct tokens; quality depends on the model, not the scorer.
- Brand tokenization (`ChatGPT`, `ElevenLabs`, `GitHub`) interacts with hyphen/space rules.
- Number style (digits vs words) dominates some edit costs when a model expands numerals under `pl_basic_v1`.
- Scripted / read speech (future Common Voice) differs from conversational audio; this protocol stays fixed across domains.

---

## `polish_asr_eval_v2`

**Protocol id:** `polish_asr_eval_v2`  
**Primary metric:** `wer_pl_normalized_v1` — WER after `pl_wer_normalized_v1`  
**Evaluation code version:** `2.0.0`  
**Taxonomy:** `taxonomy_v2` (exploratory; does not change WER)  
**Normalizer status:** **FROZEN** as of 2026-10-27 (`pl_wer_normalized_v1`)

Goal: make the primary score insensitive to non-semantic formatting differences (digit↔word numbers, `%`↔`procent`, currency abbreviations, unambiguous brand spacing) while preserving meaning-bearing differences (wrong quantities, negations, homophones, brand misspellings, hallucinations).

### Freeze decision (2026-10-27)

`pl_wer_normalized_v1` is the locked primary normalizer for the Common Voice pilot and subsequent paired scoring.

- Do **not** expand number lexicons, brand bigrams, or unit tables against holdout / pilot errors.
- Any rule change requires a **new** normalization version id (do not silently edit this freeze).
- Remaining smoke edits after normalization are treated as content / ambiguity / quoted-form issues for qualitative review — not as reasons to weaken the primary WER normalizer before the pilot.
- Smoke clip `test_pl` was used during normalizer development and is **not** an independent holdout.

### Symmetry and independence

- The same normalizer is applied to reference and hypothesis.
- Normalization does not depend on model identity or on whether a string is labeled reference vs hypothesis.
- No LLM is used for primary normalization.
- Rules are not tuned to favor a specific ASR system.

### Pipeline (`pl_wer_normalized_v1`)

1. Unicode NFC + `casefold`
2. Pre-punctuation symbol pass: `%` → `procent`; `€`/`$` → unit abbrev tokens; leading minus before digits → `minus`
3. Frozen `pl_basic_v1` (punctuation → spaces; decimal separators protected)
4. Token rules (versioned, each emitting optional trace records):
   - Nominative cardinals → digits (strict agreement on `tysiąc`/`tysiące`/`tysięcy`, `milion*`, `miliard*`)
   - `… przecinek …` decimals → `N,M`
   - Safe digit decimal unify: single `.` with non-thousands-like fraction → `,`
   - Year readings with ordinals only when followed by `rok`/`roku`/`rokiem`
   - Unit abbreviations (`zł`, `pln`, `eur`, `usd`, `kg`, `g`, `km`) expanded to agreeing full forms after a numeric token
   - Brand spacing: `chat gpt`→`chatgpt`, `eleven labs`→`elevenlabs`, `git hub`→`github` only

Optional analysis-only ablation via `enabled_rules` (does not define a new primary version).

Trace API: `normalize_with_trace(text) -> (normalized_text, transformations)`. Scoring uses the string only; the trace must not alter results.

### Supported equivalences (examples)

| Forms treated as equivalent when meaning matches |
|---|
| `120` ↔ `sto dwadzieścia` |
| `97,5 procent` ↔ `97,5%` |
| `120 złotych` ↔ `120 zł` ↔ `sto dwadzieścia złotych` |
| `W 2026 roku` ↔ `W dwa tysiące dwudziestym szóstym roku` |
| `ChatGPT` ↔ `chat GPT` |
| `ElevenLabs` ↔ `Eleven Labs` |
| `-20` ↔ `minus dwadzieścia` |

### Unsupported / ambiguous (left unchanged or not equated)

- Oblique number forms (`trzech`, `stu`, `tysiąca`, …)
- Invalid scale agreement (`pięć tysiące`)
- Standalone `jeden`/`jedna`/`jedno` without a supported unit
- Ambiguous separators: `1.234`, `1,234`, version-like `1.2.3`, leading zeros
- Homophones (`morze` / `może`)
- Negations and quantity changes
- Brand misspellings (`Git Hap`, `GitHab`) vs `GitHub`
- Percentage *points* vs percent
- Missing units (never inferred)
- Already-spelled unit agreement errors (`1 złotych` stays as written)

### Over-normalization risks (documented)

- Gender collapse: `dwa` / `dwie` → `2`
- Year ordinal case collapse (`dwudziesty` / `dwudziestym`)
- `%` always becomes invariable `procent`
- Brand bigram list was validated on the smoke clip (frozen with this version; do not expand on pilot/holdout errors)

### WER / CER / aggregation

- WER = `(S + D + I) / N` with `N` from the **normalized** reference for the selected profile (`jiwer.process_words`).
- CER uses character Levenshtein on the normalized strings **including spaces** (`jiwer.process_characters`).
- Corpus aggregation: `sum(S+D+I) / sum(N)` — never the mean of per-clip percentages.
- `aggregate_corpus` rejects mixed `normalization_version` or `evaluation_version`.
- Empty normalized reference → `EmptyReferenceError`.

### Entity evaluation

Named-entity accuracy, annotated number-value accuracy, and critical meaning-error rates are **unavailable** unless verified annotations exist. Do not invent entity labels from heuristics and report them as ground truth.

### Error taxonomy (`taxonomy_v2`)

Separates Levenshtein ops (S/D/I) from interpretation. Exclusive primary categories account for edit mass; secondary tags may overlap and are labeled as such. Automatic semantic impact: `equivalent_formatting` | `content_difference` | `undetermined`. Automatic labels use `review_status=auto_inferred` until reviewed.

WER reduction across profiles is always computed from scorer outputs, never by summing taxonomy tags. **Review annotations never change WER/CER.**

### Smoke review annotations

Path: [`results/evaluation/v2/smoke_review_annotations.json`](../results/evaluation/v2/smoke_review_annotations.json)

Purpose: qualitative audit of remaining alignment edits under `pl_wer_normalized_v1` after automatic `taxonomy_v2` tagging. Used to decide whether the normalizer is ready to freeze — not to rescale primary WER.

| Field | Role |
|---|---|
| `auto_primary_category` | Label from `taxonomy_v2` (machine) |
| `human_label` | Reviewer / assisted label for the same span |
| `human_semantic_impact` | Reviewer judgment of meaning impact for that span |
| `reviewer` | Optional reviewer identity string |
| `notes` | Free-text rationale |

**Status (2026-10-27):** labels and notes are filled for all smoke edit rows and reviewed by the clip owner (owner-recorded audio). Residual smoke errors (homophone order, quoted `Git Hap` vs `GitHab`/`GitHub`, Whisper content substitutions, trailing `koniec`) are intentionally left visible to WER and do not justify changing `pl_wer_normalized_v1` rules before the pilot.

Optional finer impact vocabulary in the review file (`none` / `minor` / `moderate` / `major`) is for human notes only; it is not a second WER metric and is not required to match the automatic three-way impact enum.

### Versioning rules

- Any change to rules, lexicons, brand lists, or unit tables requires a **new** normalization version id.
- Historical `pl_basic_v1`, `pl_numbers_v1`, and legacy smoke reports under `results/evaluation/` (not `v2/`) must remain byte-stable.
- Do not overwrite `results/smoke/`.

### Methodology references (adopted / adapted / not implemented)

Public references informing this protocol (no claim of identity or endorsement):

- [Artificial Analysis speech-to-text methodology](https://artificialanalysis.ai/methodology/speech-to-text)
- [AssemblyAI benchmarks](https://www.assemblyai.com/benchmarks)

| Principle | Status |
|---|---|
| Same normalization for reference and hypotheses | Adopted |
| WER via Levenshtein / edit distance | Adopted (`jiwer`) |
| Normalize equivalent numeric / currency / percent / unit forms | Adapted for Polish |
| Preserve meaning-bearing differences | Adopted |
| Explicit methodology versioning | Adopted |
| Separate quality, latency, cost | Partially adopted (quality offline; latency/cost out of this scorer) |
| English-centric published normalizer as-is | **Not** implemented |
| Entity / error-type evaluation with verified labels | Adapted (taxonomy exploratory; entity metrics gated on annotations) |
| Identical audio + pipeline across systems | Adopted for paired smoke/rescore |

### v2 outputs

| Path | Role |
|---|---|
| `results/evaluation/v2/smoke_metrics.json` | Machine-readable multi-profile scores + metadata |
| `results/evaluation/v2/smoke_alignment.csv` | Edit ops + taxonomy rows |
| `results/evaluation/v2/smoke_taxonomy.json` | Per-model taxonomy summary |
| `results/evaluation/v2/smoke_review_annotations.json` | Smoke edit review (freeze evidence; does not alter WER) |
| `results/evaluation/v2/smoke_comparison_v2.md` | Benchmark report (sections A–I) |

### Known limitations (v2)

- Smoke N = 1; scripted speech; sample used during normalizer development → not an independent holdout.
- Polish morphology coverage is incomplete; oblique forms are intentionally conservative.
- Some acoustic ambiguities require human review.
- No confidence intervals from one clip.

## Next work (TODO)

See `docs/TODO_next.md`: normalizer frozen; next is Common Voice 40-clip pilot (Whisper first; no unpaid API batches without approval).
