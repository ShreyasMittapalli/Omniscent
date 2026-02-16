"""
Unit tests for TemporalController.
"""

import sys
import os
import pytest
from datetime import datetime

# Ensure omniscent package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from omniscent.temporal_controller import TemporalController


@pytest.fixture(autouse=True)
def fresh_controller():
    """Reset the singleton before every test."""
    TemporalController.reset()
    yield
    TemporalController.reset()


# ------------------------------------------------------------------ #
# Singleton behaviour
# ------------------------------------------------------------------ #

class TestSingleton:
    def test_same_instance(self):
        a = TemporalController()
        b = TemporalController()
        assert a is b
        assert id(a) == id(b)

    def test_reset_creates_new_instance(self):
        a = TemporalController()
        a.set_simulation_date("2024-01-01")
        old_id = id(a)

        TemporalController.reset()

        b = TemporalController()
        assert id(b) != old_id
        # New instance should have no sim time set
        with pytest.raises(RuntimeError):
            _ = b.current_time


# ------------------------------------------------------------------ #
# Setting / reading simulation date
# ------------------------------------------------------------------ #

class TestSimulationDate:
    def test_set_and_read(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-06-01")
        assert tc.current_time == datetime(2024, 6, 1)
        assert tc.current_date_str == "2024-06-01"

    def test_unset_raises(self):
        tc = TemporalController()
        with pytest.raises(RuntimeError, match="Simulation time not set"):
            _ = tc.current_time

    def test_invalid_format_raises(self):
        tc = TemporalController()
        with pytest.raises(ValueError, match="Invalid date format"):
            tc.set_simulation_date("June 1, 2024")

    def test_overwrite(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-01-01")
        tc.set_simulation_date("2024-06-01")
        assert tc.current_date_str == "2024-06-01"


# ------------------------------------------------------------------ #
# is_in_future
# ------------------------------------------------------------------ #

class TestFutureDetection:
    def test_future_returns_true(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-06-01")
        assert tc.is_in_future(datetime(2024, 7, 1)) is True

    def test_past_returns_false(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-06-01")
        assert tc.is_in_future(datetime(2024, 5, 1)) is False

    def test_same_instant_returns_false(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-06-01")
        assert tc.is_in_future(datetime(2024, 6, 1)) is False

    def test_one_second_after_is_future(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-06-01")
        assert tc.is_in_future(datetime(2024, 6, 1, 0, 0, 1)) is True


# ------------------------------------------------------------------ #
# advance_time
# ------------------------------------------------------------------ #

class TestAdvanceTime:
    def test_advance_one_day(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-06-01")
        tc.advance_time(1)
        assert tc.current_date_str == "2024-06-02"

    def test_advance_multiple_days(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-01-01")
        tc.advance_time(30)
        assert tc.current_date_str == "2024-01-31"

    def test_advance_without_set_raises(self):
        tc = TemporalController()
        with pytest.raises(RuntimeError):
            tc.advance_time(1)


# ------------------------------------------------------------------ #
# LLM context
# ------------------------------------------------------------------ #

class TestLLMContext:
    def test_contains_date(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-06-01")
        ctx = tc.get_llm_context()
        assert "June 01, 2024" in ctx
        assert "2024-06-01" in ctx
        assert "NO knowledge" in ctx

    def test_contains_year(self):
        tc = TemporalController()
        tc.set_simulation_date("2023-03-15")
        ctx = tc.get_llm_context()
        assert "2023" in ctx


# ------------------------------------------------------------------ #
# History / audit trail
# ------------------------------------------------------------------ #

class TestHistory:
    def test_history_records_all(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-01-01")
        tc.set_simulation_date("2024-06-01")
        tc.advance_time(5)
        assert tc.history == ["2024-01-01", "2024-06-01", "2024-06-06"]

    def test_history_is_copy(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-01-01")
        h = tc.history
        h.append("hacked")
        assert "hacked" not in tc.history


# ------------------------------------------------------------------ #
# Repr
# ------------------------------------------------------------------ #

class TestRepr:
    def test_repr_unset(self):
        tc = TemporalController()
        assert "UNSET" in repr(tc)

    def test_repr_set(self):
        tc = TemporalController()
        tc.set_simulation_date("2024-06-01")
        r = repr(tc)
        assert "2024-06-01" in r
        assert "offset=" in r
