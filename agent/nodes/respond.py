"""Final response node: builds the spoken/written summary and, for audio
turns, synthesizes it via component 03 (Piper) so the server can send
audio bytes back over the websocket. Reports what was verified, not what
was merely attempted (TDD §5.1)."""
import base64
from typing import Any

from components.c03_tts.src.tts import synthesize


def _build_summary(state: dict[str, Any]) -> str:
    plan = state.get("plan") or {}
    steps = plan.get("steps") or []

    clarify_step = next((s for s in steps if s["type"] == "clarify"), None)
    if clarify_step:
        return clarify_step["target"].get("question", "Could you clarify what you'd like me to do?")
    if not steps:
        return plan.get("goal") or "There's nothing for me to do with that request."

    results = state.get("results") or []
    if not results:
        return plan.get("goal") or "I couldn't complete that request."

    last = results[-1]
    decision = last["decision"]
    result = last["result"]
    verification = last["verification"]
    step = last["step"]
    target = step.get("target", {})

    if decision["decision"] == "DENY":
        return f"Request denied. {decision['reason']}"
    if result.get("error") == "cancelled_by_user":
        return "Action cancelled."

    if step["type"] == "create":
        if not verification.get("postcondition_met"):
            return "I tried to create the file but couldn't confirm it actually landed on disk — please check manually."
        return f"Done — created {result.get('file', target.get('file', 'the file'))}."

    field = target.get("cell") or target.get("placeholder") or target.get("element_name") or "the target"
    value = result.get("value") or result.get("new_value")
    if not verification.get("postcondition_met"):
        return "The action completed but verification didn't confirm the expected result — please check it manually."
    if verification.get("anomaly_flag"):
        return (
            f"Done — {field} now shows {value}, but that's an unusually large change from before; "
            "you may want to double-check it."
        )
    return f"Done — {field} now shows {value}."


def respond(state: dict[str, Any]) -> dict[str, Any]:
    text = _build_summary(state)
    audio_b64 = None
    if state.get("input_mode") == "audio":
        wav_bytes = synthesize(text)
        audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
    return {"final_text": text, "final_audio_b64": audio_b64, "done": True}
