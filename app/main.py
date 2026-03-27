import random
import time
from fastapi import FastAPI, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

# 1. Setup Resource
resource = Resource.create({"service.name": "fastapi-observability-demo"})

# 2. Setup Prometheus Exporter
reader = PrometheusMetricReader()
provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(provider)

app = FastAPI(title="Observability Demo")

# 3. Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

@app.get("/hello")
def hello():
    """A simulated endpoint that successfully processes a request."""
    # Simulate some processing time
    time.sleep(random.uniform(0.01, 0.1))
    return {"message": "Hello, Observability!"}

@app.get("/error")
def error():
    """A simulated endpoint that encounters an error."""
    # Simulate processing time and an error response
    time.sleep(random.uniform(0.05, 0.2))
    return Response(content="Simulated Internal Server Error", status_code=500)

@app.get("/metrics")
def get_metrics():
    """Endpoint exposing the OpenTelemetry metrics for Prometheus to scrape."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
