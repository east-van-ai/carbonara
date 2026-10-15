"""Telemetry is off unless it is asked for.

Two of the four stacks call home with their own defaults, and carbonara
promises they do not, so the promise is pinned here rather than left to a code
review.
"""

import json
import re
from pathlib import Path

import pytest

from carbonara import environ, registry


@pytest.fixture
def captured_env(monkeypatch):
    """Run a stack without running anything, and hand back the environment."""
    seen = {}

    class Completed:
        returncode = 0

    def fake_run(command, env=None, **kwargs):
        seen.update(env or {})
        return Completed()

    monkeypatch.setattr(environ.subprocess, "run", fake_run)
    return seen


def test_every_framework_channel_is_named():
    """A stack that phones home through a switch nobody listed stays on."""
    assert set(environ.TELEMETRY_OFF) == {
        "CREWAI_DISABLE_TELEMETRY",
        "CREWAI_DISABLE_TRACKING",
        "OTEL_SDK_DISABLED",
        "HF_HUB_DISABLE_TELEMETRY",
        "LANGCHAIN_TRACING_V2",
        "LANGSMITH_TRACING",
        "LITELLM_LOCAL_MODEL_COST_MAP",
    }


def test_a_run_turns_telemetry_off(captured_env):
    """The default run sets every switch, for every stack, not just crewai."""
    environ.run(registry.find("crewai"))
    for key, value in environ.TELEMETRY_OFF.items():
        assert captured_env[key] == value


def test_a_run_pins_the_crewai_storage_key(captured_env):
    """Without this, consent is filed under the working directory's name.

    The answer would then be asked again from every new directory and never
    stay answered.
    """
    environ.run(registry.find("crewai"))
    assert captured_env["CREWAI_STORAGE_DIR"] == environ.CREWAI_STORAGE_NAME


def test_telemetry_flag_leaves_the_defaults_alone(captured_env, monkeypatch):
    """--telemetry is opt-in, and opting in must actually reach the stack."""
    monkeypatch.delenv("CREWAI_DISABLE_TELEMETRY", raising=False)
    environ.run(registry.find("crewai"), telemetry=True)
    assert "CREWAI_DISABLE_TELEMETRY" not in captured_env
    assert "CREWAI_STORAGE_DIR" not in captured_env


def test_overrides_still_reach_the_stack(captured_env):
    """Turning telemetry off must not trample the CARBONARA_* channel."""
    environ.run(registry.find("crewai"), {"CARBONARA_ORDER": "feed six"})
    assert captured_env["CARBONARA_ORDER"] == "feed six"


def test_tracing_is_declined_when_never_answered(tmp_path):
    """crewai's first-run prompt reads the file before it asks. A decline stops it."""
    assert environ.decline_crewai_tracing() is True
    written = json.loads((tmp_path / "state" / ".crewai_user.json").read_text())
    assert written["trace_consent"] is False


def test_the_decline_is_a_literal_false(tmp_path):
    """crewai tests consent with `is not False`, so null would enable tracing."""
    environ.decline_crewai_tracing()
    raw = (tmp_path / "state" / ".crewai_user.json").read_text()
    assert '"trace_consent": false' in raw


def test_an_existing_answer_is_never_overwritten(tmp_path):
    """A deliberate yes recorded earlier survives. carbonara answers once."""
    path = tmp_path / "state" / ".crewai_user.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"trace_consent": True, "user_id": "abc"}))

    assert environ.decline_crewai_tracing() is False
    kept = json.loads(path.read_text())
    assert kept["trace_consent"] is True
    assert kept["user_id"] == "abc"


def test_the_stacks_that_call_home_are_the_measured_ones():
    """crewai and smolagents, as measured. langgraph only could, with tracing on."""
    assert registry.PHONES_HOME == {"crewai", "smolagents"}
    assert {s.name for s in registry.stacks() if s.phones_home} == set(
        registry.PHONES_HOME
    )


def test_every_stack_that_phones_home_is_a_real_stack():
    """A typo in the set marks a stack harmless and nothing else would catch it."""
    assert registry.PHONES_HOME <= set(registry.NAMES)


def test_list_shows_which_stacks_call_home(invoke):
    """The finding has to be visible, not merely true."""
    code, out, _ = invoke("list")
    assert code == 0
    assert "CALLS HOME" in out

    # Split on the two-space column gutter, since a cell can hold a phrase:
    # the environment column carries "not built" and "no python 3.12".
    rows = {}
    for line in out.splitlines():
        cells = re.split(r"\s{2,}", line.strip())
        if cells and cells[0] in registry.NAMES:
            rows[cells[0]] = cells[3]

    assert rows["no-framework"] == "no"
    assert rows["crewai"] == "yes"
    assert rows["langgraph"] == "no"
    assert rows["smolagents"] == "yes"
    assert sorted(name for name, calls in rows.items() if calls == "yes") == sorted(
        registry.PHONES_HOME
    )


def test_calls_home_doc_agrees_with_the_registry():
    """The measured table and PHONES_HOME name the same stacks.

    The doc is where the measurement lives and the registry is what list
    prints, so a stack added to one and not the other would be a claim with
    nothing behind it.
    """
    doc = (Path(__file__).parent.parent / "docs" / "CALLS-HOME.md").read_text()
    section = doc.split("## What each stack does")[1].split("\n## ")[0]
    reached = set()
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells[0] in registry.NAMES and cells[1] != "nothing":
            reached.add(cells[0])
    assert reached == registry.PHONES_HOME
