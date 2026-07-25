"""Standalone tests for the Verification Module (component 10).

Run in isolation: pytest components/c10_verification
"""
from components.c10_verification.src.verification import detect_anomaly, verify


def test_matched_value_reports_postcondition_met():
    result = verify(
        {
            "action_result": {"cell": "B7", "expected_value": "2.4M"},
            "current_read": {"cell": "B7", "value": "2.4M"},
        }
    )
    assert result["verified"] is True
    assert result["postcondition_met"] is True
    assert result["anomaly_flag"] is False


def test_mismatched_value_reports_postcondition_not_met():
    result = verify(
        {
            "action_result": {"cell": "B7", "expected_value": "2.4M"},
            "current_read": {"cell": "B7", "value": "1.8M"},
        }
    )
    assert result["postcondition_met"] is False
    assert result["verified"] is False


def test_implausible_delta_flags_anomaly_even_when_postcondition_met():
    # TDD §11: churn rate jumping inconsistent with historical range should
    # still be flagged even though the write itself landed correctly.
    result = verify(
        {
            "action_result": {"cell": "C3", "expected_value": "500000"},
            "current_read": {"cell": "C3", "value": "500000"},
            "historical_context": {"previous_quarter_value": "1800"},
        }
    )
    assert result["postcondition_met"] is True
    assert result["anomaly_flag"] is True


def test_small_plausible_delta_does_not_flag_anomaly():
    result = verify(
        {
            "action_result": {"cell": "B7", "expected_value": "2.4M"},
            "current_read": {"cell": "B7", "value": "2.4M"},
            "historical_context": {"previous_quarter_value": "1.8M"},
        }
    )
    assert result["anomaly_flag"] is False


def test_detect_anomaly_ignores_non_numeric_values():
    assert detect_anomaly("n/a", "2.4M") is False
    assert detect_anomaly(None, "2.4M") is False
