import time
import uuid
import logging
import json
from typing import Any, Dict, List, Optional

from database.saga_compensations import get as get_compensation
from database.saga_compensations import register as register_compensation
from database.saga_crud import SagaDatabaseCRUD
from database.database_manager import DatabaseManager
from database import config

try:
    from database import db_migrations
except Exception:  # pragma: no cover - optional dependency during cold start
    db_migrations = None

logger = logging.getLogger(__name__)


class SagaOrchestrator:
    def __init__(self, manager: Optional[DatabaseManager] = None):
        self.manager = manager or DatabaseManager(config.get_database_backend_dict())
        self.crud = SagaDatabaseCRUD(manager=self.manager)

    def _get_relational(self):
        try:
            return self.manager.get_relational_backend()
        except Exception:
            return None

    def _ensure_schema(self):
        rel = self._get_relational()
        if not rel:
            return None
        if db_migrations is None:
            return rel
        flag = "_uds3_saga_schema_ready"
        if getattr(rel, flag, False):
            return rel
        try:
            db_migrations.ensure_saga_schema(rel)
            setattr(rel, flag, True)
        except Exception as exc:  # pragma: no cover - migrations best-effort
            logger.debug("ensure_saga_schema failed: %s", exc)
        return rel

    def _acquire_lock(self, saga_id: str):
        # Best-effort advisory lock: try SQLite immediate transaction or Postgres advisory
        rel = self._get_relational()
        if not rel:
            return None
        # Try Postgres advisory lock first (best-effort). We need a stable bigint key.
        try:
            if hasattr(rel, 'execute_query'):
                # compute a 64-bit key from saga_id
                key = abs(hash(saga_id)) & ((1 << 63) - 1)
                try:
                    # Try using pg_try_advisory_lock
                    rows = rel.execute_query('SELECT pg_try_advisory_lock(?) as locked', (key,))
                    if rows and isinstance(rows, list) and rows[0].get('locked'):
                        return ('pg', key, rel)
                except Exception:
                    # Not Postgres or function not available; fall through to sqlite strategy
                    pass

            # SQLite: BEGIN IMMEDIATE will acquire a write lock for the connection
            try:
                if hasattr(rel, 'execute_query'):
                    rel.execute_query('BEGIN IMMEDIATE')
                    return ('sqlite', None, rel)
            except Exception:
                pass
        except Exception:
            pass
        return None

    def _release_lock(self, rel):
        try:
            if not rel:
                return
            # rel can be a tuple from _acquire_lock
            if isinstance(rel, tuple) and rel[0] == 'pg':
                _, key, backend = rel
                try:
                    backend.execute_query('SELECT pg_advisory_unlock(?)', (key,))
                except Exception:
                    pass
                return
            # sqlite-style
            if isinstance(rel, tuple) and rel[0] == 'sqlite':
                backend = rel[2]
                try:
                    backend.execute_query('COMMIT')
                except Exception:
                    try:
                        backend.execute_query('ROLLBACK')
                    except Exception:
                        pass
                return
            # fallback: if a raw backend passed
            if hasattr(rel, 'execute_query'):
                try:
                    rel.execute_query('COMMIT')
                except Exception:
                    try:
                        rel.execute_query('ROLLBACK')
                    except Exception:
                        pass
        except Exception:
            pass

    def create_saga(self, name: str, steps: List[Dict[str, Any]], trace_id: Optional[str] = None) -> str:
        saga_id = str(uuid.uuid4())
        rel = self._ensure_schema()
        saga_record = {
            'saga_id': saga_id,
            'name': name,
            'trace_id': trace_id,
            'status': 'created',
            'context': json.dumps({'steps': steps}),
            'current_step': None,
        }
        if rel:
            try:
                # insert into uds3_sagas in a schema-aware way
                try:
                    schema = rel.get_table_schema('uds3_sagas') if hasattr(rel, 'get_table_schema') else {}
                except Exception:
                    schema = {}

                if schema:
                    allowed = set(schema.keys())
                    filtered = {k: v for k, v in saga_record.items() if k in allowed}
                    if filtered:
                        # If the target table doesn't have a conventional 'id' column, avoid rel.insert
                        if 'id' in allowed and hasattr(rel, 'insert'):
                            rel.insert('uds3_sagas', filtered)
                        else:
                            # build parameterized insert to avoid auto-injected columns
                            cols = ', '.join(filtered.keys())
                            placeholders = ', '.join(['?' for _ in filtered])
                            params = tuple(filtered.values())
                            rel.execute_query(f'INSERT INTO uds3_sagas ({cols}) VALUES ({placeholders})', params)
                    else:
                        # no matching columns, fallback to insert_record if available
                        if hasattr(rel, 'insert_record'):
                            rel.insert_record('uds3_sagas', saga_record)
                else:
                    # unknown schema: best-effort insert via insert_record or insert
                    if hasattr(rel, 'insert_record'):
                        rel.insert_record('uds3_sagas', saga_record)
                    elif hasattr(rel, 'insert'):
                        # try to avoid adding an 'id' key by passing a copy without it
                        rec = dict(saga_record)
                        rec.pop('id', None)
                        rel.insert('uds3_sagas', rec)
            except Exception:
                logger.debug('Could not insert saga record; continuing')
        return saga_id

    def execute_saga(self, saga_id: str, max_retries: int = 3, start_at: Optional[int] = None) -> Dict[str, Any]:
        # Load saga context from uds3_sagas
        rel = self._ensure_schema()
        if not rel:
            return {'success': False, 'error': 'No relational backend available'}

        rows = rel.execute_query('SELECT * FROM uds3_sagas WHERE saga_id = ?', (saga_id,))
        if not rows:
            return {'success': False, 'error': 'Saga not found'}
        saga = rows[0]
        context = json.loads(saga.get('context') or '{}')
        steps = context.get('steps') or []

        # Acquire best-effort lock
        lock = self._acquire_lock(saga_id)

        executed_steps: List[Dict[str, Any]] = []
        start_idx = int(start_at) if start_at is not None else 0
        try:
            for idx, step in enumerate(steps[start_idx:], start=start_idx):
                step_id = step.get('step_id') or f'step_{idx}'
                backend_name = step.get('backend')
                operation = step.get('operation')
                payload = step.get('payload') or {}
                compensation = step.get('compensation')
                idempotency_key = step.get('idempotency_key')

                # Write-ahead PENDING
                self.crud.write_saga_event(saga_id, step_id, 'PENDING', payload)

                # Idempotency check: if a SUCCESS event for this idempotency_key exists, skip
                if idempotency_key:
                    # Prefer indexed idempotency_key column if available
                    tried = False
                    try:
                        schema = rel.get_table_schema('uds3_saga_events') if hasattr(rel, 'get_table_schema') else {}
                    except Exception:
                        schema = {}

                    if isinstance(schema, dict) and 'idempotency_key' in schema:
                        q = 'SELECT status FROM uds3_saga_events WHERE saga_id = ? AND step_name = ? AND idempotency_key = ?'
                        rows = rel.execute_query(q, (saga_id, step_id, idempotency_key))
                        tried = True
                        if any(r.get('status') == 'SUCCESS' for r in rows):
                            logger.debug('Skipping step %s due to idempotency (column)', step_id)
                            executed_steps.append({'step_id': step_id, 'skipped': True})
                            continue

                    if not tried:
                        q = 'SELECT status FROM uds3_saga_events WHERE saga_id = ? AND step_name = ? AND payload LIKE ?'
                        rows = rel.execute_query(q, (saga_id, step_id, f'%{idempotency_key}%'))
                        if any(r.get('status') == 'SUCCESS' for r in rows):
                            logger.debug('Skipping step %s due to idempotency (payload)', step_id)
                            executed_steps.append({'step_id': step_id, 'skipped': True})
                            continue
                        logger.debug('Skipping step %s due to idempotency', step_id)
                        executed_steps.append({'step_id': step_id, 'skipped': True})
                        continue

                # Retry logic
                attempt = 0
                while attempt <= max_retries:
                    attempt += 1
                    start = time.time()
                    try:
                        result = self._execute_step(step, payload)
                        duration = int((time.time() - start) * 1000)
                        if result.get('success'):
                            self.crud.write_saga_event(saga_id, step_id, 'SUCCESS', payload)
                            executed_steps.append({'step_id': step_id, 'success': True, 'duration_ms': duration, 'payload': payload, 'compensation': compensation})
                            break
                        else:
                            raise Exception(result.get('error') or 'step failed')
                    except Exception as exc:
                        logger.debug('Step %s attempt %d failed: %s', step_id, attempt, exc)
                        if attempt > max_retries:
                            # fail the saga
                            self.crud.write_saga_event(saga_id, step_id, 'FAIL', payload, error=str(exc))
                            # trigger compensation for executed steps
                            self.compensate_saga(saga_id, executed_steps)
                            return {'success': False, 'error': str(exc), 'executed': executed_steps}
                        # backoff
                        time.sleep(0.1 * (2 ** (attempt - 1)))

            # Completed all steps
            try:
                rel.execute_query('UPDATE uds3_sagas SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE saga_id = ?', ('completed', saga_id))
            except Exception:
                pass
            return {'success': True, 'executed': executed_steps}
        finally:
            self._release_lock(lock)

    def _execute_step(self, step: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        # Delegates to SagaDatabaseCRUD for common operations, otherwise best-effort
        backend = step.get('backend')
        operation = step.get('operation')

        try:
            # Example mapping: relational create -> call crud.vector_create/relational ops
            if backend == 'vector' and operation == 'create':
                doc_id = payload.get('document_id')
                chunks = payload.get('chunks') or []
                metadata = payload.get('metadata')
                res = self.crud.vector_create(doc_id, chunks, metadata)
                return {'success': res.success, 'data': res.data, 'error': res.error}

            if backend == 'relational' and operation == 'insert':
                # expects payload {table, record}
                rel = self._get_relational()
                table = payload.get('table')
                record = payload.get('record')
                if not rel:
                    return {'success': False, 'error': 'No relational backend'}
                if hasattr(rel, 'insert'):
                    rel.insert(table, record)
                    return {'success': True}
                return {'success': False, 'error': 'Relational insert not available'}

            # Fallback: unsupported operation
            return {'success': False, 'error': f'Unsupported backend/operation: {backend}/{operation}'}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def compensate_saga(self, saga_id: str, executed_steps: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        # If executed_steps provided, compensate those in reverse order; otherwise read events
        rel = self._ensure_schema()
        to_compensate = executed_steps or []
        if not to_compensate:
            rows = rel.execute_query('SELECT step_name, payload, status FROM uds3_saga_events WHERE saga_id = ? AND status = ?', (saga_id, 'SUCCESS'))
            to_compensate = [{'step_id': r['step_name'], 'payload': json.loads(r['payload']) if r.get('payload') else {}} for r in rows]

        # reverse order
        for step in reversed(to_compensate):
            payload = step.get('payload') or {}
            # normalize payload: if record is nested, expose id for relational deletion handlers
            if isinstance(payload.get('record'), dict):
                record = payload.get('record')
                if 'id' not in payload and 'id' in record:
                    payload['id'] = record.get('id')
                # also copy common fields
                if 'document_id' not in payload and 'id' in record:
                    payload['document_id'] = record.get('id')
            comp_name = payload.get('compensation') or payload.get('compensate')
            if not comp_name:
                # nothing registered in payload; attempt default based on backend
                comp_name = payload.get('default_compensation')
            handler = get_compensation(comp_name) if comp_name else None
            if not handler:
                logger.debug('No handler for compensation %s', comp_name)
                continue
            try:
                success = handler(payload, {'relational_backend': rel, 'graph_backend': self.manager.get_graph_backend(), 'vector_backend': self.manager.get_vector_backend()})
                if success:
                    logger.debug('Compensation %s succeeded for saga %s', comp_name, saga_id)
                    self.crud.write_saga_event(saga_id, step.get('step_id', 'unknown'), 'COMPENSATED', payload)
                else:
                    logger.debug('Compensation %s failed for saga %s', comp_name, saga_id)
            except Exception as exc:
                logger.exception('Compensation handler %s raised: %s', comp_name, exc)

        try:
            rel.execute_query('UPDATE uds3_sagas SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE saga_id = ?', ('compensated', saga_id))
        except Exception:
            pass
        return {'compensated': True}

    def abort_saga(self, saga_id: str, reason: str = '') -> None:
        rel = self._ensure_schema()
        if rel:
            try:
                rel.execute_query('UPDATE uds3_sagas SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE saga_id = ?', ('aborted', saga_id))
            except Exception:
                pass
        self.crud.write_saga_event(saga_id, 'abort', 'FAIL', {'reason': reason})

    def resume_saga(self, saga_id: str) -> Dict[str, Any]:
        rel = self._ensure_schema()
        if not rel:
            return {'resumed': False, 'reason': 'No relational backend'}

        # Load saga and steps
        rows = rel.execute_query('SELECT * FROM uds3_sagas WHERE saga_id = ?', (saga_id,))
        if not rows:
            return {'resumed': False, 'reason': 'Saga not found'}
        saga = rows[0]
        context = json.loads(saga.get('context') or '{}')
        steps = context.get('steps') or []

        # Find last successful steps from events
        ev_rows = rel.execute_query('SELECT step_name, status FROM uds3_saga_events WHERE saga_id = ? ORDER BY created_at ASC', (saga_id,))
        success_steps = {r.get('step_name') for r in ev_rows if r.get('status') == 'SUCCESS'}

        # Determine the index to resume at: first step whose step_id not in success_steps
        resume_index = 0
        for idx, step in enumerate(steps):
            sid = step.get('step_id') or f'step_{idx}'
            if sid not in success_steps:
                resume_index = idx
                break
            resume_index = idx + 1

        # If resume_index is past end, nothing to do
        if resume_index >= len(steps):
            return {'resumed': False, 'reason': 'Nothing to resume', 'resume_index': resume_index}

        # Call execute_saga starting at resume_index
        return self.execute_saga(saga_id, start_at=resume_index)


__all__ = ['SagaOrchestrator']
