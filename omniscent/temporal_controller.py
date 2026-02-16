"""
Temporal Controller — Thread-safe singleton that governs simulation time.

All system components reference this controller to determine "now" in the
simulation.  Any attempt to access data or make predictions must respect
the simulation clock, preventing future data leakage.

Usage:
    from omniscent.temporal_controller import TemporalController

    tc = TemporalController()          # always returns the same instance
    tc.set_simulation_date("2024-06-01")
    print(tc.current_time)             # datetime(2024, 6, 1)
    print(tc.is_in_future(datetime(2024, 7, 1)))  # True
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Optional


class TemporalController:
    """
    Global simulation-time controller (thread-safe singleton).

    Guarantees:
      1. Only one instance exists per process.
      2. All readers see a consistent simulation date.
      3. Future timestamps are rejected by ``is_in_future``.
    """

    _instance: Optional["TemporalController"] = None
    _lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Singleton mechanics
    # ------------------------------------------------------------------ #

    def __new__(cls) -> "TemporalController":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._initialised = False
                    cls._instance = inst
        return cls._instance

    def __init__(self) -> None:
        if self._initialised:
            return
        self._current_sim_time: Optional[datetime] = None
        self._real_time: datetime = datetime.now()
        self._history: list[str] = []          # audit trail
        self._initialised = True

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton so the next call creates a fresh one.

        Intended for **test isolation only** — production code should never
        call this.
        """
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------ #
    # Core API
    # ------------------------------------------------------------------ #

    def set_simulation_date(self, sim_date: str) -> None:
        """Set the current simulation date.

        Parameters
        ----------
        sim_date : str
            Date string in ``YYYY-MM-DD`` format.

        Raises
        ------
        ValueError
            If *sim_date* is not a valid date or is in the real future.
        """
        try:
            parsed = datetime.strptime(sim_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid date format '{sim_date}'. Expected YYYY-MM-DD."
            )

        # The simulation may only travel to the **past** (or today at most)
        if parsed > self._real_time:
            raise ValueError(
                f"Cannot set simulation date to {sim_date} — "
                f"it is after real time ({self._real_time.date()})."
            )

        self._current_sim_time = parsed
        self._history.append(sim_date)

    @property
    def current_time(self) -> datetime:
        """Return the current simulation datetime.

        Raises
        ------
        RuntimeError
            If ``set_simulation_date`` has not been called yet.
        """
        if self._current_sim_time is None:
            raise RuntimeError(
                "Simulation time not set! Call set_simulation_date() first."
            )
        return self._current_sim_time

    @property
    def current_date_str(self) -> str:
        """Convenience: current simulation date as ``YYYY-MM-DD``."""
        return self.current_time.strftime("%Y-%m-%d")

    def is_in_future(self, timestamp: datetime) -> bool:
        """Return ``True`` if *timestamp* is strictly after the sim clock."""
        return timestamp > self.current_time

    # ------------------------------------------------------------------ #
    # Time stepping
    # ------------------------------------------------------------------ #

    def advance_time(self, days: int = 1) -> None:
        """Move the simulation clock forward by *days*.

        Parameters
        ----------
        days : int
            Number of calendar days to advance (default 1).

        Raises
        ------
        RuntimeError
            If simulation time is not set.
        ValueError
            If advancing would exceed real time.
        """
        new_time = self.current_time + timedelta(days=days)
        if new_time > self._real_time:
            raise ValueError(
                f"Cannot advance to {new_time.date()} — exceeds real time."
            )
        self._current_sim_time = new_time
        self._history.append(new_time.strftime("%Y-%m-%d"))

    # ------------------------------------------------------------------ #
    # LLM integration
    # ------------------------------------------------------------------ #

    def get_llm_context(self) -> str:
        """Build a temporal-context block to inject into LLM system prompts."""
        sim = self.current_time
        return (
            f"IMPORTANT TEMPORAL CONTEXT:\n"
            f"- Current date: {sim.strftime('%B %d, %Y')}\n"
            f"- You are operating in {sim.year}\n"
            f"- You have NO knowledge of events after {sim.date()}\n"
            f"- Base all analysis on information available as of this date only\n"
            f"- If asked about future events, respond that you cannot predict the future"
        )

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    @property
    def offset_days(self) -> int:
        """Number of real-world days between *now* and the simulation clock."""
        return (self._real_time - self.current_time).days

    @property
    def history(self) -> list[str]:
        """Ordered list of every simulation date that was set."""
        return list(self._history)

    def __repr__(self) -> str:
        if self._current_sim_time is None:
            return "TemporalController(sim_time=UNSET)"
        return (
            f"TemporalController("
            f"sim_time={self.current_date_str}, "
            f"offset={self.offset_days}d)"
        )
