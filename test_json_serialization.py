"""
Test JSON serialization of the return dict
"""

import json

# Simulate the pattern object
class Pattern:
    def __init__(self):
        self.pattern_id = "TEST_123"
        self.name = "Test Name"
        self.category = "workflow"
        self.nodes_definition = [{"id": "n1", "label": "Doc"}]
        self.relationships_definition = []

pattern = Pattern()
pattern_id_db = 123

# Try to create the return dict exactly as in the code
return_dict = {
    "message": "Graph Golden Pattern erfolgreich erstellt",
    "pattern_id": pattern.pattern_id,
    "id": pattern_id_db,
    "name": pattern.name,
    "category": pattern.category,
    "nodes_count": len(pattern.nodes_definition),
    "relationships_count": len(pattern.relationships_definition)
}

print("Return dict created successfully:")
print(return_dict)

# Try to serialize to JSON
try:
    json_str = json.dumps(return_dict, indent=2)
    print("\n[OK] JSON serialization successful!")
    print(json_str)
except Exception as e:
    print(f"\n[FAIL] JSON serialization failed: {e}")
    import traceback
    traceback.print_exc()
