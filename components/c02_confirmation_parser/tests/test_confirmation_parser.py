"""Standalone tests for the Confirmation/Intent Parser (component 02).

Run in isolation: pytest components/c02_confirmation_parser

Pure string-matching module, no dependencies, no mocks — a table-driven
unit test is the whole test suite, per Component_IO_Spec.md §2.
"""
import pytest

from components.c02_confirmation_parser.src.confirmation_parser import parse_confirmation

CASES = [
    # transcript, confirmed, match_rule, needs_reprompt
    ("yes", True, "affirmative_phrase", None),
    ("Yes.", True, "affirmative_phrase", None),
    ("yeah", True, "affirmative_phrase", None),
    ("go ahead", True, "affirmative_phrase", None),
    ("yes go ahead", True, "affirmative_phrase", None),
    ("sure, do it", True, "affirmative_phrase", None),
    ("that's correct", True, "affirmative_phrase", None),
    ("okay", True, "affirmative_phrase", None),
    ("sounds good", True, "affirmative_phrase", None),
    ("no", False, "negative_phrase", None),
    ("no don't", False, "negative_phrase", None),
    ("cancel that", False, "negative_phrase", None),
    ("nope", False, "negative_phrase", None),
    ("stop", False, "negative_phrase", None),
    ("wait, hold on", False, "negative_phrase", None),
    ("umm not sure", False, "no_match", True),
    ("what do you mean", False, "no_match", True),
    ("", False, "no_match", True),
    ("maybe later", False, "no_match", True),
    # mixed signals: never guess, always reprompt
    ("yes no wait cancel that", False, "no_match", True),
]


@pytest.mark.parametrize("transcript, confirmed, match_rule, needs_reprompt", CASES)
def test_parse_confirmation_table(transcript, confirmed, match_rule, needs_reprompt):
    result = parse_confirmation({"transcript": transcript})

    assert result["confirmed"] is confirmed
    assert result["match_rule"] == match_rule
    if needs_reprompt is None:
        assert "needs_reprompt" not in result
    else:
        assert result["needs_reprompt"] is needs_reprompt


def test_output_shape_matches_spec_exactly_for_affirmative():
    assert parse_confirmation({"transcript": "yes go ahead"}) == {
        "confirmed": True,
        "match_rule": "affirmative_phrase",
    }


def test_output_shape_matches_spec_exactly_for_no_match():
    assert parse_confirmation({"transcript": "umm not sure"}) == {
        "confirmed": False,
        "match_rule": "no_match",
        "needs_reprompt": True,
    }
