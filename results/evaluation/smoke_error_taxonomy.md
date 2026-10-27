# Smoke error taxonomy (`taxonomy_v0`)

- **clip_id:** `test_pl`
- **normalization (primary):** `pl_basic_v1`
- **taxonomy:** `taxonomy_v0`

Heuristics are exploratory. Tags on a chunk may be `ambiguous`; one edit operation does not always map to one semantic error. Primary WER is unchanged.

## Consistency with primary WER

| Model | S | D | I | N | mass | WER | vs baseline JSON |
|---|---:|---:|---:|---:|---:|---:|---|
| scribe_v2 | 7 | 1 | 7 | 58 | 15 | 25.9% | OK |
| whisper-large-v3-turbo | 12 | 1 | 3 | 58 | 16 | 27.6% | OK |

## Format vs content (edit mass)

| Model | format_only | content_changing | unclear |
|---|---:|---:|---:|
| scribe_v2 | 80.0% | 20.0% | — |
| whisper-large-v3-turbo | 37.5% | 62.5% | — |

## Mass by tag

| Model | number_format | proper_name | lexical | homophone | insertion_extra | ambiguous |
|---|---:|---:|---:|---:|---:|---:|
| scribe_v2 | 10 (67%) | 2 (13%) | 1 (7%) | 2 (13%) | 0 (0%) | 0 (0%) |
| whisper-large-v3-turbo | 0 (0%) | 6 (38%) | 8 (50%) | 1 (6%) | 1 (6%) | 0 (0%) |

## Auxiliary: `pl_numbers_v1` WER (not primary)

| Model | pl_basic_v1 WER | pl_numbers_v1 WER |
|---|---:|---:|
| scribe_v2 | 25.9% | 8.6% |
| whisper-large-v3-turbo | 27.6% | 27.6% |

## Operations — `scribe_v2`

| # | op | REF | HYP | mass | tag | impact | notes |
|---|---|---|---|---:|---|---|---|
| 1 | insert | ∅ | dwa tysiące dwudziestym | 3 | number_format | format_only | pl_numbers_v1_signal |
| 2 | substitute | 2026 | szóstym | 1 | number_format | format_only | pl_numbers_v1_signal |
| 3 | insert | ∅ | dziewięćdziesiąt siedem przecinek | 3 | number_format | format_only | pl_numbers_v1_signal |
| 4 | substitute | 97,5 | pięć | 1 | number_format | format_only | pl_numbers_v1_signal |
| 5 | substitute | ale | a | 1 | lexical | content_changing | — |
| 6 | insert | ∅ | sto | 1 | number_format | format_only | pl_numbers_v1_signal |
| 7 | substitute | 120 | dwadzieścia | 1 | number_format | format_only | pl_numbers_v1_signal |
| 8 | substitute | morze | może | 1 | homophone | content_changing | closed homophone list (morze/może) |
| 9 | substitute | może | morze | 1 | homophone | content_changing | closed homophone list (morze/może) |
| 10 | substitute | git | githab | 1 | proper_name | format_only | — |
| 11 | delete | hap | ∅ | 1 | proper_name | format_only | — |

## Operations — `whisper-large-v3-turbo`

| # | op | REF | HYP | mass | tag | impact | notes |
|---|---|---|---|---:|---|---|---|
| 1 | insert | ∅ | chat | 1 | proper_name | format_only | — |
| 2 | substitute | chatgpt | gpt | 1 | proper_name | format_only | — |
| 3 | insert | ∅ | eleven | 1 | proper_name | format_only | — |
| 4 | substitute | elevenlabs | labs | 1 | proper_name | format_only | — |
| 5 | substitute | procent ale koszt | a tylko z | 3 | lexical | content_changing | — |
| 6 | substitute | złotych | zł | 1 | lexical | content_changing | — |
| 7 | substitute | algorytm pomylił | algoryt pomyli | 2 | lexical | content_changing | — |
| 8 | substitute | morze | może | 1 | homophone | content_changing | closed homophone list (morze/może) |
| 9 | substitute | a nazwę | ale w | 2 | lexical | content_changing | — |
| 10 | substitute | git | github | 1 | proper_name | format_only | — |
| 11 | delete | hap | ∅ | 1 | proper_name | format_only | — |
| 12 | insert | ∅ | koniec | 1 | insertion_extra | content_changing | hallucination_trailing |

## Interpretation (from counted mass)

Scribe edit mass is dominated by number-related tags (number_format=66.7%, ambiguous-with-numbers often nearby; ambiguous=0.0%); format_only impact ≈ 80.0%. Whisper retains similar headline WER but more lexical=50.0%, proper_name=37.5%, insertion_extra=6.2%; content_changing ≈ 62.5%. Nearly equal WER therefore does not imply similar error types.

## Manual audit

Review rows tagged `ambiguous` / impact `unclear` before quoting percentages in external reports.
