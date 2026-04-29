from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication

# Allow running via `uv run scripts/...py` without installing the package.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from pomodoro_app.timer_engine import Phase, TimerConfig, TimerEngine


def _simulate_tray_left_click(engine: TimerEngine) -> None:
    """
    Mirror TrayController._on_left_click() behavior without UI:
    - running: toggle_pause()
    - idle with pending: start_pending()
    - idle without pending: start_focus()
    """
    if engine.phase != Phase.idle:
        engine.toggle_pause()
        return
    if engine.pending_phase is not None:
        engine.start_pending()
        return
    engine.start_focus()


def _force_natural_finish(engine: TimerEngine) -> None:
    engine.force_finish_phase()


def _new_engine() -> TimerEngine:
    return TimerEngine(
        TimerConfig(
            focus_minutes=1,
            short_break_minutes=1,
            long_break_minutes=1,
            long_break_every_focus=2,
        )
    )


def case_stop_short_break_then_left_click_restarts_short_break() -> None:
    engine = _new_engine()
    engine.start_short_break()
    engine.stop()
    assert engine.phase == Phase.idle
    assert engine.pending_phase == Phase.short_break

    _simulate_tray_left_click(engine)
    assert engine.phase == Phase.short_break
    assert engine.pending_phase is None


def case_stop_long_break_then_left_click_restarts_long_break() -> None:
    engine = _new_engine()
    engine.start_long_break()
    engine.stop()
    assert engine.phase == Phase.idle
    assert engine.pending_phase == Phase.long_break

    _simulate_tray_left_click(engine)
    assert engine.phase == Phase.long_break
    assert engine.pending_phase is None


def case_stop_focus_then_left_click_starts_focus() -> None:
    engine = _new_engine()
    engine.start_focus()
    engine.stop()
    assert engine.phase == Phase.idle
    assert engine.pending_phase is None

    _simulate_tray_left_click(engine)
    assert engine.phase == Phase.focus
    assert engine.pending_phase is None


def case_natural_finish_focus_then_left_click_starts_break() -> None:
    engine = _new_engine()
    engine.start_focus()
    _force_natural_finish(engine)
    assert engine.phase == Phase.idle
    assert engine.pending_phase in (Phase.short_break, Phase.long_break)

    pending = engine.pending_phase
    _simulate_tray_left_click(engine)
    assert engine.phase == pending
    assert engine.pending_phase is None


def case_natural_finish_break_then_left_click_starts_focus() -> None:
    engine = _new_engine()
    engine.start_short_break()
    _force_natural_finish(engine)
    assert engine.phase == Phase.idle
    assert engine.pending_phase == Phase.focus

    _simulate_tray_left_click(engine)
    assert engine.phase == Phase.focus
    assert engine.pending_phase is None


def main() -> None:
    # Ensure Qt timer infrastructure is available for QTimer.start/stop.
    _app = QCoreApplication([])

    tests = [
        case_stop_short_break_then_left_click_restarts_short_break,
        case_stop_long_break_then_left_click_restarts_long_break,
        case_stop_focus_then_left_click_starts_focus,
        case_natural_finish_focus_then_left_click_starts_break,
        case_natural_finish_break_then_left_click_starts_focus,
    ]

    for t in tests:
        t()
        print(f"[OK] {t.__name__}")

    print("All manual-verify cases passed.")


if __name__ == "__main__":
    main()

