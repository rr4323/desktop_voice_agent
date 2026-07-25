"""Standalone tests for the Browser Agent (component 17).

Run in isolation: pytest components/c17_browser_agent

These need a GROQ_API_KEY (see .env) and are skipped cleanly if that's not
set — this component was written to be tested on a machine with Groq
access configured, not necessarily the one running the rest of this
repo's suite.
"""
import os

import pytest

from components.c17_browser_agent.src.browser_agent import run

FIXTURE_URL = "file://" + os.path.join(
    os.path.dirname(__file__), "..", "..", "c15_browser_adapter", "fixtures", "dashboard.html"
)


@pytest.fixture(autouse=True)
def skip_if_no_groq_api_key():
    if not os.environ.get("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY not set — see .env")


def test_agent_reads_a_known_value_and_saves_it_to_file(tmp_path):
    instruction = (
        f"Navigate to {FIXTURE_URL}, read the text of the element with id "
        f"'kpi-value', then save that exact text to a file called kpi_value.txt. "
        f"Tell me the value and the file path you saved it to."
    )

    outcome = run(instruction, output_dir=str(tmp_path))

    assert "2.4M" in outcome["result"]
    saved_file = tmp_path / "kpi_value.txt"
    assert saved_file.exists()
    assert saved_file.read_text().strip() == "2.4M"


def test_agent_stays_within_step_budget_on_an_impossible_instruction(tmp_path):
    # An instruction with no way to succeed shouldn't loop forever — the
    # recursion_limit should cut it off rather than hang the test suite.
    outcome = run(
        f"Navigate to {FIXTURE_URL} and click the element with selector "
        f"'#this-selector-does-not-exist-anywhere', retrying if it fails, "
        f"until it works.",
        output_dir=str(tmp_path),
        max_steps=4,
    )
    assert outcome["step_count"] > 0
