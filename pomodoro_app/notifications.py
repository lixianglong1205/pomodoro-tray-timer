from __future__ import annotations

import json
import os
import platform
import subprocess
from shutil import which
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    title: str
    message: str


class Notifier:
    def __init__(self, *, app_id: str = "PomodoroApp", fallback=None) -> None:
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
            from winotify import Notification  # type: ignore
            from winotify import audio  # type: ignore

            toast = Notification(app_id=self._app_id, title=title, msg=message)
            # 跟随 Windows Toast 系统提示音
            toast.set_audio(audio.Default, loop=False)
            toast.show()
        except Exception:
            self._notify_fallback(title, message)

    def _show_tray_popup_macos(self, title: str, message: str) -> None:
        """
        Ensure an immediate, visible popup on macOS.

        macOS 26 may deliver notifications to Notification Center but not show a banner.
        The Qt tray balloon is a reliable "always visible" fallback.
        """
        if os.environ.get("POMODORO_TRAY_POPUP", "").strip().lower() in {"0", "false", "no"}:
            return
        if self._fallback is None:
            return
        try:
            self._fallback(title, message)
        except Exception:
            return

    def _show_qt_toast_macos(self, title: str, message: str) -> None:
        """
        Show an always-on-top in-app toast on macOS.

        Rationale: macOS 26 may deliver notifications to Notification Center but not
        show a heads-up banner. Qt tray balloons can also be routed through the same
        system mechanism. A small transient QWidget guarantees immediate visibility.
        """
        if os.environ.get("POMODORO_QT_TOAST", "").strip().lower() in {"0", "false", "no"}:
            return

        try:
            from PySide6.QtCore import QTimer, Qt
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

            # Size to content with a reasonable max width.
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
            return

    def _play_sound_macos(self) -> None:
        """
        Play an audible cue on macOS.

        We intentionally do NOT rely on Notification Center sounds because macOS
        may show notifications but suppress their audio.
        """
        # Disabled by default. Enable explicitly when you want an in-app sound cue.
        if os.environ.get("POMODORO_SOUND", "").strip().lower() not in {"1", "true", "yes"}:
            return

        sound_file = os.environ.get("POMODORO_SOUND_FILE", "").strip()
        if not sound_file:
            sound_file = "/System/Library/Sounds/Glass.aiff"

        try:
            # Fire-and-forget to avoid blocking the UI thread.
            subprocess.Popen(  # noqa: S603
                ["afplay", sound_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return

    def _notify_macos(self, title: str, message: str) -> bool:
        """
        Best-effort macOS Notification Center message via AppleScript.

        Notes:
        - First use may trigger a system prompt for the *host process* (e.g. Terminal/Python)
          to allow notifications.
        - This method does not support click callbacks.
        """
        try:
            # If the user has terminal-notifier installed, prefer it.
            # It's generally more visible/manageable in macOS Notification settings.
            tn = which("terminal-notifier")
            if not tn:
                # `uv run` / GUI launches may not include ~/.local/bin in PATH.
                candidate = os.path.expanduser("~/.local/bin/terminal-notifier")
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    tn = candidate
            if tn:
                subprocess.run(
                    [tn, "-title", title, "-message", message, "-sound", "default"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=2.5,
                )
                return True

            script = f"display notification {json.dumps(message)} with title {json.dumps(title)}"
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
                timeout=2.5,
            )
            return True
        except Exception:
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

            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            return

