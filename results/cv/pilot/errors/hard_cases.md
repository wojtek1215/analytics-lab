# Hard cases — `cv27_pl_pilot`

Primary profile: `pl_wer_normalized_v1`. Focus: content-changing residual errors after normalization.

## 1. `common_voice_pl_25378583` (max primary WER 100.0%)

- **Reference:** Chciałbym kiedyś zostać pilotem.
- **`scribe_v2`** WER 75.0% (S/D/I 2/0/1): Chciałbym kiedyś zatańczyć z Piotrem.
- **`whisper-large-v3-turbo`** WER 100.0% (S/D/I 4/0/0): Cześć! Cześć! Cześć! Cześć!

## 2. `common_voice_pl_32077476` (max primary WER 90.0%)

- **Reference:** Rząd w Hanoi jednostronnie dysponuje mieniem kościoła wbrew wcześniejszym umowom
- **`scribe_v2`** WER 90.0% (S/D/I 9/0/0): Żalycha nowi widno stronę dyskutuje imieniem puścił, brak wcześniejszym umową
- **`whisper-large-v3-turbo`** WER 60.0% (S/D/I 6/0/0): Urząd w kanali jednostronny, wspomnienia imieniem Kościoława wbrew wcześniejszym umowom.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `scribe_v2` | substitute | umowom | umową | `lexical_substitution` |
| `whisper-large-v3-turbo` | substitute | rząd | urząd | `morphology` |

## 3. `common_voice_pl_20829546` (max primary WER 60.0%)

- **Reference:** Jest godzina dwudziesta trzecia trzydzieści.
- **`scribe_v2`** WER 0.0% (S/D/I 0/0/0): Jest godzina dwudziesta trzecia trzydzieści.
- **`whisper-large-v3-turbo`** WER 60.0% (S/D/I 1/2/0): Jest godzina 23.30

## 4. `common_voice_pl_20618909` (max primary WER 33.3%)

- **Reference:** „Kiedy?” „W niedzielę”.
- **`scribe_v2`** WER 0.0% (S/D/I 0/0/0): Kiedy? W niedzielę.
- **`whisper-large-v3-turbo`** WER 33.3% (S/D/I 0/1/0): Kiedy? Niedzielę.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `whisper-large-v3-turbo` | delete | w | ∅ | `deletion` |

## 5. `common_voice_pl_20604060` (max primary WER 33.3%)

- **Reference:** Lekarz zasępił się!
- **`scribe_v2`** WER 0.0% (S/D/I 0/0/0): Lekarz zasępił się.
- **`whisper-large-v3-turbo`** WER 33.3% (S/D/I 1/0/0): Lekarz zastępił się.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `whisper-large-v3-turbo` | substitute | zasępił | zastępił | `morphology` |

## 6. `common_voice_pl_21877469` (max primary WER 20.0%)

- **Reference:** Wspomniałem o tem twojemu ojcu.
- **`scribe_v2`** WER 20.0% (S/D/I 1/0/0): Wspomniałem o tym twojemu ojcu.
- **`whisper-large-v3-turbo`** WER 20.0% (S/D/I 1/0/0): Wspomniałem o tym Twojemu ojcu.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `scribe_v2` | substitute | tem | tym | `lexical_substitution` |
| `whisper-large-v3-turbo` | substitute | tem | tym | `lexical_substitution` |

## 7. `common_voice_pl_20772455` (max primary WER 20.0%)

- **Reference:** Co ty robisz, licho zatracone?
- **`scribe_v2`** WER 20.0% (S/D/I 1/0/0): Co ty robisz, licho zatercone?
- **`whisper-large-v3-turbo`** WER 0.0% (S/D/I 0/0/0): Co ty robisz, licho, zatracone?

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `scribe_v2` | substitute | zatracone | zatercone | `morphology` |

## 8. `common_voice_pl_20775547` (max primary WER 18.2%)

- **Reference:** Dałam się pomacać trochę fotografowi z przeciwka i zdjęcia już są.
- **`scribe_v2`** WER 9.1% (S/D/I 1/0/0): Dałam się pomacać trochę fotografowi z naprzeciwka i zdjęcia już są.
- **`whisper-large-v3-turbo`** WER 18.2% (S/D/I 1/0/1): Udało mi się pomacać trochę fotografowi z przeciwka i zdjęcia już są.

| Model | Op | Ref | Hyp | Category |
|---|---|---|---|---|
| `scribe_v2` | substitute | przeciwka | naprzeciwka | `morphology` |
| `whisper-large-v3-turbo` | substitute | dałam | mi | `lexical_substitution` |
