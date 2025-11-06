from __future__ import annotations
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import List
import tempfile
import shutil
import json
from pathlib import Path
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


@router.post("/upload/files")
async def upload_files(files: List[UploadFile] = File(...)) -> JSONResponse:
    """
    Accept multipart file uploads and ingest them.

    Returns:
        JSON with job_id, file count, and status
    """
    import uuid

    job_id = str(uuid.uuid4())
    uploaded = []
    errors = []

    # Create temp directory for this upload batch
    temp_dir = Path(tempfile.mkdtemp(prefix=f"upload_{job_id}_"))

    try:
        for file in files:
            if not file.filename:
                continue
            try:
                # Stream file to disk
                file_path = temp_dir / file.filename
                with file_path.open("wb") as f:
                    while chunk := await file.read(65536):  # 64KB chunks
                        f.write(chunk)

                # Read content and ingest via container
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                result = await container.ingest_document.execute(content)

                uploaded.append({
                    "filename": file.filename,
                    "status": "success" if result.get("status") == "success" else "error",
                    "size": file_path.stat().st_size,
                })
            except Exception as e:
                errors.append({
                    "filename": file.filename,
                    "error": str(e),
                })

    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

    return JSONResponse(
        content={
            "job_id": job_id,
            "uploaded": len(uploaded),
            "errors": len(errors),
            "files": uploaded,
            "error_details": errors if errors else None,
        },
        status_code=200 if not errors else 207,  # 207 Multi-Status if partial success
    )


@router.get("/capabilities")
async def capabilities() -> JSONResponse:
    """Report supported features and key endpoints for client discovery.

    This endpoint is intentionally lightweight and stable to allow GUIs/tools
    to adapt without hardcoding feature flags. Values prefer env/config where
    possible, but fall back to safe defaults.
    """
    import os

    def as_bool(env_name: str, default: bool = False) -> bool:
        val = os.getenv(env_name)
        if val is None:
            return default
        return str(val).strip().lower() in {"1", "true", "yes", "on"}

    data = {
        "service": "covina-ingestion",
        "api_version": "v1",
        "endpoints": {
            "health": "/ingestion/health",
            "ingest": "/ingestion/ingest",
            "upload": "/ingestion/upload/files",
            "metrics": "/ingestion/metrics",
            "prometheus": "/ingestion/prometheus",
        },
        "features": {
            "file_upload": True,
            # WebSocket job notifications are not exposed by this server module
            "websocket": False,
            # Batch embeddings and Chroma batch insert flags are informative only
            "batch_embeddings": as_bool("ENABLE_BATCH_EMBEDDINGS", False),
            "chroma_batch_insert": as_bool("ENABLE_CHROMA_BATCH_INSERT", False),
        },
    }
    return JSONResponse(content=data)

@router.get("/metrics")
async def metrics() -> JSONResponse:
    """Raw JSON metrics export from utils.metrics."""
    return JSONResponse(content=metrics_registry.export_dict())


@router.get("/prometheus", response_class=PlainTextResponse)
async def prometheus() -> PlainTextResponse:
    """Prometheus-like text metrics export for scraping."""
    return PlainTextResponse(content=export_prometheus_text())


@router.get("/capabilities/supported-filetypes")
async def supported_filetypes() -> JSONResponse:
    """Report supported filetypes for uploads."""
    filetypes = [
        ".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls",
        ".csv", ".json", ".xml", ".html", ".md", ".rtf",
    ]
    return JSONResponse(
        content={
            "service": "covina-ingestion",
            "upload_supported": True,
            "supported_filetypes": filetypes,
            "all_extensions": filetypes,  # alias for GUI compatibility
        }
    )


# ============================================================================
# PROCESS INGESTION
# ============================================================================

class ProcessIngestRequest(BaseModel):
    """Request model for process ingestion via JSON body."""
    process_json: str
    run_mining: bool = True
    guidelines_path: str | None = None


