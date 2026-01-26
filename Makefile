.PHONY: help api-dev dashboard-dev up down restart logs clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

api-dev: ## Start API service in Docker
	docker-compose up -d api
	@echo "API service starting at http://localhost:8000"
	@echo "API docs available at http://localhost:8000/docs"

dashboard-dev: ## Start dashboard development server
	cd apps/dashboard && npm run dev

up: ## Start all services (postgres, redis, api)
	docker-compose up -d
	@echo "All services started"
	@echo "API: http://localhost:8000"
	@echo "Postgres: localhost:5432"
	@echo "Redis: localhost:6379"

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Show logs from all services
	docker-compose logs -f

logs-api: ## Show API service logs
	docker-compose logs -f api

clean: ## Stop services and remove volumes (WARNING: deletes data)
	docker-compose down -v
	@echo "All services stopped and volumes removed"
