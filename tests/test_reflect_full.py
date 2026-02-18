"""
Tests for persona.cognitive_modules.reflect — reflect() function.
"""
import datetime
from unittest.mock import MagicMock, patch, call

import persona.cognitive_modules.reflect as reflect_mod

# Inject 'debug' into the reflect module namespace (normally comes from
# ``from utils import *`` at runtime but the utils stub doesn't propagate
# through ``from global_methods import *``).
reflect_mod.debug = False

from persona.cognitive_modules.reflect import reflect


def _make_persona(
    importance_trigger_curr=150,
    chatting_end_time=None,
    chatting_with=None,
    chat=None,
    seq_event=None,
    seq_thought=None,
):
    """Build a minimal mock persona for reflect() tests."""
    persona = MagicMock()
    persona.name = "Alice"

    scratch = MagicMock()
    scratch.name = "Alice"
    scratch.curr_time = datetime.datetime(2023, 2, 13, 14, 0, 0)
    scratch.importance_trigger_curr = importance_trigger_curr
    scratch.importance_trigger_max = 150
    scratch.importance_ele_n = 5
    scratch.chatting_with = chatting_with
    scratch.chatting_end_time = chatting_end_time
    scratch.chat = chat
    scratch.act_description = "chatting"
    persona.scratch = scratch

    a_mem = MagicMock()
    a_mem.seq_event = seq_event if seq_event is not None else []
    a_mem.seq_thought = seq_thought if seq_thought is not None else []
    a_mem.add_thought = MagicMock()
    a_mem.get_last_chat = MagicMock(
        return_value=MagicMock(node_id="chat_123")
    )
    a_mem.embeddings = {}
    persona.a_mem = a_mem

    return persona


# ------------------------------------------------------------------ #
# 1. run_reflect called when triggered
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_run_reflect_called_when_triggered(mock_run_reflect):
    persona = _make_persona(
        importance_trigger_curr=-1,
        seq_event=[MagicMock()],
    )
    reflect(persona)
    mock_run_reflect.assert_called_once_with(persona)


# ------------------------------------------------------------------ #
# 2. counter reset after reflect
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_counter_reset_after_reflect(mock_run_reflect):
    persona = _make_persona(
        importance_trigger_curr=-1,
        seq_event=[MagicMock()],
    )
    reflect(persona)
    assert persona.scratch.importance_trigger_curr == 150
    assert persona.scratch.importance_ele_n == 0


# ------------------------------------------------------------------ #
# 3. skips when not triggered
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_skips_when_not_triggered(mock_run_reflect):
    persona = _make_persona(importance_trigger_curr=100)
    reflect(persona)
    mock_run_reflect.assert_not_called()


# ------------------------------------------------------------------ #
# 4. chatting_end_time processing runs when time matches
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_chatting_end_time_processing(mock_run_reflect):
    end_time = datetime.datetime(2023, 2, 13, 14, 0, 10)
    persona = _make_persona(
        chatting_end_time=end_time,
        chatting_with="Bob",
        chat=[["Alice", "Hi"], ["Bob", "Hello"]],
    )
    reflect(persona)
    # Two add_thought calls: planning thought + memo thought
    assert persona.a_mem.add_thought.call_count == 2


# ------------------------------------------------------------------ #
# 5. chatting_end_time not reached — processing skipped
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_chatting_end_time_not_reached(mock_run_reflect):
    # end_time does NOT equal curr_time + 10 seconds
    end_time = datetime.datetime(2023, 2, 13, 14, 5, 0)
    persona = _make_persona(
        chatting_end_time=end_time,
        chatting_with="Bob",
        chat=[["Alice", "Hi"], ["Bob", "Hello"]],
    )
    reflect(persona)
    persona.a_mem.add_thought.assert_not_called()


# ------------------------------------------------------------------ #
# 6. chatting_end_time is None — no error
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_chatting_end_time_none(mock_run_reflect):
    persona = _make_persona(chatting_end_time=None)
    reflect(persona)
    persona.a_mem.add_thought.assert_not_called()


# ------------------------------------------------------------------ #
# 7. planning thought added to a_mem
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_planning_thought_added(mock_run_reflect):
    end_time = datetime.datetime(2023, 2, 13, 14, 0, 10)
    persona = _make_persona(
        chatting_end_time=end_time,
        chatting_with="Bob",
        chat=[["Alice", "Hi"], ["Bob", "Hello"]],
    )
    reflect(persona)

    # First add_thought call is the planning thought
    first_call = persona.a_mem.add_thought.call_args_list[0]
    args = first_call[0]
    # args: created, expiration, s, p, o, thought_text, keywords, poignancy,
    #        embedding_pair, evidence
    thought_text = args[5]
    assert thought_text == "For Alice's planning: thought"


# ------------------------------------------------------------------ #
# 8. memo thought added to a_mem
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_memo_thought_added(mock_run_reflect):
    end_time = datetime.datetime(2023, 2, 13, 14, 0, 10)
    persona = _make_persona(
        chatting_end_time=end_time,
        chatting_with="Bob",
        chat=[["Alice", "Hi"], ["Bob", "Hello"]],
    )
    reflect(persona)

    # Second add_thought call is the memo thought
    second_call = persona.a_mem.add_thought.call_args_list[1]
    args = second_call[0]
    thought_text = args[5]
    assert thought_text == "Alice memo"


# ------------------------------------------------------------------ #
# 9. chat utterances concatenated correctly
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.generate_planning_thought_on_convo")
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_chat_utterances_concatenated(mock_run_reflect, mock_gen_planning):
    mock_gen_planning.return_value = "thought"
    end_time = datetime.datetime(2023, 2, 13, 14, 0, 10)
    persona = _make_persona(
        chatting_end_time=end_time,
        chatting_with="Bob",
        chat=[["Alice", "Hi"], ["Bob", "Hello"]],
    )
    reflect(persona)

    # generate_planning_thought_on_convo is called with persona and all_utt
    called_args = mock_gen_planning.call_args[0]
    all_utt = called_args[1]
    assert all_utt == "Alice: Hi\nBob: Hello\n"


# ------------------------------------------------------------------ #
# 10. evidence from last chat
# ------------------------------------------------------------------ #
@patch("persona.cognitive_modules.reflect.run_reflect")
def test_evidence_from_last_chat(mock_run_reflect):
    end_time = datetime.datetime(2023, 2, 13, 14, 0, 10)
    persona = _make_persona(
        chatting_end_time=end_time,
        chatting_with="Bob",
        chat=[["Alice", "Hi"], ["Bob", "Hello"]],
    )
    reflect(persona)

    persona.a_mem.get_last_chat.assert_called_with("Bob")

    # Both add_thought calls should use the same evidence
    for c in persona.a_mem.add_thought.call_args_list:
        evidence = c[0][9]
        assert evidence == ["chat_123"]
