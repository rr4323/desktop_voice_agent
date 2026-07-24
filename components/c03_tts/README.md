# 03. TTS Module

**Responsibility:** Convert a response string into spoken audio output, with support for barge-in interruption.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 3.

## Input

```json
{"text": "Cell B7 currently contains a value \u2014 should I overwrite it?"}
```

## Output

```json
{"handle": "playback-1", "status": "playing"}
```

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c03_tts
```

Fixtures for this component's tests live in `fixtures/`. Shared cross-component
JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

`piper-tts`

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
