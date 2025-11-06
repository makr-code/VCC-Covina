from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ingestion.infrastructure.api.versioning import (
    configure_api_versioning,
    configure_openapi_metadata,
)


def test_version_prefix_middleware():
    app = FastAPI()

    @app.get("/hello")
    async def hello():
        return {"msg": "world"}

    configure_api_versioning(app, prefix="/v1")

    client = TestClient(app)

    # Original path still works
    assert client.get("/hello").status_code == 200

    # Versioned path should work via middleware
    r = client.get("/v1/hello")
    assert r.status_code == 200
    assert r.json()["msg"] == "world"

    # OpenAPI under versioned path
    r = client.get("/v1/openapi.json")
    assert r.status_code == 200
    assert r.json()["openapi"].startswith("3.")


def test_openapi_metadata_configuration():
    app = FastAPI()
    configure_openapi_metadata(
        app,
        title="Covina API",
        version="1.2.3",
        description="Test description",
        contact={"name": "Covina", "url": "https://example.com"},
        license_info={"name": "MIT"},
    )

    client = TestClient(app)
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "Covina API"
    assert schema["info"]["version"] == "1.2.3"
    assert schema["info"]["description"] == "Test description"
    assert schema["info"]["contact"]["name"] == "Covina"
    assert schema["info"]["license"]["name"] == "MIT"
