from __future__ import annotations

from pytestqt.qtbot import QtBot

from pomodoro_app.i18n import Translator
from pomodoro_app.timer_engine import TimerEngine
from pomodoro_app.tray import TrayController


class TestTrayRetranslate:
    """Tests for TrayController.retranslate_ui()."""

    def test_retranslate_from_zh_to_en(self, qtbot: QtBot) -> None:
        Translator.setup("zh")
        engine = TimerEngine()
        tray = TrayController(engine, on_open_history=lambda: None, on_open_settings=lambda: None, on_quit=lambda: None)

        # Default (Chinese)
        assert tray._act_focus.text() == "开始集中精力"
        assert tray._act_settings.text() == "设置..."
        assert tray._act_quit.text() == "退出"

        # Switch to English via signal
        Translator.switch_language("en")
        engine.language_changed.emit("en")
        qtbot.wait(10)  # let Qt process events

        assert tray._act_focus.text() == "Start Focus"
        assert tray._act_settings.text() == "Settings…"
        assert tray._act_quit.text() == "Quit"

    def test_language_changed_signal_triggers_retranslate(self, qtbot: QtBot) -> None:
        Translator.setup("en")
        engine = TimerEngine()
        tray = TrayController(engine, on_open_history=lambda: None, on_open_settings=lambda: None, on_quit=lambda: None)

        assert tray._act_focus.text() == "Start Focus"

        # Switch back to Chinese via signal
        Translator.switch_language("zh")
        engine.language_changed.emit("zh")
        qtbot.wait(10)

        assert tray._act_focus.text() == "开始集中精力"
