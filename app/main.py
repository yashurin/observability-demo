import random
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

from logging_config import setup_logging
from middleware import LoggingMiddleware

logger = setup_logging()

# 1. Setup Resource
resource = Resource.create({"service.name": "fastapi-observability-demo"})

# 2. Setup Prometheus Exporter
reader = PrometheusMetricReader()
provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(provider)

app = FastAPI(title="Observability Demo")
app.add_middleware(LoggingMiddleware, logger=logger)

# 3. Instrument FastAPI (outermost user middleware so metrics see every request)
FastAPIInstrumentor.instrument_app(app)


@app.get("/health")
def health(request: Request):
    request.state.logger.info("Health check called")
    return {"status": "ok"}


@app.get("/hello")
def hello(request: Request):
    """A simulated endpoint that successfully processes a request."""
    request.state.logger.info("Hello handler started")
    time.sleep(random.uniform(0.01, 0.1))
    request.state.logger.info("Hello handler finished", extra={"result": "ok"})
    return {"message": "Hello, Observability!"}


@app.get("/error")
def error(request: Request):
    """A simulated endpoint that encounters an error."""
    request.state.logger.info("Error handler started")
    time.sleep(random.uniform(0.05, 0.2))
    try:
        raise RuntimeError("Simulated Internal Server Error")
    except RuntimeError:
        request.state.logger.error(
            "Simulated processing failure",
            extra={"reason": "forced_error"},
            exc_info=True,
        )
        return Response(content="Simulated Internal Server Error", status_code=500)


@app.get("/metrics")
def get_metrics():
    """Endpoint exposing the OpenTelemetry metrics for Prometheus to scrape."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
