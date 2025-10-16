"""UDS3 Package Initialisierung.
Stellt zentrale Funktionen bereit, so dass Adapter / externe Komponenten
stabil importieren können.

UDS3 Multi-Database Distribution System v1.0.0
Enterprise-ready Multi-DB Distribution für maximale administrative Flexibilität.
"""

from __future__ import annotations

# Legacy UDS3 Core Imports
try:  # pragma: no cover
    from .uds3_core import (
        UnifiedDatabaseStrategy,
        get_optimized_unified_strategy,
    )  # type: ignore
except Exception:  # Falls Abhängigkeiten fehlen soll Import nicht crashen
    UnifiedDatabaseStrategy = None  # type: ignore
    get_optimized_unified_strategy = None  # type: ignore

# New Multi-Database Distribution System Imports
try:
    from .adaptive_multi_db_strategy import (
        AdaptiveMultiDBStrategy,
        StrategyType,
        DatabaseAvailability,
        FlexibleMultiDBDistributor
    )
    
    from .uds3_multi_db_distributor import (
        UDS3MultiDBDistributor,
        ProcessorResult,
        ProcessorType,
        DistributionResult,
        create_uds3_distributor
    )
    
    from .processor_distribution_methods import (
        UDS3EnhancedMultiDBDistributor,
        create_enhanced_uds3_distributor
    )
    
    from .saga_multi_db_integration import (
        SAGAIntegratedMultiDBDistributor,
        create_saga_integrated_distributor
    )
    
    from .pipeline_integration import (
        UDS3EnhancedOrchestrator,
        bootstrap_enhanced_orchestrator
    )
    
    # Multi-DB Distribution available
    MULTI_DB_DISTRIBUTION_AVAILABLE = True
    
except ImportError:
    # Multi-DB Distribution components not available
    MULTI_DB_DISTRIBUTION_AVAILABLE = False
    AdaptiveMultiDBStrategy = None
    StrategyType = None
    UDS3MultiDBDistributor = None
    ProcessorResult = None
    ProcessorType = None


def create_secure_document_light(payload: dict) -> dict:
    """Leichter Wrapper, der aus einem einfachen Payload ein Secure Document erzeugt.

    Erwartet Felder (optional): file_path, content, chunks (Liste von Strings), security_level,
    sowie beliebige zusätzliche Metadaten.

    Rückgabe: Ergebnis-Dict analog zur Strategie oder Fehlermeldung.
    """
    if get_optimized_unified_strategy is None:
        return {"success": False, "error": "UDS3 core not available"}
    strategy = get_optimized_unified_strategy()
    file_path = payload.get("file_path", "unknown_file")
    content = payload.get("content") or payload.get("text") or ""
    if not content:
        # Minimales Platzhalter-Content falls leer
        content = f"PLACEHOLDER CONTENT FOR {file_path}"
    chunks = payload.get("chunks") or []
    if not isinstance(chunks, list):
        chunks = [str(chunks)]
    # Metadaten kopieren (alle außer reservierten Keys)
    reserved = {"file_path", "content", "text", "chunks", "security_level"}
    meta = {k: v for k, v in payload.items() if k not in reserved}
    security_level = payload.get("security_level")
    try:
        # Aufruf der Strategie-Methode
        result = strategy.create_secure_document(
            file_path=file_path,
            content=content,
            chunks=chunks,
            security_level=security_level,
            **meta,
        )
        return result
    except Exception as e:  # pragma: no cover
        return {"success": False, "error": str(e)}


__all__ = [
    "create_secure_document_light",
    "get_optimized_unified_strategy",
]


def set_runtime_config_overrides(overrides: dict) -> None:
    """Setzt zur Laufzeit globale Config-Overrides in `uds3.config`.

    Zweck: Erleichtert Tests/CI, ohne ENV-Variablen nutzen zu müssen.
    """
    try:
        from . import config as _config

        for k, v in (overrides or {}).items():
            if hasattr(_config, k):
                setattr(_config, k, v)
    except Exception:
        # Nicht kritisch - nur ein Hilfs-API
        return


def get_config_snapshot() -> dict:
    """Gibt ein flaches Snapshot-Dict der wichtigsten Config-Objekte zurück."""
    try:
        from . import config as _config

        return {
            "DATABASES": dict(getattr(_config, "DATABASES", {})),
            "FEATURES": dict(getattr(_config, "FEATURES", {})),
            "OPTIMIZATION": dict(getattr(_config, "OPTIMIZATION", {})),
        }
    except Exception:
        return {}
