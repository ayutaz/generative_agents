"""
tests/test_retrieve_pure.py

retrieve.py の純粋関数（cos_sim, normalize_dict_floats, top_highest_x_values,
extract_recency, extract_importance）のユニットテスト。
"""
import pytest
from unittest.mock import MagicMock

from persona.cognitive_modules.retrieve import (
    cos_sim,
    normalize_dict_floats,
    top_highest_x_values,
    extract_recency,
    extract_importance,
)


# ---- helpers ----

def make_node(node_id, poignancy=5):
    node = MagicMock()
    node.node_id = node_id
    node.poignancy = poignancy
    return node


# ================================================================
# cos_sim
# ================================================================

class TestCosSim:
    def test_identical_vectors(self):
        assert cos_sim([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cos_sim([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cos_sim([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_general_case_within_range(self):
        result = cos_sim([1, 2, 3], [4, 5, 6])
        assert -1.0 <= result <= 1.0


# ================================================================
# normalize_dict_floats
# ================================================================

class TestNormalizeDictFloats:
    def test_basic_normalization(self):
        d = {"a": 1, "b": 3, "c": 5}
        result = normalize_dict_floats(d, 0, 1)
        assert result["a"] == pytest.approx(0.0)
        assert result["c"] == pytest.approx(1.0)

    def test_all_same_values(self):
        d = {"a": 5, "b": 5}
        result = normalize_dict_floats(d, 0, 1)
        assert result["a"] == pytest.approx(0.5)
        assert result["b"] == pytest.approx(0.5)

    def test_order_preserved(self):
        d = {"a": 1, "b": 3, "c": 5}
        result = normalize_dict_floats(d, 0, 1)
        assert result["a"] < result["b"] < result["c"]


# ================================================================
# top_highest_x_values
# ================================================================

class TestTopHighestXValues:
    def test_basic_top_k(self):
        d = {"a": 1, "b": 3, "c": 5, "d": 2}
        result = top_highest_x_values(d, 2)
        assert "b" in result
        assert "c" in result
        assert len(result) == 2

    def test_all_items(self):
        d = {"a": 1, "b": 3, "c": 5, "d": 2}
        result = top_highest_x_values(d, len(d))
        assert set(result.keys()) == set(d.keys())

    def test_single_item(self):
        d = {"a": 1, "b": 3, "c": 5, "d": 2}
        result = top_highest_x_values(d, 1)
        assert list(result.keys()) == ["c"]


# ================================================================
# extract_recency
# ================================================================

class TestExtractRecency:
    def test_decay_progression(self):
        persona = MagicMock()
        persona.scratch.recency_decay = 0.99
        nodes = [make_node(f"n{i}") for i in range(5)]
        result = extract_recency(persona, nodes)
        values = list(result.values())
        assert values[0] > values[-1]

    def test_single_node(self):
        persona = MagicMock()
        persona.scratch.recency_decay = 0.99
        node = make_node("n0")
        result = extract_recency(persona, [node])
        assert result["n0"] == pytest.approx(0.99 ** 1)

    def test_strictly_decreasing(self):
        persona = MagicMock()
        persona.scratch.recency_decay = 0.99
        nodes = [make_node(f"n{i}") for i in range(10)]
        result = extract_recency(persona, nodes)
        values = list(result.values())
        for i in range(len(values) - 1):
            assert values[i] > values[i + 1]


# ================================================================
# extract_importance
# ================================================================

class TestExtractImportance:
    def test_poignancy_passthrough(self):
        persona = MagicMock()
        nodes = [make_node("n0", poignancy=3),
                 make_node("n1", poignancy=7),
                 make_node("n2", poignancy=10)]
        result = extract_importance(persona, nodes)
        assert result["n0"] == 3
        assert result["n1"] == 7
        assert result["n2"] == 10
