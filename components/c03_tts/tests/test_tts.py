"""Standalone tests for the TTS Module (component 03).

Run in isolation: pytest components/c03_tts

These exercise the real Piper synthesis + ffplay playback pipeline — no
other component needs to be running (per Component_IO_Spec.md §3). First
run downloads and caches the "en_US-lessac-low" Piper voice; subsequent
runs are fully local.
"""
import io
import time
import wave

from components.c03_tts.src.tts import cancel, get_status, speak, synthesize, wait


def test_synthesize_produces_real_audio():
    wav_bytes = synthesize("Cell B7 currently contains a value.")
    assert len(wav_bytes) > 1000

    with wave.open(io.BytesIO(wav_bytes)) as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        duration = frames / rate

    assert rate > 0
    assert channels == 1
    assert duration > 0.3  # a handful of words takes at least this long to say


def test_speak_returns_handle_immediately_and_completes():
    result = speak({"text": "Done."})
    assert result["status"] == "playing"
    assert result["handle"]

    final = wait(result["handle"], timeout=15)
    assert final["status"] == "done"


def test_barge_in_cancels_playback_within_bounded_latency():
    long_text = (
        "This is a long confirmation message with several sentences, "
        "designed to take a few seconds to play out loud so we can "
        "reliably interrupt it before it finishes on its own."
    )
    result = speak({"text": long_text})
    handle = result["handle"]

    time.sleep(0.5)  # let playback actually start before interrupting it
    assert get_status(handle)["status"] == "playing"

    start = time.monotonic()
    cancel_result = cancel(handle)
    elapsed = time.monotonic() - start

    assert cancel_result["status"] == "cancelled"
    assert elapsed < 1.0  # barge-in must stop playback quickly, not wait it out

    # status must stick as "cancelled" — the synthesis thread's own
    # completion handling must not overwrite it with "done" afterwards
    time.sleep(0.3)
    assert get_status(handle)["status"] == "cancelled"


def test_cancel_after_completion_is_a_noop():
    result = speak({"text": "Hi."})
    wait(result["handle"], timeout=15)

    cancel_result = cancel(result["handle"])
    assert cancel_result["status"] == "done"


def test_cancel_unknown_handle_reports_not_found():
    assert cancel("no-such-handle")["status"] == "not_found"
    assert get_status("no-such-handle")["status"] == "not_found"
