from __future__ import annotations

import platform
from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, QRectF, Qt, QTimer, Slot
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .i18n import _
from .timer_engine import Phase, PhaseFinished, PhaseRun, TimerEngine


@dataclass(frozen=True, slots=True)
class TrayTheme:
    focus_bg: QColor = field(default_factory=lambda: QColor("#D7263D"))
    break_bg: QColor = field(default_factory=lambda: QColor("#2E8B57"))
    idle_bg: QColor = field(default_factory=lambda: QColor("#FFA631"))
    text: QColor = field(default_factory=lambda: QColor("#FFFFFF"))
    outline: QColor = field(default_factory=lambda: QColor("#111827"))


def _phase_label(phase: Phase) -> str:
    if phase == Phase.focus:
        return _("集中精力")
    if phase == Phase.short_break:
        return _("短暂休息")
    if phase == Phase.long_break:
        return _("长时间休息")
    return _("空闲")


def _suggest_label(phase: Phase) -> str:
    if phase == Phase.focus:
        return _("下一步：休息")
    if phase in (Phase.short_break, Phase.long_break):
        return _("下一步：开始专注")
    return _("下一步：开始专注")


class TrayController(QObject):
    def __init__(
        self,
        engine: TimerEngine,
        on_open_history: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_quit: Callable[[], None],
        *,
        parent: QObject | None = None,
        theme: TrayTheme | None = None,
        icon_size: int = 128,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._theme = theme or TrayTheme()
        self._icon_size = icon_size
        self._is_macos = platform.system().lower() == "darwin"
        self._on_open_history = on_open_history
        self._on_open_settings = on_open_settings
        self._on_quit = on_quit

        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip(_("番茄钟"))
        self._tray.setIcon(self._render_icon(minutes=None, phase=Phase.idle, paused=False))

        self._tray.activated.connect(self._on_tray_activated)

        self._install_menu(self._create_menu())

        self._last_drawn_minute: int | None = None
        self._last_phase: Phase = Phase.idle
        self._last_paused: bool = False

        self._engine.tick.connect(self._on_tick)
        self._engine.phase_changed.connect(self._on_phase_changed)
        self._engine.phase_finished.connect(self._on_phase_finished)
        self._engine.paused_changed.connect(self._on_paused_changed)
        self._engine.stopped.connect(self._on_stopped)
        self._engine.language_changed.connect(self._on_language_changed)

    def _create_menu(self) -> QMenu:
        menu = QMenu()

        self._menu = menu
        self._act_stop = QAction(_("终止时钟"), menu)
        self._act_pause = QAction(_("暂停"), menu)
        self._act_focus = QAction(_("开始集中精力"), menu)
        self._act_short = QAction(_("开始短暂休息"), menu)
        self._act_long = QAction(_("开始长时间休息"), menu)
        self._act_restart = QAction(_("重新开始番茄钟循环"), menu)
        self._act_history = QAction(_("打开历史记录"), menu)
        self._act_settings = QAction(_("设置..."), menu)
        self._act_quit = QAction(_("退出"), menu)

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

        self._act_stop.triggered.connect(self._engine.stop)
        self._act_pause.triggered.connect(self._engine.toggle_pause)
        self._act_focus.triggered.connect(self._engine.start_focus)
        self._act_short.triggered.connect(self._engine.start_short_break)
        self._act_long.triggered.connect(self._engine.start_long_break)
        self._act_restart.triggered.connect(self._engine.restart_cycle)
        self._act_history.triggered.connect(self._on_open_history)
        self._act_settings.triggered.connect(self._on_open_settings)
        self._act_quit.triggered.connect(self._on_quit)

        return menu

    def _install_menu(self, menu: QMenu) -> None:
        # macOS：不要绑定 setContextMenu。NSStatusItem 一旦绑定原生菜单，
        # 任意点击（包括左键）都会弹菜单，无法区分左右键。
        # 右键菜单在 _on_tray_activated 里手动 exec，并配合 AppKit 激活，
        # 才能在全屏/不同 Space 下稳定显示且不“闪桌面”。
        if self._is_macos:
            return
        self._tray.setContextMenu(menu)

    def show(self) -> None:
        if self._is_macos:
            # macOS Nuitka 打包后，事件循环尚未启动时调用 setIcon 可能不生效。
            # 先 show 托盘，再用 QTimer 推迟图标渲染到事件循环运行后。
            self._tray.show()
            QTimer.singleShot(0, lambda: self._refresh(force=True))
        else:
            self._tray.show()
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
            return f"{_('番茄钟')}（{_('空闲')}）\n{_('下一步：开始专注')}"

        minutes = self._minutes_remaining(run)
        next_phase = self._engine.next_suggested_phase()
        next_name = _phase_label(next_phase)
        paused_suffix = _("，已暂停") if self._engine.is_paused else ""
        return (
            f"{_('番茄钟')}（{phase_name}{paused_suffix}）\n"
            f"{_('剩余')}：{minutes} {_('分钟')}\n"
            f"{_('下一阶段')}：{next_name}"
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

        fruit_rect = self._draw_tomato(painter, fill=bg)

        if minutes is not None:
            text = "99+" if minutes >= 100 else str(minutes)
            font = QFont()
            font.setBold(True)
            font.setPixelSize(self._suggest_minutes_font_px(minutes))
            painter.setFont(font)
            painter.setPen(self._theme.text if phase != Phase.idle else self._theme.outline)
            painter.drawText(fruit_rect.toRect(), Qt.AlignmentFlag.AlignCenter, text)

        if paused and phase != Phase.idle:
            self._draw_pause_badge(painter)

        painter.end()
        icon = QIcon(pixmap)
        if self._is_macos:
            try:
                icon.setIsTemplate(False)  # type: ignore[attr-defined]  # macOS only
            except AttributeError:
                pass
        return icon

    def _suggest_minutes_font_px(self, minutes: int) -> int:
        size = self._icon_size
        if minutes >= 100:
            scale = 0.40
        elif minutes >= 10:
            scale = 0.50
        else:
            scale = 0.56
        return max(9 if size <= 16 else 8, int(size * scale))

    def _draw_tomato(self, painter: QPainter, *, fill: QColor) -> QRectF:
        size = float(self._icon_size)
        stroke = float(max(1, int(round(size / 32))))
        pad = float(max(1, int(round(size / 14))))

        leaf_h = max(4.0, size * 0.20)
        leaf_w = max(7.0, size * 0.42)
        leaf_top = pad + stroke / 2

        fruit_left = pad + stroke / 2
        fruit_right = size - pad - stroke / 2
        fruit_top = leaf_top + leaf_h * 0.60
        fruit_bottom = size - pad - stroke / 2
        fruit_w = max(1.0, fruit_right - fruit_left)
        fruit_h = max(1.0, fruit_bottom - fruit_top)
        fruit_rect = QRectF(fruit_left, fruit_top, fruit_w, fruit_h)

        outline_pen = QPen(self._theme.outline, max(1.0, stroke))
        outline_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        outline_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setBrush(fill)
        painter.setPen(outline_pen)
        body_path = QPainterPath()
        body_path.addEllipse(fruit_rect)
        painter.drawPath(body_path)

        leaf_fill = QColor("#00BC12")
        leaf_pen = QPen(self._theme.outline, max(1.0, stroke * 0.85))
        leaf_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        leaf_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setBrush(leaf_fill)
        painter.setPen(leaf_pen)

        cx = size / 2
        crown_y = leaf_top + leaf_h * 0.85
        lobe_r = max(1.8, leaf_h * 0.26)
        painter.drawEllipse(QRectF(cx - leaf_w * 0.22 - lobe_r, crown_y - lobe_r, lobe_r * 2, lobe_r * 2))
        painter.drawEllipse(QRectF(cx - lobe_r, crown_y - lobe_r * 1.05, lobe_r * 2, lobe_r * 2))
        painter.drawEllipse(QRectF(cx + leaf_w * 0.22 - lobe_r, crown_y - lobe_r, lobe_r * 2, lobe_r * 2))

        stem_w = max(2.0, leaf_w * 0.12)
        stem_h = max(3.0, leaf_h * 0.40)
        stem_rect = QRectF(cx - stem_w / 2, leaf_top + leaf_h * 0.15, stem_w, stem_h)
        painter.drawRoundedRect(stem_rect, stem_w * 0.4, stem_w * 0.4)

        painter.restore()
        return fruit_rect

    def _draw_pause_badge(self, painter: QPainter) -> None:
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
            self._act_pause.setText(_("暂停"))
            self._act_pause.setEnabled(False)
            return
        if self._engine.is_paused:
            self._act_pause.setText(_("继续"))
            self._act_pause.setEnabled(True)
            return
        self._act_pause.setText(_("暂停"))
        self._act_pause.setEnabled(True)

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if self._is_macos and reason == QSystemTrayIcon.ActivationReason.Context:
            self._show_context_menu_macos()
            return
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._on_left_click()
            return

    def _show_context_menu_macos(self) -> None:
        menu = getattr(self, "_menu", None)
        if menu is None:
            return

        # 通过 PyObjC 静默激活当前进程，让 Qt 菜单出现在前台 App 之上。
        # 若进程为 Accessory policy（默认），该激活不会触发常规 App 切换动画。
        try:
            from AppKit import NSApplication  # type: ignore

            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass

        # activateIgnoringOtherApps_ 是异步的。若紧接着进入 menu.exec() 的嵌套事件循环，
        # 第一次点击可能被 macOS 当作“激活初始点击”吞掉，导致 QAction.triggered 不触发。
        try:
            QApplication.processEvents()
        except Exception:
            pass

        menu.exec(QCursor.pos())

    def _on_left_click(self) -> None:
        if self._engine.phase != Phase.idle:
            self._engine.toggle_pause()
            return
        if self._engine.pending_phase is not None:
            self._engine.start_pending()
            return
        self._engine.start_focus()

    def retranslate_ui(self) -> None:
        self._tray.setToolTip(_("番茄钟"))
        self._act_stop.setText(_("终止时钟"))
        self._act_pause.setText(_("暂停"))
        self._act_focus.setText(_("开始集中精力"))
        self._act_short.setText(_("开始短暂休息"))
        self._act_long.setText(_("开始长时间休息"))
        self._act_restart.setText(_("重新开始番茄钟循环"))
        self._act_history.setText(_("打开历史记录"))
        self._act_settings.setText(_("设置..."))
        self._act_quit.setText(_("退出"))
        self._sync_pause_action()
        self._refresh(force=True)

    @Slot(str)
    def _on_language_changed(self, _lang: str) -> None:
        self.retranslate_ui()

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
