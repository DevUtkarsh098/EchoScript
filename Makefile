.PHONY: setup dev test lint build smoke down monitor monitor-down

setup:
	docker compose build

dev:
	docker compose up --build

test:
	docker compose run --rm ingest-service pytest -q
	docker compose run --rm frontend npm test -- --run

lint:
	docker compose run --rm ingest-service ruff check app tests
	docker compose run --rm frontend npm run lint

build:
	docker compose build

smoke:
	powershell -ExecutionPolicy Bypass -File scripts/smoke-test.ps1

down:
	docker compose down


monitor:
	docker compose --profile monitoring up --build

monitor-down:
	docker compose --profile monitoring down
