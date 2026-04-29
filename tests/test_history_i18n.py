from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from pomodoro_app.history_window import HistoryWindow
from pomodoro_app.i18n import Translator
from pomodoro_app.storage_csv import CsvStorage


class TestHistoryWindowRetranslate:
    """Tests for HistoryWindow.retranslate_ui()."""

    @pytest.fixture
    def storage(self) -> CsvStorage:
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w")
        tmp.write("date,focus_minutes,short_break_minutes,long_break_minutes,start_time,end_time\n")
        tmp.close()
        csv_path = Path(tmp.name)
        storage = CsvStorage(csv_path)
        storage.ensure_ready()
        yield storage
        csv_path.unlink(missing_ok=True)

    def test_retranslate_from_zh_to_en(self, qtbot: QtBot, storage: CsvStorage) -> None:
        Translator.setup("zh")
        win = HistoryWindow(storage)

        # Initial Chinese state
        assert win.windowTitle() == "历史记录"
        assert win._tabs.tabText(0) == "记录明细"
        assert win._tabs.tabText(1) == "每日统计"
        assert win._label_from.text() == "从"
        assert win._label_to.text() == "到"
        assert win._btn_apply.text() == "筛选/刷新"
        assert win._btn_clear.text() == "清除筛选"

        # Retranslate to English
        Translator.switch_language("en")
        win.retranslate_ui()
        qtbot.wait(10)

        assert win.windowTitle() == "History"
        assert win._tabs.tabText(0) == "Records"
        assert win._tabs.tabText(1) == "Daily Stats"
        assert win._label_from.text() == "From"
        assert win._label_to.text() == "To"
        assert win._btn_apply.text() == "Filter / Refresh"
        assert win._btn_clear.text() == "Clear Filter"

    def test_retranslate_cycle(self, qtbot: QtBot, storage: CsvStorage) -> None:
        """Test zh -> en -> zh retranslation cycle."""
        Translator.setup("en")
        win = HistoryWindow(storage)

        assert win._tabs.tabText(0) == "Records"

        # Switch to Chinese
        Translator.switch_language("zh")
        win.retranslate_ui()
        qtbot.wait(10)
        assert win._tabs.tabText(0) == "记录明细"

        # Switch back to English
        Translator.switch_language("en")
        win.retranslate_ui()
        qtbot.wait(10)
        assert win._tabs.tabText(0) == "Records"
