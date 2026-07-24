"""TTS Module (component 03): local text-to-speech via Piper.

Responsibility: Convert a response string into spoken audio output, with
support for barge-in interruption. Contract: docs/Component_IO_Spec.md,
section 3.

Runs fully locally per the TDD's data-sovereignty goal: Piper synthesizes
speech on-device (voice model downloaded once and cached under
~/.cache/piper-voices, same pattern as the whisper model cache in
component 01), piped as raw PCM into ffplay for playback. speak() returns
immediately with a handle so the caller isn't blocked while audio plays;
cancel(handle) kills playback within a bounded latency — that's the
mechanism barge-in relies on (voice activity detection on the ASR side
calls cancel() the instant the user starts talking over the agent).
"""
import io
import os
import shutil
import subprocess
import threading
import uuid
import wave
from pathlib import Path
from typing import Any

from piper import PiperVoice
from piper.download_voices import download_voice

_VOICE_NAME = os.environ.get("TTS_VOICE", "en_US-lessac-low")
_VOICE_DIR = Path(os.environ.get("TTS_VOICE_DIR", Path.home() / ".cache" / "piper-voices"))

_voice: PiperVoice | None = None
_voice_lock = threading.Lock()

_playbacks: dict[str, "_Playback"] = {}
_playbacks_lock = threading.Lock()


class _Playback:
    def __init__(self, proc: subprocess.Popen):
        self.proc = proc
        self.status = "playing"
        self.lock = threading.Lock()
        self.done_event = threading.Event()


def _get_voice() -> PiperVoice:
    global _voice
    with _voice_lock:
        if _voice is None:
            _VOICE_DIR.mkdir(parents=True, exist_ok=True)
            model_path = _VOICE_DIR / f"{_VOICE_NAME}.onnx"
            if not model_path.exists():
                download_voice(_VOICE_NAME, _VOICE_DIR)
            _voice = PiperVoice.load(model_path)
        return _voice


def synthesize(text: str) -> bytes:
    """Synthesize `text` to WAV bytes without playing it.

    Not part of the speak/cancel contract itself — a pure synthesis helper
    used by tests (to check real audio is produced) and by anything that
    wants to save/inspect audio rather than play it to the speaker.
    """
    voice = _get_voice()
    chunks = list(voice.synthesize(text))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        if chunks:
            wav_file.setframerate(chunks[0].sample_rate)
            wav_file.setsampwidth(chunks[0].sample_width)
            wav_file.setnchannels(chunks[0].sample_channels)
        else:
            wav_file.setframerate(voice.config.sample_rate)
            wav_file.setsampwidth(2)
            wav_file.setnchannels(1)
        for chunk in chunks:
            wav_file.writeframes(chunk.audio_int16_bytes)
    return buffer.getvalue()


def _run_playback(handle: str, text: str) -> None:
    playback = _playbacks[handle]
    voice = _get_voice()
    try:
        for chunk in voice.synthesize(text):
            stdin = playback.proc.stdin
            if stdin is None or stdin.closed:
                break
            try:
                stdin.write(chunk.audio_int16_bytes)
                stdin.flush()
            except (BrokenPipeError, OSError):
                break
    finally:
        try:
            if playback.proc.stdin and not playback.proc.stdin.closed:
                playback.proc.stdin.close()
        except OSError:
            pass
        playback.proc.wait()
        with playback.lock:
            if playback.status == "playing":
                playback.status = "done"
        playback.done_event.set()


def speak(request: dict[str, Any]) -> dict[str, Any]:
    """Speak `request["text"]` out loud. Returns immediately with a handle."""
    text = request["text"]
    if not shutil.which("ffplay"):
        raise RuntimeError("ffplay not found on PATH — required for local audio playback")

    voice = _get_voice()
    proc = subprocess.Popen(
        [
            "ffplay", "-nodisp", "-autoexit",
            "-f", "s16le",
            "-ar", str(voice.config.sample_rate),
            "-ac", "1",
            "-",
        ],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    handle = str(uuid.uuid4())
    playback = _Playback(proc)
    with _playbacks_lock:
        _playbacks[handle] = playback

    thread = threading.Thread(target=_run_playback, args=(handle, text), daemon=True)
    thread.start()

    return {"handle": handle, "status": "playing"}


def cancel(handle: str) -> dict[str, Any]:
    """Stop playback for `handle` immediately — the barge-in path."""
    with _playbacks_lock:
        playback = _playbacks.get(handle)
    if playback is None:
        return {"handle": handle, "status": "not_found"}

    with playback.lock:
        if playback.status != "playing":
            return {"handle": handle, "status": playback.status}
        playback.status = "cancelled"

    playback.proc.terminate()
    try:
        playback.proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        playback.proc.kill()
        playback.proc.wait()
    playback.done_event.set()
    return {"handle": handle, "status": "cancelled"}


def get_status(handle: str) -> dict[str, Any]:
    with _playbacks_lock:
        playback = _playbacks.get(handle)
    if playback is None:
        return {"handle": handle, "status": "not_found"}
    with playback.lock:
        return {"handle": handle, "status": playback.status}


def wait(handle: str, timeout: float | None = None) -> dict[str, Any]:
    """Block until playback finishes or is cancelled. For tests/CLI use."""
    with _playbacks_lock:
        playback = _playbacks.get(handle)
    if playback is None:
        return {"handle": handle, "status": "not_found"}
    playback.done_event.wait(timeout=timeout)
    return get_status(handle)


if __name__ == "__main__":
    # Manual smoke test: python -m components.c03_tts.src.tts "text to speak"
    import sys

    result = speak({"text": sys.argv[1]})
    print(result)
    print(wait(result["handle"], timeout=30))
