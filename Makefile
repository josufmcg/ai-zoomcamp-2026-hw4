PORT ?= 8000
COMPOSE ?= docker compose

.PHONY: run up down logs url test

run: up

up:
	ORDER_TRACKER_PORT=$(PORT) $(COMPOSE) up --build -d --wait
	@echo "Order Tracker is available at http://127.0.0.1:$(PORT)"

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f app otel-collector

url:
	@echo "http://127.0.0.1:$(PORT)"

test:
	uv run --frozen pytest -q
