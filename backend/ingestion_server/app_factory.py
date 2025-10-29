from __future__ import annotations
import logging
import os
from fastapi import FastAPI
from .router import router as ingestion_router
from utils.json_logging import setup_json_logging, create_correlation_id_middleware
from utils.pii_redaction import PIIRedactionFilter


def get_app() -> FastAPI:
    # Setup JSON logging (safe fallback if lib missing)
    try:
        setup_json_logging(
            service_name="ingestion_server",
            level=logging.INFO,
            environment=os.getenv("ENVIRONMENT", "development"),
            version=os.getenv("COVINA_VERSION", "4.0.3"),
        )
        # PII redaction
        try:
            logging.getLogger().addFilter(PIIRedactionFilter())
        except Exception:
            pass
    except Exception:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

    app = FastAPI(title="Covina Ingestion Server")
    # Correlation-ID middleware for request tracing
    try:
        app.middleware("http")(create_correlation_id_middleware())
    except Exception:
        # Continue without middleware if unavailable
        pass
    app.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
    return app
