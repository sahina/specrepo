# SpecRepo Makefile
# Comprehensive task automation for development, testing, and deployment

.PHONY: help install dev build test lint clean docker-up docker-down docker-logs docker-clean setup-env migrate db-reset

# Default target
help: ## Show this help message
	@echo "SpecRepo Development Commands"
	@echo "============================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Environment Setup
# =============================================================================

install: ## Install all dependencies (frontend and backend)
	@echo "Installing frontend dependencies..."
	cd frontend && pnpm install
	@echo "Setting up backend virtual environment and dependencies..."
	cd backend && uv venv .venv && uv sync
	@echo "All dependencies installed successfully!"

install-backend: ## Install only backend dependencies
	cd backend && uv venv .venv && uv sync

install-frontend: ## Install only frontend dependencies
	cd frontend && pnpm install

sync: ## Sync all dependencies to latest compatible versions
	@echo "Syncing backend dependencies..."
	cd backend && uv sync
	@echo "Syncing frontend dependencies..."
	cd frontend && pnpm install
	@echo "All dependencies synced!"

add-dep: ## Add a new backend dependency (usage: make add-dep PACKAGE=fastapi)
	cd backend && uv add $(PACKAGE)

add-dev-dep: ## Add a new backend dev dependency (usage: make add-dev-dep PACKAGE=pytest)
	cd backend && uv add --dev $(PACKAGE)

remove-dep: ## Remove a backend dependency (usage: make remove-dep PACKAGE=fastapi)
	cd backend && uv remove $(PACKAGE)

update-deps: ## Update all backend dependencies to latest versions
	cd backend && uv sync --upgrade

lock: ## Update lock files for both frontend and backend
	cd backend && uv lock
	cd frontend && pnpm install --lockfile-only

configure-ide: ## Show IDE configuration instructions for Python interpreter
	cd backend && uv run --active python configure_ide.py

setup-env: ## Setup environment files from examples
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "Please edit .env with your configuration"; \
	else \
		echo ".env already exists"; \
	fi

# =============================================================================
# Development
# =============================================================================

dev-setup: ## Setup development environment (install deps, start db, migrate, seed)
	@echo "🔧 Setting up SpecRepo development environment..."
	@echo "Installing dependencies..."
	@$(MAKE) install
	@echo "Starting database..."
	@$(MAKE) postgres-up
	@echo "Waiting for database to be ready..."
	@sleep 5
	@echo "Running migrations..."
	@$(MAKE) migrate
	@echo "Seeding database with test data..."
	@$(MAKE) seed-data
	@echo ""
	@echo "✅ Development environment is ready!"
	@echo "Run 'make dev' to start the development servers"

dev-full: ## Start full development stack (all services: frontend, backend, postgres, n8n, wiremock)
	@echo "🚀 Starting full SpecRepo development stack..."
	@echo "Starting all services with Docker Compose..."
	@$(MAKE) docker-up
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Running migrations..."
	@$(MAKE) migrate
	@echo "Seeding database with test data..."
	@$(MAKE) seed-data
	@echo ""
	@echo "🌟 Full development stack is running!"
	@echo "Frontend: http://localhost:5173"
	@echo "Backend: http://localhost:8000"
	@echo "API Documentation: http://localhost:8000/docs"
	@echo "N8N: http://localhost:5679"
	@echo "WireMock: http://localhost:8081"
	@echo "PostgreSQL: localhost:5432"
	@echo ""
	@echo "Test API Keys:"
	@echo "  Admin: admin-dev-key-12345678901234567890"
	@echo "  Developer: dev-test-key-12345678901234567890"
	@echo "  Tester: test-api-key-12345678901234567890"
	@echo ""
	@echo "Use 'make docker-logs' to view logs"
	@echo "Use 'make docker-down' to stop all services"

dev: ## Start development servers (frontend and backend)
	@echo "🚀 Starting SpecRepo development environment..."
	@echo "Ensuring database is running..."
	@$(MAKE) postgres-up
	@echo "Waiting for database to be ready..."
	@sleep 3
	@echo "Running migrations..."
	@$(MAKE) migrate
	@echo "Seeding database with test data..."
	@$(MAKE) seed-data
	@echo ""
	@echo "🌟 Starting development servers..."
	@echo "Frontend will be available at http://localhost:5173"
	@echo "Backend will be available at http://localhost:8000"
	@echo "API Documentation at http://localhost:8000/docs"
	@echo ""
	@echo "Test API Keys:"
	@echo "  Admin: admin-dev-key-12345678901234567890"
	@echo "  Developer: dev-test-key-12345678901234567890"
	@echo "  Tester: test-api-key-12345678901234567890"
	@echo ""
	@echo "Press Ctrl+C to stop both servers"
	@trap 'kill %1 %2' INT; \
	cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && pnpm dev & \
	wait