@router.post("/processes")
async def ingest_process(req: ProcessIngestRequest) -> JSONResponse:
    """
    Ingest VPB process definition from JSON.
    
    Request body:
    - process_json: VPB JSON string (full process definition)
    - run_mining: Run self-learning mining pipeline (default: True)
    - guidelines_path: Optional path to YAML guidelines (default: processes/guidelines/process_inference.yml)
    
    Returns:
    - process_id: UUIDv7 of created Process
    - entities: Count of created entities (steps, roles, etc.)
    - mining_result: InferenceResult (if run_mining=True)
    - status: "success" or "error"
    """
    try:
        from processes.parsers import VPBParser
        from processes.graph.process_graph_writer import ProcessGraphWriter
        from processes.mining.pipeline import ProcessMiningPipeline
        from processes.mining.guidelines import RuleEngine
        from processes.mining.schemas import DocumentMeta
        from uds3.database.database_api_neo4j import Neo4jAdapter
        import os
        
        # Parse VPB JSON
        parser = VPBParser()
        process = parser.parse_json(req.process_json)
        entities = parser.get_all_entities()
        
        # Get Neo4j connection
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j")
        
        # Initialize graph writer
        graph_adapter = Neo4jAdapter(neo4j_uri, neo4j_user, neo4j_password)
        await graph_adapter.connect()
        
        try:
            writer = ProcessGraphWriter(graph_adapter)
            
            # Write Process node
            process_id = await writer.write_process(process)
            
            # Write all entities and link to process
            step_ids = []
            for role in entities["roles"]:
                await writer.write_role(role)
            
            for org_unit in entities["org_units"]:
                await writer.write_org_unit(org_unit)
            
            for system in entities["systems"]:
                await writer.write_system(system)
            
            for control in entities["controls"]:
                await writer.write_control(control)
            
            for legal_ref in entities["legal_refs"]:
                await writer.write_legal_ref(legal_ref)
                await writer.link_process_legal_ref(process_id, legal_ref.id)
            
            for info_object in entities["info_objects"]:
                await writer.write_info_object(info_object)
            
            # Parse process JSON to get steps (not stored in UPS model)
            proc_data = json.loads(req.process_json)
            steps_data = proc_data.get("process", proc_data).get("steps", [])
            
            previous_step_id = None
            for step_data in steps_data:
                from processes.domain.models import Step
                
                # Create Step model
                step = Step(
                    key=step_data.get("key", "unknown_step"),
                    name=step_data.get("name", "Unknown Step"),
                    type=step_data.get("type", "task"),
                    description=step_data.get("description"),
                    instructions=step_data.get("instructions"),
                    duration_days=step_data.get("duration_days"),
                    mandatory=step_data.get("mandatory", True),
                    automated=step_data.get("automated", False),
                    metadata=step_data.get("metadata", {}),
                )
                
                # Write step and link to process
                step_id = await writer.write_step(step, process_id)
                step_ids.append(step_id)
                
                # Link sequential steps with NEXT relation
                if previous_step_id:
                    await writer.link_step_sequence(previous_step_id, step_id)
                previous_step_id = step_id
            
            # Run mining pipeline (if enabled)
            mining_result = None
            if req.run_mining:
                guidelines_path = req.guidelines_path or "processes/guidelines/process_inference.yml"
                
                # Load guidelines
                engine = RuleEngine(guidelines_path)
                pipeline = ProcessMiningPipeline(engine)
                
                # Create DocumentMeta from process JSON
                doc_meta = DocumentMeta(
                    doc_id=process_id,
                    text=json.dumps(proc_data, ensure_ascii=False),
                    metadata={
                        "source": "vpb_json",
                        "process_key": process.key,
                        "process_version": process.version,
                    },
                )
                
                # Run inference
                inference = await pipeline.infer_online(doc_meta)
                mining_result = {
                    "process_key": inference.process_key,
                    "node_confidence": {k: round(v, 4) for k, v in inference.node_confidence.items()},
                    "paths_count": len(inference.paths),
                }
            
            return JSONResponse(
                content={
                    "status": "success",
                    "process_id": process_id,
                    "process_key": process.key,
                    "entities": {
                        "steps": len(step_ids),
                        "roles": len(entities["roles"]),
                        "org_units": len(entities["org_units"]),
                        "systems": len(entities["systems"]),
                        "controls": len(entities["controls"]),
                        "legal_refs": len(entities["legal_refs"]),
                        "info_objects": len(entities["info_objects"]),
                    },
                    "mining_result": mining_result,
                },
                status_code=201,
            )
        
        finally:
            await graph_adapter.close()
    
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Process ingestion failed: {e}")


@router.post("/processes/upload")
async def upload_process_file(file: UploadFile = File(...)) -> JSONResponse:
    """
    Upload VPB process definition file (JSON/XML/BPMN).
    
    Accepts:
    - .json: VPB JSON format
    - .xml/.bpmn: BPMN 2.0 (future)
    
    Returns:
    - Same as POST /processes (process_id, entities, mining_result)
    """
    import uuid
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".json", ".xml", ".bpmn"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {suffix}. Supported: .json, .xml, .bpmn"
        )
    
    # Create temp file
    temp_dir = Path(tempfile.mkdtemp(prefix=f"process_upload_{uuid.uuid4().hex[:8]}_"))
    
    try:
        file_path = temp_dir / file.filename
        
        # Stream file to disk
        with file_path.open("wb") as f:
            while chunk := await file.read(65536):  # 64KB chunks
                f.write(chunk)
        
        # Read content
        content = file_path.read_text(encoding="utf-8")
        
        # Parse based on extension
        if suffix == ".json":
            # Use existing JSON ingestion
            req = ProcessIngestRequest(process_json=content, run_mining=True)
            return await ingest_process(req)
        
        elif suffix in [".xml", ".bpmn"]:
            # BPMN parsing (future implementation)
            raise HTTPException(
                status_code=501, 
                detail="BPMN parsing not yet implemented. Use JSON format."
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
    
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
