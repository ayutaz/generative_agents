"""Tests for plan() control flow in persona/cognitive_modules/plan.py."""
from unittest.mock import MagicMock, patch

import pytest

from persona.cognitive_modules.plan import plan

MODULE = "persona.cognitive_modules.plan"


def _make_persona(
    *,
    act_check_finished=False,
    act_event=("Alice", "working", "painting"),
    act_address="world:sector:arena:obj",
    chatting_with=None,
    chat=None,
    chatting_end_time=None,
    chatting_with_buffer=None,
):
    persona = MagicMock()
    persona.name = "Alice"
    persona.scratch.act_check_finished.return_value = act_check_finished
    persona.scratch.act_event = act_event
    persona.scratch.act_address = act_address
    persona.scratch.chatting_with = chatting_with
    persona.scratch.chat = chat
    persona.scratch.chatting_end_time = chatting_end_time
    persona.scratch.chatting_with_buffer = (
        chatting_with_buffer if chatting_with_buffer is not None else {}
    )
    return persona


# ── PART 1: long-term planning ──────────────────────────────────────────


@patch(f"{MODULE}._long_term_planning")
def test_new_day_false_skips_ltp(mock_ltp):
    persona = _make_persona()
    plan(persona, MagicMock(), {}, False, {})
    mock_ltp.assert_not_called()


@patch(f"{MODULE}._long_term_planning")
def test_first_day_calls_ltp(mock_ltp):
    persona = _make_persona()
    plan(persona, MagicMock(), {}, "First day", {})
    mock_ltp.assert_called_once_with(persona, "First day")


@patch(f"{MODULE}._long_term_planning")
def test_new_day_calls_ltp(mock_ltp):
    persona = _make_persona()
    plan(persona, MagicMock(), {}, "New day", {})
    mock_ltp.assert_called_once_with(persona, "New day")


# ── PART 2: determine action ────────────────────────────────────────────


@patch(f"{MODULE}._determine_action")
def test_act_finished_calls_determine(mock_det):
    persona = _make_persona(act_check_finished=True)
    maze = MagicMock()
    plan(persona, maze, {}, False, {})
    mock_det.assert_called_once_with(persona, maze)


@patch(f"{MODULE}._determine_action")
def test_act_ongoing_skips_determine(mock_det):
    persona = _make_persona(act_check_finished=False)
    plan(persona, MagicMock(), {}, False, {})
    mock_det.assert_not_called()


# ── PART 3: reaction to retrieved events ────────────────────────────────


@patch(f"{MODULE}._choose_retrieved")
def test_empty_retrieved_no_reaction(mock_choose):
    persona = _make_persona()
    plan(persona, MagicMock(), {}, False, {})
    mock_choose.assert_not_called()


@patch(f"{MODULE}._should_react")
@patch(f"{MODULE}._choose_retrieved", return_value=None)
def test_choose_none_no_reaction(mock_choose, mock_react):
    persona = _make_persona()
    retrieved = {"evt": {"curr_event": "e", "events": [], "thoughts": []}}
    plan(persona, MagicMock(), {}, False, retrieved)
    mock_choose.assert_called_once()
    mock_react.assert_not_called()


@patch(f"{MODULE}._chat_react")
@patch(f"{MODULE}._should_react", return_value="chat with Bob")
@patch(f"{MODULE}._choose_retrieved", return_value={"curr_event": "e"})
def test_chat_reaction_dispatch(mock_choose, mock_react, mock_chat):
    persona = _make_persona()
    maze = MagicMock()
    personas = {"Alice": persona}
    retrieved = {"evt": {"curr_event": "e"}}
    focused = mock_choose.return_value
    plan(persona, maze, personas, False, retrieved)
    mock_chat.assert_called_once_with(
        maze, persona, focused, "chat with Bob", personas
    )


@patch(f"{MODULE}._wait_react")
@patch(
    f"{MODULE}._should_react",
    return_value="wait: Feb 13, 2023, 15:30:00",
)
@patch(f"{MODULE}._choose_retrieved", return_value={"curr_event": "e"})
def test_wait_reaction_dispatch(mock_choose, mock_react, mock_wait):
    persona = _make_persona()
    retrieved = {"evt": {"curr_event": "e"}}
    plan(persona, MagicMock(), {}, False, retrieved)
    mock_wait.assert_called_once_with(persona, "wait: Feb 13, 2023, 15:30:00")


@patch(f"{MODULE}._wait_react")
@patch(f"{MODULE}._chat_react")
@patch(f"{MODULE}._should_react", return_value=False)
@patch(f"{MODULE}._choose_retrieved", return_value={"curr_event": "e"})
def test_false_reaction_no_dispatch(mock_choose, mock_react, mock_chat, mock_wait):
    persona = _make_persona()
    retrieved = {"evt": {"curr_event": "e"}}
    plan(persona, MagicMock(), {}, False, retrieved)
    mock_chat.assert_not_called()
    mock_wait.assert_not_called()


# ── Chat cleanup ────────────────────────────────────────────────────────


def test_chat_cleanup_non_chat():
    persona = _make_persona(
        act_event=("Alice", "working", "painting"),
        chatting_with="Bob",
        chat=["some", "chat"],
        chatting_end_time="some_time",
    )
    plan(persona, MagicMock(), {}, False, {})
    assert persona.scratch.chatting_with is None
    assert persona.scratch.chat is None
    assert persona.scratch.chatting_end_time is None


def test_chat_cleanup_preserves():
    persona = _make_persona(
        act_event=("Alice", "chat with", "Bob"),
        chatting_with="Bob",
        chat=["some", "chat"],
        chatting_end_time="some_time",
    )
    plan(persona, MagicMock(), {}, False, {})
    assert persona.scratch.chatting_with == "Bob"
    assert persona.scratch.chat == ["some", "chat"]
    assert persona.scratch.chatting_end_time == "some_time"


# ── Buffer decrement ────────────────────────────────────────────────────


def test_buffer_decrement():
    persona = _make_persona(
        chatting_with=None,
        chatting_with_buffer={"Bob": 5, "Carol": 3},
    )
    plan(persona, MagicMock(), {}, False, {})
    assert persona.scratch.chatting_with_buffer["Bob"] == 4
    assert persona.scratch.chatting_with_buffer["Carol"] == 2


def test_buffer_chatting_partner_preserved():
    persona = _make_persona(
        act_event=("Alice", "chat with", "Bob"),
        chatting_with="Bob",
        chatting_with_buffer={"Bob": 5, "Carol": 3},
    )
    plan(persona, MagicMock(), {}, False, {})
    assert persona.scratch.chatting_with_buffer["Bob"] == 5
    assert persona.scratch.chatting_with_buffer["Carol"] == 2


# ── Return value ────────────────────────────────────────────────────────


def test_returns_act_address():
    persona = _make_persona(act_address="the_ville:main:cafe:table")
    result = plan(persona, MagicMock(), {}, False, {})
    assert result == "the_ville:main:cafe:table"
