"""Tests for agent_chat_v2() in persona/cognitive_modules/converse.py."""

import types

import pytest

import persona.cognitive_modules.converse as converse_mod
from persona.cognitive_modules.converse import agent_chat_v2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_persona(name, act_description="working"):
    p = types.SimpleNamespace()
    p.name = name
    scratch = types.SimpleNamespace()
    scratch.name = name
    scratch.act_description = act_description
    p.scratch = scratch
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAgentChatV2:

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch):
        self.maze = types.SimpleNamespace()
        self.init_persona = _make_persona("Alice", "painting")
        self.target_persona = _make_persona("Bob", "reading")

        # Track calls
        self.retrieve_calls = []
        self.relationship_calls = []
        self.utterance_calls = []

        # Defaults
        self._relationship = "they are friends"
        self._utterances = []  # list of (utt, end) to return in order
        self._utterance_index = 0

        def fake_retrieve(persona, focal_points, n_count):
            self.retrieve_calls.append({
                "persona": persona,
                "focal_points": focal_points,
                "n_count": n_count,
            })
            return {}

        def fake_relationship(init_p, target_p, retrieved):
            self.relationship_calls.append({
                "init_persona": init_p,
                "target_persona": target_p,
            })
            return self._relationship

        def fake_one_utterance(maze, init_p, target_p, retrieved, curr_chat):
            idx = self._utterance_index
            self._utterance_index += 1
            self.utterance_calls.append({
                "init_persona": init_p,
                "target_persona": target_p,
                "curr_chat": list(curr_chat),
            })
            if idx < len(self._utterances):
                return self._utterances[idx]
            return ("Hello", True)

        monkeypatch.setattr(converse_mod, "new_retrieve", fake_retrieve)
        monkeypatch.setattr(
            converse_mod, "generate_summarize_agent_relationship",
            fake_relationship,
        )
        monkeypatch.setattr(
            converse_mod, "generate_one_utterance",
            fake_one_utterance,
        )

    # 1
    def test_end_true_stops(self):
        """end=True on init's first utterance -> only 1 entry."""
        self._utterances = [("Hi there", True)]
        result = agent_chat_v2(self.maze, self.init_persona, self.target_persona)
        assert len(result) == 1
        assert result[0] == ["Alice", "Hi there"]

    # 2
    def test_alternating_speakers(self):
        """Init and target should alternate speaking."""
        self._utterances = [
            ("Hello", False),
            ("Hi back", False),
            ("How are you?", False),
            ("Good, thanks", True),
        ]
        result = agent_chat_v2(self.maze, self.init_persona, self.target_persona)
        assert result[0][0] == "Alice"
        assert result[1][0] == "Bob"
        assert result[2][0] == "Alice"
        assert result[3][0] == "Bob"

    # 3
    def test_max_8_rounds(self):
        """At most 8 rounds (16 entries) if end is never True."""
        self._utterances = [("line", False)] * 20
        result = agent_chat_v2(self.maze, self.init_persona, self.target_persona)
        assert len(result) <= 16

    # 4
    def test_focal_points_include_relationship(self):
        """The relationship string should appear in focal_points for the second retrieve."""
        self._relationship = "Alice and Bob are close friends"
        self._utterances = [("Hi", True)]
        agent_chat_v2(self.maze, self.init_persona, self.target_persona)
        # The second retrieve call (n_count=15) has focal_points with relationship
        second_retrieve = self.retrieve_calls[1]
        assert "Alice and Bob are close friends" in second_retrieve["focal_points"]

    # 5
    def test_last_chat_context(self):
        """After 4+ entries, focal_points should include last_chat with last 4 entries."""
        self._utterances = [
            ("msg1", False),
            ("msg2", False),
            ("msg3", False),
            ("msg4", False),
            ("msg5", True),
        ]
        agent_chat_v2(self.maze, self.init_persona, self.target_persona)
        # Find a retrieve call with n_count=15 that has 3 focal_points (relationship, desc, last_chat).
        found = False
        for rc in self.retrieve_calls:
            if rc["n_count"] == 15 and len(rc["focal_points"]) == 3:
                last_chat_fp = rc["focal_points"][2]
                if "msg" in last_chat_fp:
                    found = True
                    break
        assert found, "Expected a retrieve call with last_chat in focal_points"

    # 6
    def test_return_format(self):
        """Returns list of [name, utterance] pairs."""
        self._utterances = [("Hey", False), ("Yo", True)]
        result = agent_chat_v2(self.maze, self.init_persona, self.target_persona)
        for entry in result:
            assert isinstance(entry, list)
            assert len(entry) == 2
            assert isinstance(entry[0], str)
            assert isinstance(entry[1], str)

    # 7
    def test_empty_on_immediate_end(self):
        """Immediate end on first utterance returns a 1-element list."""
        self._utterances = [("Bye", True)]
        result = agent_chat_v2(self.maze, self.init_persona, self.target_persona)
        assert len(result) == 1
        assert result[0] == ["Alice", "Bye"]
