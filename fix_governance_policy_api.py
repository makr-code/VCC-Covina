"""
Auto-Fix Script for Governance Policy API PostgreSQL Integration
================================================================

Fixes similar issues as Golden Dataset and Graph Pattern APIs:
1. Row access: row[index] → row['column']  (psycopg3 dict_row)
2. Cursor API: postgres_backend.cursor.execute() → execute_query()
3. COUNT query: Add "as count" alias for dict access

Based on patterns from fix_graph_golden_api.py

Author: GitHub Copilot
Date: 17. Oktober 2025, 20:05 Uhr
"""

import re

def fix_governance_policy_api():
    """Fix PostgreSQL integration issues in Governance Policy API"""
    
    file_path = "main_backend.py"
    
    print("\n" + "="*80)
    print("AUTO-FIX: Governance Policy API PostgreSQL Integration")
    print("="*80)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Fix 1: GET /governance/policies - Row access (Lines ~1200-1220)
    print("\nFix 1: GET /governance/policies - Row dict access...")
    old_pattern_1 = r"policies\.append\(\{\s*'id': row\[0\],\s*'policy_id': row\[1\],\s*'name': row\[2\],"
    if re.search(old_pattern_1, content):
        # Replace all row[index] with row['column']
        section_start = content.find("for row in rows:")
        section_end = content.find("# Total Count", section_start)
        if section_start > 0 and section_end > 0:
            old_section = content[section_start:section_end]
            new_section = old_section.replace("row[0]", "row['id']") \
                                     .replace("row[1]", "row['policy_id']") \
                                     .replace("row[2]", "row['name']") \
                                     .replace("row[3]", "row['description']") \
                                     .replace("row[4]", "row['policy_type']") \
                                     .replace("row[5]", "row['scope']") \
                                     .replace("row[6]", "row['rules']") \
                                     .replace("row[7]", "row['status']") \
                                     .replace("row[8]", "row['priority']") \
                                     .replace("row[9]", "row['effective_from']") \
                                     .replace("row[10]", "row['effective_until']") \
                                     .replace("row[11]", "row['created_by']") \
                                     .replace("row[12]", "row['created_at']") \
                                     .replace("row[13]", "row['updated_at']") \
                                     .replace("row[14]", "row['approved_by']") \
                                     .replace("row[15]", "row['approved_at']") \
                                     .replace("row[16]", "row['metadata']")
            content = content[:section_start] + new_section + content[section_end:]
            fixes_applied += 1
            print("  ✅ Fixed row dict access (17 fields)")
    else:
        print("  ⏭️  Already fixed or not found")
    
    # Fix 2: COUNT query - Add alias
    print("\nFix 2: COUNT query - Add 'as count' alias...")
    old_count = 'count_result = postgres_backend.execute_query(count_query, tuple(count_params))\n        total = count_result[0][\'count\']'
    # Check if COUNT query has alias
    count_query_line = 'count_query = "SELECT COUNT(*) FROM governance_policies WHERE 1=1"'
    if count_query_line in content:
        # Add "as count" alias
        content = content.replace(
            count_query_line,
            'count_query = "SELECT COUNT(*) as count FROM governance_policies WHERE 1=1"'
        )
        fixes_applied += 1
        print("  ✅ Added 'as count' alias to COUNT query")
    else:
        print("  ⏭️  Already fixed or not found")
    
    # Fix 3: POST /governance/policies - Cursor API (Lines ~1310-1320)
    print("\nFix 3: POST /governance/policies - Cursor context manager...")
    old_cursor_pattern = r"postgres_backend\.cursor\.execute\(insert_sql, params\)\s*policy_id = postgres_backend\.cursor\.fetchone\(\)\[0\]\s*postgres_backend\.connection\.commit\(\)"
    if re.search(old_cursor_pattern, content):
        # Find the section
        section_start = content.find("postgres_backend.cursor.execute(insert_sql, params)")
        section_end = content.find("logger.info(f\"✅ Governance Policy erstellt", section_start)
        if section_start > 0 and section_end > 0:
            old_section = content[section_start:section_end]
            new_section = """with postgres_backend.conn.cursor() as cur:
            cur.execute(insert_sql, params)
            result = cur.fetchone()
            policy_id_db = result['id'] if result else None
        postgres_backend.conn.commit()
        
        """
            content = content[:section_start] + new_section + content[section_end:]
            fixes_applied += 1
            print("  ✅ Fixed cursor context manager + commit placement + dict access")
    else:
        print("  ⏭️  Already fixed or not found")
    
    # Fix 4: Rollback error handling
    print("\nFix 4: POST /governance/policies - Safe rollback...")
    old_rollback = "postgres_backend.connection.rollback()"
    new_rollback = """try:
            postgres_backend.conn.rollback()
        except:
            pass  # Ignore rollback errors if already committed"""
    if old_rollback in content and new_rollback not in content:
        content = content.replace(old_rollback, new_rollback)
        fixes_applied += 1
        print("  ✅ Added try/except for safe rollback")
    else:
        print("  ⏭️  Already fixed or not found")
    
    # Fix 5: Return statement - Update variable name
    print("\nFix 5: POST /governance/policies - Return value variable...")
    old_return = '"id": policy_id,'
    new_return = '"id": policy_id_db,'
    if old_return in content and '"id": policy_id_db,' not in content:
        # Only replace within the return statement of create_governance_policy
        section_start = content.find("return {\n            \"message\": \"Governance Policy erfolgreich erstellt\"")
        section_end = content.find("}", section_start) + 1
        if section_start > 0:
            old_section = content[section_start:section_end]
            new_section = old_section.replace(old_return, new_return)
            content = content[:section_start] + new_section + content[section_end:]
            fixes_applied += 1
            print("  ✅ Updated return variable name (policy_id → policy_id_db)")
    else:
        print("  ✅  Already fixed or not applicable")
    
    # Save changes
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n" + "="*80)
        print(f"✅ SUCCESS: {fixes_applied} fixes applied to {file_path}")
        print("="*80)
        print("\nFixed Issues:")
        print("  1. Row dict access (row[0] → row['id'], etc.) - 17 fields")
        print("  2. COUNT query alias (SELECT COUNT(*) as count)")
        print("  3. Cursor context manager (conn.cursor() context + commit)")
        print("  4. Safe rollback (try/except wrapper)")
        print("  5. Return variable name (policy_id_db)")
        print("\nNext Step: Restart backend and run tests!")
        print("  Command: Get-Process python | Stop-Process -Force")
        print("  Command: python -m uvicorn main_backend:app --host 0.0.0.0 --port 45678")
        print("  Command: python tests\\test_governance_policy_api.py")
        return True
    else:
        print("\n⚠️  No changes needed - all fixes already applied or patterns not found")
        return False

if __name__ == "__main__":
    success = fix_governance_policy_api()
    exit(0 if success else 1)
