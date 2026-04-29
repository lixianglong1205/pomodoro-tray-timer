.PHONY: run install lint

run:
	uv run python main.py

install:
	uv sync

lint:
	uv run python -m compileall pomodoro_app main.py
	uv run ruff check pomodoro_app main.py scripts/
	uv run mypy pomodoro_app main.py

