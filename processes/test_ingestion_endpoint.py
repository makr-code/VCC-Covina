"""
Test Prozess-Ingestion Endpoint

Testet POST /ingestion/processes mit VPB JSON Beispiel.
"""
import json
import requests

# Test VPB JSON (Bauleitplanung Beispiel)
VPB_PROCESS = {
    "process": {
        "key": "bauleitplanung",
        "name": "Bauleitplanung gemäß BauGB",
        "version": "1.0",
        "domain": "Stadtplanung",
        "owner": "Planungsamt",
        "status": "active",
        "description": "Aufstellung von Bebauungsplänen nach BauGB",
        "legal_refs": [
            {"source": "BauGB", "article": "§1", "description": "Aufgabe, Begriff und Grundsätze der Bauleitplanung"},
            {"source": "BauGB", "article": "§2", "description": "Aufstellung der Bauleitpläne"},
            {"source": "BauGB", "article": "§3", "description": "Beteiligung der Öffentlichkeit"},
            {"source": "BauGB", "article": "§4", "description": "Beteiligung der Behörden"},
        ],
        "steps": [
            {
                "key": "aufstellungsbeschluss",
                "name": "Aufstellungsbeschluss",
                "type": "decision",
                "description": "Gemeinde beschließt Aufstellung eines Bebauungsplans",
                "role": {"name": "Gemeinderat", "level": "council"},
                "org_unit": {"name": "Stadtrat", "level": "legislative"},
                "duration_days": 14,
                "mandatory": True,
                "legal_refs": ["BauGB §2 Abs. 1"],
                "controls": [
                    {"name": "Ratsbeschluss erforderlich", "type": "approval", "criticality": "high"}
                ],
            },
            {
                "key": "bekanntmachung",
                "name": "Öffentliche Bekanntmachung",
                "type": "notification",
                "description": "Bekanntmachung des Aufstellungsbeschlusses",
                "role": {"name": "Pressestelle", "level": "operational"},
                "org_unit": {"name": "Presseamt", "level": "department"},
                "duration_days": 7,
                "mandatory": True,
                "legal_refs": ["BauGB §2 Abs. 1"],
                "systems": [
                    {"name": "Amtsblatt System", "type": "publication"}
                ],
            },
            {
                "key": "planentwurf",
                "name": "Erstellung Planentwurf",
                "type": "task",
                "description": "Erstellung des ersten Planentwurfs mit Begründung",
                "role": {"name": "Stadtplaner", "level": "operational"},
                "org_unit": {"name": "Planungsamt", "level": "department"},
                "duration_days": 90,
                "mandatory": True,
                "legal_refs": ["BauGB §2a"],
                "inputs": [
                    {"name": "Bestandsanalyse", "type": "document", "required": True},
                    {"name": "Umweltbericht", "type": "document", "required": True},
                ],
                "outputs": [
                    {"name": "Planentwurf", "type": "document", "required": True},
                    {"name": "Begründung", "type": "document", "required": True},
                ],
            },
            {
                "key": "fruehe_beteiligung",
                "name": "Frühzeitige Öffentlichkeitsbeteiligung",
                "type": "consultation",
                "description": "Unterrichtung und Anhörung der Öffentlichkeit",
                "role": {"name": "Stadtplaner", "level": "operational"},
                "org_unit": {"name": "Planungsamt", "level": "department"},
                "duration_days": 30,
                "mandatory": True,
                "legal_refs": ["BauGB §3 Abs. 1"],
                "inputs": [
                    {"name": "Planentwurf", "type": "document", "required": True},
                ],
                "outputs": [
                    {"name": "Stellungnahmen Öffentlichkeit", "type": "document", "required": False},
                ],
            },
            {
                "key": "behoerdenbeteiligung",
                "name": "Beteiligung der Behörden",
                "type": "consultation",
                "description": "Einholung von Stellungnahmen der Träger öffentlicher Belange",
                "role": {"name": "Stadtplaner", "level": "operational"},
                "org_unit": {"name": "Planungsamt", "level": "department"},
                "duration_days": 30,
                "mandatory": True,
                "legal_refs": ["BauGB §4 Abs. 1"],
                "outputs": [
                    {"name": "Stellungnahmen Behörden", "type": "document", "required": False},
                ],
            },
            {
                "key": "oeffentliche_auslegung",
                "name": "Öffentliche Auslegung",
                "type": "consultation",
                "description": "Auslegung des Entwurfs für die Öffentlichkeit",
                "role": {"name": "Stadtplaner", "level": "operational"},
                "org_unit": {"name": "Planungsamt", "level": "department"},
                "duration_days": 30,
                "mandatory": True,
                "legal_refs": ["BauGB §3 Abs. 2"],
                "inputs": [
                    {"name": "Überarbeiteter Planentwurf", "type": "document", "required": True},
                ],
                "outputs": [
                    {"name": "Einwendungen", "type": "document", "required": False},
                ],
            },
            {
                "key": "abwaegung",
                "name": "Abwägung der Stellungnahmen",
                "type": "task",
                "description": "Abwägung der eingegangenen Stellungnahmen und Einwendungen",
                "role": {"name": "Gemeinderat", "level": "council"},
                "org_unit": {"name": "Stadtrat", "level": "legislative"},
                "duration_days": 60,
                "mandatory": True,
                "legal_refs": ["BauGB §1 Abs. 7"],
                "inputs": [
                    {"name": "Stellungnahmen Öffentlichkeit", "type": "document", "required": False},
                    {"name": "Stellungnahmen Behörden", "type": "document", "required": False},
                    {"name": "Einwendungen", "type": "document", "required": False},
                ],
                "outputs": [
                    {"name": "Abwägungstabelle", "type": "document", "required": True},
                ],
                "controls": [
                    {"name": "Gerechte Abwägung erforderlich", "type": "review", "criticality": "critical"}
                ],
            },
            {
                "key": "satzungsbeschluss",
                "name": "Satzungsbeschluss",
                "type": "decision",
                "description": "Beschluss des Bebauungsplans als Satzung",
                "role": {"name": "Gemeinderat", "level": "council"},
                "org_unit": {"name": "Stadtrat", "level": "legislative"},
                "duration_days": 14,
                "mandatory": True,
                "legal_refs": ["BauGB §10 Abs. 1"],
                "inputs": [
                    {"name": "Finaler Planentwurf", "type": "document", "required": True},
                    {"name": "Abwägungstabelle", "type": "document", "required": True},
                ],
                "controls": [
                    {"name": "Ratsbeschluss erforderlich", "type": "approval", "criticality": "high"}
                ],
            },
            {
                "key": "ausfertigung",
                "name": "Ausfertigung",
                "type": "task",
                "description": "Ausfertigung des Bebauungsplans durch den Bürgermeister",
                "role": {"name": "Bürgermeister", "level": "executive"},
                "org_unit": {"name": "Bürgermeisteramt", "level": "executive"},
                "duration_days": 7,
                "mandatory": True,
                "legal_refs": ["BauGB §10 Abs. 3"],
            },
            {
                "key": "veroeffentlichung",
                "name": "Bekanntmachung und Inkrafttreten",
                "type": "notification",
                "description": "Öffentliche Bekanntmachung des Bebauungsplans",
                "role": {"name": "Pressestelle", "level": "operational"},
                "org_unit": {"name": "Presseamt", "level": "department"},
                "duration_days": 7,
                "mandatory": True,
                "legal_refs": ["BauGB §10 Abs. 3"],
                "systems": [
                    {"name": "Amtsblatt System", "type": "publication"}
                ],
                "outputs": [
                    {"name": "Rechtskräftiger Bebauungsplan", "type": "document", "required": True, "retention_days": 3650},
                ],
            },
        ],
    }
}


def test_process_ingestion():
    """Test POST /ingestion/processes endpoint."""
    url = "http://127.0.0.1:45679/ingestion/processes"
    
    payload = {
        "process_json": json.dumps(VPB_PROCESS, ensure_ascii=False),
        "run_mining": True,
        "guidelines_path": None,  # Use default
    }
    
    print("=" * 80)
    print("Testing POST /ingestion/processes")
    print("=" * 80)
    print(f"\nURL: {url}")
    print(f"Process: {VPB_PROCESS['process']['name']}")
    print(f"Steps: {len(VPB_PROCESS['process']['steps'])}")
    print(f"Run Mining: {payload['run_mining']}")
    print("\nSending request...\n")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 201:
            print("\n✅ Process ingestion successful!")
        else:
            print(f"\n❌ Process ingestion failed with status {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is ingestion backend running on port 45679?")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_process_ingestion()
