.PHONY: help install sync run dev test lint format mypy pre-commit docker-up docker-down docker-purge docker-build docker-logs docker-restart clean

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
	@echo "  make docker-up      Start all containers"
	@echo "  make docker-down    Stop all containers"
	@echo "  make docker-purge   Stop all containers and delete volumes"
	@echo "  make docker-build   Build Docker images"
	@echo "  make docker-logs    View container logs"
	@echo "  make docker-restart Restart all containers"
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
	uv run mypy

pre-commit:
	uv run pre-commit run --all-files

# Docker commands
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-purge:
	docker compose down -v

docker-build:
	docker compose build

docker-logs:
	docker compose logs -f

docker-restart:
	docker compose restart

clean:
	uv run python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__') if p.is_dir()]; [shutil.rmtree(d) for d in ['.pytest_cache', '.mypy_cache', '.ruff_cache'] if pathlib.Path(d).exists()]"