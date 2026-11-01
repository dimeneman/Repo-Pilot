.PHONY: help dev up down logs test lint clean seed ingest rebuild

help:
	@echo "RepoPilot — Makefile Commands"
	@echo "  make dev          Start development environment with hot reloading"
	@echo "  make up           Start production docker compose stack"
	@echo "  make down         Stop all running containers"
	@echo "  make logs         Tail docker compose logs"
	@echo "  make test         Run backend pytest test suite"
	@echo "  make lint         Run ruff/flake8 syntax check"
	@echo "  make seed         Seed sample repository data"
	@echo "  make ingest URL=  Ingest a repository from URL"
	@echo "  make rebuild      Rebuild vector indices"
	@echo "  make clean        Remove cache files and temp data"

dev:
	docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up --build

up:
	docker compose -f infra/docker-compose.yml up -d --build

down:
	docker compose -f infra/docker-compose.yml down

logs:
	docker compose -f infra/docker-compose.yml logs -f

test:
	cd backend && pytest -v tests/

lint:
	python3 -m py_compile backend/app/**/*.py

seed:
	python3 scripts/seed_demo_data.py

ingest:
	@if [ -z "$(URL)" ]; then echo "Error: specify URL=https://github.com/owner/repo"; exit 1; fi
	python3 scripts/ingest_repo.py --url $(URL)

rebuild:
	python3 scripts/rebuild_index.py --all

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf data/repos/* data/uploads/*

