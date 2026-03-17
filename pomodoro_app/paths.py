from __future__ import annotations

import configparser
import os
import sys
from pathlib import Path


def app_name() -> str:
    return "pomodoro-tray-timer"


def app_root_dir() -> Path:
    """
    应用“根”可写目录（用于 settings.ini、默认数据目录等）。

    - Windows: %APPDATA%\\pomodoro-tray-timer
    - 其他平台: ~/.local/share/pomodoro-tray-timer（尽量遵循 XDG）
    """

    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / app_name()
        # 兜底：极少数环境可能没有 APPDATA
        return Path.home() / "AppData" / "Roaming" / app_name()

    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / app_name()
    return Path.home() / ".local" / "share" / app_name()


def settings_ini_path() -> Path:
    return app_root_dir() / "settings.ini"


def data_dir() -> Path:
    """
    运行时数据目录（用于 config/history 等）。

    Windows 安装包版本可通过 `%APPDATA%\\pomodoro-tray-timer\\settings.ini` 配置：
    - [app]
      DataDir=C:\\...\\somewhere
    """

    cfg_path = settings_ini_path()
    if cfg_path.exists():
        parser = configparser.ConfigParser()
        try:
            parser.read(cfg_path, encoding="utf-8")
            raw = parser.get("app", "DataDir", fallback="").strip()
            if raw:
                expanded = os.path.expandvars(raw)
                p = Path(expanded).expanduser()
                return p
        except Exception:
            pass

    return app_root_dir()


def default_config_path() -> Path:
    return data_dir() / "config.json"


def default_history_path() -> Path:
    return data_dir() / "history.csv"


def legacy_data_dir() -> Path:
    # 兼容旧版本相对路径 data/
    return Path("data")


def legacy_config_path() -> Path:
    return legacy_data_dir() / "config.json"


def legacy_history_path() -> Path:
    return legacy_data_dir() / "history.csv"

