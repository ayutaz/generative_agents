"""
tests/test_perceive.py

perceive.py の perceive() 関数のユニットテスト。
空間記憶の更新、イベント知覚フィルタリング、連想記憶への格納をテストする。
"""
import math
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest

from persona.cognitive_modules.perceive import perceive


# ---- helpers ----

def _make_persona():
    """テスト用の Persona モックを生成する。"""
    persona = MagicMock()
    persona.name = "Alice"

    scratch = MagicMock()
    scratch.curr_tile = (50, 50)
    scratch.vision_r = 4
    scratch.att_bandwidth = 3
    scratch.retention = 5
    scratch.curr_time = datetime(2023, 2, 13, 14, 0)
    scratch.importance_trigger_curr = 150
    scratch.importance_ele_n = 0
    scratch.act_event = ("Alice", "chat with", "Bob")
    scratch.act_description = "chatting with Bob"
    scratch.chat = [["Alice", "Hi"]]
    persona.scratch = scratch

    # Spatial memory: real dict so tree mutations work naturally
    s_mem = MagicMock()
    s_mem.tree = {}
    persona.s_mem = s_mem

    # Associative memory
    a_mem = MagicMock()
    a_mem.embeddings = {}
    a_mem.get_summarized_latest_events = MagicMock(return_value=[])

    event_node = MagicMock()
    event_node.node_id = "event_node_0"
    a_mem.add_event = MagicMock(return_value=event_node)

    chat_node = MagicMock()
    chat_node.node_id = "chat_node_0"
    a_mem.add_chat = MagicMock(return_value=chat_node)

    persona.a_mem = a_mem

    return persona


def _make_maze(tiles, tile_path_map=None):
    """テスト用の Maze モックを生成する。

    Args:
        tiles: dict mapping (x,y) -> tile detail dict
        tile_path_map: dict mapping (x,y) -> arena path string
    """
    maze = MagicMock()

    coords = list(tiles.keys())
    maze.get_nearby_tiles = MagicMock(return_value=coords)
    maze.access_tile = MagicMock(side_effect=lambda c: tiles[c])

    if tile_path_map is None:
        tile_path_map = {}
    # get_tile_path: first arg is coord, second is level string
    def _get_tile_path(coord, level="arena"):
        return tile_path_map.get(coord, "world:sector:arena")
    maze.get_tile_path = MagicMock(side_effect=_get_tile_path)

    return maze


def _tile(world="Smallville", sector="downtown", arena="cafe",
          game_object="", events=None):
    """Tile detail dict のショートカット。"""
    return {
        "world": world,
        "sector": sector,
        "arena": arena,
        "game_object": game_object,
        "events": events or set(),
    }


# ================================================================
# Spatial memory tests
# ================================================================

