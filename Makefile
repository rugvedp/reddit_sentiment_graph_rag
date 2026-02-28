.PHONY: help setup install dev dashboard cli lint format test clean

help:
	@echo "Sentiment Dashboard - Local Development Commands"
	@echo ""
	@echo "Setup & Install:"
	@echo "  make setup          Setup project with uv (create venv + install deps)"
	@echo "  make install        Install/update dependencies with uv"
	@echo ""
	@echo "Run & Development:"
	@echo "  make dashboard      Start Streamlit dashboard"
	@echo "  make cli            Run CLI (brands listed in Makefile)"
	@echo "  make cli BRAND=nvidia  Run CLI with specific brand"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run linter (ruff)"
	@echo "  make format         Format code (black)"
	@echo "  make test           Run tests"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          Remove cache and build files"
	@echo "  make venv-clean     Remove virtual environment"

setup:
	@echo "Setting up project..."
	@bash setup.sh

install:
	@echo "Installing dependencies..."
	uv sync

dev:
	@echo "Installing with dev dependencies..."
	uv sync --all-extras

dashboard:
	@echo "Starting Streamlit dashboard..."
	@echo "Open: http://localhost:8501"
	uv run streamlit run main.py

cli:
	@echo "Running CLI ingestion for brand: $(BRAND)"
	uv run python cli_ingest.py "$(BRAND)"

examples:
	@echo "Running example ingestions..."
	uv run python cli_ingest.py "Apple"
	uv run python cli_ingest.py "Tesla"

lint:
	@echo "Running linter..."
	uv run ruff check .

format:
	@echo "Formatting code..."
	uv run black .

test:
	@echo "Running tests..."
	uv run pytest -v

clean:
	@echo "Cleaning cache files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage 2>/dev/null || true
	@echo "✓ Cleaned"

venv-clean:
	@echo "Removing virtual environment..."
	rm -rf .venv
	@echo "✓ Removed. Run 'make setup' to recreate."
