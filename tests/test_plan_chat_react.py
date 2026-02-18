"""Tests for _chat_react() in persona/cognitive_modules/plan.py."""

import datetime
import types

import pytest

import persona.cognitive_modules.plan as plan_mod
from persona.cognitive_modules.plan import _chat_react


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_persona(name, curr_time=None, act_start_time=None):
    """Minimal persona mock for _chat_react tests."""
    p = types.SimpleNamespace()
    p.name = name
    scratch = types.SimpleNamespace()
    scratch.name = name
    scratch.curr_time = curr_time or datetime.datetime(2023, 2, 13, 10, 0, 0)
    scratch.act_start_time = act_start_time or datetime.datetime(2023, 2, 13, 9, 30, 0)
    p.scratch = scratch
    return p


def _make_personas_dict(init_persona, target_persona, reaction_mode):
    """Build the personas lookup dict expected by _chat_react."""
    key = reaction_mode[9:].strip()
    return {key: target_persona}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestChatReact:
    """Tests for _chat_react."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch):
        """Shared setup: patch generate_convo, generate_convo_summary, _create_react."""
        self.convo = [["Alice", "Hi"], ["Bob", "Hello"]]
        self.duration = 10
        self.summary = "Alice and Bob greeted each other."

        monkeypatch.setattr(
            plan_mod, "generate_convo",
            lambda maze, init_p, target_p: (self.convo, self.duration),
        )
        monkeypatch.setattr(
            plan_mod, "generate_convo_summary",
            lambda persona, convo: self.summary,
        )

        # Capture all _create_react calls
        self.create_react_calls = []

        def _fake_create_react(persona, inserted_act, inserted_act_dur,
                               act_address, act_event, chatting_with,
                               chat, chatting_with_buffer, chatting_end_time,
                               act_pronunciatio, act_obj_description,
                               act_obj_pronunciatio, act_obj_event,
                               act_start_time):
            self.create_react_calls.append({
                "persona": persona,
                "inserted_act": inserted_act,
                "inserted_act_dur": inserted_act_dur,
                "act_address": act_address,
                "act_event": act_event,
                "chatting_with": chatting_with,
                "chat": chat,
                "chatting_with_buffer": chatting_with_buffer,
                "chatting_end_time": chatting_end_time,
                "act_pronunciatio": act_pronunciatio,
                "act_obj_description": act_obj_description,
                "act_obj_pronunciatio": act_obj_pronunciatio,
                "act_obj_event": act_obj_event,
                "act_start_time": act_start_time,
            })

        monkeypatch.setattr(plan_mod, "_create_react", _fake_create_react)

        self.maze = types.SimpleNamespace()
        self.init_persona = _make_persona("Alice")
        self.target_persona = _make_persona("Bob")
        self.reaction_mode = "chat with Bob"
        self.personas = _make_personas_dict(
            self.init_persona, self.target_persona, self.reaction_mode
        )

    def _run(self, **overrides):
        maze = overrides.get("maze", self.maze)
        persona = overrides.get("persona", self.init_persona)
        focused_event = overrides.get("focused_event", None)
        reaction_mode = overrides.get("reaction_mode", self.reaction_mode)
        personas = overrides.get("personas", self.personas)
        _chat_react(maze, persona, focused_event, reaction_mode, personas)

    # 1
    def test_both_personas_get_create_react(self):
        self._run()
        assert len(self.create_react_calls) == 2

    # 2
    def test_init_act_address_format(self):
        self._run()
        init_call = self.create_react_calls[0]
        assert init_call["act_address"] == "<persona> Bob"

    # 3
    def test_target_act_address_format(self):
        self._run()
        target_call = self.create_react_calls[1]
        assert target_call["act_address"] == "<persona> Alice"

    # 4
    def test_buffer_800(self):
        self._run()
        for call in self.create_react_calls:
            for val in call["chatting_with_buffer"].values():
                assert val == 800

    # 5
    def test_chatting_end_time_calc(self):
        """End time = target curr_time + duration (seconds == 0 path)."""
        self._run()
        expected = datetime.datetime(2023, 2, 13, 10, 0, 0) + datetime.timedelta(minutes=10)
        for call in self.create_react_calls:
            assert call["chatting_end_time"] == expected

    # 6
    def test_convo_passed_to_both(self):
        self._run()
        for call in self.create_react_calls:
            assert call["chat"] is self.convo

    # 7
    def test_act_event_format(self):
        self._run()
        init_call = self.create_react_calls[0]
        assert init_call["act_event"] == ("Alice", "chat with", "Bob")
        target_call = self.create_react_calls[1]
        assert target_call["act_event"] == ("Bob", "chat with", "Alice")

    # 8
    def test_pronunciatio_chat_emoji(self):
        self._run()
        for call in self.create_react_calls:
            assert call["act_pronunciatio"] == "\U0001f4ac"

    # 9
    def test_act_start_from_target(self):
        """act_start_time should come from target_persona.scratch.act_start_time."""
        target_start = datetime.datetime(2023, 2, 13, 9, 45, 0)
        self.target_persona.scratch.act_start_time = target_start
        self._run()
        for call in self.create_react_calls:
            assert call["act_start_time"] == target_start

    # 10
    def test_convo_summary_generated(self):
        """generate_convo_summary should be called; its result is used as inserted_act."""
        self._run()
        for call in self.create_react_calls:
            assert call["inserted_act"] == self.summary


class TestChatReactEndTimeNonZeroSeconds:
    """Verify chatting_end_time when curr_time.second != 0."""

    def test_chatting_end_time_nonzero_seconds(self, monkeypatch):
        convo = [["A", "hi"]]
        duration = 5
        monkeypatch.setattr(plan_mod, "generate_convo", lambda *a: (convo, duration))
        monkeypatch.setattr(plan_mod, "generate_convo_summary", lambda *a: "summary")
        calls = []

        def _capture(*args, **kwargs):
            calls.append(args)

        monkeypatch.setattr(plan_mod, "_create_react", _capture)

        init_p = _make_persona("A")
        # target has curr_time with non-zero seconds
        target_p = _make_persona("B", curr_time=datetime.datetime(2023, 2, 13, 10, 0, 30))
        personas = {"B": target_p}
        maze = types.SimpleNamespace()

        _chat_react(maze, init_p, None, "chat with B", personas)

        # temp_curr_time = 10:01:00, end = 10:06:00
        expected_end = datetime.datetime(2023, 2, 13, 10, 1, 0) + datetime.timedelta(minutes=5)
        # chatting_end_time is the 9th positional arg (index 8)
        for c in calls:
            assert c[8] == expected_end
