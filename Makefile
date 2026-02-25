.PHONY: help install sync run dev test lint format mypy pre-commit docker-up docker-down logs clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make install        Install dependencies"
	@echo "  make sync           Sync dependencies with lockfile"
	@echo "  make run            Run FastAPI app"
	@echo "  make dev            Run app in development mode"
	@echo "  make lint           Run linter"
	@echo "  make format         Format code"
	@echo "  make mypy           Run type checking with mypy"
	@echo "  make pre-commit     Run pre-commit hooks"
	@echo "  make clean          Clean cache files"

install:
	uv sync

sync:
	uv lock

run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 

dev:
	uv run uvicorn app.main:app --reload

lint:
	uv run ruff check

format:
	uv run ruff format

mypy:
	uv run mypy app

pre-commit:
	uv run pre-commit run --all-files

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache