class TTSModule:
    """Part 1: Text-to-Speech Module Stub.
    
    Replace `speak` logic with Piper-TTS when ready.
    """
    def __init__(self, voice="en_US-lessac-medium"):
        self.voice = voice

    def speak(self, text: str):
        """Converts text string into spoken audio."""
        print(f"\n[AGENT SPEAKING via TTS]: '{text}'\n")
        # =========================================================================
        # TODO [PART 1 DEVELOPER]: Replace below with Piper execution / sounddevice
        # piper_process.write(text)
        # =========================================================================

    def stop(self):
        """Supports barge-in / user interruption."""
        pass