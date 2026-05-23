.PHONY: help setup install dev serve queue-work migrate test clean deploy

# Variables
PYTHON_VENV := venv
PYTHON := $(PYTHON_VENV)/bin/python3
PIP := $(PYTHON_VENV)/bin/pip

help:
	@echo "ERT Station - Available Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup              - Complete setup (install, migrate, seed)"
	@echo "  make install            - Install PHP & Python dependencies"
	@echo "  make venv               - Create Python virtual environment"
	@echo ""
	@echo "Development:"
	@echo "  make dev                - Run Laravel dev server + queue worker"
	@echo "  make serve              - Start Laravel development server (port 8000)"
	@echo "  make queue-work         - Start queue worker for background jobs"
	@echo "  make tinker             - Start Laravel Tinker REPL"
	@echo ""
	@echo "Database:"
	@echo "  make migrate            - Run database migrations"
	@echo "  make seed               - Seed database with sample data"
	@echo "  make migrate-rollback   - Rollback last migration batch"
	@echo "  make db-reset           - Reset database (migrations + seed)"
	@echo ""
	@echo "Testing & Code Quality:"
	@echo "  make test               - Run PHPUnit tests"
	@echo "  make coverage           - Run tests with coverage report"
	@echo "  make lint               - Run code linting (Pint, PHPStan)"
	@echo "  make format             - Format code with Pint"
	@echo ""
	@echo "Python Emulator:"
	@echo "  make test-emulator      - Test Python emulator directly"
	@echo "  make emulator-scan      - Run a sample scan (requires DB setup)"
	@echo ""
	@echo "Production:"
	@echo "  make build              - Build production artifacts"
	@echo "  make deploy             - Deploy to production"
	@echo "  make cache-clear        - Clear all application caches"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean              - Remove temporary files & caches"
	@echo "  make logs               - Tail application logs"
	@echo "  make status             - Show system status"

# ============================================
# Setup & Installation
# ============================================

setup: install migrate seed
	@echo "✅ Setup complete! Run 'make dev' to start development."

install: composer-install venv pip-install
	@echo "✅ All dependencies installed"

composer-install:
	composer install

venv:
	python3 -m venv $(PYTHON_VENV)
	@echo "✅ Python virtual environment created"

pip-install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Python dependencies installed"

# ============================================
# Development
# ============================================

dev:
	@echo "🚀 Starting development environment..."
	@echo "   - Laravel Server: http://localhost:8000"
	@echo "   - Queue Worker: Running"
	@echo "   - Press Ctrl+C to stop"
	@(trap 'kill %1 %2' SIGINT; php artisan serve & php artisan queue:work)

serve:
	php artisan serve

queue-work:
	php artisan queue:work --tries=1 --timeout=3600 --verbose

tinker:
	php artisan tinker

# ============================================
# Database
# ============================================

migrate:
	php artisan migrate

seed:
	php artisan db:seed

migrate-rollback:
	php artisan migrate:rollback

db-reset:
	php artisan migrate:reset
	php artisan migrate
	php artisan db:seed
	@echo "✅ Database reset & seeded"

# ============================================
# Testing & Code Quality
# ============================================

test:
	php artisan test

coverage:
	php artisan test --coverage

lint:
	./vendor/bin/pint --test
	./vendor/bin/phpstan analyse

format:
	./vendor/bin/pint

# ============================================
# Python Emulator
# ============================================

test-emulator:
	@echo "Testing Python emulator..."
	$(PYTHON) emulator/matrix_scanner.py --scan_id=999 --spacing=1.0 2>&1 | head -20

emulator-scan:
	@echo "Running test scan (requires database)..."
	$(PYTHON) emulator/matrix_scanner.py --scan_id=1 --spacing=1.0

# ============================================
# Production
# ============================================

build: cache-clear
	php artisan config:cache
	php artisan route:cache
	php artisan view:cache
	@echo "✅ Production build complete"

deploy: build
	@echo "🚀 Deploying to production..."
	@echo "⚠️  Manual steps may be required (DNS, SSL, CDN, etc.)"

cache-clear:
	php artisan cache:clear
	php artisan config:clear
	php artisan route:clear
	php artisan view:clear
	@echo "✅ Caches cleared"

# ============================================
# Utilities
# ============================================

clean:
	rm -rf bootstrap/cache/*
	rm -f storage/logs/*.log
	rm -rf node_modules
	@echo "✅ Temporary files cleaned"

logs:
	tail -f storage/logs/laravel.log

status:
	@echo "ERT Station - System Status"
	@echo "============================="
	@echo ""
	@echo "Laravel Configuration:"
	@echo "  APP_ENV=$(grep APP_ENV .env | cut -d= -f2)"
	@echo "  APP_URL=$(grep APP_URL .env | cut -d= -f2)"
	@echo ""
	@echo "Database:"
	@php -r "require 'vendor/autoload.php'; \$$env = parse_ini_file('.env'); echo '  Host: ' . \$$env['DB_HOST'] . PHP_EOL; echo '  Database: ' . \$$env['DB_DATABASE'] . PHP_EOL;"
	@echo ""
	@echo "Python Environment:"
	@echo "  Virtual Env: $(if $(wildcard $(PYTHON_VENV)),✅ Exists,❌ Missing)"
	@echo "  Python Version: $$($(PYTHON) --version 2>&1 || echo 'Not installed')"
	@echo ""
	@echo "Project Structure:"
	@echo "  Total Files: $$(find . -type f ! -path './vendor/*' ! -path './venv/*' ! -path './node_modules/*' ! -path './.git/*' | wc -l)"
	@echo "  Storage Size: $$(du -sh storage 2>/dev/null || echo 'N/A')"

.DEFAULT_GOAL := help
