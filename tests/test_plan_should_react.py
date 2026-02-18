"""Tests for _should_react() in persona/cognitive_modules/plan.py."""

import datetime
from unittest.mock import MagicMock

import pytest

from persona.cognitive_modules import plan as plan_module
from persona.cognitive_modules.plan import _should_react


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_persona(name, **scratch_attrs):
    """Return a MagicMock persona with sensible scratch defaults."""
    p = MagicMock()
    p.name = name

    defaults = dict(
        act_address="the_ville:main_room",
        act_description="working on a project",
        chatting_with=None,
        chatting_with_buffer={},
        curr_time=datetime.datetime(2023, 2, 13, 10, 0),
        planned_path=[(1, 2), (3, 4)],
        act_start_time=datetime.datetime(2023, 2, 13, 10, 0),
        act_duration=30,
    )
    defaults.update(scratch_attrs)

    for attr, val in defaults.items():
        setattr(p.scratch, attr, val)

    return p


def _make_retrieved(subject):
    """Build a minimal retrieved dict with a ConceptNode stub."""
    node = MagicMock()
    node.subject = subject
    return {"curr_event": node, "events": [], "thoughts": []}


# ---------------------------------------------------------------------------
# Top-level guard tests
# ---------------------------------------------------------------------------

class TestTopLevelGuards:
    def test_chatting_with_returns_false(self):
        """persona.scratch.chatting_with is set -> False immediately."""
        persona = make_persona("Alice", chatting_with="Bob")
        target = make_persona("Bob")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        assert _should_react(persona, retrieved, personas) is False

    def test_waiting_address_returns_false(self):
        """persona.scratch.act_address contains '<waiting>' -> False."""
        persona = make_persona("Alice", act_address="<waiting> for Bob")
        target = make_persona("Bob")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        assert _should_react(persona, retrieved, personas) is False

    def test_non_persona_event_returns_false(self):
        """curr_event.subject contains ':' (object event) -> False."""
        persona = make_persona("Alice")
        retrieved = _make_retrieved("the_ville:kitchen:stove")
        personas = {}

        assert _should_react(persona, retrieved, personas) is False


# ---------------------------------------------------------------------------
# lets_talk path tests
# ---------------------------------------------------------------------------

class TestLetsTalk:
    def test_target_no_act_address(self, monkeypatch):
        """Target's act_address is None -> lets_talk returns False, no chat."""
        persona = make_persona("Alice")
        target = make_persona("Bob", act_address=None)
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        # lets_talk returns False (no act_address), then lets_react is called.
        # Make lets_react also return False.
        monkeypatch.setattr(
            plan_module, "generate_decide_to_react", lambda *a, **kw: "2"
        )

        result = _should_react(persona, retrieved, personas)
        assert result is False

    def test_sleeping_returns_false(self, monkeypatch):
        """Either persona sleeping -> lets_talk returns False."""
        persona = make_persona("Alice", act_description="sleeping in bed")
        target = make_persona("Bob")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_react", lambda *a, **kw: "2"
        )

        result = _should_react(persona, retrieved, personas)
        assert result is False

    def test_hour_23_returns_false(self, monkeypatch):
        """curr_time.hour == 23 -> lets_talk returns False."""
        persona = make_persona(
            "Alice", curr_time=datetime.datetime(2023, 2, 13, 23, 0)
        )
        target = make_persona("Bob")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_react", lambda *a, **kw: "2"
        )

        result = _should_react(persona, retrieved, personas)
        assert result is False

    def test_target_waiting(self, monkeypatch):
        """Target's act_address contains '<waiting>' -> lets_talk returns False."""
        persona = make_persona("Alice")
        target = make_persona("Bob", act_address="<waiting> for Alice")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_react", lambda *a, **kw: "2"
        )

        result = _should_react(persona, retrieved, personas)
        assert result is False

    def test_target_chatting(self, monkeypatch):
        """Target is already chatting -> lets_talk returns False."""
        persona = make_persona("Alice")
        target = make_persona("Bob", chatting_with="Charlie")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_react", lambda *a, **kw: "2"
        )

        result = _should_react(persona, retrieved, personas)
        assert result is False

    def test_buffer_positive(self, monkeypatch):
        """Buffer > 0 for target -> lets_talk returns False."""
        persona = make_persona("Alice", chatting_with_buffer={"Bob": 5})
        target = make_persona("Bob")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_react", lambda *a, **kw: "2"
        )

        result = _should_react(persona, retrieved, personas)
        assert result is False

    def test_buffer_zero_allows(self, monkeypatch):
        """Buffer == 0 + decide_to_talk=True -> 'chat with Bob'."""
        persona = make_persona("Alice", chatting_with_buffer={"Bob": 0})
        target = make_persona("Bob")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_talk", lambda *a, **kw: True
        )

        result = _should_react(persona, retrieved, personas)
        assert result == "chat with Bob"


