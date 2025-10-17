"""
Auto-Fix Script für Graph Golden Dataset API
Konvertiert alle cursor.execute() Calls zu execute_query()
"""

import re

# Read file
with open('main_backend.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Track changes
changes = []

# Function to fix the graph-golden-dataset GET endpoint (Lines 700-844)
# Fix 1: cursor.execute → execute_query
old_1 = """        # Execute
        postgres_backend.cursor.execute(query, tuple(params))
        rows = postgres_backend.cursor.fetchall()"""

new_1 = """        # Execute
        rows = postgres_backend.execute_query(query, tuple(params))"""

if old_1 in content:
    content = content.replace(old_1, new_1)
    changes.append("✅ Fixed LINE ~776: cursor.execute → execute_query (GET list)")
else:
    changes.append("❌ Pattern 1 not found (GET execute)")

# Fix 2: Row access index → dict (Lines 781-808)
old_2 = """            patterns.append({
                'id': row[0],
                'pattern_id': row[1],
                'name': row[2],
                'description': row[3],
                'category': row[4],
                'nodes_definition': row[5],
                'relationships_definition': row[6],
                'validation_rules': row[7],
                'created_by': row[8],
                'created_at': str(row[9]),
                'updated_at': str(row[10]),
                'reviewed_by': row[11],
                'reviewed_at': str(row[12]) if row[12] else None,
                'status': row[13],
                'tags': row[14],
                'neo4j_pattern_label': row[15],
                'usage_count': row[16],
                'last_used_at': str(row[17]) if row[17] else None,
                'metadata': row[18]
            })"""

new_2 = """            patterns.append({
                'id': row['id'],
                'pattern_id': row['pattern_id'],
                'name': row['name'],
                'description': row['description'],
                'category': row['category'],
                'nodes_definition': row['nodes_definition'],
                'relationships_definition': row['relationships_definition'],
                'validation_rules': row['validation_rules'],
                'created_by': row['created_by'],
                'created_at': str(row['created_at']),
                'updated_at': str(row['updated_at']),
                'reviewed_by': row['reviewed_by'],
                'reviewed_at': str(row['reviewed_at']) if row['reviewed_at'] else None,
                'status': row['status'],
                'tags': row['tags'],
                'neo4j_pattern_label': row['neo4j_pattern_label'],
                'usage_count': row['usage_count'],
                'last_used_at': str(row['last_used_at']) if row['last_used_at'] else None,
                'metadata': row['metadata']
            })"""

if old_2 in content:
    content = content.replace(old_2, new_2)
    changes.append("✅ Fixed LINE ~781-808: row[0] → row['id'] (dict access)")
else:
    changes.append("❌ Pattern 2 not found (row dict access)")

# Fix 3: Count query cursor → execute_query
old_3 = """        postgres_backend.cursor.execute(count_query, tuple(count_params))
        total = postgres_backend.cursor.fetchone()[0]"""

new_3 = """        count_result = postgres_backend.execute_query(count_query, tuple(count_params))
        total = count_result[0]['count'] if count_result else 0"""

if old_3 in content:
    content = content.replace(old_3, new_3)
    changes.append("✅ Fixed LINE ~833-834: count query cursor → execute_query")
else:
    changes.append("❌ Pattern 3 not found (count query)")

# Fix 4: POST endpoint cursor.execute → conn.cursor() context manager (Lines 906-912)
old_4 = """        postgres_backend.cursor.execute(insert_sql, params)
        pattern_id = postgres_backend.cursor.fetchone()[0]
        postgres_backend.connection.commit()"""

new_4 = """        with postgres_backend.conn.cursor() as cur:
            cur.execute(insert_sql, params)
            result = cur.fetchone()
            pattern_id_db = result['id'] if result else None
            postgres_backend.conn.commit()"""

if old_4 in content:
    content = content.replace(old_4, new_4)
    changes.append("✅ Fixed LINE ~906-912: POST cursor → conn.cursor() context manager")
else:
    changes.append("❌ Pattern 4 not found (POST insert)")

# Fix 5: Return statement pattern_id → pattern_id_db
old_5 = """        return {
            "message": "Graph Golden Pattern erfolgreich erstellt",
            "pattern_id": pattern.pattern_id,
            "id": pattern_id,"""

new_5 = """        return {
            "message": "Graph Golden Pattern erfolgreich erstellt",
            "pattern_id": pattern.pattern_id,
            "id": pattern_id_db,"""

if old_5 in content:
    content = content.replace(old_5, new_5)
    changes.append("✅ Fixed LINE ~917-919: pattern_id → pattern_id_db")
else:
    changes.append("❌ Pattern 5 not found (return statement)")

# Fix 6: GET /{pattern_id} endpoint cursor → execute_query (Line 959-1005)
old_6 = """        postgres_backend.cursor.execute(query, (pattern_id,))
        row = postgres_backend.cursor.fetchone()"""

new_6 = """        rows = postgres_backend.execute_query(query, (pattern_id,))
        row = rows[0] if rows else None"""

if old_6 in content:
    content = content.replace(old_6, new_6)
    changes.append("✅ Fixed LINE ~959-960: GET /{pattern_id} cursor → execute_query")
else:
    changes.append("❌ Pattern 6 not found (GET single pattern)")

# Fix 7: GET /{pattern_id} row access (Lines 965-993)
old_7 = """        pattern_data = {
            'id': row[0],
            'pattern_id': row[1],
            'name': row[2],
            'description': row[3],
            'category': row[4],
            'nodes_definition': row[5],
            'relationships_definition': row[6],
            'validation_rules': row[7],
            'created_by': row[8],
            'created_at': str(row[9]),
            'updated_at': str(row[10]),
            'reviewed_by': row[11],
            'reviewed_at': str(row[12]) if row[12] else None,
            'status': row[13],
            'tags': row[14],
            'neo4j_pattern_label': row[15],
            'usage_count': row[16],
            'last_used_at': str(row[17]) if row[17] else None,
            'metadata': row[18]
        }"""

new_7 = """        pattern_data = {
            'id': row['id'],
            'pattern_id': row['pattern_id'],
            'name': row['name'],
            'description': row['description'],
            'category': row['category'],
            'nodes_definition': row['nodes_definition'],
            'relationships_definition': row['relationships_definition'],
            'validation_rules': row['validation_rules'],
            'created_by': row['created_by'],
            'created_at': str(row['created_at']),
            'updated_at': str(row['updated_at']),
            'reviewed_by': row['reviewed_by'],
            'reviewed_at': str(row['reviewed_at']) if row['reviewed_at'] else None,
            'status': row['status'],
            'tags': row['tags'],
            'neo4j_pattern_label': row['neo4j_pattern_label'],
            'usage_count': row['usage_count'],
            'last_used_at': str(row['last_used_at']) if row['last_used_at'] else None,
            'metadata': row['metadata']
        }"""

if old_7 in content:
    content = content.replace(old_7, new_7)
    changes.append("✅ Fixed LINE ~965-993: GET /{pattern_id} row dict access")
else:
    changes.append("❌ Pattern 7 not found (GET single row access)")

# Write updated content
with open('main_backend.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Print summary
print("=" * 60)
print("Graph Golden Dataset API Auto-Fix Complete")
print("=" * 60)
for change in changes:
    print(change)

print("\n" + "=" * 60)
print(f"Total Fixes Applied: {sum(1 for c in changes if '✅' in c)}/{len(changes)}")
print("=" * 60)
print("\n✅ main_backend.py updated successfully!")
print("\nNext Steps:")
print("1. Restart backends: .\\scripts\\stop_services.ps1 && .\\scripts\\start_services.ps1")
print("2. Run test: python tests\\test_graph_pattern_api.py")
