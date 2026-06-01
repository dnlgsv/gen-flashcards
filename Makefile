.PHONY: run dev backend frontend test lint fmt typecheck check install

## Start the local browser app
run:
	uv run anki-cards

## Start backend + frontend together for frontend development
dev:
	uv run uvicorn src.api.run:app --host 0.0.0.0 --port 8000 --reload & cd frontend && npm run dev

## Start the FastAPI backend only
backend:
	uv run uvicorn src.api.run:app --host 0.0.0.0 --port 8000 --reload

## Start the Next.js frontend only
frontend:
	cd frontend && npm run dev

## Run the test suite
test:
	uv run pytest tests/ -v --no-cov

## Run tests with coverage report
test-cov:
	uv run pytest tests/ --cov=src --cov-report=term-missing

## Lint with ruff
lint:
	uv run ruff check src/ tests/

## Auto-fix lint issues
fmt:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

## Type-check with ty
typecheck:
	uv run ty check src/

## Run lint + type checks + tests
check: lint typecheck test

## Install / sync dependencies
install:
	uv sync
