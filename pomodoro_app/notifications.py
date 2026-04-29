from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from shutil import which

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    title: str
    message: str


class Notifier:
    def __init__(self, *, app_id: str = "PomodoroApp", fallback: Callable[[str, str], None] | None = None) -> None:
        self._app_id = app_id
        self._fallback = fallback

    def notify(self, title: str, message: str) -> None:
        system = platform.system().lower()
        if system == "darwin":
            notified = self._notify_macos(title, message)
            if notified:
                self._show_tray_popup_macos(title, message)
                self._show_qt_toast_macos(title, message)
                return
            self._notify_fallback(title, message)
            return

        if system != "windows":
            self._notify_fallback(title, message)
            return

        try:
            from winotify import (
                Notification,
                audio,
            )

            toast = Notification(app_id=self._app_id, title=title, msg=message)
            # 跟随 Windows Toast 系统提示音
            toast.set_audio(audio.Default, loop=False)
            toast.show()
        except Exception:
            logger.warning("winotify notification failed, using fallback")
            self._notify_fallback(title, message)

    def _show_tray_popup_macos(self, title: str, message: str) -> None:
        if os.environ.get("POMODORO_TRAY_POPUP", "").strip().lower() in {"0", "false", "no"}:
            return
        if self._fallback is None:
            return
        try:
            self._fallback(title, message)
        except Exception:
            logger.warning("macOS tray popup failed")

    def _show_qt_toast_macos(self, title: str, message: str) -> None:
        if os.environ.get("POMODORO_QT_TOAST", "").strip().lower() in {"0", "false", "no"}:
            return

        try:
            from PySide6.QtCore import Qt, QTimer
            from PySide6.QtGui import QGuiApplication
            from PySide6.QtWidgets import QLabel, QWidget

            app = QGuiApplication.instance()
            if app is None:
                return

            text = f"{title}\n{message}".strip()
            toast = QWidget()
            toast.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            toast.setWindowFlags(
                Qt.WindowType.Tool
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.BypassWindowManagerHint
            )
            toast.setStyleSheet(
                """
                QWidget {
                    background: rgba(20, 20, 20, 220);
                    border: 1px solid rgba(255, 255, 255, 40);
                    border-radius: 12px;
                }
                QLabel {
                    color: white;
                    padding: 12px 14px;
                    font-size: 13px;
                }
                """
            )

            label = QLabel(text, toast)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            label.setWordWrap(True)
            label.adjustSize()

            max_w = 360
            w = min(max_w, max(260, label.sizeHint().width()))
            label.setFixedWidth(w)
            label.adjustSize()
            toast.resize(label.sizeHint().width(), label.sizeHint().height())

            screen = QGuiApplication.primaryScreen()
            if screen is None:
                return
            geom = screen.availableGeometry()
            margin = 16
            x = geom.x() + geom.width() - toast.width() - margin
            y = geom.y() + margin
            toast.move(x, y)

            toast.show()
            toast.raise_()

            duration_ms = int(os.environ.get("POMODORO_QT_TOAST_DURATION_MS", "4500").strip() or "4500")
            duration_ms = max(1000, min(duration_ms, 15000))
            QTimer.singleShot(duration_ms, toast.close)
        except Exception:
            logger.warning("macOS Qt toast failed")

    def _notify_macos(self, title: str, message: str) -> bool:
        try:
            tn = which("terminal-notifier")
            if not tn:
                candidate = os.path.expanduser("~/.local/bin/terminal-notifier")
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    tn = candidate
            if tn:
                subprocess.run(  # noqa: S603
                    [tn, "-title", title, "-message", message, "-sound", "default"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=2.5,
                )
                return True

            script = f"display notification {json.dumps(message)} with title {json.dumps(title)}"
            subprocess.run(  # noqa: S603
                ["osascript", "-e", script],  # noqa: S607
                check=True,
                capture_output=True,
                text=True,
                timeout=2.5,
            )
            return True
        except Exception:
            logger.warning("macOS notification failed")
            return False

    def _notify_fallback(self, title: str, message: str) -> None:
        if platform.system().lower() == "windows":
            self._beep_windows()
        if self._fallback is None:
            return
        try:
            self._fallback(title, message)
        except Exception:
            return

    def _beep_windows(self) -> None:
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONASTERISK)  # type: ignore[attr-defined]
        except Exception:
            return
