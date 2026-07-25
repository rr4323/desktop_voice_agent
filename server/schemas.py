"""Pydantic models for the client -> server side of the WebSocket
protocol. Server -> client events are plain dicts built in server/ws.py —
there's no client-side validation to gain from modeling those too."""
from typing import Any, Literal

from pydantic import BaseModel


class ClientTextMessage(BaseModel):
    type: Literal["text"]
    text: str
    context: dict[str, Any] | None = None


class ClientAudioMessage(BaseModel):
    type: Literal["audio"]
    audio_b64: str
    mime: str = "audio/wav"
    context: dict[str, Any] | None = None


class ClientCancelMessage(BaseModel):
    type: Literal["cancel"]


ClientMessage = ClientTextMessage | ClientAudioMessage | ClientCancelMessage

_MESSAGE_TYPES: dict[str, type[BaseModel]] = {
    "text": ClientTextMessage,
    "audio": ClientAudioMessage,
    "cancel": ClientCancelMessage,
}


def parse_client_message(raw: dict[str, Any]) -> ClientMessage:
    msg_type = raw.get("type")
    model = _MESSAGE_TYPES.get(msg_type)
    if model is None:
        raise ValueError(f"unknown message type: {msg_type!r}; expected one of {sorted(_MESSAGE_TYPES)}")
    return model(**raw)
