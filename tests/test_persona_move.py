"""Tests for Persona.move() — the main cognitive loop."""

import datetime
from unittest.mock import MagicMock, patch, call

from persona.persona import Persona


class FakePersona:
    """Minimal stand-in that borrows Persona.move without touching the filesystem."""

    def __init__(self):
        self.name = "Alice"
        self.scratch = MagicMock()
        self.scratch.curr_time = None
        self.scratch.curr_tile = None

    # Bind the real move/phase methods from Persona
    move = Persona.move
    move_phase_a = Persona.move_phase_a
    move_phase_b = Persona.move_phase_b


def _make_persona(**overrides):
    """Create a FakePersona with monkeypatched cognitive methods."""
    p = FakePersona()
    p.perceive = MagicMock(return_value=["perceived_event"])
    p.retrieve = MagicMock(return_value={"retrieved": True})
    p.plan = MagicMock(return_value="plan_output")
    p.reflect = MagicMock(return_value=None)
    p.execute = MagicMock(return_value=((58, 9), "\U0001f4a4", "sleeping"))
    for k, v in overrides.items():
        setattr(p, k, v) if not k.startswith("scratch.") else None
    return p


# ---- fixtures reused across tests ----
_MAZE = MagicMock(name="maze")
_PERSONAS = {"Alice": "persona_obj"}
_TILE = (10, 20)
_TIME = datetime.datetime(2023, 2, 13, 8, 0, 0)


# -----------------------------------------------------------------------
# 1. curr_tile is set on scratch
# -----------------------------------------------------------------------
def test_curr_tile_set():
    p = _make_persona()
    with patch("persona.persona.plan_action_only"), \
         patch("persona.persona.plan_react_only", return_value="plan_output"):
        p.move(_MAZE, _PERSONAS, _TILE, _TIME)
    assert p.scratch.curr_tile == _TILE


# -----------------------------------------------------------------------
# 2. curr_time is set on scratch
# -----------------------------------------------------------------------
def test_curr_time_set():
    p = _make_persona()
    with patch("persona.persona.plan_action_only"), \
         patch("persona.persona.plan_react_only", return_value="plan_output"):
        p.move(_MAZE, _PERSONAS, _TILE, _TIME)
    assert p.scratch.curr_time == _TIME


# -----------------------------------------------------------------------
# 3. curr_time=None before move -> new_day="First day"
# -----------------------------------------------------------------------
def test_first_day_when_none():
    p = _make_persona()
    p.scratch.curr_time = None
    with patch("persona.persona.plan_action_only") as mock_pa, \
         patch("persona.persona.plan_react_only", return_value="plan_output"):
        p.move(_MAZE, _PERSONAS, _TILE, _TIME)
    # plan_action_only is called with (persona, maze, new_day)
    mock_pa.assert_called_once()
    _, _, new_day = mock_pa.call_args[0]
    assert new_day == "First day"


# -----------------------------------------------------------------------
# 4. date change -> new_day="New day"
# -----------------------------------------------------------------------
def test_new_day_date_change():
    p = _make_persona()
    p.scratch.curr_time = datetime.datetime(2023, 2, 12, 23, 59, 0)
    new_time = datetime.datetime(2023, 2, 13, 0, 1, 0)
    with patch("persona.persona.plan_action_only") as mock_pa, \
         patch("persona.persona.plan_react_only", return_value="plan_output"):
        p.move(_MAZE, _PERSONAS, _TILE, new_time)
    _, _, new_day = mock_pa.call_args[0]
    assert new_day == "New day"


# -----------------------------------------------------------------------
# 5. same day -> new_day=False
# -----------------------------------------------------------------------
def test_same_day():
    p = _make_persona()
    p.scratch.curr_time = datetime.datetime(2023, 2, 13, 7, 0, 0)
    new_time = datetime.datetime(2023, 2, 13, 8, 0, 0)
    with patch("persona.persona.plan_action_only") as mock_pa, \
         patch("persona.persona.plan_react_only", return_value="plan_output"):
        p.move(_MAZE, _PERSONAS, _TILE, new_time)
    _, _, new_day = mock_pa.call_args[0]
    assert new_day is False


