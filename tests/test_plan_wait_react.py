"""Tests for _wait_react() in persona/cognitive_modules/plan.py."""

import datetime
from unittest.mock import MagicMock

import pytest

import persona.cognitive_modules.plan as plan_module
from persona.cognitive_modules.plan import _wait_react


@pytest.fixture
def persona():
    """Mock persona with scratch attributes used by _wait_react."""
    p = MagicMock()
    p.name = "Isabella Rodriguez"
    p.scratch.act_description = "working on project (painting canvas)"
    p.scratch.curr_time = datetime.datetime(2023, 2, 13, 14, 0)
    p.scratch.curr_tile = (55, 35)
    return p


@pytest.fixture
def reaction_mode():
    return "wait: February 13, 2023, 15:30:00"


@pytest.fixture
def captured_args(monkeypatch):
    """Monkeypatch _create_react to capture its call arguments."""
    calls = []

    def mock_create_react(*args):
        calls.append(args)

    monkeypatch.setattr(plan_module, "_create_react", mock_create_react)
    return calls


# -----------------------------------------------------------------------
# 1. inserted_act format: "waiting to start {parenthetical content}"
# -----------------------------------------------------------------------
def test_inserted_act_format(persona, reaction_mode, captured_args):
    _wait_react(persona, reaction_mode)
    assert len(captured_args) == 1
    # args: (persona, inserted_act, inserted_act_dur, ...)
    inserted_act = captured_args[0][1]
    assert inserted_act == "waiting to start painting canvas"


# -----------------------------------------------------------------------
# 2. Duration calculation: (end_h*60 + end_m) - (curr_h*60 + curr_m) + 1
# -----------------------------------------------------------------------
def test_duration_calculation(persona, reaction_mode, captured_args):
    _wait_react(persona, reaction_mode)
    inserted_act_dur = captured_args[0][2]
    # end_time = 15:30 → 15*60+30 = 930
    # curr_time = 14:00 → 14*60+0 = 840
    # duration = 930 - 840 + 1 = 91
    assert inserted_act_dur == 91


# -----------------------------------------------------------------------
# 3. act_address format: "<waiting> x y"
# -----------------------------------------------------------------------
def test_act_address_format(persona, reaction_mode, captured_args):
    _wait_react(persona, reaction_mode)
    act_address = captured_args[0][3]
    assert act_address == "<waiting> 55 35"


# -----------------------------------------------------------------------
# 4. act_event format: (name, "waiting to start", detail)
# -----------------------------------------------------------------------
def test_act_event_format(persona, reaction_mode, captured_args):
    _wait_react(persona, reaction_mode)
    act_event = captured_args[0][4]
    assert act_event == ("Isabella Rodriguez", "waiting to start", "painting canvas")


# -----------------------------------------------------------------------
# 5. Pronunciatio is the hourglass emoji
# -----------------------------------------------------------------------
def test_pronunciatio_hourglass(persona, reaction_mode, captured_args):
    _wait_react(persona, reaction_mode)
    act_pronunciatio = captured_args[0][9]
    assert act_pronunciatio == "\u231b"


# -----------------------------------------------------------------------
# 6. _create_react is called with all correct parameters
# -----------------------------------------------------------------------
def test_create_react_called(persona, reaction_mode, captured_args):
    _wait_react(persona, reaction_mode)
    assert len(captured_args) == 1
    args = captured_args[0]
    # 13 positional args total
    assert len(args) == 13
    assert args[0] is persona               # persona
    assert args[1] == "waiting to start painting canvas"  # inserted_act
    assert args[2] == 91                     # inserted_act_dur
    assert args[3] == "<waiting> 55 35"      # act_address
    assert args[4] == ("Isabella Rodriguez", "waiting to start", "painting canvas")  # act_event
    assert args[5] is None                   # chatting_with
    assert args[6] is None                   # chat
    assert args[7] is None                   # chatting_with_buffer
    assert args[8] is None                   # chatting_end_time
    assert args[9] == "\u231b"               # act_pronunciatio
    assert args[10] is None                  # act_obj_description
    assert args[11] is None                  # act_obj_pronunciatio
    assert args[12] == (None, None, None)    # act_obj_event
