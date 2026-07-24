"""ASR Module (component 01): local speech-to-text via faster-whisper.

Responsibility: Convert microphone audio into a transcript with a confidence
signal. Contract: docs/Component_IO_Spec.md, section 1.

Runs fully locally (no cloud ASR API) per the TDD's data-sovereignty goal —
the whisper model runs on-device via faster-whisper/ctranslate2, downloaded
once from Hugging Face and cached locally after that.
"""
import math
import os
from typing import Any

from faster_whisper import WhisperModel

_MODEL_SIZE = os.environ.get("ASR_MODEL_SIZE", "tiny")
_MODEL_DEVICE = os.environ.get("ASR_MODEL_DEVICE", "cpu")
_MODEL_COMPUTE_TYPE = os.environ.get("ASR_MODEL_COMPUTE_TYPE", "int8")

# Segments scoring below this are surfaced as low_confidence_spans rather
# than silently included in the transcript (TDD §5.1: "low-confidence spans
# flagged for clarification rather than guessed").
LOW_CONFIDENCE_THRESHOLD = float(os.environ.get("ASR_LOW_CONFIDENCE_THRESHOLD", "0.5"))

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(_MODEL_SIZE, device=_MODEL_DEVICE, compute_type=_MODEL_COMPUTE_TYPE)
    return _model


def _segment_confidence(segment) -> float:
    # faster-whisper doesn't expose a direct confidence score; avg_logprob is
    # the average log-probability of the tokens in the segment, so
    # exp(avg_logprob) approximates a per-segment confidence in [0, 1].
    # no_speech_prob further discounts segments whisper itself thinks are
    # non-speech (silence/noise), which matters for the noisy-audio case.
    raw = math.exp(segment.avg_logprob) * (1.0 - segment.no_speech_prob)
    return max(0.0, min(1.0, raw))


def transcribe(request: dict[str, Any]) -> dict[str, Any]:
    """Transcribe a .wav file per the ASR module's documented I/O contract.

    request: {"audio_path": str, "language": str | None}
    returns: {"transcript": str, "confidence": float, "low_confidence_spans": [...]}
    """
    audio_path = request["audio_path"]
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"audio file not found: {audio_path}")

    model = _get_model()
    segments, _info = model.transcribe(audio_path, language=request.get("language"))

    texts = []
    confidences = []
    low_confidence_spans = []
    for segment in segments:
        text = segment.text.strip()
        confidence = _segment_confidence(segment)
        if text:
            texts.append(text)
            confidences.append(confidence)
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            low_confidence_spans.append(
                {
                    "text": text,
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "confidence": round(confidence, 4),
                }
            )

    transcript = " ".join(texts)
    overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return {
        "transcript": transcript,
        "confidence": round(overall_confidence, 4),
        "low_confidence_spans": low_confidence_spans,
    }


if __name__ == "__main__":
    # Manual smoke test: python -m components.c01_asr.src.asr path/to/audio.wav [language]
    import json
    import sys

    path = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(transcribe({"audio_path": path, "language": lang}), indent=2))
