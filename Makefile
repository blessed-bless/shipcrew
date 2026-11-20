.PHONY: run test lint fmt format

run:
	powershell -File scripts/dev.ps1

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

fmt format:
	cd backend && ruff format app tests && ruff check --fix app tests