dev-frontend: ## Start only frontend development server
	cd frontend && pnpm dev

dev-backend: ## Start only backend development server
	cd backend && uv run --active uvicorn main:app --reload --host 0.0.0.0 --port 8000

# =============================================================================
# Building
# =============================================================================

build: ## Build frontend and backend for production
	@echo "Building frontend..."
	cd frontend && pnpm build
	@echo "Frontend build complete!"

build-frontend: ## Build only frontend
	cd frontend && pnpm build

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests (backend and frontend)
	@echo "Running backend tests..."
	$(MAKE) test-backend
	@echo "Running frontend tests..."
	$(MAKE) test-frontend

test-backend: ## Run backend tests with pytest
	cd backend && uv run --active pytest -v

test-frontend: ## Run frontend tests with Jest
	cd frontend && pnpm test

test-backend-coverage: ## Run backend tests with coverage report
	cd backend && uv run --active pytest --cov=app --cov-report=html --cov-report=term-missing -v

test-frontend-watch: ## Run frontend tests in watch mode
	cd frontend && pnpm test:watch

test-watch: ## Run backend tests in watch mode
	cd backend && uv run --active pytest-watch

# =============================================================================
# Linting and Code Quality
# =============================================================================

lint: ## Run linting for both frontend and backend
	$(MAKE) lint-backend
	$(MAKE) lint-frontend

lint-backend: ## Run backend linting with ruff
	cd backend && uv run --active ruff check .

lint-backend-fix: ## Run backend linting with auto-fix
	cd backend && uv run --active ruff check . --fix

format-backend: ## Format backend code with ruff
	cd backend && uv run --active ruff format .

lint-frontend: ## Run frontend linting with eslint
	cd frontend && pnpm lint

lint-frontend-fix: ## Run frontend linting with auto-fix
	cd frontend && pnpm lint --fix

format-frontend: ## Format frontend code with prettier
	cd frontend && pnpm prettier --write .

# =============================================================================
# Database Operations
# =============================================================================

migrate: ## Run database migrations
	cd backend && uv run --active alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="description")
	cd backend && uv run --active alembic revision --autogenerate -m "$(MESSAGE)"

migrate-downgrade: ## Downgrade database by one migration
	cd backend && uv run --active alembic downgrade -1

migrate-history: ## Show migration history
	cd backend && uv run --active alembic history

seed-data: ## Seed database with test users and sample data for development
	@echo "Seeding database with test data..."
	cd backend && uv run --active python seed_data.py

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "WARNING: This will destroy all database data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker-compose down postgres
	docker volume rm specrepo_postgres_data || true
	docker-compose up -d postgres
	sleep 5
	$(MAKE) migrate

db-reset-with-seed: ## Reset database and seed with test data
	$(MAKE) db-reset
	$(MAKE) seed-data

# =============================================================================
# Docker Operations
# =============================================================================

docker-up: ## Start all services with docker-compose
	docker-compose up -d

docker-up-build: ## Start all services with docker-compose and rebuild images
	docker-compose up -d --build

docker-down: ## Stop all docker-compose services
	docker-compose down

docker-down-volumes: ## Stop all services and remove volumes
	docker-compose down -v

docker-logs: ## Show logs for all services
	docker-compose logs -f

docker-logs-backend: ## Show logs for backend service
	docker-compose logs -f backend

docker-logs-frontend: ## Show logs for frontend service
	docker-compose logs -f frontend

docker-logs-postgres: ## Show logs for postgres service
	docker-compose logs -f postgres

docker-logs-n8n: ## Show logs for n8n service
	docker-compose logs -f n8n

docker-logs-wiremock: ## Show logs for wiremock service
	docker-compose logs -f wiremock

docker-restart: ## Restart all docker-compose services
	docker-compose restart

docker-restart-backend: ## Restart only backend service
	docker-compose restart backend

