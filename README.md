# FastAPI Observability Demo

This project demonstrates how to add observability to a Python FastAPI application: Prometheus metrics via OpenTelemetry, and structured JSON logs that can be correlated across a request with `request_id` and `trace_id`.

The logging approach follows [Structured logs in FastAPI: a practical guide from request_id to trace_id](https://habr.com/ru/companies/otus/articles/1067632/).

## Architecture

1. **FastAPI Application**: A simple web application instrumented with OpenTelemetry (`app/main.py`).
2. **OpenTelemetry**: Automatically instruments FastAPI requests to capture latency, status codes, and other telemetry data. It exposes these metrics locally at `/metrics`.
3. **Structured logging**: Every log line is a JSON object. Middleware attaches `trace_id`, `request_id`, `user_id`, `endpoint`, and `method` to all logs for a request, and records duration and response size when the request finishes.
4. **Prometheus**: Scrapes the `/metrics` endpoint on the FastAPI application every 5 seconds, storing the time-series data for querying.
5. **Docker Compose**: Orchestrates the seamless bringing up of both services.

## Getting Started

1. Make sure you have Docker and Docker Compose installed and running.
2. Start the application:
   ```bash
   docker compose up --build -d
   ```
3. Generate some traffic to populate metrics and logs:
   ```bash
   curl http://localhost:8000/hello
   curl http://localhost:8000/error
   curl -H "X-User-Id: 12345" -H "X-Trace-ID: demo-trace-1" http://localhost:8000/hello
   ```
4. Inspect JSON logs:
   ```bash
   docker compose logs app
   ```

## Structured Logging

Logs go to stdout as one JSON object per event. Filebeat, Fluentd, or `docker compose logs` can consume them without extra parsing rules.

### Request context

`LoggingMiddleware` reads `X-Trace-ID` and `X-Request-ID` from the incoming request, or generates UUIDs when they are missing. It also reads `X-User-Id` (defaults to `anonymous`). Those fields are stored on a `ContextLogger` in `request.state.logger`, so handlers can log without repeating them:

```python
request.state.logger.info("Hello handler started")
request.state.logger.info("Hello handler finished", extra={"result": "ok"})
```

Pass extra data as fields, not as interpolated strings. This keeps values queryable:

```python
# Do this
logger.info("User bought item", extra={"user_id": user_id, "item_id": item_id})

# Don't do this — parsers cannot filter on user_id as a field
logger.info(f"User {user_id} bought {item_id}")
```

The middleware also:

- logs `Incoming request` and `Request finished` (skipped for `/metrics` so Prometheus scrapes stay quiet)
- measures `duration_ms` and `size_bytes`
- echoes `X-Trace-ID`, `X-Request-ID`, and `X-Response-Time` on the response
- logs unhandled exceptions as a structured `exception` object (type, message, last 5 stack frames)

### Example log

A successful `/hello` call looks like:

```json
{
  "timestamp": "2026-09-17T12:00:00.123456Z",
  "level": "INFO",
  "logger": "app",
  "message": "Request finished",
  "location": "middleware:60",
  "function": "dispatch",
  "trace_id": "demo-trace-1",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "12345",
  "endpoint": "/hello",
  "method": "GET",
  "status_code": 200,
  "duration_ms": 47.12,
  "size_bytes": 35
}
```

Filter logs by `trace_id` to see the full path of one request, or by `user_id` to see everything that user triggered. `/error` returns HTTP 500 and logs a structured `exception` object (type, message, and stack frames).

### Endpoints

| Path | Purpose |
| --- | --- |
| `GET /health` | Liveness check, emits a structured log |
| `GET /hello` | Successful request (also used for metrics) |
| `GET /error` | Simulated failure: HTTP 500 + structured exception log |
| `GET /metrics` | Prometheus scrape endpoint (access logs suppressed) |

## Prometheus Metrics & Queries

Once the containers are running and traffic has been generated, you can access the Prometheus dashboard at:
[http://localhost:9090](http://localhost:9090)

You can query the gathered OpenTelemetry metrics using PromQL in the Prometheus interface. Here are some useful queries you can try:

### 1. Total Number of HTTP Requests
Count the total number of HTTP requests processed by the server:
```promql
http_server_duration_ms_count
```

### 2. Request Rate (per second)
View the rate of HTTP requests over the last 1 minute:
```promql
rate(http_server_duration_ms_count[1m])
```

### 3. HTTP 5xx Error Rate
Find out how frequently internal server errors (e.g., HTTP 500) are occurring:
```promql
rate(http_server_duration_ms_count{http_status_code=~"5.."}[5m])
```

### 4. 95th Percentile Request Latency
Calculate the 95th percentile latency (in milliseconds) for HTTP requests to see how slow the slowest 5% of requests are:
```promql
histogram_quantile(0.95, sum(rate(http_server_duration_ms_bucket[5m])) by (le))
```

### 5. Requests Breakdown by Path
See the distribution of HTTP requests organized by the endpoint path:
```promql
sum(http_server_duration_ms_count) by (http_route)
```
