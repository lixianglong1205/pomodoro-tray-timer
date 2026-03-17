from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .models import CSV_HEADER, SessionRecord
from .paths import default_history_path, legacy_history_path


@dataclass(frozen=True, slots=True)
class DailyStats:
    date: str
    focus_count: int
    focus_minutes: int


class CsvStorage:
    def __init__(self, csv_path: str | Path | None = None) -> None:
        self._path = Path(csv_path) if csv_path is not None else default_history_path()

    @property
    def path(self) -> Path:
        return self._path

    def _migrate_legacy_if_needed(self) -> None:
        legacy = legacy_history_path()
        if self._path.exists() or not legacy.exists():
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._path.write_bytes(legacy.read_bytes())
        except Exception:
            return

    def ensure_ready(self) -> None:
        self._migrate_legacy_if_needed()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            with self._path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)

    def append(self, record: SessionRecord) -> None:
        self.ensure_ready()
        with self._path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writerow(record.to_csv_row())

    def read_all(self) -> list[SessionRecord]:
        if not self._path.exists():
            return []

        records: list[SessionRecord] = []
        with self._path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    record = SessionRecord.from_csv_row(row)  # type: ignore[arg-type]
                    if not record.date or not record.start_time or not record.end_time:
                        continue
                    records.append(record)
                except Exception:
                    continue

        def sort_key(r: SessionRecord) -> str:
            return r.start_time

        records.sort(key=sort_key, reverse=True)
        return records

    def aggregate_daily(self, records: list[SessionRecord] | None = None) -> list[DailyStats]:
        rows = records if records is not None else self.read_all()
        by_date: dict[str, DailyStats] = {}
        for r in rows:
            cur = by_date.get(r.date)
            focus_minutes = r.focus_minutes or 0
            focus_count = 1 if r.focus_minutes is not None else 0
            if cur is None:
                by_date[r.date] = DailyStats(
                    date=r.date,
                    focus_count=focus_count,
                    focus_minutes=focus_minutes,
                )
            else:
                by_date[r.date] = DailyStats(
                    date=cur.date,
                    focus_count=cur.focus_count + focus_count,
                    focus_minutes=cur.focus_minutes + focus_minutes,
                )

        stats = list(by_date.values())
        stats.sort(key=lambda s: s.date, reverse=True)
        return stats

