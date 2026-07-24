# 03. TTS Module

**Responsibility:** Convert a response string into spoken audio output, with support for barge-in interruption.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 3.

## Input

```json
{"text": "Cell B7 currently contains a value \u2014 should I overwrite it?"}
```

## Output

`speak()` returns immediately, before playback finishes:

```json
{"handle": "7d85fda6-ad00-4be7-95e8-deb940b71fe4", "status": "playing"}
```

## API

Beyond `speak()`, this module exposes what the spec's "returns a handle that
can be cancelled mid-playback" implies:

- `cancel(handle) -> {"handle", "status"}` \u2014 stops playback immediately.
  This is the barge-in mechanism: as soon as voice-activity-detection on the
  ASR side notices the user talking over the agent, it calls `cancel()`
  instead of waiting for the sentence to finish.
- `get_status(handle) -> {"handle", "status"}` \u2014 `"playing" | "done" |
  "cancelled" | "not_found"`.
- `wait(handle, timeout=None)` \u2014 blocks until playback finishes or is
  cancelled (for tests/CLI use; the orchestrator shouldn't need this since
  it should stay responsive to barge-in while a response plays).
- `synthesize(text) -> bytes` \u2014 synthesis only, no playback; returns WAV
  bytes. Not part of the speak/cancel contract, but useful for tests
  (confirming real audio is produced) and for anything that wants to save
  audio instead of playing it live.

## Implementation notes

- Synthesizes with [Piper](https://github.com/OHF-voice/piper1-gpl)
  (`en_US-lessac-low` by default, override via `TTS_VOICE`) \u2014 fully local,
  no cloud TTS API, per the TDD's data-sovereignty requirement. The voice
  model downloads once from Hugging Face and is cached under
  `~/.cache/piper-voices` (override via `TTS_VOICE_DIR`) \u2014 same pattern as
  the whisper model cache in component 01. First use needs network; every
  run after is offline.
- Plays back by piping raw PCM into `ffplay` as a subprocess. `speak()`
  starts a background thread to feed audio into that subprocess and returns
  right away; `cancel()` terminates the subprocess directly, which is what
  makes the barge-in latency bounded \u2014 cancelling doesn't wait for playback
  to reach a natural stopping point.

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c03_tts
```

Covers: real synthesis produces valid, non-trivial-duration audio;
`speak()` returns a handle immediately and reaches `"done"` on its own;
barge-in (`cancel()` mid-playback) stops audio in well under a second and
the status sticks as `"cancelled"`; cancelling an already-finished or
unknown handle is a clean no-op/`"not_found"` rather than an error.

Shared cross-component JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

`piper-tts` (pulls in `onnxruntime`). Also requires `ffplay` (from ffmpeg)
on `PATH` for playback \u2014 not a pip package, install via your OS package
manager if it's missing.

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
