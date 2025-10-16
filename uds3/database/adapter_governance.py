"""Governance-Richtlinien für Datenbank-Adapter.

Dieses Modul bündelt nachvollziehbare Regeln, welche Operationen auf den
Backend-Adaptern erlaubt sind und welche Felder bzw. Datentypen in den
Payloads auftreten dürfen. Es dient als zentrale Stelle für die
Governance-Prüfungen, damit sowohl der `DatabaseManager` als auch höhere
Schichten (z.\u202fB. `UnifiedDatabaseStrategy`) konsistente Entscheidungen
über Zulässigkeit und Validität treffen können.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(slots=True)
class GovernanceViolation:
    """Repräsentiert einen Verstoß gegen eine Governance-Regel."""

    backend: str
    operation: str
    field_path: Optional[str]
    message: str


class AdapterGovernanceError(RuntimeError):
    """Ausnahme für Governance-Verstöße."""

    def __init__(self, message: str, violations: Optional[Sequence[GovernanceViolation]] = None) -> None:
        super().__init__(message)
        self.violations: Tuple[GovernanceViolation, ...] = tuple(violations or ())


class AdapterGovernance:
    """Governance-Prüflogik für alle unterstützten Backend-Typen."""

    DEFAULT_POLICIES: Dict[str, Dict[str, Any]] = {
        "vector": {
            "allowed_operations": {"create", "read", "update", "delete"},
            "payload_rules": {},
        },
        "graph": {
            "allowed_operations": {"create", "read", "update", "delete"},
            "payload_rules": {
                "forbidden_fields": {
                    "content",
                    "fulltext",
                    "raw_content",
                    "binary_content",
                    "file_content",
                    "chunks",
                },
                "forbidden_types": (bytes, bytearray, memoryview),
            },
        },
        "relational": {
            "allowed_operations": {"create", "read", "update", "delete"},
            "payload_rules": {
                "forbidden_fields": {
                    "binary_content",
                    "file_bytes",
                    "raw_content",
                    "blob",
                    "binary",
                },
                "forbidden_types": (bytes, bytearray, memoryview),
            },
        },
        "file": {
            "allowed_operations": {"create", "read", "update", "delete"},
            "payload_rules": {},
        },
    }

    def __init__(self, policies: Optional[Dict[str, Dict[str, Any]]] = None, *, strict: bool = True) -> None:
        self.strict = strict
        self.policies = self._merge_policies(self.DEFAULT_POLICIES, policies or {})

    def _merge_policies(
        self,
        defaults: Dict[str, Dict[str, Any]],
        overrides: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        for backend, definition in defaults.items():
            merged[backend] = {
                "allowed_operations": set(definition.get("allowed_operations", set())),
                "payload_rules": dict(definition.get("payload_rules", {})),
            }
        for backend, definition in overrides.items():
            backend_lower = backend.lower()
            target = merged.setdefault(
                backend_lower,
                {
                    "allowed_operations": set(),
                    "payload_rules": {},
                },
            )
            if "allowed_operations" in definition:
                target["allowed_operations"] = set(definition["allowed_operations"])
            if "payload_rules" in definition:
                payload_rules = dict(target.get("payload_rules", {}))
                payload_rules.update(definition["payload_rules"])
                target["payload_rules"] = payload_rules
        return merged

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------
    def allowed_operations(self, backend: str) -> Sequence[str]:
        policy = self.policies.get(backend.lower(), {})
        return sorted(policy.get("allowed_operations", set()))

    def ensure_operation_allowed(self, backend: str, operation: str) -> None:
        policy = self.policies.get(backend.lower())
        if not policy:
            return
        allowed = policy.get("allowed_operations")
        if allowed and operation not in allowed:
            message = f"Operation '{operation}' ist für Backend '{backend}' nicht zulässig"
            raise AdapterGovernanceError(message)

    def enforce_payload(self, backend: str, operation: str, payload: Any) -> None:
        violations = self.validate_payload(backend, operation, payload)
        if violations:
            message = "; ".join(v.message for v in violations)
            raise AdapterGovernanceError(message, violations)

    def validate_payload(self, backend: str, operation: str, payload: Any) -> List[GovernanceViolation]:
        policy = self.policies.get(backend.lower())
        if not policy:
            return []
        rules = policy.get("payload_rules") or {}
        forbidden_fields = {str(field).lower() for field in rules.get("forbidden_fields", set())}
        forbidden_types = rules.get("forbidden_types", ())

        violations: List[GovernanceViolation] = []
        if not forbidden_fields and not forbidden_types:
            return violations

        for field_path, value in self._iterate_payload(payload):
            field_key = field_path.split(".")[-1].lower()
            if forbidden_fields and field_key in forbidden_fields:
                violations.append(
                    GovernanceViolation(
                        backend=backend,
                        operation=operation,
                        field_path=field_path,
                        message=f"Feld '{field_path}' ist für Backend '{backend}' nicht erlaubt",
                    )
                )
            if forbidden_types and isinstance(value, forbidden_types):
                violations.append(
                    GovernanceViolation(
                        backend=backend,
                        operation=operation,
                        field_path=field_path,
                        message=f"Datentyp '{type(value).__name__}' in Feld '{field_path}' ist für Backend '{backend}' verboten",
                    )
                )
        return violations

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------
    def _iterate_payload(self, payload: Any, prefix: Optional[str] = None) -> Iterable[Tuple[str, Any]]:
        if payload is None:
            return
        current_prefix = prefix or ""
        if isinstance(payload, dict):
            for key, value in payload.items():
                path = f"{current_prefix}.{key}" if current_prefix else str(key)
                yield path, value
                if isinstance(value, (dict, list, tuple, set)):
                    yield from self._iterate_payload(value, path)
        elif isinstance(payload, (list, tuple, set)):
            for index, value in enumerate(payload):
                path = f"{current_prefix}[{index}]" if current_prefix else f"[{index}]"
                yield path, value
                if isinstance(value, (dict, list, tuple, set)):
                    yield from self._iterate_payload(value, path)
        else:
            path = current_prefix or "value"
            yield path, payload