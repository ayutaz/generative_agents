"""Tests for _choose_retrieved() in persona/cognitive_modules/plan.py."""

import random
from unittest.mock import MagicMock

import pytest

from persona.cognitive_modules.plan import _choose_retrieved


def _make_node(subject, predicate="is", obj="something", description=None):
    """Create a mock ConceptNode with the given attributes."""
    node = MagicMock()
    node.subject = subject
    node.predicate = predicate
    node.object = obj
    node.description = description or f"{subject} {predicate} {obj}"
    return node


def _make_entry(node):
    """Wrap a ConceptNode into a retrieved-dict entry."""
    return {"curr_event": node, "events": [node], "thoughts": []}


# -----------------------------------------------------------------------
# 1. Empty retrieved dict returns None
# -----------------------------------------------------------------------
def test_empty_retrieved_returns_none():
    persona = MagicMock()
    persona.name = "Alice"
    assert _choose_retrieved(persona, {}) is None


# -----------------------------------------------------------------------
# 2. Self-events are filtered out
# -----------------------------------------------------------------------
def test_self_events_filtered_out():
    persona = MagicMock()
    persona.name = "Alice"

    node = _make_node("Alice", "is", "cooking")
    retrieved = {node.description: _make_entry(node)}

    result = _choose_retrieved(persona, retrieved)
    assert result is None


# -----------------------------------------------------------------------
# 3. Persona events (no ":" in subject) are prioritized over object events
# -----------------------------------------------------------------------
def test_persona_event_prioritized():
    persona = MagicMock()
    persona.name = "Alice"

    person_node = _make_node("Bob", "is", "talking")
    object_node = _make_node("kitchen:stove", "is", "on")

    retrieved = {
        person_node.description: _make_entry(person_node),
        object_node.description: _make_entry(object_node),
    }

    result = _choose_retrieved(persona, retrieved)
    assert result["curr_event"].subject == "Bob"


# -----------------------------------------------------------------------
# 4. Object event chosen when no persona events exist
# -----------------------------------------------------------------------
def test_object_event_chosen_when_no_persona():
    persona = MagicMock()
    persona.name = "Alice"

    obj_node = _make_node("kitchen:stove", "is", "on")
    retrieved = {obj_node.description: _make_entry(obj_node)}

    result = _choose_retrieved(persona, retrieved)
    assert result is not None
    assert result["curr_event"].subject == "kitchen:stove"


# -----------------------------------------------------------------------
# 5. "is idle" events are skipped when non-idle events exist
# -----------------------------------------------------------------------
def test_idle_events_skipped():
    persona = MagicMock()
    persona.name = "Alice"

    idle_node = _make_node("kitchen:stove", "is", "idle",
                           description="kitchen:stove is idle")
    active_node = _make_node("kitchen:oven", "is", "heating",
                             description="kitchen:oven is heating")

    retrieved = {
        idle_node.description: _make_entry(idle_node),
        active_node.description: _make_entry(active_node),
    }

    result = _choose_retrieved(persona, retrieved)
    assert result is not None
    assert result["curr_event"].subject == "kitchen:oven"


# -----------------------------------------------------------------------
# 6. All idle events returns None
# -----------------------------------------------------------------------
def test_all_idle_returns_none():
    persona = MagicMock()
    persona.name = "Alice"

    idle1 = _make_node("kitchen:stove", "is", "idle",
                       description="kitchen:stove is idle")
    idle2 = _make_node("bedroom:lamp", "is", "idle",
                       description="bedroom:lamp is idle")

    retrieved = {
        idle1.description: _make_entry(idle1),
        idle2.description: _make_entry(idle2),
    }

    result = _choose_retrieved(persona, retrieved)
    assert result is None


# -----------------------------------------------------------------------
# 7. Mix of self + other persona + object events
# -----------------------------------------------------------------------
def test_mixed_self_and_other():
    persona = MagicMock()
    persona.name = "Alice"

    self_node = _make_node("Alice", "is", "walking")
    other_node = _make_node("Bob", "is", "running")
    obj_node = _make_node("park:bench", "is", "empty")

    retrieved = {
        self_node.description: _make_entry(self_node),
        other_node.description: _make_entry(other_node),
        obj_node.description: _make_entry(obj_node),
    }

    result = _choose_retrieved(persona, retrieved)
    # Self-event removed; Bob (persona, no ":") should be prioritized
    assert result["curr_event"].subject == "Bob"


# -----------------------------------------------------------------------
# 8. Multiple candidates => random.choice is called
# -----------------------------------------------------------------------
def test_random_choice_with_seed(monkeypatch):
    persona = MagicMock()
    persona.name = "Alice"

    bob_node = _make_node("Bob", "is", "talking")
    carol_node = _make_node("Carol", "is", "singing")

    retrieved = {
        bob_node.description: _make_entry(bob_node),
        carol_node.description: _make_entry(carol_node),
    }

    chosen = []
    original_choice = random.choice

    def tracking_choice(seq):
        result = original_choice(seq)
        chosen.append(result)
        return result

    monkeypatch.setattr(random, "choice", tracking_choice)

    _choose_retrieved(persona, retrieved)
    assert len(chosen) == 1
    assert chosen[0]["curr_event"].subject in ("Bob", "Carol")


# -----------------------------------------------------------------------
# 9. Original retrieved dict has self-events deleted (mutation)
# -----------------------------------------------------------------------
def test_retrieved_mutated_removes_self():
    persona = MagicMock()
    persona.name = "Alice"

    self_node = _make_node("Alice", "is", "sleeping")
    other_node = _make_node("Bob", "is", "reading")

    retrieved = {
        self_node.description: _make_entry(self_node),
        other_node.description: _make_entry(other_node),
    }

    _choose_retrieved(persona, retrieved)

    # The original dict should no longer contain the self-event
    assert self_node.description not in retrieved
    assert other_node.description in retrieved
