# FastAPI Observability Demo

This project demonstrates how to add observability and metrics gathering to a Python FastAPI application using OpenTelemetry (OTel) and Prometheus.

## Architecture

1. **FastAPI Application**: A simple web application instrumented with OpenTelemetry (`app/main.py`).
2. **OpenTelemetry**: Automatically instruments FastAPI requests to capture latency, status codes, and other telemetry data. It exposes these metrics locally at `/metrics`.
3. **Prometheus**: Scrapes the `/metrics` endpoint on the FastAPI application every 5 seconds, storing the time-series data for querying.
4. **Docker Compose**: Orchestrates the seamless bringing up of both services.

## Getting Started

1. Make sure you have Docker and Docker Compose installed and running.
2. Start the application:
   ```bash
   docker compose up --build -d
   ```
3. Generate some traffic to populate metrics:
   ```bash
   curl http://localhost:8000/hello
   curl http://localhost:8000/error
   ```

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
