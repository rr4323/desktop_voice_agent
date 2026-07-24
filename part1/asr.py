class ASRModule:
    """Part 1: Speech-to-Text Module Stub.
    Replace `transcribe` logic with `faster-whisper` when ready.
    """
    def __init__(self, model_size="small"):
        self.model_size = model_size

    def transcribe(self, audio_input) -> dict:
        """Converts audio/pcm stream or text mock into transcript payload."""
        # IF MOCK TEXT PASSED DIRECTLY (FOR TESTING):
        if isinstance(audio_input, str):
            return {
                "transcript": audio_input,
                "confidence": 0.98,
                "low_confidence_spans": []
            }
        # =========================================================================
        # TODO [PART 1 DEVELOPER]: Replace below with faster-whisper local call:
        # segments, info = self.model.transcribe(audio_input)
        # =========================================================================
        return {
            "transcript": "pull the q3 revenue total from the network report and put it into the kpi tracker",
            "confidence": 0.95,
            "low_confidence_spans": []
        }