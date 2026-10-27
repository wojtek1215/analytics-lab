# Evaluation protocol — Polish ASR smoke / corpus scoring

**Primary metric:** Word Error Rate after `pl_basic_v1` (`wer_pl_basic_v1`).  
**Secondary:** Character Error Rate after the same normalizer.  
**Evaluation code version:** `1.0.0`  
**Normalization version:** `pl_basic_v1`

## Scope

This protocol scores **already produced** hypotheses against a frozen reference. It does not call STT models or the ElevenLabs API.

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
uv run python scripts/evaluate_smoke.py \
  --reference data/raw/test_pl_reference.txt \
  --scribe results/smoke/scribe.txt \
  --whisper results/smoke/whisper.txt \
  --output results/evaluation
uv run python scripts/diagnose_smoke_errors.py
```

## Known Polish limitations

- Homophones (`morze` / `może`) are distinct tokens; quality depends on the model, not the scorer.
- Brand tokenization (`ChatGPT`, `ElevenLabs`, `GitHub`) interacts with hyphen/space rules.
- Number style (digits vs words) dominates some edit costs when a model expands numerals under `pl_basic_v1`.
- Scripted / read speech (future Common Voice) differs from conversational audio; this protocol stays fixed across domains.

## Next work (TODO)

Common Voice pilot after reviewing smoke taxonomy diagnostics — still no unpaid API batches without approval.