# ---------------------------------------------------------------------------
# lets_react path tests
# ---------------------------------------------------------------------------

class TestLetsReact:
    def test_different_address(self, monkeypatch):
        """Different act_address between init and target -> False."""
        persona = make_persona("Alice", act_address="the_ville:park")
        target = make_persona("Bob", act_address="the_ville:library")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_talk", lambda *a, **kw: False
        )

        result = _should_react(persona, retrieved, personas)
        assert result is False

    def test_empty_planned_path(self, monkeypatch):
        """planned_path == [] -> lets_react returns False."""
        persona = make_persona("Alice", planned_path=[])
        target = make_persona("Bob")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_talk", lambda *a, **kw: False
        )

        result = _should_react(persona, retrieved, personas)
        assert result is False

    def test_react_mode_1_wait(self, monkeypatch):
        """React mode '1' -> returns 'wait: <datetime>' string."""
        start = datetime.datetime(2023, 2, 13, 10, 0)
        persona = make_persona("Alice")
        target = make_persona(
            "Bob",
            act_start_time=start,
            act_duration=30,
        )
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_talk", lambda *a, **kw: False
        )
        monkeypatch.setattr(
            plan_module, "generate_decide_to_react", lambda *a, **kw: "1"
        )

        result = _should_react(persona, retrieved, personas)
        expected_time = (start + datetime.timedelta(minutes=29)).strftime(
            "%B %d, %Y, %H:%M:%S"
        )
        assert result == f"wait: {expected_time}"

    def test_react_mode_2_false(self, monkeypatch):
        """React mode '2' -> returns False."""
        persona = make_persona("Alice")
        target = make_persona("Bob")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_talk", lambda *a, **kw: False
        )
        monkeypatch.setattr(
            plan_module, "generate_decide_to_react", lambda *a, **kw: "2"
        )

        result = _should_react(persona, retrieved, personas)
        assert result is False


# ---------------------------------------------------------------------------
# Cross-persona scratch field access
# ---------------------------------------------------------------------------

class TestCrossPersonaScratchFields:
    def test_cross_persona_scratch_fields(self, monkeypatch):
        """Verify which scratch fields of the target persona are read.

        We set up a scenario where lets_talk passes all guards and then
        GPT decides to talk.  We verify that the code accessed the expected
        scratch attributes on the target: act_address, act_description,
        chatting_with, and name.
        """
        persona = make_persona("Alice")
        target = make_persona("Bob")
        retrieved = _make_retrieved("Bob")
        personas = {"Bob": target}

        monkeypatch.setattr(
            plan_module, "generate_decide_to_talk", lambda *a, **kw: True
        )

        result = _should_react(persona, retrieved, personas)
        assert result == "chat with Bob"

        # Verify target scratch fields that were accessed
        scratch = target.scratch
        # act_address is checked in both lets_talk guard and lets_react guard
        assert scratch.act_address is not None
        # act_description is checked for "sleeping"
        assert scratch.act_description is not None
        # chatting_with is checked in lets_talk
        # name is used to look up chatting_with_buffer
        assert target.name == "Bob"
