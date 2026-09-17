import json
import logging
import logging.config
import traceback
from datetime import datetime, timezone

# LogRecord fields that must not be copied into the JSON payload as extra context.
_RESERVED_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "taskName",
    "thread",
    "threadName",
}


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record, including extra context and structured exceptions."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "location": f"{record.module}:{record.lineno}",
            "function": record.funcName,
            "pid": record.process,
            "thread": record.threadName,
        }

        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry.update(record.extra)

        for key, value in record.__dict__.items():
            if key in _RESERVED_ATTRS or key == "extra" or key.startswith("_"):
                continue
            log_entry[key] = value

        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            stack_summary = traceback.extract_tb(exc_tb)
            log_entry["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value),
                "stack": [
                    {
                        "file": frame.filename,
                        "line": frame.lineno,
                        "function": frame.name,
                        "code": frame.line,
                    }
                    for frame in stack_summary[-5:]
                ],
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ContextLogger(logging.LoggerAdapter):
    """Always merge request-scoped context into `extra` so callers don't pass it on every call."""

    def process(self, msg, kwargs):
        context = dict(self.extra) if self.extra else {}
        extra = kwargs.get("extra")
        if extra:
            context.update(extra)
        kwargs["extra"] = context
        return msg, kwargs


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {"()": JsonFormatter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            }
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
        "loggers": {
            # Keep uvicorn noise down and avoid duplicate non-JSON access lines.
            "uvicorn": {"level": "WARNING"},
            "uvicorn.access": {"level": "WARNING", "propagate": False},
            "uvicorn.error": {"level": "INFO"},
        },
    }
    logging.config.dictConfig(config)
    return logging.getLogger("app")
