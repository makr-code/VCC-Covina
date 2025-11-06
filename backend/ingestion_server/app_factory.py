from __future__ import annotations
import logging
import os
from fastapi import FastAPI
from .router import router as ingestion_router
from utils.json_logging import setup_json_logging, create_correlation_id_middleware
from utils.pii_redaction import PIIRedactionFilter
from ingestion.infrastructure.api.versioning import (
    configure_api_versioning,
    configure_openapi_metadata,
)


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
    # OpenAPI metadata and API versioning (/v1 prefix)
    try:
        configure_openapi_metadata(
            app,
            title="Covina Ingestion Server",
            version=os.getenv("COVINA_VERSION", "4.0.3"),
            description="File ingestion, NLP extraction, and multi-DB persistence",
        )
        configure_api_versioning(app, prefix="/v1", add_docs_redirect=True)
    except Exception:
        # Safe fallback: continue without versioned docs if utilities unavailable
        pass

    # Routes
    app.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
    return app
