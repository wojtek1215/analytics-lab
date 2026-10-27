# ASR inference configuration audit (smoke)

Offline evaluation does **not** re-run these systems. This note documents what produced the frozen smoke hypotheses in `results/smoke/`, based on repository code and public API documentation. Verified facts are separated from assumptions.

Source script: `scripts/smoke_test.py` (do not change inference behavior for evaluation-protocol work).

## Scribe v2 (ElevenLabs API)

### Request as coded

- Endpoint: `POST https://api.elevenlabs.io/v1/speech-to-text`
- Form fields sent:
  - `model_id`: `scribe_v2`
  - `language_code`: `pl`
  - `tag_audio_events`: `false`
- File: `data/raw/test_pl.m4a` (`audio/mp4`)
- Auth: `xi-api-key` from `ELEVENLABS_API_KEY` in local `.env` (never committed)
- Saved hypothesis: `response["text"].strip()` → `results/smoke/scribe.txt`

### Parameters **not** set in the smoke script

| Parameter | In smoke script? | Notes |
|---|---|---|
| `no_verbatim` | Not set | Documented for `scribe_v2`; default value not stated in the fetched API page → treat as **unspecified/default** |
| `keyterms` | Not set | Documented; 20% surcharge when used |
| `transcript_edit` | Not set | Documented post-processing instruction; returns additional `edited_transcript`; 30% surcharge |
| `numbers_format` | Not set | **Not present** in the Speech-to-Text convert endpoint specification consulted for this audit |

### Verified from ElevenLabs convert API reference

Consulted: [Speech to Text convert](https://elevenlabs.io/docs/api-reference/speech-to-text/convert)

- `transcript_edit` (optional string): natural-language edit instruction; edited result returned alongside the original transcript; cannot combine with some entity/multi-channel options; additional billing.
- `edited_transcript` in the response model: present when an edit was requested; compare with top-level `text`.
- `no_verbatim` (optional boolean): if true, omit filler words / false starts / non-speech sounds; **only supported with `scribe_v2`**.
- `keyterms` (optional list of strings): biasing terms; length/count limits and surcharge documented.
- `numbers_format`: **not** listed among request parameters for this endpoint in the consulted specification. Do not introduce undocumented parameters.

### Assumptions (not verified)

- Exact server-side default for `no_verbatim` when omitted.
- Whether any undocumented server-side formatting is applied to `text` before return.
- Model revision / training cut for `scribe_v2` beyond the public model id string.

## Whisper large-v3-turbo (local MLX)

### Call as coded

```python
mlx_whisper.transcribe(
    str(AUDIO),
    path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
    language="pl",
    verbose=False,
)
```

Saved hypothesis: `whisper["text"].strip()` → `results/smoke/whisper.txt`.

### Decoding parameters

Explicitly passed: `language="pl"`, `verbose=False`, model repo id.

All other arguments use `mlx_whisper.transcribe` defaults (verified from installed package signature), including:

- `temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)`
- `compression_ratio_threshold=2.4`
- `logprob_threshold=-1.0`
- `no_speech_threshold=0.6`
- `condition_on_previous_text=True`
- `initial_prompt=None`
- `word_timestamps=False`

### Assumptions / caveats

- Hugging Face revision for `mlx-community/whisper-large-v3-turbo` is **not pinned** in the smoke script.
- Runtime depends on local MLX / hardware; not comparable as a latency benchmark to the API path without a controlled study.

## Comparability caveats

- Different stacks (hosted API vs local MLX Whisper).
- Scribe smoke request does not enable keyterm biasing or `transcript_edit`.
- `no_verbatim` is not explicitly configured for Scribe.
- Primary evaluation scores **raw saved text** only; any future post-edit experiment must be separate.

## Future experiment (not primary accuracy)

**Scribe raw versus Scribe `transcript_edit`**

1. Transcribe once; keep original `text` as the ASR hypothesis.
2. Optionally request `transcript_edit` and store `edited_transcript` separately.
3. Score both under `polish_asr_eval_v2`, labeling the edited condition as post-processing.
4. Never replace raw ASR output with `edited_transcript` in the primary accuracy table.

This experiment requires budget approval (edit surcharge) and is out of scope for offline rescoring.
