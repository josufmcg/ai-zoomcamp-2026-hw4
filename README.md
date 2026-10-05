# Order Tracker

A small order tracking app for the AI Dev Tools Zoomcamp observability homework. It includes a web page, API, tests, and a Docker Compose observability stack. OpenTelemetry metrics, logs, and traces are sent from the app to the Collector, then stored in Prometheus, Loki, and Tempo.

The main user flow is creating an order and checking its status. Three sample orders are created on first startup.

## Run it

You need Docker with Compose. To run the tests, you also need Python 3.11+ and `uv`.

```bash
docker compose up --build -d
```

Open <http://127.0.0.1:8000> for the app and <http://127.0.0.1:3000> for Grafana. The default Grafana login is `admin` / `admin`; set `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` before starting to change it. The provisioned **Order Tracker** dashboard shows request and error rates, and Grafana includes a 5xx alert evaluated over a five-minute window. Prometheus is available at <http://127.0.0.1:9090>, Loki at <http://127.0.0.1:3100>, and Tempo at <http://127.0.0.1:3200>.

### Incident response

Start the host-side incident receiver in a second terminal:

```bash
make incident-response
```

Grafana sends alerts to `POST /alerts` on port 8001. The receiver stores the alert in `incident-response/incidents.db`, collects recent Order Tracker logs from Loki and traces from Tempo, and starts Claude Code in headless read-only plan mode (`Read` tool only) for firing alerts. Install and authenticate Claude Code on the host before starting the receiver. Use `GET /incidents` and `GET /incidents/{id}` from localhost to inspect saved context and diagnosis. The webhook is accepted only from localhost or the configured Compose subnet; keep `INCIDENT_RESPONSE_TRUSTED_SUBNET` aligned with `ORDER_TRACKER_SUBNET`.

If a port is occupied, set `ORDER_TRACKER_PORT`, `GRAFANA_PORT`, `PROMETHEUS_PORT`, `LOKI_PORT`, or `TEMPO_PORT`, for example:

```bash
ORDER_TRACKER_PORT=18080 GRAFANA_PORT=3300 docker compose up --build -d
```

Run tests with `uv run --frozen pytest -q`. Stop the stack with `docker compose down`. Add `-v` only if you also want to delete the order and observability data.

## Telemetry

Inspect Collector and app logs with:

```bash
docker compose logs -f app otel-collector
```

Each HTTP request increments `http.server.request.count` with `http.route` and `http.response.status_code` attributes. Order detail lookups emit an `order.lookup` trace span and a structured log record, including whether the order was found. The Collector receives OTLP over gRPC, exports metrics for Prometheus scraping, and forwards logs and traces to Loki and Tempo.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Web page |
| GET | `/healthz` | Database health check |
| GET | `/api/orders` | List orders |
| POST | `/api/orders` | Create an order |
| GET | `/api/orders/{id}` | Check an order |
| PATCH | `/api/orders/{id}` | Change an order status |

The app uses SQLite to keep setup small. Run one app container at a time. The course exercise is about detecting and handling an incident, not scaling the database.
