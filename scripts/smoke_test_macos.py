from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# Ensure the project root is importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pomodoro_app.config_store import AppConfig
from pomodoro_app.notifications import Notifier
from pomodoro_app.storage_csv import CsvStorage
from pomodoro_app.timer_engine import PhaseFinished, TimerEngine
from pomodoro_app.tray import TrayController


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Use a short config so the phase finishes quickly.
    engine = TimerEngine(
        config=AppConfig(
            focus_minutes=1,
            short_break_minutes=1,
            long_break_minutes=1,
            long_break_every_focus=1,
        ).to_timer_config()
    )
    storage = CsvStorage()
    tray = TrayController(engine, on_open_history=lambda: None, on_open_settings=lambda: None, on_quit=app.quit)
    notifier = Notifier(app_id="PomodoroApp", fallback=tray.show_message)

    done: dict[str, bool] = {"notified": False, "persisted": False}

    def on_phase_finished(finished: PhaseFinished) -> None:
        notifier.notify("冒烟测试：阶段结束", f"phase={finished.phase.value}, planned={finished.planned_minutes}min")
        done["notified"] = True
        storage.append(
            # Reuse the normal record creation path for parity.
            __import__("pomodoro_app.models", fromlist=["SessionRecord"]).SessionRecord.from_phase_finished(finished)
        )
        done["persisted"] = True
        QTimer.singleShot(250, app.quit)

    engine.phase_finished.connect(on_phase_finished)

    tray.show()
    # Exercise the primary tray interaction: left-click should start / pause / resume.
    QTimer.singleShot(250, tray._on_left_click)  # start focus (idle -> start)
    QTimer.singleShot(2250, tray._on_left_click)  # pause (running -> pause)
    QTimer.singleShot(4250, tray._on_left_click)  # resume (paused -> resume)

    # Safety timeout: never hang forever in CI / automated runs.
    QTimer.singleShot(90_000, app.quit)
    code = app.exec()
    if not all(done.values()):
        return 2
    return code


if __name__ == "__main__":
    raise SystemExit(main())

