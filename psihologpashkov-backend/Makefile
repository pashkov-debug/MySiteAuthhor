.PHONY: install lint format test check run docker-build docker-up docker-down docker-logs migrate

install:
	python -m pip install --upgrade pip
	pip install -e ".[dev]"

lint:
	ruff check backend

format:
	ruff check backend --fix
	ruff format backend

test:
	pytest

check:
	ruff check backend
	ruff format --check backend
	pytest

run:
	python -m uvicorn app.main:app --reload --app-dir backend

docker-build:
	docker build -t psihologpashkov-api:local .

docker-up:
	docker compose -f infra/compose.full.local.yml up -d --build

docker-down:
	docker compose -f infra/compose.full.local.yml down

docker-logs:
	docker compose -f infra/compose.full.local.yml logs -f api

migrate:
	alembic upgrade head