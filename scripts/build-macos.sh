#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:-dist}"
APP_NAME="${APP_NAME:-pomodoro-tray-timer}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="${2:?missing value for --output-dir}"
      shift 2
      ;;
    --app-name)
      APP_NAME="${2:?missing value for --app-name}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if ! command -v uv >/dev/null 2>&1; then
  echo "Command not found: uv. Please install uv and ensure it is in PATH." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

uv sync --all-groups

uv run python -m nuitka \
  main.py \
  --standalone \
  --enable-plugins=pyside6 \
  --assume-yes-for-downloads \
  --disable-console \
  --macos-create-app-bundle \
  --macos-app-icon="assets/icon-red-tomato.icns" \
  --output-dir="$OUTPUT_DIR" \
  --output-filename="$APP_NAME"

TARGET_APP="$OUTPUT_DIR/$APP_NAME.app"

if [[ ! -d "$TARGET_APP" ]]; then
  shopt -s nullglob
  apps=("$OUTPUT_DIR"/*.app)
  shopt -u nullglob

  if [[ ${#apps[@]} -eq 0 ]]; then
    echo "No .app bundle found in: $OUTPUT_DIR" >&2
    exit 1
  fi

  rm -rf "$TARGET_APP"
  mv "${apps[0]}" "$TARGET_APP"
fi

echo "Build done: $TARGET_APP"

