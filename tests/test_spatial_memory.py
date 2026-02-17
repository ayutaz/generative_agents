"""tests/test_spatial_memory.py -- MemoryTree (spatial memory) unit tests."""
import json
import pathlib
import sys

import pytest

_MEM_DIR = str(pathlib.Path(__file__).resolve().parent.parent
               / "reverie" / "backend_server" / "persona" / "memory_structures")
if _MEM_DIR not in sys.path:
    sys.path.insert(0, _MEM_DIR)

from spatial_memory import MemoryTree

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
SPATIAL_JSON = str(FIXTURES / "spatial_memory_minimal.json")


@pytest.fixture
def mem():
    """MemoryTree loaded from the minimal fixture."""
    return MemoryTree(SPATIAL_JSON)


# ── construction ──────────────────────────────────────────────────────

class TestConstruction:
    def test_empty_tree_on_bad_path(self):
        mt = MemoryTree("__nonexistent__/spatial.json")
        assert mt.tree == {}

    def test_loaded_tree_not_empty(self, mem):
        assert mem.tree != {}


# ── accessible sectors ────────────────────────────────────────────────

class TestAccessibleSectors:
    def test_sectors_contain_isabella_house(self, mem):
        result = mem.get_str_accessible_sectors("the_ville")
        assert "isabella_house" in result

    def test_sectors_contain_town_square(self, mem):
        result = mem.get_str_accessible_sectors("the_ville")
        assert "town_square" in result

    def test_sectors_comma_separated(self, mem):
        result = mem.get_str_accessible_sectors("the_ville")
        assert "," in result


# ── accessible arenas ─────────────────────────────────────────────────

class TestAccessibleArenas:
    def test_arenas_contain_main_room(self, mem):
        result = mem.get_str_accessible_sector_arenas("the_ville:isabella_house")
        assert "main_room" in result

    def test_arenas_contain_kitchen(self, mem):
        result = mem.get_str_accessible_sector_arenas("the_ville:isabella_house")
        assert "kitchen" in result


# ── accessible game objects ───────────────────────────────────────────

class TestAccessibleGameObjects:
    def test_objects_contain_easel(self, mem):
        result = mem.get_str_accessible_arena_game_objects(
            "the_ville:isabella_house:main_room"
        )
        assert "easel" in result

    def test_case_fallback(self, mem):
        # Passing arena name with different case triggers try/except fallback
        result = mem.get_str_accessible_arena_game_objects(
            "the_ville:isabella_house:Main_Room"
        )
        assert "easel" in result


# ── save / reload round-trip ──────────────────────────────────────────

class TestSaveReload:
    def test_round_trip(self, mem, tmp_path):
        out_file = str(tmp_path / "spatial_out.json")
        mem.save(out_file)
        reloaded = MemoryTree(out_file)
        assert reloaded.tree == mem.tree
