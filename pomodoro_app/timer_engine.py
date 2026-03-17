from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum

from PySide6.QtCore import QObject, QTimer, Signal


class Phase(str, Enum):
    idle = "idle"
    focus = "focus"
    short_break = "short_break"
    long_break = "long_break"


@dataclass(frozen=True, slots=True)
class TimerConfig:
    focus_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    long_break_every_focus: int = 4

    def validate(self) -> None:
        for name in (
            "focus_minutes",
            "short_break_minutes",
            "long_break_minutes",
            "long_break_every_focus",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} 必须是正整数，当前为 {value!r}")


@dataclass(frozen=True, slots=True)
class PhaseRun:
    phase: Phase
    total_seconds: int
    remaining_seconds: int
    started_at: datetime | None


@dataclass(frozen=True, slots=True)
class PhaseFinished:
    phase: Phase
    planned_minutes: int
    actual_seconds: int
    started_at: datetime
    finished_at: datetime
    focus_index: int


def _now_local() -> datetime:
    return datetime.now().astimezone()


class TimerEngine(QObject):
    tick = Signal(object)  # PhaseRun
    phase_changed = Signal(object)  # PhaseRun
    phase_finished = Signal(object)  # PhaseFinished
    paused_changed = Signal(bool)
    stopped = Signal()

    def __init__(self, config: TimerConfig | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config or TimerConfig()
        self._config.validate()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_timeout)

        self._phase: Phase = Phase.idle
        self._pending_phase: Phase | None = None
        self._started_at: datetime | None = None
        self._total_seconds: int = 0
        self._remaining_seconds: int = 0
        self._focus_completed_in_cycle: int = 0
        self._paused: bool = False

    @property
    def config(self) -> TimerConfig:
        return self._config

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def pending_phase(self) -> Phase | None:
        return self._pending_phase

    @property
    def is_paused(self) -> bool:
        return self._phase != Phase.idle and self._paused

    @property
    def is_running(self) -> bool:
        return self._phase != Phase.idle and (not self._paused)

    @property
    def phase_run(self) -> PhaseRun:
        return PhaseRun(
            phase=self._phase,
            total_seconds=self._total_seconds,
            remaining_seconds=self._remaining_seconds,
            started_at=self._started_at,
        )

    @property
    def focus_completed_in_cycle(self) -> int:
        return self._focus_completed_in_cycle

    def update_config(self, **kwargs: int) -> None:
        new_config = replace(self._config, **kwargs)
        new_config.validate()
        self._config = new_config

        if self._phase == Phase.idle:
            return

        planned = self._planned_seconds_for(self._phase)
        elapsed = max(0, self._total_seconds - self._remaining_seconds)
        self._total_seconds = planned
        self._remaining_seconds = max(0, planned - elapsed)
        self.tick.emit(self.phase_run)

    def start_focus(self) -> None:
        self._start_phase(Phase.focus)

    def start_short_break(self) -> None:
        self._start_phase(Phase.short_break)

    def start_long_break(self) -> None:
        self._start_phase(Phase.long_break)

    def start_pending(self) -> None:
        pending = self._pending_phase
        if pending is None:
            return
        self._pending_phase = None
        self._start_phase(pending)

    def pause(self) -> None:
        if self._phase == Phase.idle or self._paused:
            return
        self._timer.stop()
        self._paused = True
        self.paused_changed.emit(True)
        self.tick.emit(self.phase_run)

    def resume(self) -> None:
        if self._phase == Phase.idle or (not self._paused):
            return
        self._paused = False
        self.paused_changed.emit(False)
        self.tick.emit(self.phase_run)
        self._timer.start()

    def toggle_pause(self) -> None:
        if self._phase == Phase.idle:
            return
        if self._paused:
            self.resume()
        else:
            self.pause()

    def stop(self) -> None:
        if self._phase == Phase.idle:
            if self._pending_phase is None:
                return
            self._pending_phase = None
            self.phase_changed.emit(self.phase_run)
            return
        self._timer.stop()
        was_paused = self._paused
        self._paused = False
        self._phase = Phase.idle
        self._pending_phase = None
        self._started_at = None
        self._total_seconds = 0
        self._remaining_seconds = 0
        self.stopped.emit()
        if was_paused:
            self.paused_changed.emit(False)
        self.phase_changed.emit(self.phase_run)

    def restart_cycle(self) -> None:
        self._focus_completed_in_cycle = 0
        self.start_focus()

    def next_suggested_phase(self) -> Phase:
        return self._suggest_next(self._phase, self._focus_completed_in_cycle)

    def _suggest_next(self, phase: Phase, focus_completed_in_cycle: int) -> Phase:
        if phase == Phase.focus:
            if focus_completed_in_cycle % self._config.long_break_every_focus == 0:
                return Phase.long_break
            return Phase.short_break
        if phase in (Phase.short_break, Phase.long_break):
            return Phase.focus
        return Phase.focus

    def _planned_seconds_for(self, phase: Phase) -> int:
        if phase == Phase.focus:
            return self._config.focus_minutes * 60
        if phase == Phase.short_break:
            return self._config.short_break_minutes * 60
        if phase == Phase.long_break:
            return self._config.long_break_minutes * 60
        return 0

    def _planned_minutes_for(self, phase: Phase) -> int:
        if phase == Phase.focus:
            return self._config.focus_minutes
        if phase == Phase.short_break:
            return self._config.short_break_minutes
        if phase == Phase.long_break:
            return self._config.long_break_minutes
        return 0

    def _start_phase(self, phase: Phase) -> None:
        if phase == Phase.idle:
            self.stop()
            return

        self._timer.stop()
        was_paused = self._paused
        self._paused = False
        self._pending_phase = None
        self._phase = phase
        self._started_at = _now_local()
        self._total_seconds = self._planned_seconds_for(phase)
        self._remaining_seconds = self._total_seconds
        if was_paused:
            self.paused_changed.emit(False)
        self.phase_changed.emit(self.phase_run)
        self.tick.emit(self.phase_run)
        self._timer.start()

    def _on_timeout(self) -> None:
        if self._phase == Phase.idle:
            self._timer.stop()
            return

        self._remaining_seconds = max(0, self._remaining_seconds - 1)
        self.tick.emit(self.phase_run)

        if self._remaining_seconds > 0:
            return

        started_at = self._started_at or _now_local()
        finished_at = _now_local()
        planned_minutes = self._planned_minutes_for(self._phase)
        actual_seconds = self._total_seconds

        if self._phase == Phase.focus:
            self._focus_completed_in_cycle += 1

        pending = self._suggest_next(self._phase, self._focus_completed_in_cycle)
        self._pending_phase = pending

        finished = PhaseFinished(
            phase=self._phase,
            planned_minutes=planned_minutes,
            actual_seconds=actual_seconds,
            started_at=started_at,
            finished_at=finished_at,
            focus_index=self._focus_completed_in_cycle,
        )
        self.phase_finished.emit(finished)

        self._timer.stop()
        was_paused = self._paused
        self._paused = False
        self._phase = Phase.idle
        self._started_at = None
        self._total_seconds = 0
        self._remaining_seconds = 0
        if was_paused:
            self.paused_changed.emit(False)
        self.phase_changed.emit(self.phase_run)

