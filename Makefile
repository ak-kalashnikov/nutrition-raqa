.PHONY: help install test lint format clean docker run dev

help:  ## Show this help message
	@echo "Nutrition RAQA - Makefile Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies in virtual environment
	python -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -r requirements.txt

install-dev:  ## Install development dependencies
	. .venv/bin/activate && pip install pytest pytest-cov ruff black isort

test:  ## Run tests with coverage
	. .venv/bin/activate && pytest tests/ -v --cov=app --cov-report=term --cov-report=html

lint:  ## Run linting checks
	. .venv/bin/activate && ruff check app/ tests/

format:  ## Format code with black and isort
	. .venv/bin/activate && black app/ tests/
	. .venv/bin/activate && isort app/ tests/

clean:  ## Clean cache and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/ .coverage htmlcov/

docker-build:  ## Build Docker image
	docker build -t nutrition-raqa:latest .

docker-run:  ## Run Docker container
	docker-compose up -d

docker-stop:  ## Stop Docker containers
	docker-compose down

docker-logs:  ## Show Docker logs
	docker-compose logs -f

dev:  ## Run development server
	. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

build-db:  ## Build  RAG database from sources
	. .venv/bin/activate && python build_rag_database.py

demo:  ## Run Streamlit demo UI
	. .venv/bin/activate && streamlit run demo.py --server.port 8501