class TestSpatialMemory:
    def test_spatial_memory_updated(self):
        """s_mem.tree が近くのタイル情報で更新される。"""
        persona = _make_persona()
        tiles = {
            (50, 50): _tile("Smallville", "downtown", "cafe"),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        assert "Smallville" in persona.s_mem.tree
        assert "downtown" in persona.s_mem.tree["Smallville"]
        assert "cafe" in persona.s_mem.tree["Smallville"]["downtown"]

    def test_spatial_hierarchy(self):
        """world -> sector -> arena -> objects の階層構造が構築される。"""
        persona = _make_persona()
        tiles = {
            (50, 50): _tile("Smallville", "downtown", "cafe", "espresso_machine"),
            (51, 50): _tile("Smallville", "downtown", "cafe", "table"),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        tree = persona.s_mem.tree
        assert isinstance(tree["Smallville"], dict)
        assert isinstance(tree["Smallville"]["downtown"], dict)
        assert isinstance(tree["Smallville"]["downtown"]["cafe"], list)
        assert "espresso_machine" in tree["Smallville"]["downtown"]["cafe"]
        assert "table" in tree["Smallville"]["downtown"]["cafe"]

    def test_no_duplicate_objects(self):
        """同じ game_object が重複して追加されない。"""
        persona = _make_persona()
        tiles = {
            (50, 50): _tile("Smallville", "downtown", "cafe", "table"),
            (51, 50): _tile("Smallville", "downtown", "cafe", "table"),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        objects = persona.s_mem.tree["Smallville"]["downtown"]["cafe"]
        assert objects.count("table") == 1


# ================================================================
# Event filtering tests
# ================================================================

class TestEventFiltering:
    def test_events_filtered_by_arena(self):
        """同じアリーナパス内のイベントのみが知覚される。"""
        persona = _make_persona()
        same_arena_event = ("Bob", "cooking", "food", "cooking food")
        diff_arena_event = ("Carol", "sleeping", "bed", "sleeping in bed")

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={same_arena_event}),
            (52, 50): _tile(events={diff_arena_event}),
        }

        tile_path_map = {
            (50, 50): "world:sector:cafe",
            (51, 50): "world:sector:cafe",
            (52, 50): "world:sector:bedroom",  # different arena
        }
        maze = _make_maze(tiles, tile_path_map)

        perceive(persona, maze)

        # add_event should be called for same_arena_event only
        assert persona.a_mem.add_event.call_count == 1
        # The subject arg (3rd positional, index 2) should be "Bob"
        add_event_args = persona.a_mem.add_event.call_args
        assert add_event_args[0][2] == "Bob"

    def test_att_bandwidth_limit(self):
        """att_bandwidth を超えるイベントは知覚されない。"""
        persona = _make_persona()
        persona.scratch.att_bandwidth = 2

        events = [
            ("Obj1", "is", "on", "on the table"),
            ("Obj2", "is", "on", "on the shelf"),
            ("Obj3", "is", "on", "on the floor"),
        ]
        tiles = {
            (50, 50): _tile(events=set()),
            (50, 51): _tile(events={tuple(events[0])}),
            (50, 52): _tile(events={tuple(events[1])}),
            (50, 53): _tile(events={tuple(events[2])}),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        # Only 2 events should be added (att_bandwidth=2)
        assert persona.a_mem.add_event.call_count == 2

    def test_events_sorted_by_distance(self):
        """近いイベントが先に知覚される。"""
        persona = _make_persona()
        persona.scratch.att_bandwidth = 10  # no limit effectively

        far_event = ("Far", "is", "away", "far away")
        close_event = ("Close", "is", "near", "very near")

        tiles = {
            (50, 50): _tile(events=set()),
            (55, 50): _tile(events={far_event}),   # dist = 5
            (51, 50): _tile(events={close_event}),  # dist = 1
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        # Close event should be processed first (add_event called first)
        assert persona.a_mem.add_event.call_count == 2
        first_call_subject = persona.a_mem.add_event.call_args_list[0][0][2]
        second_call_subject = persona.a_mem.add_event.call_args_list[1][0][2]
        assert first_call_subject == "Close"
        assert second_call_subject == "Far"


# ================================================================
# Retention filter test
# ================================================================

class TestRetentionFilter:
    def test_retention_filters_known(self):
        """既知のイベント（latest_events に含まれる）はスキップされる。"""
        persona = _make_persona()
        known_event = ("Bob", "cooking", "food", "cooking food")

        # Return the event triple as already known
        persona.a_mem.get_summarized_latest_events = MagicMock(
            return_value=[("Bob", "cooking", "food")]
        )

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={known_event}),
        }
        maze = _make_maze(tiles)

        result = perceive(persona, maze)

        assert persona.a_mem.add_event.call_count == 0
        assert result == []


# ================================================================
# Event storage tests
# ================================================================

class TestEventStorage:
    def test_new_event_added_to_amem(self):
        """新規イベントが a_mem.add_event で記憶に追加される。"""
        persona = _make_persona()
        event = ("Bob", "cooking", "food", "cooking food")

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={event}),
        }
        maze = _make_maze(tiles)

        result = perceive(persona, maze)

        persona.a_mem.add_event.assert_called_once()
        assert len(result) == 1

    def test_idle_event_default(self):
        """空の述語のイベントは "is idle" にデフォルトされる。"""
        persona = _make_persona()
        idle_event = ("Bob", "", "", "")

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={idle_event}),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        persona.a_mem.add_event.assert_called_once()
        args = persona.a_mem.add_event.call_args[0]
        # args: (curr_time, None, s, p, o, desc, keywords, poignancy, embedding_pair, chat_ids)
        s, p, o, desc = args[2], args[3], args[4], args[5]
        assert p == "is"
        assert o == "idle"
        assert "idle" in desc

    def test_importance_trigger_decremented(self):
        """importance_trigger_curr がイベントの poignancy 分だけ減少する。"""
        persona = _make_persona()
        initial_trigger = persona.scratch.importance_trigger_curr  # 150
        event = ("Bob", "cooking", "food", "cooking food")

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={event}),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        # run_gpt_prompt_event_poignancy stub returns (1, None) => poignancy = 1
        assert persona.scratch.importance_trigger_curr == initial_trigger - 1

    def test_importance_ele_n_incremented(self):
        """importance_ele_n がイベントごとに 1 ずつ増加する。"""
        persona = _make_persona()
        event = ("Bob", "cooking", "food", "cooking food")

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={event}),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        assert persona.scratch.importance_ele_n == 1


