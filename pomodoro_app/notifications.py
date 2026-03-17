from __future__ import annotations

import platform
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
        if platform.system().lower() != "windows":
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

