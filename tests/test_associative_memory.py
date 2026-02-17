"""tests/test_associative_memory.py -- AssociativeMemory unit tests."""
import datetime
import pathlib
import sys

import pytest

_MEM_DIR = str(pathlib.Path(__file__).resolve().parent.parent
               / "reverie" / "backend_server" / "persona" / "memory_structures")
if _MEM_DIR not in sys.path:
    sys.path.insert(0, _MEM_DIR)

from associative_memory import AssociativeMemory, ConceptNode

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
AM_DIR = str(FIXTURES / "associative_memory")


@pytest.fixture
def am():
    """Fresh AssociativeMemory loaded from the (empty) fixture directory."""
    return AssociativeMemory(AM_DIR)


def _make_event(am, idx=1, description="Isabella is painting (working on canvas)",
                subject="Isabella", predicate="is", obj="painting",
                keywords=None, poignancy=5):
    """Helper to add a single event and return the node."""
    if keywords is None:
        keywords = {"isabella", "painting"}
    return am.add_event(
        datetime.datetime(2023, 2, 13, 8, 0),
        None,
        subject, predicate, obj,
        description,
        keywords,
        poignancy,
        (f"emb_{idx}", [0.1] * 10),
        [],
    )


# ── construction ──────────────────────────────────────────────────────

class TestConstruction:
    def test_empty_instance(self, am):
        assert len(am.id_to_node) == 0
        assert am.seq_event == []
        assert am.seq_thought == []
        assert am.seq_chat == []


# ── add_event ─────────────────────────────────────────────────────────

class TestAddEvent:
    def test_seq_event_increases(self, am):
        _make_event(am)
        assert len(am.seq_event) == 1

    def test_node_id_format(self, am):
        node = _make_event(am)
        assert node.node_id == "node_1"

    def test_registered_in_id_to_node(self, am):
        node = _make_event(am)
        assert "node_1" in am.id_to_node
        assert am.id_to_node["node_1"] is node

    def test_description_bracket_removal(self, am):
        node = _make_event(am)
        # "Isabella is painting (working on canvas)"
        # After bracket removal: first 3 words + content inside parens minus closing
        assert "(" not in node.description


# ── add_thought ───────────────────────────────────────────────────────

class TestAddThought:
    def test_seq_thought_increases(self, am):
        am.add_thought(
            datetime.datetime(2023, 2, 13, 9, 0),
            None,
            "Isabella", "thinks", "art is important",
            "Isabella thinks art is important",
            {"isabella", "art"},
            6,
            ("emb_t1", [0.2] * 10),
            [],
        )
        assert len(am.seq_thought) == 1

    def test_depth_with_filling(self, am):
        # Add an event first (depth=0)
        _make_event(am)
        # Add a thought that references the event node
        node = am.add_thought(
            datetime.datetime(2023, 2, 13, 9, 0),
            None,
            "Isabella", "reflects", "on painting",
            "Isabella reflects on painting",
            {"isabella"},
            6,
            ("emb_t2", [0.3] * 10),
            ["node_1"],
        )
        # depth = 1 + max depth of filling nodes (0) = 1
        assert node.depth == 1


# ── add_chat ──────────────────────────────────────────────────────────

class TestAddChat:
    def test_seq_chat_increases(self, am):
        am.add_chat(
            datetime.datetime(2023, 2, 13, 10, 0),
            None,
            "Isabella", "chats with", "Maria",
            "Isabella chats with Maria about art",
            {"isabella", "maria"},
            3,
            ("emb_c1", [0.4] * 10),
            [["Isabella", "Hello"], ["Maria", "Hi"]],
        )
        assert len(am.seq_chat) == 1


# ── sequential node IDs ──────────────────────────────────────────────

class TestSequentialNodeIds:
    def test_three_events_sequential_ids(self, am):
        n1 = _make_event(am, idx=1)
        n2 = _make_event(am, idx=2)
        n3 = _make_event(am, idx=3)
        assert n1.node_id == "node_1"
        assert n2.node_id == "node_2"
        assert n3.node_id == "node_3"


# ── ConceptNode.spo_summary ──────────────────────────────────────────

class TestConceptNode:
    def test_spo_summary(self, am):
        node = _make_event(am)
        spo = node.spo_summary()
        assert isinstance(spo, tuple)
        assert spo == (node.subject, node.predicate, node.object)


# ── get_summarized_latest_events ──────────────────────────────────────

class TestSummarizedLatestEvents:
    def test_retention_limit(self, am):
        _make_event(am, idx=1, subject="A", predicate="does", obj="x",
                    keywords={"a"}, description="A does x")
        _make_event(am, idx=2, subject="B", predicate="does", obj="y",
                    keywords={"b"}, description="B does y")
        _make_event(am, idx=3, subject="C", predicate="does", obj="z",
                    keywords={"c"}, description="C does z")
        result = am.get_summarized_latest_events(retention=2)
        assert len(result) == 2


# ── retrieve_relevant_events ──────────────────────────────────────────

class TestRetrieveRelevantEvents:
    def test_known_keyword(self, am):
        _make_event(am, keywords={"isabella", "painting"})
        # kw_to_event keys are lowered
        result = am.retrieve_relevant_events("isabella", "", "")
        assert len(result) >= 1

    def test_unknown_keyword(self, am):
        _make_event(am, keywords={"isabella", "painting"})
        result = am.retrieve_relevant_events("unknown_xyz", "", "")
        assert len(result) == 0


# ── retrieve_relevant_thoughts ────────────────────────────────────────

class TestRetrieveRelevantThoughts:
    def test_keyword_search(self, am):
        am.add_thought(
            datetime.datetime(2023, 2, 13, 9, 0),
            None,
            "Isabella", "thinks", "about art",
            "Isabella thinks about art",
            {"isabella", "art"},
            5,
            ("emb_th1", [0.5] * 10),
            [],
        )
        # Keywords are lowered internally, so pass lowercase
        result = am.retrieve_relevant_thoughts("isabella", "", "")
        assert len(result) >= 1


# ── get_last_chat ─────────────────────────────────────────────────────

class TestGetLastChat:
    def test_found(self, am):
        am.add_chat(
            datetime.datetime(2023, 2, 13, 10, 0),
            None,
            "Isabella", "chats with", "Maria",
            "chatting about art",
            {"isabella", "maria"},
            3,
            ("emb_chat1", [0.6] * 10),
            [["Isabella", "Hello"]],
        )
        result = am.get_last_chat("Maria")
        assert result is not False
        assert result.type == "chat"

    def test_not_found(self, am):
        result = am.get_last_chat("Nobody")
        assert result is False


# ── kw_strength_event ─────────────────────────────────────────────────

class TestKwStrengthEvent:
    def test_non_idle_increments(self, am):
        _make_event(am, predicate="is", obj="painting",
                    keywords={"painting"})
        assert am.kw_strength_event.get("painting", 0) >= 1

    def test_idle_does_not_increment(self, am):
        am.add_event(
            datetime.datetime(2023, 2, 13, 8, 0),
            None,
            "Isabella", "is", "idle",
            "Isabella is idle",
            {"isabella"},
            1,
            ("emb_idle", [0.0] * 10),
            [],
        )
        # "is idle" should NOT increment kw_strength_event
        assert am.kw_strength_event.get("isabella", 0) == 0
