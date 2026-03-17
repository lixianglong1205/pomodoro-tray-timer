from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .timer_engine import TimerConfig
from .paths import default_config_path, legacy_config_path


@dataclass(frozen=True, slots=True)
class AppConfig:
    focus_minutes: int
    short_break_minutes: int
    long_break_minutes: int
    long_break_every_focus: int

    @classmethod
    def from_timer_config(cls, config: TimerConfig) -> "AppConfig":
        return cls(
            focus_minutes=config.focus_minutes,
            short_break_minutes=config.short_break_minutes,
            long_break_minutes=config.long_break_minutes,
            long_break_every_focus=config.long_break_every_focus,
        )

    def to_timer_config(self) -> TimerConfig:
        cfg = TimerConfig(
            focus_minutes=self.focus_minutes,
            short_break_minutes=self.short_break_minutes,
            long_break_minutes=self.long_break_minutes,
            long_break_every_focus=self.long_break_every_focus,
        )
        cfg.validate()
        return cfg


def default_config() -> AppConfig:
    return AppConfig.from_timer_config(TimerConfig())


def config_path() -> Path:
    return default_config_path()


def _migrate_legacy_config_if_needed(target: Path) -> None:
    legacy = legacy_config_path()
    if target.exists() or not legacy.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        return


def load_config(path: Path | None = None) -> AppConfig:
    p = path or config_path()
    _migrate_legacy_config_if_needed(p)
    if not p.exists():
        return default_config()

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default_config()

    try:
        data = _coerce_dict(raw)
        defaults = default_config()
        cfg = AppConfig(
            focus_minutes=_as_pos_int(data.get("focus_minutes")),
            short_break_minutes=_as_pos_int(data.get("short_break_minutes")),
            long_break_minutes=_as_pos_int(data.get("long_break_minutes")),
            long_break_every_focus=_as_pos_int(data.get("long_break_every_focus", defaults.long_break_every_focus)),
        )
        cfg.to_timer_config()
        return cfg
    except Exception:
        return default_config()


def save_config(config: AppConfig, path: Path | None = None) -> None:
    p = path or config_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    # 校验：避免写入坏数据
    config.to_timer_config()

    payload = {
        "focus_minutes": config.focus_minutes,
        "short_break_minutes": config.short_break_minutes,
        "long_break_minutes": config.long_break_minutes,
        "long_break_every_focus": config.long_break_every_focus,
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _coerce_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise TypeError("config must be a dict")


def _as_pos_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("value must be int, not bool")
    if isinstance(value, int):
        v = value
    elif isinstance(value, str) and value.strip().isdigit():
        v = int(value.strip())
    else:
        raise ValueError(f"invalid int: {value!r}")
    if v <= 0:
        raise ValueError(f"value must be positive: {v!r}")
    return v