docker-restart-frontend: ## Restart only frontend service
	docker-compose restart frontend

docker-ps: ## Show status of all docker-compose services
	docker-compose ps

docker-clean: ## Clean up docker containers, networks, and images
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

# =============================================================================
# Individual Service Management
# =============================================================================

postgres-up: ## Start only postgres service
	docker-compose up -d postgres

postgres-down: ## Stop postgres service
	docker-compose stop postgres

postgres-shell: ## Connect to postgres shell
	docker-compose exec postgres psql -U user -d appdb

n8n-up: ## Start only n8n service
	docker-compose up -d n8n

n8n-down: ## Stop n8n service
	docker-compose stop n8n

wiremock-up: ## Start only wiremock service
	docker-compose up -d wiremock

wiremock-down: ## Stop wiremock service
	docker-compose stop wiremock

# =============================================================================
# Utility Commands
# =============================================================================

clean: ## Clean up build artifacts and caches
	@echo "Cleaning up build artifacts..."
	rm -rf frontend/dist
	rm -rf frontend/node_modules/.cache
	rm -rf backend/.pytest_cache
	rm -rf backend/__pycache__
	rm -rf backend/.ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete!"

reset: ## Full reset - clean, reinstall dependencies, rebuild
	$(MAKE) clean
	$(MAKE) docker-down-volumes
	$(MAKE) install
	$(MAKE) docker-up-build

health-check: ## Check health of all services
	@echo "Checking service health..."
	@echo "Frontend: http://localhost:5173"
	@curl -f http://localhost:5173 >/dev/null 2>&1 && echo "✅ Frontend is healthy" || echo "❌ Frontend is not responding"
	@echo "Backend: http://localhost:8000/health"
	@curl -f http://localhost:8000/health >/dev/null 2>&1 && echo "✅ Backend is healthy" || echo "❌ Backend is not responding"
	@echo "Postgres: localhost:5432"
	@docker-compose exec -T postgres pg_isready -U user -d appdb >/dev/null 2>&1 && echo "✅ Postgres is healthy" || echo "❌ Postgres is not responding"
	@echo "N8N: http://localhost:5679"
	@curl -f http://localhost:5679 >/dev/null 2>&1 && echo "✅ N8N is healthy" || echo "❌ N8N is not responding"
	@echo "Wiremock: http://localhost:8081/__admin/"
	@curl -f http://localhost:8081/__admin/ >/dev/null 2>&1 && echo "✅ Wiremock is healthy" || echo "❌ Wiremock is not responding"

# =============================================================================
# CI/CD and Production
# =============================================================================

ci-test: ## Run tests suitable for CI environment
	$(MAKE) lint
	$(MAKE) test-backend-coverage

ci-build: ## Build for CI environment
	$(MAKE) build

deploy-staging: ## Deploy to staging environment
	@echo "Deploying to staging..."
	$(MAKE) ci-test
	$(MAKE) ci-build
	# Add your staging deployment commands here

deploy-production: ## Deploy to production environment
	@echo "Deploying to production..."
	@echo "WARNING: This will deploy to production!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	$(MAKE) ci-test
	$(MAKE) ci-build
	# Add your production deployment commands here

# =============================================================================
# Task Master Integration
# =============================================================================

tasks: ## Show current tasks from Task Master
	task-master list

next-task: ## Show next task to work on
	task-master next

task-status: ## Update task status (usage: make task-status ID=1 STATUS=done)
	task-master set-status --id=$(ID) --status=$(STATUS)

# =============================================================================
# Quick Start Commands
# =============================================================================

first-run: ## First time setup - install dependencies and start services
	@echo "Setting up SpecRepo for first time..."
	$(MAKE) setup-env
	$(MAKE) install
	$(MAKE) docker-up
	@echo "Waiting for services to start..."
	sleep 10
	$(MAKE) migrate
	@echo ""
	@echo "🎉 SpecRepo is ready!"
	@echo "Frontend: http://localhost:5173"
	@echo "Backend: http://localhost:8000"
	@echo "N8N: http://localhost:5679"
	@echo "Wiremock: http://localhost:8081"
	@echo ""
	@echo "Run 'make dev' to start development servers"

quick-start: ## Quick start for development (assumes setup is done)
	$(MAKE) docker-up
	sleep 5
	$(MAKE) dev