# ================================================================
# Chat event tests
# ================================================================

class TestChatEvent:
    def test_chat_event_creates_chat_node(self):
        """自身の "chat with" イベントで a_mem.add_chat が呼ばれる。"""
        persona = _make_persona()
        # The subject must be persona.name and predicate "chat with"
        chat_event = ("Alice", "chat with", "Bob", "chatting with Bob")

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={chat_event}),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        persona.a_mem.add_chat.assert_called_once()
        # add_event should also be called, with chat_node_ids populated
        persona.a_mem.add_event.assert_called_once()
        add_event_args = persona.a_mem.add_event.call_args[0]
        chat_node_ids = add_event_args[9]
        assert chat_node_ids == ["chat_node_0"]


# ================================================================
# Embedding tests
# ================================================================

class TestEmbedding:
    @patch("persona.cognitive_modules.perceive.get_embeddings_batch")
    def test_embedding_from_description(self, mock_batch_embed):
        """get_embeddings_batch がイベント記述テキストで呼ばれる。"""
        mock_batch_embed.return_value = [(0.1, 0.2, 0.3)]
        persona = _make_persona()
        event = ("Bob", "cooking", "food", "cooking food")

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={event}),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        mock_batch_embed.assert_called()
        # The texts list should contain "Bob is cooking food"
        call_texts = mock_batch_embed.call_args[0][0]
        assert "Bob is cooking food" in call_texts

    @patch("persona.cognitive_modules.perceive.get_embeddings_batch")
    def test_parenthetical_extraction(self, mock_batch_embed):
        """'desc (inner)' 形式の記述では括弧内がembeddingに使われる。"""
        mock_batch_embed.return_value = [(0.1, 0.2, 0.3)]
        persona = _make_persona()
        # desc with parenthetical: after prefixing "Bob is ", it becomes
        # "Bob is doing stuff (real inner meaning)"
        event = ("Bob", "cooking", "food", "doing stuff (real inner meaning)")

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={event}),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        mock_batch_embed.assert_called()
        # The texts list should contain the parenthetical extraction
        call_texts = mock_batch_embed.call_args[0][0]
        assert "real inner meaning" in call_texts

    @patch("persona.cognitive_modules.perceive.get_embeddings_batch")
    @patch("persona.cognitive_modules.perceive.get_embedding")
    def test_cached_embedding_reused(self, mock_get_embedding, mock_batch_embed):
        """a_mem.embeddings にキャッシュがあれば batch call はスキップされる。"""
        mock_get_embedding.return_value = (0.5, 0.5, 0.5)
        mock_batch_embed.return_value = []
        persona = _make_persona()
        event = ("Bob", "cooking", "food", "cooking food")

        # Pre-cache the embedding for the expected desc_embedding_in
        cached_vec = (0.9, 0.8, 0.7)
        persona.a_mem.embeddings["Bob is cooking food"] = cached_vec

        tiles = {
            (50, 50): _tile(events=set()),
            (51, 50): _tile(events={event}),
        }
        maze = _make_maze(tiles)

        perceive(persona, maze)

        # batch call should not include the cached text (empty list)
        if mock_batch_embed.called:
            call_texts = mock_batch_embed.call_args[0][0]
            assert "Bob is cooking food" not in call_texts
        # get_embedding should NOT be called since embedding was cached
        mock_get_embedding.assert_not_called()
        # Verify the cached embedding was used in add_event
        add_event_args = persona.a_mem.add_event.call_args[0]
        event_embedding_pair = add_event_args[8]
        assert event_embedding_pair == ("Bob is cooking food", cached_vec)
