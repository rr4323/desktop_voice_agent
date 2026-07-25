"""Standalone tests for the Audit Logger (component 12).

Run in isolation: pytest components/c12_audit_logger
"""
import json

from components.c12_audit_logger.src.audit_logger import log_entry


def test_known_pii_field_is_masked_and_listed(tmp_path):
    log_path = str(tmp_path / "audit.log")
    entry = log_entry(
        {
            "transcript_snippet": "update the kpi tracker with the q3 revenue total",
            "action": {"type": "write", "target": "kpi_tracker.xlsx!B7"},
            "decision": {"decision": "ASK_CONFIRM", "reason": "overwrite of existing value"},
            "confirmation": "user_approved",
            "result": "success",
            "verification": "pass",
            "raw_fields": {"msisdn": "491701234567"},
            "log_path": log_path,
        }
    )
    assert "msisdn" in entry["masked_fields"]
    assert "491701234567" not in json.dumps(entry)
    assert "raw_fields" not in entry


def test_multiple_pii_field_names_all_masked(tmp_path):
    log_path = str(tmp_path / "audit.log")
    entry = log_entry(
        {
            "transcript_snippet": "x",
            "action": {},
            "decision": {},
            "confirmation": "user_approved",
            "result": "success",
            "verification": "pass",
            "raw_fields": {"msisdn": "1", "cdr_id": "2", "billing_account": "3"},
            "log_path": log_path,
        }
    )
    assert set(entry["masked_fields"]) >= {"msisdn", "cdr_id", "billing_account"}


def test_inline_phone_number_in_visible_text_is_masked(tmp_path):
    log_path = str(tmp_path / "audit.log")
    entry = log_entry(
        {
            "transcript_snippet": "call subscriber at 491701234567 about their bill",
            "action": {},
            "decision": {},
            "confirmation": "user_approved",
            "result": "success",
            "verification": "pass",
            "log_path": log_path,
        }
    )
    assert "491701234567" not in entry["transcript_snippet"]
    assert "inline_phone" in entry["masked_fields"]


def test_entry_with_no_pii_has_empty_masked_fields(tmp_path):
    log_path = str(tmp_path / "audit.log")
    entry = log_entry(
        {
            "transcript_snippet": "pull the q3 revenue total",
            "action": {"type": "read"},
            "decision": {"decision": "ALLOW"},
            "confirmation": "n/a",
            "result": "success",
            "verification": "pass",
            "log_path": log_path,
        }
    )
    assert entry["masked_fields"] == []


def test_multi_step_task_produces_one_entry_per_step(tmp_path):
    log_path = str(tmp_path / "audit.log")
    for step_id in (1, 2, 3):
        log_entry(
            {
                "transcript_snippet": f"step {step_id}",
                "action": {"step_id": step_id},
                "decision": {"decision": "ALLOW"},
                "confirmation": "n/a",
                "result": "success",
                "verification": "pass",
                "log_path": log_path,
            }
        )
    with open(log_path) as f:
        lines = [line for line in f if line.strip()]
    assert len(lines) == 3
    for line in lines:
        json.loads(line)  # each line is valid, standalone JSON
