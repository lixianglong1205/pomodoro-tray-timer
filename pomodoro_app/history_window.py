from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .i18n import _
from .models import CSV_HEADER, SessionRecord
from .storage_csv import CsvStorage, DailyStats

_RECORD_HEADERS = [_("日期"), _("集中精力"), _("短暂休息"), _("长休息"), _("开始时间"), _("结束时间")]
_STATS_HEADERS = [_("日期"), _("专注时钟数"), _("专注总分钟")]


def _qdate_to_date(d: QDate) -> date:
    return date(d.year(), d.month(), d.day())


def _parse_date(value: str) -> date | None:
    try:
        y, m, dd = value.split("-")
        return date(int(y), int(m), int(dd))
    except Exception:
        return None


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date | None
    end: date | None

    def contains(self, d: date) -> bool:
        if self.start is not None and d < self.start:
            return False
        if self.end is not None and d > self.end:
            return False
        return True


class HistoryWindow(QDialog):
    def __init__(self, storage: CsvStorage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._storage = storage

        self.setWindowTitle(_("历史记录"))
        self.setMinimumWidth(860)
        self.setMinimumHeight(520)

        self._from_date = QDateEdit()
        self._from_date.setCalendarPopup(True)
        self._from_date.setDisplayFormat("yyyy-MM-dd")
        self._from_date.setSpecialValueText(_("开始日期"))
        self._from_date.setDate(QDate.currentDate().addDays(-7))

        self._to_date = QDateEdit()
        self._to_date.setCalendarPopup(True)
        self._to_date.setDisplayFormat("yyyy-MM-dd")
        self._to_date.setSpecialValueText(_("结束日期"))
        self._to_date.setDate(QDate.currentDate())

        self._btn_apply = QPushButton(_("筛选/刷新"))
        self._btn_clear = QPushButton(_("清除筛选"))

        self._label_from = QLabel(_("从"))
        self._label_to = QLabel(_("到"))

        top = QHBoxLayout()
        top.addWidget(self._label_from)
        top.addWidget(self._from_date)
        top.addWidget(self._label_to)
        top.addWidget(self._to_date)
        top.addSpacing(12)
        top.addWidget(self._btn_apply)
        top.addWidget(self._btn_clear)
        top.addStretch(1)

        self._tabs = QTabWidget()
        self._records_table = self._build_records_table()
        self._stats_table = self._build_stats_table()

        records_tab = QWidget()
        records_layout = QVBoxLayout(records_tab)
        records_layout.addWidget(self._records_table)

        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        stats_layout.addWidget(self._stats_table)

        self._tabs.addTab(records_tab, _("记录明细"))
        self._tabs.addTab(stats_tab, _("每日统计"))

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self._tabs)

        self._btn_apply.clicked.connect(self.refresh)
        self._btn_clear.clicked.connect(self.clear_filter)

        self.refresh()

    def _build_records_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(CSV_HEADER))
        table.setHorizontalHeaderLabels(_RECORD_HEADERS)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setSortingEnabled(False)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _build_stats_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(_STATS_HEADERS)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setSortingEnabled(False)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _current_range(self) -> DateRange:
        start = _qdate_to_date(self._from_date.date()) if self._from_date.date().isValid() else None
        end = _qdate_to_date(self._to_date.date()) if self._to_date.date().isValid() else None
        return DateRange(start=start, end=end)

    def clear_filter(self) -> None:
        self._from_date.setDate(QDate.currentDate().addDays(-7))
        self._to_date.setDate(QDate.currentDate())
        self.refresh()

    def refresh(self) -> None:
        records = self._storage.read_all()
        dr = self._current_range()

        filtered_records: list[SessionRecord] = []
        for r in records:
            d = _parse_date(r.date)
            if d is None:
                continue
            if dr.contains(d):
                filtered_records.append(r)

        self._render_records(filtered_records)
        self._render_stats(self._storage.aggregate_daily(filtered_records))

    def retranslate_ui(self) -> None:
        self.setWindowTitle(_("历史记录"))
        self._from_date.setSpecialValueText(_("开始日期"))
        self._to_date.setSpecialValueText(_("结束日期"))
        self._label_from.setText(_("从"))
        self._label_to.setText(_("到"))
        self._btn_apply.setText(_("筛选/刷新"))
        self._btn_clear.setText(_("清除筛选"))
        self._records_table.setHorizontalHeaderLabels(
            [_("日期"), _("集中精力"), _("短暂休息"), _("长休息"), _("开始时间"), _("结束时间")]
        )
        self._stats_table.setHorizontalHeaderLabels(
            [_("日期"), _("专注时钟数"), _("专注总分钟")]
        )
        self._tabs.setTabText(0, _("记录明细"))
        self._tabs.setTabText(1, _("每日统计"))

    def _render_records(self, records: list[SessionRecord]) -> None:
        self._records_table.setRowCount(len(records))
        # 第 1~3 列为数值列（集中精力，短暂休息，长休息），右对齐
        right_align_cols = {1, 2, 3}
        for i, r in enumerate(records):
            row = r.to_csv_row()
            for j, col in enumerate(CSV_HEADER):
                item = QTableWidgetItem(row.get(col, ""))
                if j in right_align_cols:
                    item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
                self._records_table.setItem(i, j, item)
        self._records_table.resizeColumnsToContents()

    def _render_stats(self, stats: list[DailyStats]) -> None:
        self._stats_table.setRowCount(len(stats))
        for i, s in enumerate(stats):
            self._stats_table.setItem(i, 0, QTableWidgetItem(s.date))
            self._stats_table.setItem(i, 1, QTableWidgetItem(str(s.focus_count)))
            self._stats_table.setItem(i, 2, QTableWidgetItem(str(s.focus_minutes)))
        self._stats_table.resizeColumnsToContents()
