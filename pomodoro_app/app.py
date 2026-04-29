from __future__ import annotations

import logging
import os
import platform
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from .config_store import load_config
from .history_window import HistoryWindow
from .i18n import Translator as I18n
from .i18n import _
from .models import SessionRecord
from .notifications import Notifier
from .settings_window import SettingsWindow
from .storage_csv import CsvStorage
from .timer_engine import Phase, PhaseFinished, TimerEngine
from .tray import TrayController

logger = logging.getLogger(__name__)


def _is_macos() -> bool:
    return platform.system().lower() == "darwin"


def _env_truthy(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _set_macos_activation_policy() -> bool:
    if not _is_macos():
        return False
    try:
        from AppKit import (
            NSApplication,
            NSApplicationActivationPolicyAccessory,
            NSApplicationActivationPolicyRegular,
        )

        show_dock_icon = _env_truthy("POMODORO_MACOS_SHOW_DOCK_ICON", default=True)
        policy = (
            NSApplicationActivationPolicyRegular
            if show_dock_icon
            else NSApplicationActivationPolicyAccessory
        )
        NSApplication.sharedApplication().setActivationPolicy_(policy)
        return not show_dock_icon
    except Exception:
        logger.warning("failed to set macOS accessory activation policy")
        return False


def _report_tray_unavailable(app: QApplication) -> None:
    msg = (
        "系统托盘（菜单栏图标）不可用，无法显示右上角图标。\n\n"
        "常见原因：\n"
        "- 不是在本机图形界面会话里启动（例如 SSH/CI/launchd 无 Aqua）\n"
        "- macOS 系统设置把菜单栏图标隐藏到了控制中心/自动隐藏菜单栏\n\n"
        "你可以尝试：\n"
        "- 确认进程运行在当前用户的桌面会话中\n"
        '- 系统设置 → 控制中心：检查“菜单栏项目”的显示策略\n'
        "- 先退出所有正在运行的 pomodoro 进程后再启动一次"
    )
    print(msg, file=sys.stderr, flush=True)

    try:
        QMessageBox.critical(None, _("番茄钟：无法显示菜单栏图标"), msg)
    except Exception:
        pass


def run() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    is_accessory_policy = _set_macos_activation_policy()

    if not QSystemTrayIcon.isSystemTrayAvailable():
        _report_tray_unavailable(app)
        return 2

    app_cfg = load_config()
    I18n.setup(app_cfg.language)

    engine = TimerEngine(config=app_cfg.to_timer_config())
    storage = CsvStorage()

    tray: TrayController | None = None
    notifier: Notifier | None = None
    history: HistoryWindow | None = None

    def on_open_history() -> None:
        nonlocal history
        if history is None:
            history = HistoryWindow(storage)
        history.show()
        history.raise_()
        history.activateWindow()

    def on_open_settings() -> None:
        w = SettingsWindow(engine)
        w.show()
        w.raise_()
        w.activateWindow()

    def on_quit() -> None:
        if tray is not None:
            tray.hide()
        engine.stop()
        app.quit()
        if _is_macos() and is_accessory_policy:
            # app.quit() may not terminate NSRunLoop under Accessory policy.
            # Schedule forced exit as safety net instead of immediate os._exit,
            # giving Qt a chance to clean up first.
            QTimer.singleShot(3000, lambda: os._exit(0))

    tray = TrayController(engine, on_open_history=on_open_history, on_open_settings=on_open_settings, on_quit=on_quit)
    notifier = Notifier(app_id="PomodoroApp", fallback=tray.show_message)

    def notify_phase_finished(finished: PhaseFinished) -> None:
        if finished.phase == Phase.focus:
            total = engine.config.long_break_every_focus
            n = ((max(1, finished.focus_index) - 1) % max(1, total)) + 1
            title = _("第{n}/{total}次集中精力").format(n=n, total=total)
        elif finished.phase == Phase.short_break:
            title = _("短暂休息结束")
        elif finished.phase == Phase.long_break:
            title = _("长休息结束")
        else:
            title = _("阶段结束")

        next_phase = engine.pending_phase or engine.next_suggested_phase()
        if next_phase == Phase.focus:
            message = _("下一阶段：集中精力")
        elif next_phase == Phase.short_break:
            message = _("下一阶段：短暂休息")
        elif next_phase == Phase.long_break:
            message = _("下一阶段：长时间休息")
        else:
            message = _("下一阶段：开始专注")

        notifier.notify(title, message)

    engine.phase_finished.connect(notify_phase_finished)

    def persist_phase_finished(finished: PhaseFinished) -> None:
        record = SessionRecord.from_phase_finished(finished)
        storage.append(record)

    engine.phase_finished.connect(persist_phase_finished)

    def on_language_changed(_lang: str) -> None:
        if history is not None:
            history.retranslate_ui()

    engine.language_changed.connect(on_language_changed)

    tray.show()

    exit_code = app.exec()

    # macOS 上正常退出路径已由 on_quit 的 os._exit 处理；这里作为兜底，
    # 防止 app.exec 意外返回时挂在 PyObjC/NSRunLoop 清理上。
    if _is_macos() and is_accessory_policy:
        os._exit(int(exit_code) if exit_code is not None else 0)

    return exit_code
