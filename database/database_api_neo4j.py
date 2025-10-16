#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""



"""
Neo4j Graph Database Backend
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Set

LABEL_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PROPERTY_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DEFAULT_ALLOWED_NODE_LABELS: Set[str] = {
    "Document",
    "DocumentChunk",
    "FileVersion",
    "Chunk",
    "MetadataTag",
    "QualityReport",
    "SecurityEvent",
    "ProcessStep",
    "AgencyUnit",
    "RelationTemplate",
    "VectorSpace",
    "Policy",
    "AuditLog",
}

DEFAULT_ALLOWED_RELATION_TYPES: Set[str] = {
    "HAS_VERSION",
    "DERIVES_FROM",
    "HAS_CHUNK",
    "NEXT_CHUNK",
    "REFERENCES_CHUNK",
    "SEMANTIC_SIMILAR",
    "EMBEDDED_IN",
    "TAGGED_WITH",
    "HAS_QUALITY_REPORT",
    "REFERENCES_ISSUE",
    "LOGGED_BY",
    "GUARDED_BY",
    "AUDITED_BY",
    "PART_OF_PROCESS",
    "NEXT_STEP",
    "OWNED_BY",
    "IMPLEMENTED_AS",
    "DEFINED_BY",
    "RELATED_TO",
}

DEFAULT_IDENTITY_KEYS: Dict[str, str] = {
    "Document": "document_id",
    "DocumentChunk": "chunk_id",
    "Chunk": "chunk_id",
    "FileVersion": "file_version_id",
    "MetadataTag": "tag_id",
    "QualityReport": "quality_report_id",
    "SecurityEvent": "security_event_id",
    "ProcessStep": "process_step_id",
    "AgencyUnit": "agency_unit_id",
    "RelationTemplate": "relation_type_id",
    "VectorSpace": "vector_space_id",
    "Policy": "policy_id",
    "AuditLog": "audit_log_id",
}

DEFAULT_IDENTITY_KEY = "id"
NODE_IDENTIFIER_SEPARATOR = "::"

from database.database_api_base import GraphDatabaseBackend, RelationshipIdentifier

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

NEO4J_IMPORT_ERROR = None
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except Exception as e:
    # Catch all exceptions to avoid import-time crashes (e.g. environment issues
    # like missing socket constants). Defer real connection attempts to connect().
    NEO4J_AVAILABLE = False
    NEO4J_IMPORT_ERROR = str(e)

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class Neo4jGraphBackend(GraphDatabaseBackend):
    """Neo4j Graph Database mit Adaptive Batch Processing

    Konsolidierte Implementierung: nutzt primär den offiziellen Neo4j-Python-Driver
    (bolt:// / neo4j:// URIs) und bietet bei Bedarf eine HTTP-Transaktions-API
    Fallback-Option. Initialisierung ist lazy (connect()).
    """

    def __init__(self, config: Dict):
        super().__init__(config)
        if not NEO4J_AVAILABLE:
            logger.warning("Neo4j driver not available at import time; connect() will fall back to HTTP if configured")

        # lazy initialization
        self._initialized = False
        # default to neo4j:// for modern driver routing, but allow explicit override
        self.uri = config.get('uri', 'neo4j://127.0.0.1:7687')
        self.username = config.get('username', 'neo4j')
        self.password = config.get('password', '')
        self.database = config.get('database', 'neo4j')
        self.driver = None

        # HTTP fallback options
        self.http_fallback = bool(config.get('use_http_fallback', True))
        self.http_url = config.get('http_url')  # optional explicit HTTP base URL
        self.http_session = None

        # Defensive: get_unified_database_strategy may be None or not callable
        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed: {exc}")
            self.strategy = None

        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"Neo4j Backend initialisiert mit Strategie {strategy_version}")

        validation_cfg = config.get('validation') or {}
        self.strict_validation = bool(validation_cfg.get('strict', True))
        self.allowed_node_labels: Set[str] = set(
            validation_cfg.get('allowed_node_labels') or DEFAULT_ALLOWED_NODE_LABELS
        )
        self.allowed_relationship_types: Set[str] = set(
            validation_cfg.get('allowed_relationship_types') or DEFAULT_ALLOWED_RELATION_TYPES
        )
        identity_cfg = validation_cfg.get('identity_keys') or {}
        configured_identity_keys = {
            label: key for label, key in identity_cfg.items()
            if label not in {'_default', '_separator'}
        }
        self.default_identity_key: str = identity_cfg.get('_default', DEFAULT_IDENTITY_KEY)
        self.identity_keys: Dict[str, str] = {**DEFAULT_IDENTITY_KEYS, **configured_identity_keys}
        self.identifier_separator: str = identity_cfg.get('_separator', NODE_IDENTIFIER_SEPARATOR)

    def connect(self) -> bool:
        """Stellt eine Verbindung her. Versucht zuerst den offiziellen Driver, dann optional HTTP-Fallback."""
        if self._initialized:
            return True

        # Try native driver first
        if NEO4J_AVAILABLE:
            try:
                self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
                # reduce noisy notifications
                try:
                    logging.getLogger('neo4j.notifications').setLevel(logging.WARNING)
                except Exception:
                    pass

                # quick smoke test
                try:
                    with self.driver.session(database=self.database) as session:
                        session.run("RETURN 1")
                    self._initialized = True
                    logger.info(f"Neo4j driver connected ({self.uri})")
                    return True
                except Exception:
                    # driver exists but session failed; fallthrough to fallback
                    logger.warning("Neo4j driver connected but session test failed; will try HTTP fallback if enabled")
            except Exception as e:
                logger.warning(f"Neo4j driver not usable: {e}")

        # HTTP fallback
        if self.http_fallback:
            if not REQUESTS_AVAILABLE:
                logger.error("HTTP fallback requested but 'requests' library is not available")
                return False

            http_url = self.http_url
            if not http_url:
                host = self.config.get('host') or '127.0.0.1'
                port = self.config.get('port') or 7474
                scheme = self.config.get('http_scheme') or 'http'
                http_url = f"{scheme}://{host}:{port}"

            if not http_url:
                logger.error("Cannot determine HTTP URL for Neo4j fallback")
                return False

            tx_url = f"{http_url.rstrip('/')}/db/{self.database}/tx/commit"
            payload = {"statements": [{"statement": "RETURN 1"}]}
            try:
                session = requests.Session()
                session.auth = (self.username, self.password)
                resp = session.post(tx_url, json=payload, timeout=5)
                if resp.status_code in (200, 201):
                    self.http_session = session
                    self._initialized = True
                    logger.info(f"Neo4j HTTP fallback connected to {tx_url}")
                    return True
                logger.error(f"Neo4j HTTP fallback returned status {resp.status_code}: {resp.text}")
                return False
            except Exception as e:
                logger.error(f"Neo4j HTTP fallback connect failed: {e}")
                return False

        logger.error("Neo4j connect failed: no driver available and HTTP fallback not configured")
        return False

    def disconnect(self) -> bool:
        """Schließt Treiber oder HTTP-Session sauber."""
        try:
            if getattr(self, 'driver', None):
                try:
                    self.driver.close()
                except Exception:
                    pass
                self.driver = None
        except Exception:
            pass

        try:
            if getattr(self, 'http_session', None):
                try:
                    self.http_session.close()
                except Exception:
                    pass
                self.http_session = None
        except Exception:
            pass

        self._initialized = False
        return True

    def _ensure_node_label_allowed(self, label: str) -> str:
        if not isinstance(label, str):
            raise ValueError("Node-Label muss ein String sein")
        if not LABEL_PATTERN.match(label):
            raise ValueError(f"Node-Label '{label}' enthält unzulässige Zeichen")
        if self.allowed_node_labels and label not in self.allowed_node_labels:
            message = f"Node-Label '{label}' nicht in erlaubter Whitelist"
            if self.strict_validation:
                raise ValueError(message)
            logger.warning(message)
        return label

    def _ensure_relationship_type_allowed(self, relationship_type: str) -> str:
        if not isinstance(relationship_type, str):
            raise ValueError("Relationship-Type muss ein String sein")
        if not LABEL_PATTERN.match(relationship_type):
            raise ValueError(f"Relationship-Type '{relationship_type}' enthält unzulässige Zeichen")
        if self.allowed_relationship_types and relationship_type not in self.allowed_relationship_types:
            message = f"Relationship-Type '{relationship_type}' nicht in erlaubter Whitelist"
            if self.strict_validation:
                raise ValueError(message)
            logger.warning(message)
        return relationship_type

    def _validate_property_key(self, key: str, *, context: str = "") -> Optional[str]:
        key_str = key if isinstance(key, str) else str(key)
        if not PROPERTY_KEY_PATTERN.match(key_str):
            message = f"Ungültiger Property-Key '{key_str}'" + (f" ({context})" if context else "")
            if self.strict_validation:
                raise ValueError(message)
            logger.warning(message)
            return None
        return key_str

    def _sanitize_value(self, value: Any, *, key: str, context: str) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            sanitized_list = []
            for item in value:
                if item is None or isinstance(item, (str, int, float, bool)):
                    sanitized_list.append(item)
                else:
                    message = (
                        f"Liste enthält nicht-primitive Werte am Key '{key}'" +
                        (f" ({context})" if context else "")
                    )
                    if self.strict_validation:
                        raise ValueError(message)
                    logger.warning(message)
                    sanitized_list.append(str(item))
            return sanitized_list
        if isinstance(value, dict):
            message = f"Dict-Properties sind nicht erlaubt für Key '{key}'" + (f" ({context})" if context else "")
            if self.strict_validation:
                raise ValueError(message)
            logger.warning(message)
            return str(value)
        return str(value)

    def _sanitize_properties(self, properties: Optional[Dict[str, Any]], *, context: str) -> Dict[str, Any]:
        if not properties:
            return {}

        sanitized: Dict[str, Any] = {}
        for raw_key, value in properties.items():
            key = self._validate_property_key(raw_key, context=context)
            if key is None:
                continue
            sanitized[key] = self._sanitize_value(value, key=key, context=context)
        return sanitized

    def _get_identity_key(self, label: Optional[str]) -> str:
        if label and label in self.identity_keys:
            return self.identity_keys[label]
        return self.default_identity_key

    def _format_business_identifier(self, label: Optional[str], value: Any) -> str:
        value_str = str(value)
        if label:
            return f"{label}{self.identifier_separator}{value_str}"
        return value_str

    def _coerce_identifier_value(self, value: Any, *, context: str) -> Any:
        sanitized = self._sanitize_value(value, key="identity", context=context)
        if isinstance(sanitized, list):
            raise ValueError(f"Identifier in Kontext '{context}' darf keine Liste sein")
        return sanitized

    def _resolve_node_identifier(
        self,
        identifier: Any,
        *,
        context: str,
        label_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Normalisiert Node-Referenzen auf Business- oder elementId-Matching."""

        if identifier is None:
            raise ValueError(f"Identifier im Kontext '{context}' darf nicht None sein")

        # Dict-Unterstützung für explizite Angaben
        if isinstance(identifier, dict):
            if 'element_id' in identifier or 'internal_id' in identifier:
                return {
                    'mode': 'internal',
                    'value': identifier.get('element_id') or identifier.get('internal_id')
                }
            label = identifier.get('label') or label_hint
            key = identifier.get('key')
            value = identifier.get('value')
            if value is None and key:
                value = identifier.get(key)
            if value is None:
                value = identifier.get('id')
            if value is None:
                raise ValueError(f"Identifier im Kontext '{context}' erfordert einen Wert")
            label = label or label_hint
            validated_label = self._ensure_node_label_allowed(label) if label else None
            identity_key = key or self._get_identity_key(validated_label)
            identity_key = self._validate_property_key(identity_key, context=f"{context} identity") or identity_key
            coerced_value = self._coerce_identifier_value(value, context=context)
            return {
                'mode': 'business',
                'label': validated_label,
                'key': identity_key,
                'value': coerced_value
            }

        # Tuple-Unterstützung: (Label, Wert)
        if isinstance(identifier, tuple) and len(identifier) == 2:
            label, value = identifier
            validated_label = self._ensure_node_label_allowed(label)
            identity_key = self._validate_property_key(
                self._get_identity_key(validated_label),
                context=f"{context} identity"
            ) or self._get_identity_key(validated_label)
            coerced_value = self._coerce_identifier_value(value, context=context)
            return {
                'mode': 'business',
                'label': validated_label,
                'key': identity_key,
                'value': coerced_value
            }

        # String-Unterstützung: Label::Wert oder elementId
        if isinstance(identifier, str):
            if self.identifier_separator in identifier:
                label_part, value_part = identifier.split(self.identifier_separator, 1)
                validated_label = self._ensure_node_label_allowed(label_part)
                identity_key = self._validate_property_key(
                    self._get_identity_key(validated_label),
                    context=f"{context} identity"
                ) or self._get_identity_key(validated_label)
                coerced_value = self._coerce_identifier_value(value_part, context=context)
                return {
                    'mode': 'business',
                    'label': validated_label,
                    'key': identity_key,
                    'value': coerced_value
                }
            # Fallback: elementId
            return {'mode': 'internal', 'value': identifier}

        # Standardfall: alles andere als elementId behandeln
        return {'mode': 'internal', 'value': identifier}

    def _prepare_match_component(
        self,
        alias: str,
        reference: Dict[str, Any],
        params: Dict[str, Any],
        value_param: str
    ) -> Tuple[str, str]:
        if reference['mode'] == 'internal':
            params[value_param] = reference['value']
            return f"({alias})", f"elementId({alias}) = ${value_param}"

        label = reference.get('label')
        key = reference['key']
        pattern = f"({alias}:{label})" if label else f"({alias})"
        params[value_param] = reference['value']
        return pattern, f"{alias}.{key} = ${value_param}"

    def _resolve_relationship_reference(self, identifier: Any, *, context: str) -> Dict[str, Any]:
        if isinstance(identifier, dict):
            rel_type = identifier.get('type') or identifier.get('relationship_type')
            if rel_type:
                validated_type = self._ensure_relationship_type_allowed(rel_type)
            else:
                validated_type = None
            if 'id' in identifier:
                value = identifier['id']
            elif 'value' in identifier:
                value = identifier['value']
            else:
                value = identifier.get('relationship_id')
            if value is None:
                raise ValueError(f"Relationship-Identifier im Kontext '{context}' erfordert einen Wert")
            coerced_value = self._coerce_identifier_value(value, context=context)
            if validated_type:
                return {'mode': 'business', 'type': validated_type, 'value': coerced_value}
            return {'mode': 'internal', 'value': coerced_value}

        if isinstance(identifier, str) and self.identifier_separator in identifier:
            rel_type, rel_business_id = identifier.split(self.identifier_separator, 1)
            validated_type = self._ensure_relationship_type_allowed(rel_type)
            coerced_value = self._coerce_identifier_value(rel_business_id, context=context)
            return {'mode': 'business', 'type': validated_type, 'value': coerced_value}

        return {'mode': 'internal', 'value': identifier}

    def _build_relationship_match(
        self,
        identifier: Any,
        params: Dict[str, Any],
        *,
        context: str
    ) -> Tuple[str, str]:
        reference = self._resolve_relationship_reference(identifier, context=context)
        if reference['mode'] == 'business':
            params['edge_identifier'] = reference['value']
            relationship_type = reference['type']
            return (
                f"MATCH ()-[r:{relationship_type}]-()",
                "r.id = $edge_identifier OR r.relationship_id = $edge_identifier"
            )

        params['edge_identifier'] = reference['value']
        return "MATCH ()-[r]-()", "elementId(r) = $edge_identifier"
        
    def _backend_connect(self) -> bool:
        """Implementiert Neo4j-spezifische Verbindungslogik"""
        try:
            # Konfiguriere Neo4j Driver 
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            
            # Reduziere Notification-Logging für diesen Driver
            import logging
            # Neo4j Driver Notifications auf WARNING Level setzen
            logging.getLogger('neo4j.notifications').setLevel(logging.WARNING)
            
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            
            logging.info(f"Neo4j verbunden: {self.uri}")
            return True
            
        except Exception as e:
            logging.error(f"Neo4j Verbindung fehlgeschlagen: {e}")
            return False
    
    def disconnect(self):
        if self.driver:
            self.driver.close()
            self.driver = None
    
    def is_available(self) -> bool:
        try:
            if self.driver:
                with self.driver.session(database=self.database) as session:
                    session.run("RETURN 1")
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        return "Neo4j"
    
    def create_node(self, node_type: str, properties: Dict, merge_key: str = None) -> str:
        """
        Erstellt oder aktualisiert einen Node in Neo4j
        
        Args:
            node_type: Label des Nodes
            properties: Properties des Nodes
            merge_key: Property-Key für MERGE (wenn None, wird CREATE verwendet)
        
        Returns:
            str: Node-ID oder None bei Fehler
        """
        try:
            if not self.driver:
                return None

            label = self._ensure_node_label_allowed(node_type)
            sanitized_props = self._sanitize_properties(properties or {}, context=f"Node<{label}>")

            use_merge = False
            merge_value = None
            merge_key_name: Optional[str] = None
            if merge_key:
                merge_key_name = self._validate_property_key(merge_key, context=f"Node<{label}> merge_key")
                if merge_key_name and merge_key_name in sanitized_props:
                    merge_value = sanitized_props[merge_key_name]
                    if merge_value is None:
                        message = f"MERGE-Key '{merge_key_name}' für Node '{label}' darf nicht None sein"
                        if self.strict_validation:
                            raise ValueError(message)
                        logger.warning(message + " – fallback auf CREATE")
                    else:
                        use_merge = True
                elif merge_key_name:
                    message = f"MERGE-Key '{merge_key_name}' fehlt in Properties für Node '{label}'"
                    if self.strict_validation:
                        raise ValueError(message)
                    logger.warning(message + " – fallback auf CREATE")
                else:
                    logger.warning(f"MERGE-Key '{merge_key}' ungültig – fallback auf CREATE")
            else:
                default_key_candidate = self._validate_property_key(
                    self._get_identity_key(label),
                    context=f"Node<{label}> identity"
                ) or self._get_identity_key(label)
                if default_key_candidate in sanitized_props:
                    merge_key_name = default_key_candidate
                    merge_value = sanitized_props[merge_key_name]
                    if merge_value is None:
                        message = (
                            f"Identitäts-Property '{merge_key_name}' für Node '{label}' darf nicht None sein"
                        )
                        if self.strict_validation:
                            raise ValueError(message)
                        logger.warning(message + " – fallback auf CREATE")
                        merge_key_name = None
                        merge_value = None
                    else:
                        use_merge = True

            params = {'props': sanitized_props}

            with self.driver.session(database=self.database) as session:
                if use_merge and merge_key_name:
                    params['merge_value'] = merge_value
                    query = f"""
                        MERGE (n:{label} {{{merge_key_name}: $merge_value}})
                        SET n += $props
                        RETURN elementId(n) as node_id
                    """
                else:
                    query = f"""
                        CREATE (n:{label})
                        SET n += $props
                        RETURN elementId(n) as node_id
                    """

                result = session.run(query, params)
                record = result.single()

                if record:
                    node_id = record['node_id']
                    logging.debug(f"Neo4j Node erstellt/aktualisiert: {label} (ID: {node_id})")
                    business_identifier = None
                    if merge_key_name and merge_key_name in sanitized_props:
                        try:
                            business_identifier = self._coerce_identifier_value(
                                sanitized_props[merge_key_name],
                                context=f"Node<{label}> identity return"
                            )
                        except ValueError:
                            business_identifier = None
                    if business_identifier is not None:
                        return self._format_business_identifier(label, business_identifier)
                    return node_id
                return None
                
        except Exception as e:
            logging.error(f"Neo4j Node erstellen fehlgeschlagen: {e}")
            return None
    
    def create_edge(self, from_id: str, to_id: str, edge_type: str, 
                   properties: Dict = None) -> str:
        try:
            if not self.driver:
                return None

            relationship_type = self._ensure_relationship_type_allowed(edge_type)
            rel_props = self._sanitize_properties(properties or {}, context=f"Relationship<{relationship_type}>")

            with self.driver.session(database=self.database) as session:
                params = {'props': rel_props}
                source_ref = self._resolve_node_identifier(from_id, context="create_edge.from_id")
                target_ref = self._resolve_node_identifier(to_id, context="create_edge.to_id")
                pattern_a, cond_a = self._prepare_match_component('a', source_ref, params, 'from_identifier')
                pattern_b, cond_b = self._prepare_match_component('b', target_ref, params, 'to_identifier')
                where_clauses = [clause for clause in (cond_a, cond_b) if clause]
                match_clause = f"MATCH {pattern_a}, {pattern_b}"
                where_clause = ""
                if where_clauses:
                    where_clause = "WHERE " + " AND ".join(where_clauses)

                query = f"""
                    {match_clause}
                    {where_clause}
                    MERGE (a)-[r:{relationship_type}]->(b)
                    SET r += $props
                    RETURN elementId(r) as edge_id
                """

                result = session.run(query, params)
                record = result.single()

                if record:
                    return record['edge_id']
                return None
                
        except Exception as e:
            logging.error(f"Neo4j Edge erstellen fehlgeschlagen: {e}")
            return None
    
    def create_relationship(self, from_node_type: str, from_node_props: Dict, 
                           to_node_type: str, to_node_props: Dict, 
                           relationship_type: str, relationship_props: Dict = None) -> Optional[str]:
        """
        Erstellt eine Relationship zwischen zwei Nodes
        
        Args:
            from_node_type: Label des Quell-Nodes
            from_node_props: Properties zum Finden des Quell-Nodes
            to_node_type: Label des Ziel-Nodes  
            to_node_props: Properties zum Finden des Ziel-Nodes
            relationship_type: Typ der Relationship
            relationship_props: Properties der Relationship
        
        Returns:
            str: ID der erstellten Relationship oder None bei Fehler
        """
        try:
            if not self.driver:
                return None

            from_label = self._ensure_node_label_allowed(from_node_type)
            to_label = self._ensure_node_label_allowed(to_node_type)
            rel_type = self._ensure_relationship_type_allowed(relationship_type)

            from_props = self._sanitize_properties(from_node_props or {}, context=f"from_node<{from_label}>")
            to_props = self._sanitize_properties(to_node_props or {}, context=f"to_node<{to_label}>")

            if not from_props or not to_props:
                message = (
                    f"from_node_props ({from_label}) und to_node_props ({to_label}) dürfen nicht leer sein"
                )
                if self.strict_validation:
                    raise ValueError(message)
                logger.warning(message)
                return None

            rel_props = self._sanitize_properties(relationship_props or {}, context=f"Relationship<{rel_type}>")

            with self.driver.session(database=self.database) as session:
                params: Dict[str, Any] = {'rel_props': rel_props}

                from_conditions = []
                for key, value in from_props.items():
                    param_key = f"from_{key}"
                    from_conditions.append(f"from_node.{key} = ${param_key}")
                    params[param_key] = value

                to_conditions = []
                for key, value in to_props.items():
                    param_key = f"to_{key}"
                    to_conditions.append(f"to_node.{key} = ${param_key}")
                    params[param_key] = value

                where_clauses = from_conditions + to_conditions

                query = f"""
                    MATCH (from_node:{from_label}), (to_node:{to_label})
                    WHERE {" AND ".join(where_clauses)}
                    MERGE (from_node)-[r:{rel_type}]->(to_node)
                    SET r += $rel_props
                    RETURN elementId(r) as relationship_id
                """

                result = session.run(query, params)
                record = result.single()

                if record:
                    relationship_id = record['relationship_id']
                    logging.debug(f"Neo4j Relationship erstellt: {rel_type} (ID: {relationship_id})")
                    return relationship_id
                else:
                    logging.warning(
                        f"Neo4j Relationship konnte nicht erstellt werden: {from_label} -> {to_label}"
                    )
                    return None
                    
        except Exception as e:
            logging.error(f"Neo4j Relationship erstellen fehlgeschlagen: {e}")
            return None

    def create_relationship_by_id(self, from_node_id: str, to_node_id: str, 
                                  relationship_type: str, properties: Dict = None) -> Optional[str]:
        """
        Erstellt eine Relationship zwischen zwei Nodes anhand ihrer IDs
        
        Args:
            from_node_id: ID des Quell-Nodes (wird als 'id' Property gesucht)
            to_node_id: ID des Ziel-Nodes (wird als 'id' Property gesucht)
            relationship_type: Typ der Relationship
            properties: Properties der Relationship
        
        Returns:
            str: ID der erstellten Relationship oder None bei Fehler
        """
        try:
            if not self.driver:
                return None

            rel_type = self._ensure_relationship_type_allowed(relationship_type)
            rel_props = self._sanitize_properties(properties or {}, context=f"Relationship<{rel_type}>")

            with self.driver.session(database=self.database) as session:
                params = {
                    'from_id': from_node_id,
                    'to_id': to_node_id,
                    'rel_props': rel_props
                }

                query = f"""
                    MATCH (from_node {{id: $from_id}}), (to_node {{id: $to_id}})
                    MERGE (from_node)-[r:{rel_type}]->(to_node)
                    SET r += $rel_props
                    RETURN elementId(r) as relationship_id
                """

                result = session.run(query, params)
                record = result.single()

                if record:
                    relationship_id = record['relationship_id']
                    logging.debug(f"Neo4j Relationship by ID erstellt: {rel_type} (ID: {relationship_id})")
                    return relationship_id
                else:
                    logging.warning(
                        f"Neo4j Relationship by ID konnte nicht erstellt werden: {from_node_id} -> {to_node_id}"
                    )
                    return None
                    
        except Exception as e:
            logging.error(f"Neo4j Relationship by ID erstellen fehlgeschlagen: {e}")
            return None
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        try:
            if not self.driver:
                return None
            
            with self.driver.session(database=self.database) as session:
                params: Dict[str, Any] = {}
                reference = self._resolve_node_identifier(node_id, context="get_node.node_id")
                pattern, condition = self._prepare_match_component('n', reference, params, 'node_identifier')
                match_clause = f"MATCH {pattern}"
                where_clause = f"WHERE {condition}" if condition else ""

                query = f"""
                    {match_clause}
                    {where_clause}
                    RETURN n, labels(n) as node_labels, elementId(n) as internal_id
                """

                result = session.run(query, params)
                record = result.single()
                
                if record:
                    node = record['n']
                    labels = record['node_labels'] or []
                    primary_label = labels[0] if labels else None
                    business_key = self._get_identity_key(primary_label)
                    business_id = None
                    if primary_label and business_key in node:
                        try:
                            business_id = self._coerce_identifier_value(
                                node[business_key],
                                context=f"get_node<{primary_label}> business_id"
                            )
                        except ValueError:
                            business_id = None
                    return {
                        'id': business_id or record['internal_id'],
                        'internal_id': record['internal_id'],
                        'business_id': business_id,
                        'type': primary_label or 'Unknown',
                        'properties': dict(node),
                        'labels': labels
                    }
                return None
                
        except Exception as e:
            logging.error(f"Neo4j Node abrufen fehlgeschlagen: {e}")
            return None
    
    def find_nodes(self, node_type: str, filters: Dict = None) -> List[Dict]:
        try:
            if not self.driver:
                return []
            
            with self.driver.session(database=self.database) as session:
                params = {}
                where_conditions = []
                
                # Node type filter
                query = f"MATCH (n:{node_type})"
                
                # Property filters
                if filters:
                    for key, value in filters.items():
                        where_conditions.append(f"n.{key} = ${key}")
                        params[key] = value
                
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
                
                query += " RETURN n, labels(n) as node_labels, elementId(n) as node_id"
                
                result = session.run(query, params)
                
                results = []
                for record in result:
                    node = record['n']
                    labels = record['node_labels'] or []
                    primary_label = labels[0] if labels else None
                    business_key = self._get_identity_key(primary_label)
                    business_id = None
                    if primary_label and business_key in node:
                        try:
                            business_id = self._coerce_identifier_value(
                                node[business_key],
                                context=f"find_nodes<{primary_label}> business_id"
                            )
                        except ValueError:
                            business_id = None
                    results.append({
                        'id': business_id or record['node_id'],
                        'internal_id': record['node_id'],
                        'business_id': business_id,
                        'type': primary_label if primary_label else 'Unknown',
                        'properties': dict(node),
                        'labels': labels
                    })
                
                return results
                
        except Exception as e:
            logging.error(f"Neo4j Nodes suchen fehlgeschlagen: {e}")
            return []
    
    def get_relationships(self, node_id: str, direction: str = "both") -> List[Dict]:
        try:
            if not self.driver:
                return []
            
            with self.driver.session(database=self.database) as session:
                params: Dict[str, Any] = {}
                reference = self._resolve_node_identifier(node_id, context="get_relationships.node_id")
                pattern_n, cond_n = self._prepare_match_component('n', reference, params, 'node_identifier')
                base_match = f"MATCH {pattern_n}"
                base_where = f"WHERE {cond_n}" if cond_n else ""

                if direction == "outgoing":
                    query = f"""
                        {base_match}
                        {base_where}
                        MATCH (n)-[r]->(target)
                        RETURN r, type(r) as edge_type, elementId(r) as edge_id,
                               target, labels(target) as target_labels, elementId(target) as target_id
                    """
                elif direction == "incoming":
                    query = f"""
                        {base_match}
                        {base_where}
                        MATCH (source)-[r]->(n)
                        RETURN r, type(r) as edge_type, elementId(r) as edge_id,
                               source as target, labels(source) as target_labels, elementId(source) as target_id
                    """
                else:  # both
                    query = f"""
                        {base_match}
                        {base_where}
                        MATCH (n)-[r]-(target)
                        RETURN r, type(r) as edge_type, elementId(r) as edge_id,
                               target, labels(target) as target_labels, elementId(target) as target_id
                    """

                result = session.run(query, params)
                
                results = []
                for record in result:
                    relationship = record['r']
                    target = record['target']
                    target_labels = record['target_labels'] or []
                    target_primary = target_labels[0] if target_labels else None
                    target_business_key = self._get_identity_key(target_primary)
                    target_business_id = None
                    if target_primary and target_business_key in target:
                        try:
                            target_business_id = self._coerce_identifier_value(
                                target[target_business_key],
                                context=f"get_relationships<{target_primary}> target business_id"
                            )
                        except ValueError:
                            target_business_id = None
                    rel_props = dict(relationship)
                    relationship_business_id = rel_props.get('id') or rel_props.get('relationship_id')
                    results.append({
                        'edge_id': relationship_business_id or record['edge_id'],
                        'internal_id': record['edge_id'],
                        'business_id': relationship_business_id,
                        'edge_type': record['edge_type'],
                        'edge_properties': rel_props,
                        'target_id': target_business_id or record['target_id'],
                        'target_internal_id': record['target_id'],
                        'target_business_id': target_business_id,
                        'target_type': target_primary if target_primary else 'Unknown',
                        'target_properties': dict(target),
                        'target_labels': target_labels
                    })
                
                return results
                
        except Exception as e:
            logging.error(f"Neo4j Relationships abrufen fehlgeschlagen: {e}")
            return []
    
    def run_cypher(self, query: str, params: Dict = None) -> List[Dict]:
        """Führe eine custom Cypher Query aus"""
        try:
            if not self.driver:
                return []
            
            with self.driver.session(database=self.database) as session:
                result = session.run(query, params or {})
                
                results = []
                for record in result:
                    results.append(dict(record))
                
                return results
                
        except Exception as e:
            logging.error(f"Neo4j Cypher Query fehlgeschlagen: {e}")
            return []

    def execute_query(self, query: str, params: Tuple = None) -> List[Dict]:
        """Implementierung der abstrakten execute_query Methode für Neo4j"""
        # Konvertiere Tuple-params zu Dict-params für Neo4j
        dict_params = {}
        if params:
            # Für parametrisierte Queries: Tuple zu Dict konvertieren
            for i, param in enumerate(params):
                dict_params[f'param_{i}'] = param
        
        return self.run_cypher(query, dict_params)

    def create_table(self, table_name: str, schema: Dict) -> bool:
        """Neo4j hat keine Tabellen - Dummy-Implementierung für Interface-Kompatibilität"""
        logger.warning("create_table nicht anwendbar für Neo4j Graph Database")
        return True

    def insert_record(self, table_name: str, data: Dict) -> Any:
        """Erstelle Node als Record-Äquivalent"""
        try:
            # Verwende table_name als Node-Label
            return self.create_node(table_name, data)
        except Exception as e:
            logger.error(f"Neo4j insert_record fehlgeschlagen: {e}")
            return None

    def update_record(self, table_name: str, record_id: Any, data: Dict) -> bool:
        """Update Node-Properties"""
        try:
            if not self.driver:
                return False
            
            with self.driver.session(database=self.database) as session:
                # Setze Properties für Node mit gegebener ID
                set_clauses = []
                params: Dict[str, Any] = {}
                target_label = self._ensure_node_label_allowed(table_name)
                reference = self._resolve_node_identifier(
                    record_id,
                    context=f"update_record<{target_label}>",
                    label_hint=target_label
                )
                if reference['mode'] == 'internal':
                    params['node_identifier'] = reference['value']
                    pattern = f"(n:{target_label})"
                    fallback_identity_key = self._validate_property_key(
                        self._get_identity_key(target_label),
                        context=f"update_record<{target_label}> identity"
                    ) or self._get_identity_key(target_label)
                    where_condition = (
                        f"elementId(n) = $node_identifier OR n.{fallback_identity_key} = $node_identifier"
                    )
                else:
                    label = reference.get('label') or target_label
                    pattern = f"(n:{label})"
                    params['node_identifier'] = reference['value']
                    identity_key = reference['key']
                    where_condition = f"n.{identity_key} = $node_identifier"

                for key, value in data.items():
                    param_key = f'val_{key}'
                    set_clauses.append(f'n.{key} = ${param_key}')
                    params[param_key] = value
                
                query = f"""
                    MATCH {pattern}
                    WHERE {where_condition}
                    SET {', '.join(set_clauses)}
                    RETURN n
                """
                
                result = session.run(query, params)
                return result.single() is not None
                
        except Exception as e:
            logger.error(f"Neo4j update_record fehlgeschlagen: {e}")
            return False
    
    def get_node_count(self) -> int:
        """Anzahl aller Nodes"""
        try:
            results = self.run_cypher("MATCH (n) RETURN count(n) as count")
            if results:
                return results[0]['count']
            return 0
            
        except Exception as e:
            logging.error(f"Neo4j Node Count fehlgeschlagen: {e}")
            return 0
    
    def get_relationship_count(self) -> int:
        """Anzahl aller Relationships"""
        try:
            results = self.run_cypher("MATCH ()-[r]->() RETURN count(r) as count")
            if results:
                return results[0]['count']
            return 0
            
        except Exception as e:
            logging.error(f"Neo4j Relationship Count fehlgeschlagen: {e}")
            return 0
    
    def delete_node(self, node_id: str) -> bool:
        """Lösche Node und alle Relationships"""
        try:
            if not self.driver:
                return False
            
            with self.driver.session(database=self.database) as session:
                params: Dict[str, Any] = {}
                reference = self._resolve_node_identifier(node_id, context="delete_node.node_id")
                pattern, condition = self._prepare_match_component('n', reference, params, 'node_identifier')
                match_clause = f"MATCH {pattern}"
                where_clause = f"WHERE {condition}" if condition else ""

                query = f"""
                    {match_clause}
                    {where_clause}
                    DETACH DELETE n
                """

                session.run(query, params)
                return True
                
        except Exception as e:
            logging.error(f"Neo4j Node löschen fehlgeschlagen: {e}")
            return False
    
    def delete_relationship(self, edge_id: RelationshipIdentifier) -> bool:
        """Löscht Relationship anhand eines generischen Identifiers."""

        try:
            if not self.driver:
                return False

            with self.driver.session(database=self.database) as session:
                params: Dict[str, Any] = {}
                match_clause, where_condition = self._build_relationship_match(
                    edge_id,
                    params,
                    context="delete_relationship"
                )
                where_clause = f"WHERE {where_condition}" if where_condition else ""

                query = f"""
                    {match_clause}
                    {where_clause}
                    DELETE r
                """

                session.run(query, params)
                return True

        except Exception as e:
            logging.error(f"Neo4j Relationship löschen fehlgeschlagen: {e}")
            return False

    def update_relationship_weight(
        self,
        relationship_id: RelationshipIdentifier,
        *,
        weight: float,
        confidence: Optional[float] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Aktualisiert Gewichtungs-Properties einer Relationship inkl. Historie."""

        if weight is None:
            raise ValueError("weight darf nicht None sein")

        try:
            weight_value = float(weight)
        except (TypeError, ValueError):
            raise ValueError("weight muss numerisch sein")

        confidence_value: Optional[float]
        if confidence is not None:
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                raise ValueError("confidence muss numerisch sein")
        else:
            confidence_value = None

        history_timestamp = (timestamp or datetime.now(timezone.utc)).isoformat()
        history_entry = {
            "weight": weight_value,
            "confidence": confidence_value,
            "reason": reason,
            "updated_at": history_timestamp,
        }
        if metadata:
            history_entry["metadata"] = metadata

        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

        params: Dict[str, Any] = {}
        match_clause, where_condition = self._build_relationship_match(
            relationship_id,
            params,
            context="update_relationship_weight"
        )
        where_clause = f"WHERE {where_condition}" if where_condition else ""

        try:
            if not self.driver:
                return None

            with self.driver.session(database=self.database) as session:
                fetch_query = f"""
                    {match_clause}
                    {where_clause}
                    RETURN elementId(r) as edge_id, r.weight_history_json as history_json
                """
                fetch_result = session.run(fetch_query, params)
                fetch_record = fetch_result.single()
                if not fetch_record:
                    return None

                existing_history_raw = fetch_record.get('history_json')
                try:
                    history_data = json.loads(existing_history_raw) if existing_history_raw else []
                except (TypeError, json.JSONDecodeError):
                    history_data = []
                history_data.append(history_entry)

                params.update({
                    'weight': weight_value,
                    'history_json': json.dumps(history_data, ensure_ascii=False),
                    'timestamp': history_timestamp,
                })

                set_clauses = [
                    "r.weight = $weight",
                    "r.weight_updated_at = datetime($timestamp)",
                    "r.weight_history_json = $history_json",
                    "r.last_modified_at = datetime($timestamp)",
                    "r.is_active = coalesce(r.is_active, true)",
                ]

                if confidence_value is not None:
                    params['weight_confidence'] = confidence_value
                    set_clauses.append("r.weight_confidence = $weight_confidence")

                if metadata_json is not None:
                    params['weight_metadata_json'] = metadata_json
                    set_clauses.append("r.weight_metadata_json = $weight_metadata_json")

                if reason:
                    params['weight_reason'] = reason
                    set_clauses.append("r.weight_update_reason = $weight_reason")

                update_query = f"""
                    {match_clause}
                    {where_clause}
                    SET {', '.join(set_clauses)}
                    RETURN elementId(r) as edge_id,
                           type(r) as edge_type,
                           r.weight as weight,
                           r.weight_confidence as weight_confidence,
                           r.weight_history_json as history_json,
                           r.is_active as is_active
                """

                update_result = session.run(update_query, params)
                update_record = update_result.single()
                if not update_record:
                    return None

                history_json_raw = update_record.get('history_json')
                try:
                    history = json.loads(history_json_raw) if history_json_raw else []
                except (TypeError, json.JSONDecodeError):
                    history = []

                return {
                    'edge_id': update_record.get('edge_id'),
                    'edge_type': update_record.get('edge_type'),
                    'weight': update_record.get('weight'),
                    'weight_confidence': update_record.get('weight_confidence'),
                    'history': history,
                    'is_active': update_record.get('is_active', True),
                }

        except Exception as exc:
            logger.error(f"Neo4j Relationship-Gewicht aktualisieren fehlgeschlagen: {exc}")
            return None

    def soft_delete_relationship(
        self,
        relationship_id: RelationshipIdentifier,
        *,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Markiert eine Relationship als inaktiv (Soft Delete) und protokolliert die Aktion."""

        lifecycle_timestamp = (timestamp or datetime.now(timezone.utc)).isoformat()
        lifecycle_entry = {
            "event": "soft_delete",
            "timestamp": lifecycle_timestamp,
            "reason": reason,
        }
        if metadata:
            lifecycle_entry["metadata"] = metadata

        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

        params: Dict[str, Any] = {}
        match_clause, where_condition = self._build_relationship_match(
            relationship_id,
            params,
            context="soft_delete_relationship"
        )
        where_clause = f"WHERE {where_condition}" if where_condition else ""

        try:
            if not self.driver:
                return False

            with self.driver.session(database=self.database) as session:
                fetch_query = f"""
                    {match_clause}
                    {where_clause}
                    RETURN r.lifecycle_history_json as history_json
                """
                fetch_result = session.run(fetch_query, params)
                fetch_record = fetch_result.single()
                if not fetch_record:
                    return False

                existing_history_raw = fetch_record.get('history_json')
                try:
                    history_data = json.loads(existing_history_raw) if existing_history_raw else []
                except (TypeError, json.JSONDecodeError):
                    history_data = []
                history_data.append(lifecycle_entry)

                params.update({
                    'timestamp': lifecycle_timestamp,
                    'history_json': json.dumps(history_data, ensure_ascii=False),
                })

                set_clauses = [
                    "r.is_active = false",
                    "r.deleted_at = datetime($timestamp)",
                    "r.lifecycle_history_json = $history_json",
                    "r.last_modified_at = datetime($timestamp)",
                ]

                if metadata_json is not None:
                    params['lifecycle_metadata_json'] = metadata_json
                    set_clauses.append("r.lifecycle_metadata_json = $lifecycle_metadata_json")

                if reason:
                    params['deletion_reason'] = reason
                    set_clauses.append("r.deletion_reason = $deletion_reason")

                update_query = f"""
                    {match_clause}
                    {where_clause}
                    SET {', '.join(set_clauses)}
                    RETURN elementId(r) as edge_id
                """

                update_result = session.run(update_query, params)
                return update_result.single() is not None

        except Exception as exc:
            logger.error(f"Neo4j Relationship Soft Delete fehlgeschlagen: {exc}")
            return False

    def restore_relationship(
        self,
        relationship_id: RelationshipIdentifier,
        *,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Reaktiviert eine zuvor soft-gelöschte Relationship und dokumentiert die Wiederherstellung."""

        lifecycle_timestamp = (timestamp or datetime.now(timezone.utc)).isoformat()
        lifecycle_entry = {
            "event": "restore",
            "timestamp": lifecycle_timestamp,
            "reason": reason,
        }
        if metadata:
            lifecycle_entry["metadata"] = metadata

        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

        params: Dict[str, Any] = {}
        match_clause, where_condition = self._build_relationship_match(
            relationship_id,
            params,
            context="restore_relationship"
        )
        where_clause = f"WHERE {where_condition}" if where_condition else ""

        try:
            if not self.driver:
                return False

            with self.driver.session(database=self.database) as session:
                fetch_query = f"""
                    {match_clause}
                    {where_clause}
                    RETURN r.lifecycle_history_json as history_json
                """
                fetch_result = session.run(fetch_query, params)
                fetch_record = fetch_result.single()
                if not fetch_record:
                    return False

                existing_history_raw = fetch_record.get('history_json')
                try:
                    history_data = json.loads(existing_history_raw) if existing_history_raw else []
                except (TypeError, json.JSONDecodeError):
                    history_data = []
                history_data.append(lifecycle_entry)

                params.update({
                    'timestamp': lifecycle_timestamp,
                    'history_json': json.dumps(history_data, ensure_ascii=False),
                })

                set_clauses = [
                    "r.is_active = true",
                    "r.lifecycle_history_json = $history_json",
                    "r.last_modified_at = datetime($timestamp)",
                    "r.deleted_at = NULL",
                ]

                if metadata_json is not None:
                    params['lifecycle_metadata_json'] = metadata_json
                    set_clauses.append("r.lifecycle_metadata_json = $lifecycle_metadata_json")

                if reason:
                    params['restore_reason'] = reason
                    set_clauses.append("r.restore_reason = $restore_reason")

                set_clauses.append("r.deletion_reason = NULL")

                update_query = f"""
                    {match_clause}
                    {where_clause}
                    SET {', '.join(set_clauses)}
                    RETURN elementId(r) as edge_id
                """

                update_result = session.run(update_query, params)
                return update_result.single() is not None

        except Exception as exc:
            logger.error(f"Neo4j Relationship Restore fehlgeschlagen: {exc}")
            return False
    
    def get_graph_stats(self) -> Dict:
        """Graph Statistiken abrufen"""
        try:
            if not self.driver:
                return {}
            
            with self.driver.session(database=self.database) as session:
                # Anzahl Nodes
                node_result = session.run("MATCH (n) RETURN count(n) as node_count")
                node_count = node_result.single()['node_count']
                
                # Anzahl Relationships
                edge_result = session.run("MATCH ()-[r]->() RETURN count(r) as edge_count")
                edge_count = edge_result.single()['edge_count']
                
                # Labels zählen
                label_result = session.run("CALL db.labels()")
                labels = [record['label'] for record in label_result]
                
                # Relationship Types zählen
                rel_result = session.run("CALL db.relationshipTypes()")
                rel_types = [record['relationshipType'] for record in rel_result]
                
                return {
                    'nodes': node_count,
                    'edges': edge_count,
                    'labels': labels,
                    'relationship_types': rel_types,
                    'backend': 'Neo4j'
                }
                
        except Exception as e:
            logging.error(f"Neo4j Stats abrufen fehlgeschlagen: {e}")
            return {}
    
    def create_document_with_strategy(self, file_path: str, content: str, **metadata) -> str:
        """Erstelle Document-Node mit der neuen Unified Strategy"""
        try:
            # Generiere ID und Properties mit Strategy
            document_id = self.strategy.generate_document_id(file_path, content[:200])
            properties = self.strategy.create_document_properties(
                file_path=file_path,
                content_preview=content[:200],
                **metadata
            )
            
            # Erstelle Node mit MERGE für Eindeutigkeit
            return self.create_node("Document", properties, merge_key="id")
            
        except Exception as e:
            logger.error(f"Document mit Strategy erstellen fehlgeschlagen: {e}")
            return None
    
    def create_chunk_with_strategy(self, document_id: str, chunk_index: int, 
                                  content: str, **metadata) -> str:
        """Erstelle DocumentChunk-Node mit der neuen Unified Strategy"""
        try:
            # Generiere Chunk ID und Properties
            chunk_id = self.strategy.generate_chunk_id(document_id, chunk_index)
            properties = self.strategy.create_chunk_properties(
                document_id=document_id,
                chunk_index=chunk_index,
                content=content,
                **metadata
            )
            
            # Erstelle Node mit MERGE für Eindeutigkeit
            return self.create_node("DocumentChunk", properties, merge_key="id")
            
        except Exception as e:
            logger.error(f"Chunk mit Strategy erstellen fehlgeschlagen: {e}")
            return None
    
    def create_relationship_with_strategy(self, from_node_id: str, to_node_id: str, 
                                         relationship_type: str, **metadata) -> str:
        """Erstelle Relationship mit der neuen Unified Strategy"""
        try:
            rel_type = self._ensure_relationship_type_allowed(relationship_type)
            raw_props = self.strategy.create_relationship_properties(
                relationship_type=rel_type,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                **metadata
            )
            rel_props = self._sanitize_properties(raw_props or {}, context=f"Relationship<{rel_type}> strategy")

            with self.driver.session(database=self.database) as session:
                query = f"""
                MATCH (from {{id: $from_id}})
                MATCH (to {{id: $to_id}})
                MERGE (from)-[r:{rel_type}]->(to)
                SET r += $properties
                RETURN id(r) as rel_id
                """

                result = session.run(query, {
                    'from_id': from_node_id,
                    'to_id': to_node_id,
                    'properties': rel_props
                })

                record = result.single()
                if record:
                    rel_id = str(record['rel_id'])
                    logger.info(f"✅ Relationship {rel_type} erstellt: {rel_id}")
                    return rel_id
                else:
                    logger.error("❌ Relationship konnte nicht erstellt werden - Nodes nicht gefunden")
                    return None
            
        except Exception as e:
            logger.error(f"Relationship mit Strategy erstellen fehlgeschlagen: {e}")
            return None


def get_backend_class():
    """Factory-Funktion für Neo4j Backend"""
    return Neo4jGraphBackend

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_neo4j"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
module_file_key = "6db513a5e969d6dd3eaf3176f711c1f034484054c33b325d7b38601f184281dc"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
