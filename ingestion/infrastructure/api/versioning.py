"""
API Versioning and OpenAPI Enhancements

Provides:
- Version prefix middleware (supports /v1 without refactoring routes)
- OpenAPI metadata configuration (title, version, contact, license)
- Convenience endpoints for /v1/openapi.json and /v1/docs redirect
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


class VersionPrefixMiddleware(BaseHTTPMiddleware):
    """Middleware that transparently supports a versioned prefix like /v1.
    If the request path starts with the given prefix, it is stripped before routing.
    """

    def __init__(self, app: FastAPI, prefix: str = "/v1") -> None:
        super().__init__(app)
        self.prefix = prefix.rstrip("/")

    async def dispatch(self, request, call_next):
        scope = request.scope
        path: str = scope.get("path", "")
        if path.startswith(self.prefix + "/") or path == self.prefix:
            # Rewrite the path by stripping the prefix
            scope["path"] = path[len(self.prefix) :] or "/"
        return await call_next(request)


def configure_api_versioning(app: FastAPI, prefix: str = "/v1", add_docs_redirect: bool = True) -> None:
    """Enable transparent API versioning via prefix and optional docs endpoints.

    - Allows calling existing routes via /v1/... without refactoring.
    - Adds /v1/openapi.json (serves current OpenAPI)
    - Adds /v1/docs redirect to current docs (if enabled)
    """
    app.add_middleware(VersionPrefixMiddleware, prefix=prefix)

    # OpenAPI under versioned path
    versioned_openapi = f"{prefix}/openapi.json"

    @app.get(versioned_openapi)
    async def openapi_v1():
        return JSONResponse(app.openapi())

    if add_docs_redirect:
        versioned_docs = f"{prefix}/docs"

        @app.get(versioned_docs)
        async def docs_v1():
            # Redirect to current docs UI; the OpenAPI URL may still be /openapi.json
            return RedirectResponse(url=app.docs_url or "/docs")


def configure_openapi_metadata(
    app: FastAPI,
    *,
    title: Optional[str] = None,
    version: Optional[str] = None,
    description: Optional[str] = None,
    contact: Optional[Dict[str, Any]] = None,
    license_info: Optional[Dict[str, Any]] = None,
) -> None:
    """Set OpenAPI metadata on FastAPI app."""
    if title is not None:
        app.title = title
    if version is not None:
        app.version = version
    if description is not None:
        app.description = description
    if contact is not None:
        app.contact = contact
    if license_info is not None:
        app.license_info = license_info
