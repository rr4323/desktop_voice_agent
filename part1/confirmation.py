import re

class ConfirmationParser:
    """Part 1: Deterministic Affirmative/Negative Spoken Intent Parser.
    
    Strict rule-matching (NO LLM) per safety contract.
    """
    AFFIRMATIVE = {
        "yes", "yeah", "yep", "go ahead", "approve", "confirm", 
        "do it", "sure", "proceed", "ok", "okay"
    }
    NEGATIVE = {
        "no", "nope", "don't", "cancel", "stop", "abort", 
        "deny", "wait", "hold on"
    }

    def parse(self, transcript: str) -> dict:
        clean = re.sub(r"[^\w\s]", "", transcript.lower().strip())
        
        for phrase in self.AFFIRMATIVE:
            if phrase in clean:
                return {"confirmed": True, "match_rule": "affirmative_phrase", "needs_reprompt": False}

        for phrase in self.NEGATIVE:
            if phrase in clean:
                return {"confirmed": False, "match_rule": "negative_phrase", "needs_reprompt": False}

        return {"confirmed": False, "match_rule": "no_match", "needs_reprompt": True}