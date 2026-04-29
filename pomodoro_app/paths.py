from __future__ import annotations

import configparser
import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def app_name() -> str:
    return "pomodoro-tray-timer"


def _xdg_data_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / app_name()
    return Path.home() / ".local" / "share" / app_name()


def _macos_app_support_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / app_name()


def _dir_has_user_files(p: Path) -> bool:
    if not p.exists() or not p.is_dir():
        return False
    for child in p.iterdir():
        if child.name.startswith("."):
            continue
        return True
    return False


def _safe_copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in {".DS_Store"}:
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _looks_like_pomodoro_data_dir(p: Path) -> bool:
    if not p.exists() or not p.is_dir():
        return False
    expected = {"settings.ini", "config.json", "history.csv"}
    try:
        names = {c.name for c in p.iterdir() if c.is_file()}
    except Exception:
        logger.warning("failed to list directory %s", p)
        return False
    return bool(names & expected)


def _try_one_time_migrate_legacy_dirs(dst: Path) -> None:
    marker = dst / ".migrated_from_legacy"
    if marker.exists():
        return
    if _dir_has_user_files(dst):
        return

    sources: list[Path] = []
    xdg = _xdg_data_dir()
    if xdg != dst:
        sources.append(xdg)

    legacy = legacy_data_dir()
    legacy_abs = legacy if legacy.is_absolute() else legacy.resolve()
    if _looks_like_pomodoro_data_dir(legacy_abs):
        sources.append(legacy_abs)

    migrated_from: Path | None = None
    for src in sources:
        if not _dir_has_user_files(src):
            continue
        try:
            _safe_copy_tree(src, dst)
            migrated_from = src
            break
        except Exception:
            logger.warning("failed to migrate data from %s to %s", src, dst)
            continue

    if migrated_from is not None:
        try:
            dst.mkdir(parents=True, exist_ok=True)
            marker.write_text(str(migrated_from), encoding="utf-8")
        except Exception:
            logger.warning("failed to write migration marker in %s", dst)


def app_root_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / app_name()
        return Path.home() / "AppData" / "Roaming" / app_name()

    if sys.platform == "darwin":
        dst = _macos_app_support_dir()
        _try_one_time_migrate_legacy_dirs(dst)
        return dst

    return _xdg_data_dir()


def settings_ini_path() -> Path:
    return app_root_dir() / "settings.ini"


def data_dir() -> Path:
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
            logger.warning("failed to parse settings.ini for DataDir")

    return app_root_dir()


def default_config_path() -> Path:
    return data_dir() / "config.json"


def default_history_path() -> Path:
    return data_dir() / "history.csv"


def legacy_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def legacy_config_path() -> Path:
    return legacy_data_dir() / "config.json"


def legacy_history_path() -> Path:
    return legacy_data_dir() / "history.csv"
