"""Tests for execute() in persona/cognitive_modules/execute.py."""
import random
from unittest.mock import MagicMock, patch, call

import pytest

from persona.cognitive_modules.execute import execute

MODULE = "persona.cognitive_modules.execute"


def _make_persona(
    *,
    curr_tile=(50, 50),
    act_path_set=False,
    planned_path=None,
    act_description="painting",
    act_address="world:sector:arena:obj",
    act_pronunciatio="\U0001f3a8",
):
    persona = MagicMock()
    persona.scratch.curr_tile = curr_tile
    persona.scratch.act_path_set = act_path_set
    persona.scratch.planned_path = planned_path if planned_path is not None else []
    persona.scratch.act_description = act_description
    persona.scratch.act_address = act_address
    persona.scratch.act_pronunciatio = act_pronunciatio
    return persona


def _make_maze(address_tiles=None, collision_maze=None, access_tile_events=None):
    maze = MagicMock()
    maze.collision_maze = collision_maze or [[0] * 100 for _ in range(100)]
    maze.address_tiles = address_tiles if address_tiles is not None else {
        "world:sector:arena:obj": [(55, 55), (56, 55)],
    }
    if access_tile_events is None:
        maze.access_tile.return_value = {"events": set()}
    else:
        maze.access_tile.side_effect = access_tile_events
    return maze


def _straight_path(start, end):
    """Generate a simple straight horizontal path for mocking."""
    x0, y0 = start
    x1, y1 = end
    path = []
    x = x0
    step = 1 if x1 >= x0 else -1
    while x != x1 + step:
        path.append((x, y0))
        x += step
    return path


# ── 1. <persona> plan routing ──────────────────────────────────────────


@patch(f"{MODULE}.path_finder")
def test_persona_plan_routing(mock_pf):
    """<persona> Bob plan looks up Bob's curr_tile."""
    persona = _make_persona()
    bob = MagicMock()
    bob.scratch.curr_tile = (60, 60)
    personas = {"Bob": bob}
    maze = _make_maze()

    # Short path so we hit the len<=2 branch
    mock_pf.return_value = [(50, 50), (60, 60)]

    execute(persona, maze, personas, "<persona> Bob")

    # First call should be path_finder to Bob's tile
    first_call = mock_pf.call_args_list[0]
    assert first_call[0][1] == (50, 50)  # start
    assert first_call[0][2] == (60, 60)  # Bob's tile


# ── 2. <waiting> plan routing ──────────────────────────────────────────


@patch(f"{MODULE}.path_finder")
def test_waiting_plan_routing(mock_pf):
    """<waiting> 55 35 sets target_tiles=[[55, 35]]."""
    persona = _make_persona()
    maze = _make_maze()
    mock_pf.return_value = [(50, 50), (55, 35)]

    execute(persona, maze, {}, "<waiting> 55 35")

    # path_finder should be called with [55, 35] as target
    assert mock_pf.call_args_list[-1][0][2] == [55, 35]


# ── 3. <random> plan routing ──────────────────────────────────────────


@patch(f"{MODULE}.path_finder")
@patch(f"{MODULE}.random")
def test_random_plan_routing(mock_random, mock_pf):
    """<random> with address_tiles samples from address_tiles."""
    persona = _make_persona(planned_path=[])
    maze = _make_maze(address_tiles={
        "world:sector:arena": [(70, 70), (71, 71), (72, 72)],
    })

    mock_random.sample.side_effect = lambda lst, k: list(lst)[:k]
    mock_pf.return_value = [(50, 50), (70, 70)]

    execute(persona, maze, {}, "world:sector:arena:<random>")

    # Should look up "world:sector:arena" (stripped of :<random>)
    assert "world:sector:arena" in maze.address_tiles


# ── 4. Default plan routing ───────────────────────────────────────────


@patch(f"{MODULE}.path_finder")
def test_default_plan_routing(mock_pf):
    """Normal address uses address_tiles[plan]."""
    persona = _make_persona()
    tiles = [(55, 55), (56, 55)]
    maze = _make_maze(address_tiles={"world:sector:arena:obj": tiles})
    mock_pf.return_value = [(50, 50), (55, 55)]

    execute(persona, maze, {}, "world:sector:arena:obj")

    # path_finder target should be one of the address_tiles
    target = mock_pf.call_args_list[-1][0][2]
    assert target in tiles


# ── 5. act_path_set=True skips path finding ───────────────────────────


@patch(f"{MODULE}.path_finder")
def test_path_set_true_skips_finding(mock_pf):
    """When act_path_set=True, path_finder is NOT called."""
    persona = _make_persona(act_path_set=True, planned_path=[(51, 50)])
    maze = _make_maze()

    execute(persona, maze, {}, "world:sector:arena:obj")

    mock_pf.assert_not_called()


# ── 6. Next tile from path ────────────────────────────────────────────


@patch(f"{MODULE}.path_finder")
def test_next_tile_from_path(mock_pf):
    """planned_path has items; first is popped and returned as next tile."""
    persona = _make_persona(
        act_path_set=True,
        planned_path=[(51, 50), (52, 50), (53, 50)],
    )
    maze = _make_maze()

    ret, _, _ = execute(persona, maze, {}, "world:sector:arena:obj")

    assert ret == (51, 50)
    assert persona.scratch.planned_path == [(52, 50), (53, 50)]


