from __future__ import annotations

from dataclasses import dataclass

from .timer_engine import Phase, PhaseFinished

CSV_HEADER = ["日期", "集中精力", "短暂休息", "长休息", "开始时间", "结束时间"]


@dataclass(frozen=True, slots=True)
class SessionRecord:
    date: str  # YYYY-MM-DD
    focus_minutes: int | None
    short_break_minutes: int | None
    long_break_minutes: int | None
    start_time: str  # YYYY-MM-DD HH:MM:SS
    end_time: str  # YYYY-MM-DD HH:MM:SS

    @staticmethod
    def from_phase_finished(finished: PhaseFinished) -> SessionRecord:
        date = finished.started_at.date().isoformat()
        start_time = finished.started_at.strftime("%Y-%m-%d %H:%M:%S")
        end_time = finished.finished_at.strftime("%Y-%m-%d %H:%M:%S")

        focus = short_b = long_b = None
        if finished.phase == Phase.focus:
            focus = finished.planned_minutes
        elif finished.phase == Phase.short_break:
            short_b = finished.planned_minutes
        elif finished.phase == Phase.long_break:
            long_b = finished.planned_minutes

        return SessionRecord(
            date=date,
            focus_minutes=focus,
            short_break_minutes=short_b,
            long_break_minutes=long_b,
            start_time=start_time,
            end_time=end_time,
        )

    def to_csv_row(self) -> dict[str, str]:
        def v(x: int | None) -> str:
            return "" if x is None else str(x)

        return {
            "日期": self.date,
            "集中精力": v(self.focus_minutes),
            "短暂休息": v(self.short_break_minutes),
            "长休息": v(self.long_break_minutes),
            "开始时间": self.start_time,
            "结束时间": self.end_time,
        }

    @staticmethod
    def from_csv_row(row: dict[str, str]) -> SessionRecord:
        def parse_int(x: str) -> int | None:
            x = (x or "").strip()
            if not x:
                return None
            return int(x)

        return SessionRecord(
            date=(row.get("日期") or "").strip(),
            focus_minutes=parse_int(row.get("集中精力") or ""),
            short_break_minutes=parse_int(row.get("短暂休息") or ""),
            long_break_minutes=parse_int(row.get("长休息") or ""),
            start_time=(row.get("开始时间") or "").strip(),
            end_time=(row.get("结束时间") or "").strip(),
        )



