# 01. ASR Module

**Responsibility:** Convert microphone audio into a transcript with a confidence signal.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 1.

## Input

```json
{"audio_path": "fixtures/audio/sample_clean.wav"}
```

## Output

```json
{
    "transcript": "update the kpi tracker with the q3 revenue total",
    "confidence": 0.94,
    "low_confidence_spans": []
}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c01_asr
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

`faster-whisper`

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
