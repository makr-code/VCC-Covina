import logging
from typing import Callable, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Registry
_REGISTRY: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], bool]] = {}


def register(name: str, handler: Callable[[Dict[str, Any], Dict[str, Any]], bool]) -> None:
    """Register a compensation handler by name."""
    _REGISTRY[name] = handler


def get(name: str) -> Optional[Callable[[Dict[str, Any], Dict[str, Any]], bool]]:
    return _REGISTRY.get(name)


# Default handlers
def relational_delete_handler(payload: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """Default relational delete handler expects payload: { 'table': str, 'id': str }"""
    try:
        table = payload.get('table')
        record_id = payload.get('id') or payload.get('document_id')
        backend = ctx.get('relational_backend')
        if not backend:
            logger.debug("No relational backend provided to compensation handler")
            return False
        if not table or not record_id:
            logger.debug("relational_delete_handler missing table or id in payload")
            return False

        # Use delete helper if available
        if hasattr(backend, 'delete'):
                try:
                    deleted = backend.delete(table, {'id': record_id})
                    if deleted:
                        return True
                    # If delete returned False, check whether the row still exists; if not, treat as idempotent success
                    try:
                        rows = backend.execute_query(f"SELECT id FROM {table} WHERE id = ?", (record_id,))
                        if not rows:
                            return True
                    except Exception:
                        pass
                    return False
                except Exception:
                    # fall through to fallback
                    pass

        # Fallback: execute raw SQL
        try:
            backend.execute_query(f"DELETE FROM {table} WHERE id = ?", (record_id,))
            return True
        except Exception as exc:
            logger.debug("Relational delete fallback failed: %s", exc)
            return False
    except Exception as exc:
        logger.exception("relational_delete_handler failed: %s", exc)
        return False


def graph_delete_node_handler(payload: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """Attempt to delete a node from graph backend.

    Expected payload: { 'label': str, 'id': str } or { 'identity': str }
    ctx should provide 'graph_backend'. The handler will try several common
    backend methods (delete_node, delete, delete_by_id) and return True if any succeed.
    """
    try:
        backend = ctx.get('graph_backend')
        if not backend:
            logger.debug("No graph backend provided to compensation handler")
            return False

        label = payload.get('label')
        record_id = payload.get('id') or payload.get('identity')

        # Try common method names
        if record_id is None:
            logger.debug("graph_delete_node_handler missing id in payload")
            return False

        try_names = [
            ('delete_node', (label, record_id)),
            ('delete_by_id', (record_id,)),
            ('delete', (label, record_id)),
            ('remove_node', (label, record_id)),
        ]

        for name, args in try_names:
            fn = getattr(backend, name, None)
            if callable(fn):
                try:
                    res = fn(*[a for a in args if a is not None])
                    # treat truthy return or None as success (if backend raises, we catch below)
                    return bool(res) if res is not None else True
                except Exception:
                    logger.debug("graph backend method %s failed, trying next", name)
                    continue

        # As a last resort, if backend exposes execute_query, attempt a delete cypher/sql
        if hasattr(backend, 'execute_query'):
            try:
                # best-effort: attempt a cypher-like delete
                if label:
                    backend.execute_query(f"MATCH (n:{label} {{id: ?}}) DETACH DELETE n", (record_id,))
                else:
                    backend.execute_query("MATCH (n {id: ?}) DETACH DELETE n", (record_id,))
                return True
            except Exception:
                logger.debug("graph fallback execute_query failed")

        logger.debug("graph_delete_node_handler could not perform deletion")
        return False
    except Exception as exc:
        logger.exception("graph_delete_node_handler failed: %s", exc)
        return False


def vector_delete_chunks_handler(payload: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """Attempt to delete vector documents or chunks from a vector backend.

    Expected payload: { 'ids': [..] } or { 'document_id': str }.
    ctx should provide 'vector_backend'. Tries common methods: delete_documents,
    remove_documents, delete_chunks, delete_by_ids.
    """
    try:
        backend = ctx.get('vector_backend')
        if not backend:
            logger.debug("No vector backend provided to compensation handler")
            return False

        ids = payload.get('ids')
        if not ids and payload.get('document_id'):
            ids = [payload.get('document_id')]

        if not ids:
            logger.debug("vector_delete_chunks_handler missing ids/document_id in payload")
            return False

        try_names = [
            ('delete_documents', (ids,)),
            ('remove_documents', (ids,)),
            ('delete_chunks', (ids,)),
            ('delete_by_ids', (ids,)),
        ]

        for name, args in try_names:
            fn = getattr(backend, name, None)
            if callable(fn):
                try:
                    res = fn(*args)
                    return bool(res) if res is not None else True
                except Exception:
                    logger.debug("vector backend method %s failed, trying next", name)
                    continue

        # Fallback: if backend supports execute_query, maybe it exposes a delete SQL
        if hasattr(backend, 'execute_query'):
            try:
                # best-effort: attempt to delete from a generic 'documents' table
                for _id in ids:
                    backend.execute_query("DELETE FROM documents WHERE id = ?", (_id,))
                return True
            except Exception:
                logger.debug("vector fallback execute_query failed")

        logger.debug("vector_delete_chunks_handler could not perform deletion")
        return False
    except Exception as exc:
        logger.exception("vector_delete_chunks_handler failed: %s", exc)
        return False


# register defaults
register('relational_delete', relational_delete_handler)
register('graph_delete_node', graph_delete_node_handler)
register('vector_delete_chunks', vector_delete_chunks_handler)


__all__ = ['register', 'get', 'relational_delete_handler', 'graph_delete_node_handler', 'vector_delete_chunks_handler']
