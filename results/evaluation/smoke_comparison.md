# Smoke evaluation — `pl_basic_v1`

- **clip_id:** `test_pl`
- **normalization_version:** `pl_basic_v1`
- **evaluation_version:** `1.0.0`

## Scores

| Model | WER | CER | S | D | I | N_words | N_chars |
|---|---:|---:|---:|---:|---:|---:|---:|
| scribe_v2 | 25.9% | 21.7% | 7 | 1 | 7 | 58 | 423 |
| whisper-large-v3-turbo | 27.6% | 9.0% | 12 | 1 | 3 | 58 | 423 |

## vs historical notes (plan)

| Model | Historical WER | Recomputed WER | Historical CER | Recomputed CER |
|---|---:|---:|---:|---:|
| scribe_v2 | 10.3% | 25.9% | 2.4% | 21.7% |
| whisper-large-v3-turbo | 20.7% | 27.6% | 6.4% | 9.0% |

## Normalized texts

### scribe_v2

**Reference (normalized):**

```
w 2026 roku sztuczna inteligencja zmienia sposób w jaki pracujemy czy chatgpt whisper i elevenlabs zastąpią kiedyś analityków danych według mojego eksperymentu dokładność rozpoznawania mowy wynosiła 97,5 procent ale koszt przetworzenia tysiąca nagrań przekroczył 120 złotych co ciekawe algorytm pomylił słowa morze i może a nazwę github zapisał jako git hap czy naprawdę możemy ufać automatyzacji automatycznej transkrypcji
```

**Hypothesis (normalized):**

```
w dwa tysiące dwudziestym szóstym roku sztuczna inteligencja zmienia sposób w jaki pracujemy czy chatgpt whisper i elevenlabs zastąpią kiedyś analityków danych według mojego eksperymentu dokładność rozpoznawania mowy wynosiła dziewięćdziesiąt siedem przecinek pięć procent a koszt przetworzenia tysiąca nagrań przekroczył sto dwadzieścia złotych co ciekawe algorytm pomylił słowa może i morze a nazwę github zapisał jako githab czy naprawdę możemy ufać automatyzacji automatycznej transkrypcji
```

### whisper-large-v3-turbo

**Reference (normalized):**

```
w 2026 roku sztuczna inteligencja zmienia sposób w jaki pracujemy czy chatgpt whisper i elevenlabs zastąpią kiedyś analityków danych według mojego eksperymentu dokładność rozpoznawania mowy wynosiła 97,5 procent ale koszt przetworzenia tysiąca nagrań przekroczył 120 złotych co ciekawe algorytm pomylił słowa morze i może a nazwę github zapisał jako git hap czy naprawdę możemy ufać automatyzacji automatycznej transkrypcji
```

**Hypothesis (normalized):**

```
w 2026 roku sztuczna inteligencja zmienia sposób w jaki pracujemy czy chat gpt whisper i eleven labs zastąpią kiedyś analityków danych według mojego eksperymentu dokładność rozpoznawania mowy wynosiła 97,5 a tylko z przetworzenia tysiąca nagrań przekroczył 120 zł co ciekawe algoryt pomyli słowa może i może ale w github zapisał jako github czy naprawdę możemy ufać automatyzacji automatycznej transkrypcji koniec
```

## Why recomputed ≠ historical

Recomputed pl_basic_v1 scores are higher than the plan notes (Scribe ~10.3%/2.4%, Whisper ~20.7%/6.4%). Likely causes: (1) no scoring code existed in-repo for those notes; (2) pl_basic_v1 counts digit↔word expansions as errors (Scribe spells 2026, 97.5, 120 → large S/I and CER insertions); (3) Whisper still pays for ChatGPT/ElevenLabs tokenization, homophone/content errors, and the trailing 'KONIEC' insertion. Historical figures are retained only as notes — not overwritten.

## Notes

Historical WER/CER were reported before this evaluator existed; differences may come from a different normalizer or reference. Do not overwrite results/smoke/.

Primary metric: corpus / clip WER after `pl_basic_v1`. Digit vs spelled-number mismatches count as errors. Spaces are included in CER. `results/smoke/` was not modified.
