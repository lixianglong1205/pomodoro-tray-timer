from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .config_store import AppConfig, default_config, save_config
from .timer_engine import TimerConfig, TimerEngine


class SettingsWindow(QDialog):
    def __init__(self, engine: TimerEngine, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self.setWindowTitle("设置")
        self.setMinimumWidth(420)

        self._hint = QLabel("修改后点击“保存”即可立即生效。")
        self._hint.setWordWrap(True)
        self._hint.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._spin_focus = self._make_spinbox()
        self._spin_short = self._make_spinbox()
        self._spin_long = self._make_spinbox()
        self._spin_long_every = self._make_every_spinbox()

        form.addRow("集中精力（分钟）", self._spin_focus)
        form.addRow("短暂休息（分钟）", self._spin_short)
        form.addRow("长休息（分钟）", self._spin_long)
        form.addRow("长休息频率（每完成 n 次专注）", self._spin_long_every)

        self._btn_default = QPushButton("恢复默认")
        self._btn_cancel = QPushButton("取消")
        self._btn_save = QPushButton("保存")
        self._btn_save.setDefault(True)

        self._btn_default.clicked.connect(self._on_restore_default)
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_save.clicked.connect(self._on_save)

        buttons = QHBoxLayout()
        buttons.addWidget(self._btn_default)
        buttons.addStretch(1)
        buttons.addWidget(self._btn_cancel)
        buttons.addWidget(self._btn_save)

        root = QVBoxLayout(self)
        root.addWidget(self._hint)
        root.addLayout(form)
        root.addStretch(1)
        root.addLayout(buttons)

        self._sync_from_engine()

    def _make_spinbox(self) -> QSpinBox:
        spin = QSpinBox(self)
        spin.setRange(1, 240)
        spin.setSingleStep(1)
        spin.setAccelerated(True)
        return spin

    def _make_every_spinbox(self) -> QSpinBox:
        spin = QSpinBox(self)
        spin.setRange(1, 20)
        spin.setSingleStep(1)
        spin.setAccelerated(True)
        return spin

    def _sync_from_engine(self) -> None:
        cfg = self._engine.config
        self._spin_focus.setValue(cfg.focus_minutes)
        self._spin_short.setValue(cfg.short_break_minutes)
        self._spin_long.setValue(cfg.long_break_minutes)
        self._spin_long_every.setValue(cfg.long_break_every_focus)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._sync_from_engine()
        super().showEvent(event)

    def _values_to_timer_config(self) -> TimerConfig:
        cfg = TimerConfig(
            focus_minutes=int(self._spin_focus.value()),
            short_break_minutes=int(self._spin_short.value()),
            long_break_minutes=int(self._spin_long.value()),
            long_break_every_focus=int(self._spin_long_every.value()),
        )
        cfg.validate()
        return cfg

    def _on_restore_default(self) -> None:
        d = default_config()
        self._spin_focus.setValue(d.focus_minutes)
        self._spin_short.setValue(d.short_break_minutes)
        self._spin_long.setValue(d.long_break_minutes)
        self._spin_long_every.setValue(d.long_break_every_focus)

    def _on_save(self) -> None:
        cfg = self._values_to_timer_config()
        save_config(AppConfig.from_timer_config(cfg))
        self._engine.update_config(
            focus_minutes=cfg.focus_minutes,
            short_break_minutes=cfg.short_break_minutes,
            long_break_minutes=cfg.long_break_minutes,
            long_break_every_focus=cfg.long_break_every_focus,
        )
        self.accept()

