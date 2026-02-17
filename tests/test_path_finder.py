"""Tests for reverie/backend_server/path_finder.py"""
import copy
import pytest

from path_finder import (
    path_finder_v1,
    path_finder_v2,
    path_finder,
    closest_coordinate,
    path_finder_2,
    path_finder_3,
)

# ---------------------------------------------------------------------------
# Test maze (module-level helper)
# ---------------------------------------------------------------------------
MAZE = [
    ['#','#','#','#','#','#','#','#','#','#','#','#','#'],
    [' ',' ','#',' ',' ',' ',' ',' ','#',' ',' ',' ','#'],
    ['#',' ','#',' ',' ','#','#',' ',' ',' ','#',' ','#'],
    ['#',' ','#',' ',' ','#','#',' ','#',' ','#',' ','#'],
    ['#',' ',' ',' ',' ',' ',' ',' ','#',' ',' ',' ','#'],
    ['#','#','#',' ','#',' ','#','#','#',' ','#',' ','#'],
    ['#',' ',' ',' ',' ',' ',' ',' ',' ',' ','#',' ',' '],
    ['#','#','#','#','#','#','#','#','#','#','#','#','#'],
]

COLLISION = '#'


def _maze():
    """Return a fresh deep-copy of MAZE."""
    return copy.deepcopy(MAZE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_on_open_tiles(path, maze):
    """Assert that no step in path lands on a collision block."""
    for r, c in path:
        assert maze[r][c] != COLLISION, f"Path crosses collision block at ({r},{c})"


def _is_connected(path):
    """Assert each consecutive pair is Manhattan distance 1."""
    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        assert abs(r1 - r2) + abs(c1 - c2) == 1, (
            f"Discontinuity at step {i}: {path[i]} -> {path[i+1]}"
        )


# ===================================================================
# path_finder_v2 tests (BFS, row/col coordinates)
# ===================================================================

class TestPathFinderV2:
    def test_same_point(self):
        """Same start and end should return path of length 1."""
        maze = _maze()
        path = path_finder_v2(maze, (1, 0), (1, 0), COLLISION)
        assert len(path) == 1
        assert path[0] == (1, 0)

    def test_adjacent_point(self):
        """Adjacent start and end should return path of length 2."""
        maze = _maze()
        path = path_finder_v2(maze, (1, 0), (1, 1), COLLISION)
        assert len(path) == 2
        assert path[0] == (1, 0)
        assert path[-1] == (1, 1)

    def test_known_route_found(self):
        """A known route from (1,0) to (6,12) should be found."""
        maze = _maze()
        path = path_finder_v2(maze, (1, 0), (6, 12), COLLISION)
        assert len(path) > 1
        assert path[0] == (1, 0)
        assert path[-1] == (6, 12)

    def test_path_connectivity(self):
        """Each step in the path should be Manhattan distance 1."""
        maze = _maze()
        path = path_finder_v2(maze, (1, 0), (6, 12), COLLISION)
        _is_connected(path)

    def test_no_collision_blocks(self):
        """The path must not cross any collision block."""
        maze = _maze()
        original = _maze()
        path = path_finder_v2(maze, (1, 0), (6, 12), COLLISION)
        _all_on_open_tiles(path, original)


# ===================================================================
# path_finder_v1 tests (DFS, destructive)
# ===================================================================

class TestPathFinderV1:
    def test_path_found(self):
        """v1 should find a path between two reachable open tiles."""
        maze = _maze()
        path = path_finder_v1(maze, (1, 0), (6, 12), COLLISION)
        assert path is not False
        assert len(path) > 0
        assert path[0] == (1, 0)
        assert path[-1] == (6, 12)

    def test_unreachable_returns_false(self):
        """v1 should return False for unreachable targets."""
        # End cell is completely isolated by walls
        sealed = [
            ['#', '#', '#', '#', '#'],
            [' ', ' ', '#', ' ', '#'],
            ['#', '#', '#', '#', '#'],
        ]
        result = path_finder_v1(sealed, (1, 0), (1, 3), COLLISION)
        assert result is False


# ===================================================================
# path_finder tests (coordinate transformation wrapper)
# ===================================================================

class TestPathFinder:
    def test_coordinate_transform_same_point(self):
        """path_finder with x,y input should return x,y output."""
        maze = _maze()
        # (x=0, y=1) -> internally (row=1, col=0) which is open
        path = path_finder(maze, (0, 1), (0, 1), COLLISION)
        assert len(path) == 1
        assert path[0] == (0, 1)

    def test_coordinate_transform_route(self):
        """path_finder should convert (x,y) to (row,col), find path, convert back."""
        maze = _maze()
        # (x=0, y=1) -> internal (1,0); (x=12, y=6) -> internal (6,12)
        path = path_finder(maze, (0, 1), (12, 6), COLLISION)
        assert len(path) > 1
        assert path[0] == (0, 1)
        assert path[-1] == (12, 6)

    def test_no_collision_blocks_xy(self):
        """Converted path should not cross collision blocks."""
        maze = _maze()
        original = _maze()
        path = path_finder(maze, (0, 1), (12, 6), COLLISION)
        # Convert x,y back to row,col for checking against maze
        for x, y in path:
            assert original[y][x] != COLLISION, f"Collision at x={x},y={y}"


# ===================================================================
# closest_coordinate tests
# ===================================================================

class TestClosestCoordinate:
    def test_single_target(self):
        """Single target should be returned as-is."""
        result = closest_coordinate((0, 0), [(3, 4)])
        assert result == (3, 4)

    def test_multiple_targets(self):
        """Should return the nearest target by Euclidean distance."""
        result = closest_coordinate((0, 0), [(10, 10), (1, 1), (5, 5)])
        assert result == (1, 1)


# ===================================================================
# path_finder_2 tests (path to adjacent tile of target)
# ===================================================================

class TestPathFinder2:
    def test_path_to_adjacent_tile(self):
        """path_finder_2 should find a path to a tile adjacent to end."""
        maze = _maze()
        # start=(0,1) end=(12,6) in x,y
        path = path_finder_2(maze, (0, 1), (12, 6), COLLISION)
        assert len(path) >= 1
        # The last tile should be adjacent to the target (Manhattan distance 1)
        last = path[-1]
        assert abs(last[0] - 12) + abs(last[1] - 6) == 1


# ===================================================================
# path_finder_3 tests (path splitting)
# ===================================================================

class TestPathFinder3:
    def test_split_long_path(self):
        """For a path > 2, path_finder_3 should return (a_path, b_path) tuple."""
        maze = _maze()
        result = path_finder_3(maze, (0, 1), (12, 6), COLLISION)
        assert isinstance(result, tuple)
        assert len(result) == 2
        a_path, b_path = result
        assert len(a_path) > 0
        assert len(b_path) > 0

    def test_short_path_returns_empty(self):
        """For path length <= 2, path_finder_3 should return empty list."""
        maze = _maze()
        # Same point -> path length 1
        result = path_finder_3(maze, (0, 1), (0, 1), COLLISION)
        assert result == []
