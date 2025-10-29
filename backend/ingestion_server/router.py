from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from ingestion.boot.container import container
from utils.metrics import metrics_registry, export_prometheus_text

router = APIRouter()

class IngestRequest(BaseModel):
    text: str

@router.get("/health")
async def health() -> dict:
    # Export a tiny summary of key metrics (avoid huge payloads here)
    data = metrics_registry.export_dict()
    # Extract some highlights for quick checks
    highlights = {
        "extractions_total": 0,
        "extractions_success": 0,
        "extractions_error": 0,
    }
    for m in data.get("metrics", []):
        if m.get("name") == "legal_nlp_extractions_total":
            for s in m.get("samples", []):
                status = (s.get("labels") or {}).get("status", "")
                val = int(s.get("value") or 0)
                highlights["extractions_total"] += val
                if status in ("success", "error"):
                    highlights[f"extractions_{status}"] = val
            break
    return {"status": "ok", "metrics": highlights}

@router.post("/ingest")
async def ingest(req: IngestRequest) -> dict:
    result = await container.ingest_document.execute(req.text)
    return result


@router.get("/metrics")
async def metrics() -> JSONResponse:
    """Raw JSON metrics export from utils.metrics."""
    return JSONResponse(content=metrics_registry.export_dict())


@router.get("/prometheus", response_class=PlainTextResponse)
async def prometheus() -> PlainTextResponse:
    """Prometheus-like text metrics export for scraping."""
    return PlainTextResponse(content=export_prometheus_text())
