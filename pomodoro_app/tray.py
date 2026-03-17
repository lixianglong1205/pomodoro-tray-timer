from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import time
import uuid

from PySide6.QtCore import QObject, Qt, Slot
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .timer_engine import Phase, PhaseFinished, PhaseRun, TimerEngine


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


@dataclass(frozen=True, slots=True)
class TrayTheme:
    focus_bg: QColor = field(default_factory=lambda: QColor("#D7263D"))
    break_bg: QColor = field(default_factory=lambda: QColor("#2E8B57"))
    idle_bg: QColor = field(default_factory=lambda: QColor("#4B5563"))
    text: QColor = field(default_factory=lambda: QColor("#FFFFFF"))
    outline: QColor = field(default_factory=lambda: QColor("#111827"))


def _phase_label(phase: Phase) -> str:
    if phase == Phase.focus:
        return "集中精力"
    if phase == Phase.short_break:
        return "短暂休息"
    if phase == Phase.long_break:
        return "长时间休息"
    return "空闲"


def _suggest_label(phase: Phase) -> str:
    if phase == Phase.focus:
        return "下一步：休息"
    if phase in (Phase.short_break, Phase.long_break):
        return "下一步：开始专注"
    return "下一步：开始专注"


class TrayController(QObject):
    def __init__(
        self,
        engine: TimerEngine,
        on_open_history,
        on_open_settings,
        on_quit,
        *,
        parent: QObject | None = None,
        theme: TrayTheme | None = None,
        icon_size: int = 128,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._theme = theme or TrayTheme()
        self._icon_size = icon_size
        self._agent_run_id = f"pre-fix_{int(time.time())}"

        self._tray = QSystemTrayIcon(self)
        _agent_log(
            run_id=self._agent_run_id,
            hypothesis_id="H1",
            location="pomodoro_app/tray.py:TrayController.__init__",
            message="QSystemTrayIcon created",
            data={
                "isSystemTrayAvailable": bool(QSystemTrayIcon.isSystemTrayAvailable()),
                "supportsMessages": bool(QSystemTrayIcon.supportsMessages()),
            },
        )
        self._tray.setToolTip("番茄钟")
        self._tray.setIcon(self._render_icon(minutes=None, phase=Phase.idle, paused=False))

        self._tray.activated.connect(self._on_tray_activated)

        menu = QMenu()
        self._act_stop = QAction("终止时钟", menu)
        self._act_pause = QAction("暂停", menu)
        self._act_focus = QAction("开始集中精力", menu)
        self._act_short = QAction("开始短暂休息", menu)
        self._act_long = QAction("开始长时间休息", menu)
        self._act_restart = QAction("重新开始番茄钟循环", menu)
        self._act_history = QAction("打开历史记录", menu)
        self._act_settings = QAction("设置...", menu)
        self._act_quit = QAction("退出", menu)

        menu.addAction(self._act_stop)
        menu.addAction(self._act_pause)
        menu.addSeparator()
        menu.addAction(self._act_focus)
        menu.addAction(self._act_short)
        menu.addAction(self._act_long)
        menu.addSeparator()
        menu.addAction(self._act_restart)
        menu.addSeparator()
        menu.addAction(self._act_history)
        menu.addAction(self._act_settings)
        menu.addSeparator()
        menu.addAction(self._act_quit)
        self._tray.setContextMenu(menu)

        self._act_stop.triggered.connect(self._engine.stop)
        self._act_pause.triggered.connect(self._engine.toggle_pause)
        self._act_focus.triggered.connect(self._engine.start_focus)
        self._act_short.triggered.connect(self._engine.start_short_break)
        self._act_long.triggered.connect(self._engine.start_long_break)
        self._act_restart.triggered.connect(self._engine.restart_cycle)
        self._act_history.triggered.connect(on_open_history)
        self._act_settings.triggered.connect(on_open_settings)
        self._act_quit.triggered.connect(on_quit)

        self._last_drawn_minute: int | None = None
        self._last_phase: Phase = Phase.idle
        self._last_paused: bool = False

        self._engine.tick.connect(self._on_tick)
        self._engine.phase_changed.connect(self._on_phase_changed)
        self._engine.phase_finished.connect(self._on_phase_finished)
        self._engine.paused_changed.connect(self._on_paused_changed)
        self._engine.stopped.connect(self._on_stopped)

    def show(self) -> None:
        _agent_log(
            run_id=self._agent_run_id,
            hypothesis_id="H2",
            location="pomodoro_app/tray.py:TrayController.show",
            message="Tray show() called",
            data={},
        )
        try:
            self._tray.show()
            _agent_log(
                run_id=self._agent_run_id,
                hypothesis_id="H2",
                location="pomodoro_app/tray.py:TrayController.show",
                message="Tray show() returned",
                data={"visible": bool(self._tray.isVisible())},
            )
        except Exception as e:
            _agent_log(
                run_id=self._agent_run_id,
                hypothesis_id="H2",
                location="pomodoro_app/tray.py:TrayController.show",
                message="Tray show() raised",
                data={"exc_type": type(e).__name__, "exc": str(e)},
            )
            raise
        self._refresh(force=True)

    def hide(self) -> None:
        self._tray.hide()

    def show_message(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message)

    def _minutes_remaining(self, run: PhaseRun) -> int | None:
        if run.phase == Phase.idle:
            return None
        seconds = max(0, run.remaining_seconds)
        minutes = seconds // 60
        if seconds % 60:
            minutes += 1
        return max(0, minutes)

    def _refresh(self, *, force: bool = False) -> None:
        run = self._engine.phase_run
        minutes = self._minutes_remaining(run)
        phase = run.phase
        paused = self._engine.is_paused

        if not force and phase == self._last_phase and minutes == self._last_drawn_minute and paused == self._last_paused:
            return

        self._tray.setIcon(self._render_icon(minutes=minutes, phase=phase, paused=paused))
        self._tray.setToolTip(self._build_tooltip(run))
        self._sync_pause_action()
        self._last_drawn_minute = minutes
        self._last_phase = phase
        self._last_paused = paused

    def _build_tooltip(self, run: PhaseRun) -> str:
        phase_name = _phase_label(run.phase)
        if run.phase == Phase.idle:
            return "番茄钟（空闲）\n下一步：开始专注"

        minutes = self._minutes_remaining(run)
        next_phase = self._engine.next_suggested_phase()
        next_name = _phase_label(next_phase)
        paused_suffix = "，已暂停" if self._engine.is_paused else ""
        return (
            f"番茄钟（{phase_name}{paused_suffix}）\n"
            f"剩余：{minutes} 分钟\n"
            f"下一阶段：{next_name}"
        )

    def _render_icon(self, *, minutes: int | None, phase: Phase, paused: bool) -> QIcon:
        bg = self._theme.idle_bg
        if phase == Phase.focus:
            bg = self._theme.focus_bg
        elif phase in (Phase.short_break, Phase.long_break):
            bg = self._theme.break_bg

        pixmap = QPixmap(self._icon_size, self._icon_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setBrush(bg)
        painter.setPen(QPen(self._theme.outline, max(2, self._icon_size // 32)))
        pad = max(4, self._icon_size // 16)
        painter.drawRoundedRect(pad, pad, self._icon_size - pad * 2, self._icon_size - pad * 2, pad * 2, pad * 2)

        if minutes is not None:
            text = "99+" if minutes >= 100 else str(minutes)
            font = QFont()
            font.setBold(True)
            font.setPixelSize(int(self._icon_size * 0.55))
            painter.setFont(font)
            painter.setPen(self._theme.text)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)

        if paused and phase != Phase.idle:
            self._draw_pause_badge(painter)

        painter.end()
        return QIcon(pixmap)

    def _draw_pause_badge(self, painter: QPainter) -> None:
        # top-right badge with "||"
        size = self._icon_size
        pad = max(6, size // 18)
        badge = max(26, size // 4)
        x = size - pad - badge
        y = pad

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor(0, 0, 0, 160))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(x, y, badge, badge, badge * 0.25, badge * 0.25)

        bar_w = max(3, badge // 7)
        bar_h = int(badge * 0.55)
        gap = max(3, bar_w)
        left = x + (badge - (bar_w * 2 + gap)) // 2
        top = y + (badge - bar_h) // 2
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(left, top, bar_w, bar_h, bar_w / 2, bar_w / 2)
        painter.drawRoundedRect(left + bar_w + gap, top, bar_w, bar_h, bar_w / 2, bar_w / 2)
        painter.restore()

    def _sync_pause_action(self) -> None:
        if self._engine.phase == Phase.idle:
            self._act_pause.setText("暂停")
            self._act_pause.setEnabled(False)
            return
        if self._engine.is_paused:
            self._act_pause.setText("继续")
            self._act_pause.setEnabled(True)
            return
        self._act_pause.setText("暂停")
        self._act_pause.setEnabled(True)

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return
        self._on_left_click()

    def _on_left_click(self) -> None:
        if self._engine.phase != Phase.idle:
            self._engine.toggle_pause()
            return
        if self._engine.pending_phase is not None:
            self._engine.start_pending()
            return
        self._engine.start_focus()

    @Slot(object)
    def _on_tick(self, _run: PhaseRun) -> None:
        self._refresh(force=False)

    @Slot(object)
    def _on_phase_changed(self, _run: PhaseRun) -> None:
        self._refresh(force=True)

    @Slot(object)
    def _on_phase_finished(self, _finished: PhaseFinished) -> None:
        self._refresh(force=True)

    @Slot(bool)
    def _on_paused_changed(self, _paused: bool) -> None:
        self._refresh(force=True)

    @Slot()
    def _on_stopped(self) -> None:
        self._refresh(force=True)

