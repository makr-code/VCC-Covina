from typing import Dict, Any
import os


def _sqlite_type_for_value(v: Any) -> str:
    if isinstance(v, int):
        return 'INTEGER'
    if isinstance(v, float):
        return 'REAL'
    from typing import Dict, Any, Optional
    import os
    import json


    def _sqlite_type_for_value(v: Any) -> str:
        if isinstance(v, int):
            return 'INTEGER'
        if isinstance(v, float):
            return 'REAL'
        # default to TEXT for strings, dicts, lists
        return 'TEXT'


    def ensure_table_for_relational_operation(
        rel_backend,
        table_name: str,
        sample_data: Dict[str, Any],
        pk_policy: str = 'document_id',
        verbose: bool = False,
    ) -> bool:
        """Create a simple SQLite table to accommodate the keys in sample_data.

        pk_policy: 'document_id'|'id'|'auto' - preferred primary key selection
        """
        if verbose:
            print(f"[uds3_plan_db_utils] ensure_table_for_relational_operation: {table_name}, pk_policy={pk_policy}")

        if not isinstance(sample_data, dict):
            schema = {'id': 'TEXT PRIMARY KEY', 'data': 'TEXT'}
            return rel_backend.create_table(table_name, schema)

from typing import Dict, Any
import os
import json


def _sqlite_type_for_value(v: Any) -> str:
    if isinstance(v, int):
        return 'INTEGER'
    if isinstance(v, float):
        return 'REAL'
    # default to TEXT for strings, dicts, lists
    return 'TEXT'


def ensure_table_for_relational_operation(
    rel_backend,
    table_name: str,
    sample_data: Dict[str, Any],
    pk_policy: str = 'document_id',
    verbose: bool = False,
) -> bool:
    """Create a simple SQLite table to accommodate the keys in sample_data.

    pk_policy: 'document_id'|'id'|'auto' - preferred primary key selection
    """
    if verbose:
        print(f"[uds3_plan_db_utils] ensure_table_for_relational_operation: {table_name}, pk_policy={pk_policy}")

    if not isinstance(sample_data, dict):
        schema = {'id': 'TEXT PRIMARY KEY', 'data': 'TEXT'}
        return rel_backend.create_table(table_name, schema)

    # decide primary key according to policy
    pk = None
    if pk_policy == 'document_id' and 'document_id' in sample_data:
        pk = 'document_id'
    elif pk_policy == 'id' and 'id' in sample_data:
        pk = 'id'
    else:
        # auto: prefer document_id if present, else id, else create id
        if 'document_id' in sample_data:
            pk = 'document_id'
        elif 'id' in sample_data:
            pk = 'id'
        else:
            pk = 'id'

    schema = {}
    for k, v in sample_data.items():
        if k == pk:
            schema[k] = 'TEXT PRIMARY KEY'
        else:
            schema[k] = _sqlite_type_for_value(v)

    if pk not in schema:
        schema[pk] = 'TEXT PRIMARY KEY'

    return rel_backend.create_table(table_name, schema)


def _serialize_value(v: Any) -> Any:
    # Convert dict/list to JSON string for storage
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False, default=str)
        except Exception:
            return str(v)
    return v


def apply_relational_operations_from_plan(
    rel_backend,
    plan_rel: Dict[str, Any],
    document_id: str,
    pk_policy: str = 'document_id',
    verbose: bool = False,
) -> list:
    """Execute relational operations from a UDS3 plan on provided relational backend.

    This function creates tables as needed and inserts data. It's conservative and
    uses TEXT for unknown types. pk_policy controls primary-key selection.
    """
    ops = plan_rel.get('operations', []) if isinstance(plan_rel, dict) else []
    results = []
    for op in ops:
        op_type = op.get('type')
        table = op.get('table')
        data = op.get('data')
        if not table or data is None:
            continue
        if verbose:
            print(f"[uds3_plan_db_utils] Applying {op_type} on {table}")

        # if list -> many inserts
        if isinstance(data, list):
            if data:
                sample = data[0] if isinstance(data[0], dict) else {'data': str(data[0])}
                ensure_table_for_relational_operation(rel_backend, table, sample, pk_policy=pk_policy, verbose=verbose)
            for item in data:
                if isinstance(item, dict):
                    rec = {k: _serialize_value(v) for k, v in item.items()}
                    if 'document_id' not in rec:
                        rec['document_id'] = document_id
                    if 'id' not in rec:
                        rec.setdefault('id', os.urandom(8).hex())
                    rel_backend.insert_record(table, rec)
                else:
                    rec = {'id': os.urandom(8).hex(), 'document_id': document_id, 'data': str(item)}
                    rel_backend.insert_record(table, rec)
        elif isinstance(data, dict):
            # ensure table exists
            ensure_table_for_relational_operation(rel_backend, table, data, pk_policy=pk_policy, verbose=verbose)
            rec = {k: _serialize_value(v) for k, v in data.items()}
            # fill ids if missing
            if 'document_id' not in rec:
                rec['document_id'] = document_id

            # check if table has document_id column as pk
            try:
                schema = rel_backend.get_table_schema(table)
            except Exception:
                schema = {}

            if 'document_id' in schema and schema.get('document_id', {}).get('type'):
                cols = list(rec.keys())
                placeholders = ', '.join(['?' for _ in cols])
                rel_backend.execute_query(f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", tuple(rec[c] for c in cols))
            else:
                if 'id' not in rec:
                    rec['id'] = os.urandom(8).hex()
                rel_backend.insert_record(table, rec)
        results.append({'table': table, 'type': op_type})
    return results
