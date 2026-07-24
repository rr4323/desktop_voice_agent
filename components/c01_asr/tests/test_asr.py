"""Standalone tests for the ASR Module (component 01).

Run in isolation: pytest components/c01_asr

These exercise the real faster-whisper wrapper against checked-in fixture
audio in fixtures/audio/ — no other component needs to be running (per
Component_IO_Spec.md §1: "this is a pure audio-in, JSON-out function").
First run downloads and caches the "tiny" whisper model from Hugging Face;
subsequent runs are fast and fully local.
"""
import os

import pytest

from components.c01_asr.src.asr import LOW_CONFIDENCE_THRESHOLD, transcribe

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures", "audio")


def test_clean_speech_transcribes_with_high_confidence():
    result = transcribe({"audio_path": os.path.join(FIXTURES, "clean_speech.wav"), "language": "en"})

    assert "tracker" in result["transcript"].lower() or "trackle" in result["transcript"].lower()
    assert "revenue" in result["transcript"].lower()
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["confidence"] > LOW_CONFIDENCE_THRESHOLD


def test_noisy_speech_flags_low_confidence_span():
    result = transcribe({"audio_path": os.path.join(FIXTURES, "noisy_speech.wav"), "language": "en"})

    assert result["confidence"] < LOW_CONFIDENCE_THRESHOLD
    assert len(result["low_confidence_spans"]) >= 1
    for span in result["low_confidence_spans"]:
        assert span["confidence"] < LOW_CONFIDENCE_THRESHOLD
        assert {"text", "start", "end", "confidence"} <= span.keys()


def test_silence_produces_empty_transcript_and_zero_confidence():
    result = transcribe({"audio_path": os.path.join(FIXTURES, "silence.wav")})

    assert result["transcript"] == ""
    assert result["confidence"] == 0.0
    assert result["low_confidence_spans"] == []


def test_missing_audio_file_raises_clean_error():
    with pytest.raises(FileNotFoundError):
        transcribe({"audio_path": os.path.join(FIXTURES, "does_not_exist.wav")})