# ── 7. Empty path stays at curr_tile ─────────────────────────────────


@patch(f"{MODULE}.path_finder")
def test_empty_path_stays(mock_pf):
    """Empty planned_path returns curr_tile."""
    persona = _make_persona(act_path_set=True, planned_path=[])
    maze = _make_maze()

    ret, _, _ = execute(persona, maze, {}, "world:sector:arena:obj")

    assert ret == (50, 50)


# ── 8. Description format ─────────────────────────────────────────────


@patch(f"{MODULE}.path_finder")
def test_description_format(mock_pf):
    """Output description is '{act_description} @ {act_address}'."""
    persona = _make_persona(
        act_path_set=True,
        planned_path=[],
        act_description="painting",
        act_address="world:sector:arena:obj",
    )
    maze = _make_maze()

    _, _, desc = execute(persona, maze, {}, "world:sector:arena:obj")

    assert desc == "painting @ world:sector:arena:obj"


# ── 9. <random> resets act_path_set ───────────────────────────────────


@patch(f"{MODULE}.path_finder")
@patch(f"{MODULE}.random")
def test_random_resets_path_set(mock_random, mock_pf):
    """<random> + empty planned_path sets act_path_set=False."""
    persona = _make_persona(act_path_set=True, planned_path=[])
    maze = _make_maze(address_tiles={
        "world:sector:arena": [(70, 70)],
    })

    mock_random.sample.side_effect = lambda lst, k: list(lst)[:k]
    mock_pf.return_value = [(50, 50), (70, 70)]

    execute(persona, maze, {}, "world:sector:arena:<random>")

    # path_finder should have been called because act_path_set was reset to False
    mock_pf.assert_called()


# ── 10. <persona> short path (<=2) uses first element ─────────────────


@patch(f"{MODULE}.path_finder")
def test_persona_short_path(mock_pf):
    """Short persona path (<=2 tiles) uses path[0] as target."""
    persona = _make_persona()
    bob = MagicMock()
    bob.scratch.curr_tile = (51, 50)
    personas = {"Bob": bob}
    maze = _make_maze()

    # Short path of 2
    short_path = [(50, 50), (51, 50)]
    # First call: path to Bob; subsequent calls: path to target tile
    mock_pf.side_effect = [
        short_path,  # path to Bob
        [(50, 50)],  # path to target_tiles[0] = (50,50) = short_path[0]
    ]

    execute(persona, maze, personas, "<persona> Bob")

    # target_tiles should be [short_path[0]] = [(50,50)]
    # Second path_finder call target should be (50, 50)
    second_call = mock_pf.call_args_list[1]
    assert second_call[0][2] == (50, 50)


# ── 11. <persona> long path uses midpoint ─────────────────────────────


@patch(f"{MODULE}.path_finder")
def test_persona_long_path_midpoint(mock_pf):
    """Long persona path (>2) picks midpoint via shorter sub-path."""
    persona = _make_persona()
    bob = MagicMock()
    bob.scratch.curr_tile = (60, 50)
    personas = {"Bob": bob}
    maze = _make_maze()

    # Long path of 10 tiles
    long_path = [(50 + i, 50) for i in range(10)]
    mid = int(len(long_path) / 2)  # 5

    mock_pf.side_effect = [
        long_path,    # initial path to Bob
        [(50, 50), (55, 50)],      # potential_1: path to long_path[5]
        [(50, 50), (55, 50), (56, 50)],  # potential_2: path to long_path[6]
        [(50, 50), (55, 50)],      # final path_finder for chosen target
    ]

    execute(persona, maze, personas, "<persona> Bob")

    # potential_1 is shorter, so target should be long_path[mid] = (55, 50)
    # The second call is path_finder to midpoint
    second_call = mock_pf.call_args_list[1]
    assert second_call[0][2] == long_path[mid]


# ── 12. Overlap avoidance ─────────────────────────────────────────────


@patch(f"{MODULE}.path_finder")
def test_overlap_avoidance(mock_pf):
    """Tiles with persona events are avoided if alternatives exist."""
    persona = _make_persona()
    tiles = [(55, 55), (56, 55), (57, 55)]
    maze = _make_maze(address_tiles={"world:sector:arena:obj": tiles})

    # (55,55) has a persona event; others are clear
    def access_tile_side_effect(tile):
        if tuple(tile) == (55, 55):
            return {"events": {("Bob", "standing", "around")}}
        return {"events": set()}

    maze.access_tile.side_effect = access_tile_side_effect
    personas = {"Bob": MagicMock()}

    # Return progressively shorter paths to pick the closest non-occupied tile
    mock_pf.side_effect = [
        [(50, 50), (56, 55)],       # path to (56, 55)
        [(50, 50), (57, 55)],       # path to (57, 55) -- same length
    ]

    ret, _, _ = execute(persona, maze, personas, "world:sector:arena:obj")

    # path_finder should NOT have been called with (55, 55) as target
    # because it was filtered out as occupied by Bob
    pf_targets = [c[0][2] for c in mock_pf.call_args_list]
    assert (55, 55) not in pf_targets
