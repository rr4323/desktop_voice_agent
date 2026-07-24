# 01. ASR Module

**Responsibility:** Convert microphone audio into a transcript with a confidence signal.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 1.

## Input

```json
{"audio_path": "fixtures/audio/clean_speech.wav", "language": "en"}
```

`language` is optional — omit it to let whisper auto-detect (needed for the
multi-country/multilingual case in TDD §6.1 and §8).

## Output

```json
{
    "transcript": "Update the KPI Trackle with the Q3 Revenue Total.",
    "confidence": 0.6766,
    "low_confidence_spans": []
}
```

`confidence` is the mean of per-segment `exp(avg_logprob) * (1 - no_speech_prob)`
— faster-whisper doesn't expose a direct confidence score, so this is the
standard proxy for it. Segments scoring below `LOW_CONFIDENCE_THRESHOLD`
(env: `ASR_LOW_CONFIDENCE_THRESHOLD`, default `0.5`) are surfaced in
`low_confidence_spans` with `{text, start, end, confidence}` instead of being
silently included, per the "ask for clarification rather than guess" goal.

## Implementation notes

- Runs fully locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
  (ctranslate2 + whisper weights) — no cloud ASR API, per the TDD's
  data-sovereignty requirement. `ASR_MODEL_SIZE` (default `tiny`),
  `ASR_MODEL_DEVICE` (default `cpu`), and `ASR_MODEL_COMPUTE_TYPE`
  (default `int8`) are configurable via env vars; swap to a bigger model
  (`small`/`medium`) for better accuracy once off laptop-CPU constraints.
- The model itself is downloaded once from Hugging Face on first use and
  cached locally after that (`~/.cache/huggingface`) — that first download
  needs network access; every run after is offline.

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c01_asr
```

Covers: clean speech (transcript + confidence), noisy speech (confidence
drops, low-confidence span raised), silence (empty transcript, zero
confidence, no exception), and a missing file (clean `FileNotFoundError`
rather than a whisper/ctranslate2 stack trace).

Fixtures live in `fixtures/audio/` (see `fixtures/audio/README.md` for how
they were generated) and are checked into the repo so tests are
reproducible without needing a microphone or TTS tool at test time. Shared
cross-component JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

`faster-whisper`

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