# -----------------------------------------------------------------------
# 6. perceive->retrieve->plan_action->reflect->plan_react->execute order
# -----------------------------------------------------------------------
def test_cognitive_sequence_order():
    call_order = []
    p = _make_persona()
    p.perceive = MagicMock(side_effect=lambda m: (call_order.append("perceive"), ["ev"])[1])
    p.retrieve = MagicMock(side_effect=lambda pr: (call_order.append("retrieve"), {"r": 1})[1])
    p.reflect = MagicMock(side_effect=lambda: call_order.append("reflect"))
    p.execute = MagicMock(side_effect=lambda m, ps, pl: (call_order.append("execute"), ((0, 0), "", ""))[1])

    with patch("persona.persona.plan_action_only",
               side_effect=lambda *a: call_order.append("plan_action")), \
         patch("persona.persona.plan_react_only",
               side_effect=lambda *a: (call_order.append("plan_react"), "pln")[1]):
        p.move(_MAZE, _PERSONAS, _TILE, _TIME)

    assert call_order == [
        "perceive", "retrieve", "plan_action", "reflect",
        "plan_react", "execute"
    ]


# -----------------------------------------------------------------------
# 7. perceive called with maze
# -----------------------------------------------------------------------
def test_perceive_receives_maze():
    p = _make_persona()
    with patch("persona.persona.plan_action_only"), \
         patch("persona.persona.plan_react_only", return_value="plan_output"):
        p.move(_MAZE, _PERSONAS, _TILE, _TIME)
    p.perceive.assert_called_once_with(_MAZE)


# -----------------------------------------------------------------------
# 8. retrieve called with perceive's result
# -----------------------------------------------------------------------
def test_retrieve_receives_perceived():
    p = _make_persona()
    p.perceive.return_value = ["special_perceived"]
    with patch("persona.persona.plan_action_only"), \
         patch("persona.persona.plan_react_only", return_value="plan_output"):
        p.move(_MAZE, _PERSONAS, _TILE, _TIME)
    p.retrieve.assert_called_once_with(["special_perceived"])


# -----------------------------------------------------------------------
# 9. plan_action_only called with (persona, maze, new_day)
#    plan_react_only called with (persona, maze, personas, retrieved)
# -----------------------------------------------------------------------
def test_plan_receives_args():
    p = _make_persona()
    p.scratch.curr_time = None  # -> "First day"
    p.retrieve.return_value = {"key": "val"}
    with patch("persona.persona.plan_action_only") as mock_pa, \
         patch("persona.persona.plan_react_only", return_value="addr") as mock_pr:
        p.move(_MAZE, _PERSONAS, _TILE, _TIME)
    mock_pa.assert_called_once_with(p, _MAZE, "First day")
    mock_pr.assert_called_once_with(p, _MAZE, _PERSONAS, {"key": "val"})


# -----------------------------------------------------------------------
# 10. execute's return value is move()'s return value
# -----------------------------------------------------------------------
def test_execute_output_returned():
    p = _make_persona()
    expected = ((58, 9), "\U0001f4a4", "sleeping")
    p.execute.return_value = expected
    with patch("persona.persona.plan_action_only"), \
         patch("persona.persona.plan_react_only", return_value="plan_output"):
        result = p.move(_MAZE, _PERSONAS, _TILE, _TIME)
    assert result == expected


# -----------------------------------------------------------------------
# 11. date comparison uses '%A %B %d' format
# -----------------------------------------------------------------------
def test_strftime_comparison():
    """Two datetimes that differ in year but share the same '%A %B %d' are
    treated as the same day by move().  E.g., Monday February 13 appears
    in both 2023 and 2034, so move() should set new_day=False."""
    p = _make_persona()
    p.scratch.curr_time = datetime.datetime(2023, 2, 13, 10, 0, 0)
    new_time = datetime.datetime(2034, 2, 13, 10, 0, 0)
    with patch("persona.persona.plan_action_only") as mock_pa, \
         patch("persona.persona.plan_react_only", return_value="plan_output"):
        p.move(_MAZE, _PERSONAS, _TILE, new_time)
    _, _, new_day = mock_pa.call_args[0]
    assert new_day is False, (
        "move() should compare dates using '%A %B %d' (weekday month day), "
        "ignoring the year"
    )
