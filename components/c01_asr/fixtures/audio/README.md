# ASR test fixtures

- `clean_speech.wav` — "update the kpi tracker with the q3 revenue total",
  16kHz mono. Generated once via gTTS (Google's TTS, needs internet) and
  converted with ffmpeg; this is a dev-time convenience for producing a
  realistic speech sample to check in, not a runtime dependency of the ASR
  module or the shipped agent — the agent itself only ever calls
  faster-whisper locally.
- `noisy_speech.wav` — the same speech with white noise mixed in via
  `ffmpeg amix`, to exercise the low-confidence-span path.
- `silence.wav` — 2s of digital silence via `ffmpeg anullsrc`, to exercise
  the empty-transcript / zero-confidence path.

Regenerate with:

```bash
python -c "from gtts import gTTS; gTTS('update the kpi tracker with the q3 revenue total', lang='en').save('/tmp/speech.mp3')"
ffmpeg -y -i /tmp/speech.mp3 -ar 16000 -ac 1 clean_speech.wav
ffmpeg -y -i clean_speech.wav -f lavfi -i anoisesrc=color=white:amplitude=0.35:duration=4.656 \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0" -ar 16000 -ac 1 noisy_speech.wav
ffmpeg -y -f lavfi -i anullsrc=r=16000:cl=mono -t 2 silence.wav
```
