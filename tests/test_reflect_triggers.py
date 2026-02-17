"""
tests/test_reflect_triggers.py

reflect.py の reflection_trigger / reset_reflection_counter のユニットテスト。
"""
import pytest
from unittest.mock import MagicMock

from persona.cognitive_modules.reflect import (
    reflection_trigger,
    reset_reflection_counter,
)


# ---- helpers ----

def make_node(node_id="ev1"):
    node = MagicMock()
    node.node_id = node_id
    node.embedding_key = f"key_{node_id}"
    return node


def make_persona(trigger_curr=0, trigger_max=150,
                 seq_event=None, seq_thought=None):
    persona = MagicMock()
    persona.scratch.importance_trigger_curr = trigger_curr
    persona.scratch.importance_trigger_max = trigger_max
    persona.scratch.importance_ele_n = 10
    persona.scratch.name = "TestPersona"
    persona.a_mem.seq_event = seq_event if seq_event is not None else []
    persona.a_mem.seq_thought = seq_thought if seq_thought is not None else []
    return persona


# ================================================================
# reflection_trigger
# ================================================================

class TestReflectionTrigger:
    def test_trigger_curr_zero_with_events(self):
        persona = make_persona(trigger_curr=0,
                               seq_event=[make_node()])
        assert reflection_trigger(persona) is True

    def test_trigger_curr_positive(self):
        persona = make_persona(trigger_curr=50,
                               seq_event=[make_node()])
        assert reflection_trigger(persona) is False

    def test_trigger_curr_zero_empty_memory(self):
        persona = make_persona(trigger_curr=0,
                               seq_event=[], seq_thought=[])
        assert reflection_trigger(persona) is False

    def test_trigger_curr_negative_with_events(self):
        persona = make_persona(trigger_curr=-10,
                               seq_event=[make_node()])
        assert reflection_trigger(persona) is True


# ================================================================
# reset_reflection_counter
# ================================================================

class TestResetReflectionCounter:
    def test_curr_restored_to_max(self):
        persona = make_persona(trigger_curr=0, trigger_max=150)
        reset_reflection_counter(persona)
        assert persona.scratch.importance_trigger_curr == 150

    def test_importance_ele_n_reset_to_zero(self):
        persona = make_persona()
        persona.scratch.importance_ele_n = 42
        reset_reflection_counter(persona)
        assert persona.scratch.importance_ele_n == 0

    def test_custom_max_value(self):
        persona = make_persona(trigger_curr=-20, trigger_max=200)
        reset_reflection_counter(persona)
        assert persona.scratch.importance_trigger_curr == 200
        assert persona.scratch.importance_ele_n == 0
