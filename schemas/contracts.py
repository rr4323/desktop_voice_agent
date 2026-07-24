"""Shared data-shape definitions for the voice agent pipeline.

Plain dataclasses, not a validation framework — components exchange plain
dicts/JSON at their boundaries (see docs/Component_IO_Spec.md); these exist
so editors can type-check against the same shapes both sides of the
pipeline agree on. See schemas/examples/ for concrete JSON fixtures.
"""
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ActionRequest:
    step_id: int
    type: Literal["read", "write", "clarify"]
    target: dict[str, Any]
    value_ref: str | None = None
    depends_on: list[int] = field(default_factory=list)


@dataclass
class PolicyDecision:
    step_id: int
    decision: Literal["ALLOW", "ASK_CONFIRM", "DENY"]
    tier: str
    reason: str


@dataclass
class ActionResult:
    step_id: int
    value: Any
    provenance: dict[str, Any]


@dataclass
class VerificationResult:
    verified: bool
    postcondition_met: bool
    anomaly_flag: bool


@dataclass
class AuditLogEntry:
    timestamp: str
    transcript_snippet: str
    action: dict[str, Any]
    decision: dict[str, Any]
    confirmation: str
    result: str
    verification: str
    masked_fields: list[str] = field(default_factory=list)
