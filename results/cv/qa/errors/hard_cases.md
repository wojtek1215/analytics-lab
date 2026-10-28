# Hard cases — `cv27_pl_qa`

Primary profile: `pl_wer_normalized_v1`. Focus: content-changing residual errors after normalization.

## 1. `common_voice_pl_20621575` (max primary WER 66.7%)

- **Reference:** Wszystko bierze dosłownie.
- **`scribe_v2`** WER 0.0% (S/D/I 0/0/0): Wszystko bierze dosłownie
- **`whisper-large-v3-turbo`** WER 66.7% (S/D/I 1/0/1): Wszystko bierze do słowa.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `whisper-large-v3-turbo` | substitute | dosłownie | słowa | `lexical_substitution` |

## 2. `common_voice_pl_20686554` (max primary WER 50.0%)

- **Reference:** Nie ucieknie! — pocieszał siebie samego jednoręki.
- **`scribe_v2`** WER 33.3% (S/D/I 2/0/0): Nie uciekną — pocieszał siebie samego jednak
- **`whisper-large-v3-turbo`** WER 50.0% (S/D/I 2/0/1): Nie ucieknę, pocieszał w siebie samego jednoletnie.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `scribe_v2` | substitute | ucieknie | uciekną | `morphology` |
| `scribe_v2` | substitute | jednoręki | jednak | `lexical_substitution` |
| `whisper-large-v3-turbo` | substitute | ucieknie | ucieknę | `morphology` |
| `whisper-large-v3-turbo` | substitute | jednoręki | jednoletnie | `lexical_substitution` |

## 3. `common_voice_pl_20653502` (max primary WER 50.0%)

- **Reference:** Pochylone są ku ziemi te kształty.
- **`scribe_v2`** WER 0.0% (S/D/I 0/0/0): Pochylone są ku ziemi te kształty.
- **`whisper-large-v3-turbo`** WER 50.0% (S/D/I 2/1/0): Pochylione są kóziemi te kształty.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `whisper-large-v3-turbo` | substitute | pochylone | pochylione | `morphology` |
| `whisper-large-v3-turbo` | substitute | ku | kóziemi | `lexical_substitution` |
| `whisper-large-v3-turbo` | delete | ziemi | ∅ | `deletion` |

## 4. `common_voice_pl_20603985` (max primary WER 25.0%)

- **Reference:** — No, to idźże jeszcze raz i dobrze poszukaj!
- **`scribe_v2`** WER 0.0% (S/D/I 0/0/0): No to idźże jeszcze raz i dobrze poszukaj
- **`whisper-large-v3-turbo`** WER 25.0% (S/D/I 1/0/1): No, to idź że jeszcze raz i dobrze poszukaj.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `whisper-large-v3-turbo` | substitute | idźże | że | `lexical_substitution` |

## 5. `common_voice_pl_20647765` (max primary WER 14.3%)

- **Reference:** Szła stamtąd na nas stęchlizna i zaduch.
- **`scribe_v2`** WER 14.3% (S/D/I 1/0/0): Szła stamtąd na nas tęchlizna i zaduch.
- **`whisper-large-v3-turbo`** WER 14.3% (S/D/I 1/0/0): Szła stamtąd na nas tęchlizna i zaduch.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `scribe_v2` | substitute | stęchlizna | tęchlizna | `morphology` |
| `whisper-large-v3-turbo` | substitute | stęchlizna | tęchlizna | `morphology` |

## 6. `common_voice_pl_20619232` (max primary WER 12.5%)

- **Reference:** Zamiast odpowiedzi Andrzej przybliżył mi do oczu kukłę.
- **`scribe_v2`** WER 0.0% (S/D/I 0/0/0): Zamiast odpowiedzi Andrzej przybliżył mi do oczu kukłę.
- **`whisper-large-v3-turbo`** WER 12.5% (S/D/I 1/0/0): Zamiast odpowiedzi Andrzej przybliżył mi do oczu kukły.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `whisper-large-v3-turbo` | substitute | kukłę | kukły | `morphology` |
