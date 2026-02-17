"""tests/test_scratch.py -- Scratch (short-term memory) unit tests."""
import datetime
import pathlib
import sys

import pytest

# scratch.py lives under persona/memory_structures/ which has no __init__.py,
# so we add that directory to sys.path for a flat import.
_MEM_DIR = str(pathlib.Path(__file__).resolve().parent.parent
               / "reverie" / "backend_server" / "persona" / "memory_structures")
if _MEM_DIR not in sys.path:
    sys.path.insert(0, _MEM_DIR)

from scratch import Scratch

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
SCRATCH_JSON = str(FIXTURES / "scratch_minimal.json")


# ── construction helpers ──────────────────────────────────────────────

@pytest.fixture
def scratch():
    """Scratch loaded from the minimal fixture."""
    return Scratch(SCRATCH_JSON)


def _empty_scratch():
    """Scratch built with a non-existent path (defaults only)."""
    return Scratch("__nonexistent_path__/scratch.json")


# ── default values (non-existent path) ────────────────────────────────

class TestScratchDefaults:
    def test_vision_r_default(self):
        s = _empty_scratch()
        assert s.vision_r == 4

    def test_att_bandwidth_default(self):
        s = _empty_scratch()
        assert s.att_bandwidth == 3

    def test_retention_default(self):
        s = _empty_scratch()
        assert s.retention == 5

    def test_name_is_none(self):
        s = _empty_scratch()
        assert s.name is None


# ── loading from fixture ──────────────────────────────────────────────

class TestScratchLoad:
    def test_name(self, scratch):
        assert scratch.name == "Isabella Rodriguez"

    def test_age(self, scratch):
        assert scratch.age == 34

    def test_curr_time_parsed(self, scratch):
        assert isinstance(scratch.curr_time, datetime.datetime)
        assert scratch.curr_time == datetime.datetime(2023, 2, 13, 8, 0, 0)


# ── getter methods ────────────────────────────────────────────────────

class TestScratchGetters:
    def test_get_str_name(self, scratch):
        assert scratch.get_str_name() == "Isabella Rodriguez"

    def test_get_str_firstname(self, scratch):
        assert scratch.get_str_firstname() == "Isabella"

    def test_get_str_lastname(self, scratch):
        assert scratch.get_str_lastname() == "Rodriguez"

    def test_get_str_age(self, scratch):
        result = scratch.get_str_age()
        assert result == "34"
        assert isinstance(result, str)

    def test_get_str_innate(self, scratch):
        assert scratch.get_str_innate() == "friendly, creative, curious"

    def test_get_str_curr_date_str(self, scratch):
        result = scratch.get_str_curr_date_str()
        # curr_time is February 13, 2023 => "Monday February 13"
        assert result == scratch.curr_time.strftime("%A %B %d")

    def test_get_str_iss_contains_name(self, scratch):
        result = scratch.get_str_iss()
        assert "Name:" in result
        assert "Isabella Rodriguez" in result
        assert "\n" in result  # multi-line string


# ── daily schedule index ──────────────────────────────────────────────

class TestDailyScheduleIndex:
    def test_index_at_midnight(self, scratch):
        scratch.curr_time = scratch.curr_time.replace(hour=0, minute=0)
        idx = scratch.get_f_daily_schedule_index()
        assert idx == 0

    def test_index_with_advance_past_first_task(self, scratch):
        # f_daily_schedule: [["sleeping",360],["waking up",30],["painting",120]]
        # total = 510 min.  With hour=0, min=0, advance=361 => elapsed=361 > 360
        scratch.curr_time = scratch.curr_time.replace(hour=0, minute=0)
        idx = scratch.get_f_daily_schedule_index(advance=361)
        assert idx >= 1


# ── action helpers ────────────────────────────────────────────────────

class TestActionHelpers:
    def test_act_check_finished_no_address(self, scratch):
        scratch.act_address = None
        assert scratch.act_check_finished() is True

    def test_add_new_action(self, scratch):
        scratch.add_new_action(
            action_address="the_ville:town_square:plaza:fountain",
            action_duration=30,
            action_description="sitting by the fountain",
            action_pronunciatio="~",
            action_event=("Isabella Rodriguez", "is", "sitting"),
            chatting_with=None,
            chat=None,
            chatting_with_buffer=None,
            chatting_end_time=None,
            act_obj_description="being sat near",
            act_obj_pronunciatio="~",
            act_obj_event=("fountain", "is", "idle"),
        )
        assert scratch.act_address == "the_ville:town_square:plaza:fountain"
        assert scratch.act_description == "sitting by the fountain"
        assert scratch.act_duration == 30
        assert scratch.act_path_set is False


# ── daily schedule summary ────────────────────────────────────────────

class TestDailyScheduleSummary:
    def test_summary_contains_separator(self, scratch):
        result = scratch.get_str_daily_schedule_summary()
        assert "||" in result
