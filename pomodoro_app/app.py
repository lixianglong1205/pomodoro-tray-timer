from __future__ import annotations

import json
import os
import platform
import sys
import time
import uuid

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from .config_store import load_config
from .notifications import Notifier
from .models import SessionRecord
from .storage_csv import CsvStorage
from .timer_engine import Phase, PhaseFinished, TimerEngine
from .tray import TrayController
from .history_window import HistoryWindow
from .settings_window import SettingsWindow


# region agent log
_AGENT_LOG_PATH = "/mnt/d/project/new_start-073-番茄钟PC软件/.cursor/debug-b1818b.log"


def _agent_log(*, run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "b1818b",
        "id": f"log_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
        "timestamp": int(time.time() * 1000),
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
    }
    try:
        os.makedirs(os.path.dirname(_AGENT_LOG_PATH), exist_ok=True)
        with open(_AGENT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return


# endregion


def run() -> int:
    run_id = f"pre-fix_{int(time.time())}"
    _agent_log(
        run_id=run_id,
        hypothesis_id="H1",
        location="pomodoro_app/app.py:run",
        message="App starting; capture runtime env",
        data={
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "python": sys.version.split()[0],
            "XDG_CURRENT_DESKTOP": os.environ.get("XDG_CURRENT_DESKTOP"),
            "XDG_SESSION_TYPE": os.environ.get("XDG_SESSION_TYPE"),
            "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY"),
            "DISPLAY": os.environ.get("DISPLAY"),
            "DBUS_SESSION_BUS_ADDRESS_present": bool(os.environ.get("DBUS_SESSION_BUS_ADDRESS")),
            "WSL_DISTRO_NAME": os.environ.get("WSL_DISTRO_NAME"),
        },
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    app_cfg = load_config()
    engine = TimerEngine(config=app_cfg.to_timer_config())
    storage = CsvStorage()

    tray: TrayController | None = None
    notifier: Notifier | None = None
    history: HistoryWindow | None = None
    settings: SettingsWindow | None = None

    def on_open_history() -> None:
        nonlocal history
        if history is None:
            history = HistoryWindow(storage)
        history.show()
        history.raise_()
        history.activateWindow()

    def on_open_settings() -> None:
        nonlocal settings
        if settings is None:
            settings = SettingsWindow(engine)
        settings.show()
        settings.raise_()
        settings.activateWindow()

    def on_quit() -> None:
        if tray is not None:
            tray.hide()
        engine.stop()
        app.quit()

    _agent_log(
        run_id=run_id,
        hypothesis_id="H1",
        location="pomodoro_app/app.py:run",
        message="Qt system tray availability check",
        data={
            "isSystemTrayAvailable": bool(getattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: False)()),
        },
    )

    tray = TrayController(engine, on_open_history=on_open_history, on_open_settings=on_open_settings, on_quit=on_quit)
    notifier = Notifier(app_id="PomodoroApp", fallback=tray.show_message)
    _agent_log(
        run_id=run_id,
        hypothesis_id="H2",
        location="pomodoro_app/app.py:run",
        message="TrayController created",
        data={},
    )

    def notify_phase_finished(finished: PhaseFinished) -> None:
        if finished.phase == Phase.focus:
            title = "专注结束"
        elif finished.phase == Phase.short_break:
            title = "短暂休息结束"
        elif finished.phase == Phase.long_break:
            title = "长休息结束"
        else:
            title = "阶段结束"

        next_phase = engine.phase
        if next_phase == Phase.focus:
            message = "下一阶段：集中精力"
        elif next_phase == Phase.short_break:
            message = "下一阶段：短暂休息"
        elif next_phase == Phase.long_break:
            message = "下一阶段：长时间休息"
        else:
            message = "下一阶段：开始专注"

        notifier.notify(title, message)

    engine.phase_finished.connect(notify_phase_finished)

    def persist_phase_finished(finished: PhaseFinished) -> None:
        record = SessionRecord.from_phase_finished(finished)
        storage.append(record)

    engine.phase_finished.connect(persist_phase_finished)
    tray.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())

