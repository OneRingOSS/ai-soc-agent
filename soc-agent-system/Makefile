# ============================================================================
# SOC Agent System - Makefile
# ============================================================================
# 
# Available targets:
#   Quality Gates:
#     make lint          - Run ruff linter on backend code
#     make test          - Run pytest with coverage (requires 80%+ coverage)
#     make scan-secrets  - Scan for secrets using TruffleHog
#     make scan-image    - Scan Docker images for vulnerabilities using Trivy
#     make quality-gate  - Run all quality gates (lint, test, scan-secrets, scan-image)
#
#   Docker Operations:
#     make build         - Build Docker images for backend and frontend
#     make up            - Start services with docker-compose
#     make down          - Stop and remove containers
#     make clean         - Stop containers, remove images, and prune
#
#   Demo:
#     make demo          - Build, start, and open demo in browser
#
#   Utilities:
#     make help          - Show this help message
#
# Requirements:
#   - ruff (Python linter): pip install ruff
#   - pytest (Testing): pip install pytest pytest-cov
#   - trufflehog (Secret scanning): brew install trufflehog
#   - trivy (Image scanning): brew install trivy
#   - docker & docker-compose
#   - jq (JSON processor): brew install jq
#   - curl
#
# ============================================================================

.PHONY: help lint test test-integration scan-secrets scan-image validate-lockfile quality-gate build up down clean demo all

# Default target
help:
	@echo "SOC Agent System - Available Make Targets"
	@echo "=========================================="
	@echo ""
	@echo "Quality Gates:"
	@echo "  make lint             - Run ruff linter on backend code"
	@echo "  make test             - Run unit tests with coverage (55%+ required)"
	@echo "  make test-integration - Run integration tests (requires Redis)"
	@echo "  make scan-secrets     - Scan for secrets using TruffleHog"
	@echo "  make scan-image       - Scan Docker images using Trivy"
	@echo "  make quality-gate     - Run all quality gates (unit tests only)"
	@echo ""
	@echo "Docker Operations:"
	@echo "  make build         - Build Docker images"
	@echo "  make up            - Start services"
	@echo "  make down          - Stop services"
	@echo "  make clean         - Clean up everything"
	@echo ""
	@echo "Demo:"
	@echo "  make demo          - Build, start, and open demo"
	@echo ""

# ============================================================================
# Quality Gates
# ============================================================================

lint:
	@echo "🔍 Running ruff linter..."
	@cd backend && ruff check src/ --output-format=concise
	@echo "✅ Linting passed"

test:
	@echo "🧪 Running unit tests with coverage..."
	@cd backend && pytest tests/test_agents.py tests/test_coordinator.py tests/test_threat_generator.py \
		-v --cov=src --cov-report=term-missing --cov-fail-under=55 -m "not integration"
	@echo "✅ Unit tests passed with 55%+ coverage"

test-integration:
	@echo "🧪 Running integration tests (requires Redis)..."
	@cd backend && bash tests/integration/run_integration_tests.sh

scan-secrets:
	@echo "🔐 Scanning for secrets..."
	@trufflehog filesystem . --only-verified --fail --exclude-paths=.trufflehog-exclude.txt || \
		(echo "⚠️  Secrets found! Check output above." && exit 1)
	@echo "✅ No secrets found"

scan-image:
	@echo "🐳 Scanning Docker images for vulnerabilities..."
	@echo "Scanning backend image..."
	@trivy image soc-backend:latest --severity CRITICAL --exit-code 1
	@echo "Scanning frontend image..."
	@trivy image soc-frontend:latest --severity CRITICAL --exit-code 1
	@echo "✅ No critical vulnerabilities found"

validate-lockfile: ## Verify package-lock.json is consistent
	@echo "📦 Validating frontend lockfile..."
	@cd frontend && npm ci --ignore-scripts --dry-run
	@echo "✅ Lockfile valid"

quality-gate: lint test scan-secrets scan-image
	@echo ""
	@echo "✅ ============================================"
	@echo "✅  ALL QUALITY GATES PASSED"
	@echo "✅ ============================================"
	@echo ""

# ============================================================================
# Docker Operations
# ============================================================================

build:
	@echo "🔨 Building Docker images..."
	@cd backend && docker build -t soc-backend:latest .
	@cd frontend && docker build -t soc-frontend:latest .
	@echo "✅ Docker images built"

up:
	@echo "🚀 Starting services..."
	@docker-compose -f observability/docker-compose.yml up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 10
	@echo "✅ Services started"

down:
	@echo "🛑 Stopping services..."
	@docker-compose -f observability/docker-compose.yml down -v
	@echo "✅ Services stopped"

clean: down
	@echo "🧹 Cleaning up Docker resources..."
	@docker rmi -f soc-backend:latest soc-frontend:latest 2>/dev/null || true
	@docker system prune -f
	@echo "✅ Cleanup complete"

# ============================================================================
# Demo
# ============================================================================

demo: build up
	@echo "🎬 Opening demo in browser..."
	@sleep 5
	@echo "⏳ Waiting for backend health check..."
	@until curl -s http://localhost:8000/health | jq -e '.status == "healthy"' > /dev/null 2>&1; do \
		echo "Waiting for backend..."; \
		sleep 2; \
	done
	@echo "✅ Backend is healthy"
	@echo "🌐 Opening browser tabs..."
	@open http://localhost:3000 || xdg-open http://localhost:3000 || echo "Please open http://localhost:3000"
	@open http://localhost:3001 || xdg-open http://localhost:3001 || echo "Please open http://localhost:3001 (Grafana)"
	@open http://localhost:16686 || xdg-open http://localhost:16686 || echo "Please open http://localhost:16686 (Jaeger)"
	@echo "✅ Demo ready!"

# ============================================================================
# Convenience
# ============================================================================

all: quality-gate
	@echo "✅ All targets completed successfully"

