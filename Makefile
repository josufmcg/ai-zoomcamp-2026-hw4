PORT ?= 8000
GRAFANA_PORT ?= 3000
PROMETHEUS_PORT ?= 9090
LOKI_PORT ?= 3100
TEMPO_PORT ?= 3200
COMPOSE ?= docker compose

.PHONY: run up down logs url test

run: up

up:
	ORDER_TRACKER_PORT=$(PORT) GRAFANA_PORT=$(GRAFANA_PORT) PROMETHEUS_PORT=$(PROMETHEUS_PORT) LOKI_PORT=$(LOKI_PORT) TEMPO_PORT=$(TEMPO_PORT) $(COMPOSE) up --build -d --wait
	@$(MAKE) --no-print-directory url

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f app otel-collector

url:
	@echo "Order Tracker: http://127.0.0.1:$(PORT)"
	@echo "Grafana:       http://127.0.0.1:$(GRAFANA_PORT)"
	@echo "Prometheus:    http://127.0.0.1:$(PROMETHEUS_PORT)"
	@echo "Loki:          http://127.0.0.1:$(LOKI_PORT)"
	@echo "Tempo:         http://127.0.0.1:$(TEMPO_PORT)"

test:
	uv run --frozen pytest -q
