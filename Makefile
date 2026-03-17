.PHONY: run install lint

run:
	uv run python main.py

install:
	uv sync

lint:
	uv run python -m compileall pomodoro_app main.py

