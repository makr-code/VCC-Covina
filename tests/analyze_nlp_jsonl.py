"""
Phase L6A: JSONL-Analyse-Tool
Einfaches Skript zur Analyse der extrahierten Entitäten aus data/nlp/entities.jsonl
"""

import json
import os
from collections import Counter
from typing import Dict, Any

def analyze_jsonl(path: str) -> Dict[str, Any]:
    """Analysiert die JSONL-Datei und gibt Statistiken zurück."""
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    
    total_records = 0
    total_entities = 0
    total_relations = 0
    errors = 0
    
    entity_labels = Counter()
    domain_counts = Counter()
    relation_types = Counter()
    
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                total_records += 1
                
                if "error" in record:
                    errors += 1
                    continue
                
                entities = record.get("entities", [])
                total_entities += len(entities)
                for ent in entities:
                    entity_labels[ent.get("label", "UNKNOWN")] += 1
                
                domain = record.get("domain", "Unbekannt")
                domain_counts[domain] += 1
                
                relations = record.get("relations", [])
                total_relations += len(relations)
                for rel in relations:
                    relation_types[rel.get("type", "UNKNOWN")] += 1
                    
            except json.JSONDecodeError:
                errors += 1
    
    return {
        "total_records": total_records,
        "total_entities": total_entities,
        "total_relations": total_relations,
        "errors": errors,
        "top_entity_labels": entity_labels.most_common(10),
        "domain_distribution": domain_counts.most_common(10),
        "top_relation_types": relation_types.most_common(10),
        "avg_entities_per_doc": total_entities / total_records if total_records else 0,
        "avg_relations_per_doc": total_relations / total_records if total_records else 0,
    }

if __name__ == "__main__":
    jsonl_path = os.environ.get("NLP_OUTPUT_JSONL", os.path.join("data", "nlp", "entities.jsonl"))
    print(f"[ANALYZE] Reading: {jsonl_path}")
    stats = analyze_jsonl(jsonl_path)
    
    if "error" in stats:
        print(f"[ERROR] {stats['error']}")
    else:
        print("\n=== NLP Extraction Statistics ===")
        print(f"Total Documents:      {stats['total_records']}")
        print(f"Total Entities:       {stats['total_entities']}")
        print(f"Total Relations:      {stats['total_relations']}")
        print(f"Errors:               {stats['errors']}")
        print(f"Avg Entities/Doc:     {stats['avg_entities_per_doc']:.2f}")
        print(f"Avg Relations/Doc:    {stats['avg_relations_per_doc']:.2f}")
        
        print("\n--- Top Entity Labels ---")
        for label, count in stats["top_entity_labels"]:
            print(f"  {label:20} {count:6}")
        
        print("\n--- Domain Distribution ---")
        for domain, count in stats["domain_distribution"]:
            print(f"  {domain:20} {count:6}")
        
        if stats["top_relation_types"]:
            print("\n--- Top Relation Types ---")
            for rel_type, count in stats["top_relation_types"]:
                print(f"  {rel_type:20} {count:6}")
