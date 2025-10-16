# Neo4j Schema Setup - Manuelle Anleitung

**Status:** PowerShell-Automatisierung hat Probleme mit Neo4j HTTP API.  
**Lösung:** Manuelles Copy-Paste im Neo4j Browser (5 Minuten)

---

## 🚀 Quick Setup (5 Minuten)

### 1. Neo4j Browser öffnen

```
http://192.168.178.94:7474
```

**Login:**
- User: `neo4j`
- Password: `v3f3b1d7`

---

### 2. Schema-Setup ausführen

**Öffne:** `scripts/neo4j_schema_setup.cypher`

**Methode 1: Gesamtes Script** (empfohlen)
1. Kopiere GESAMTEN Inhalt von `neo4j_schema_setup.cypher`
2. Paste in Neo4j Browser
3. Klicke ▶ (Play) ODER Ctrl+Enter
4. Warte ~10 Sekunden

**Methode 2: Abschnittweise** (bei Problemen)
1. Kopiere Abschnitt 1 (Constraints & Indexes)
2. Paste & Execute
3. Warte auf Erfolg
4. Wiederhole für Abschnitt 2-5

---

### 3. Verifikation

**Test-Query:**
```cypher
// Nodes zählen
MATCH (n)
RETURN labels(n)[0] AS NodeType, count(n) AS Count
ORDER BY Count DESC;
```

**Erwartete Ausgabe:**
```
NodeType         | Count
-----------------+-------
Document         | 4
LegalReference   | 4
ProcessStep      | 5
Person           | 2
Organization     | 2
```

**Relationships zählen:**
```cypher
MATCH ()-[r]->()
RETURN type(r) AS RelationType, count(r) AS Count
ORDER BY Count DESC;
```

**Erwartete Ausgabe:**
```
RelationType     | Count
-----------------+-------
REFERENCES       | 4
REQUIRES         | 2
FOLLOWED_BY      | 3
BASED_ON         | 1
SUBMITS          | 1
PROCESSES        | 1
WORKS_FOR        | 1
```

---

### 4. Graph visualisieren

**Query:**
```cypher
MATCH path = (d:Document {id: "doc_wohngeld_antrag_2024"})-[*1..2]-(related)
RETURN path
LIMIT 20;
```

**Klicke auf "Graph" View** → Siehst du Nodes & Relationships!

---

## ✅ Schema erfolgreich? → Weiter!

```powershell
# Demo ausführen
python examples\demo_graph_rag.py
```

---

## ⚠️ Troubleshooting

### Problem: "Constraint already exists"

**Lösung:** Ignorieren (harmlos) ODER Schema löschen:

```cypher
// WARNUNG: Löscht ALLE Daten!
MATCH (n) DETACH DELETE n;

DROP CONSTRAINT document_id_unique IF EXISTS;
DROP CONSTRAINT legal_ref_unique IF EXISTS;
DROP CONSTRAINT process_step_unique IF EXISTS;
DROP CONSTRAINT person_id_unique IF EXISTS;
DROP CONSTRAINT org_id_unique IF EXISTS;
```

Dann Script erneut ausführen.

### Problem: Neo4j Browser lädt nicht

**Prüfen:**
```powershell
Test-NetConnection -ComputerName 192.168.178.94 -Port 7474
```

**Wenn fehlgeschlagen:**
- Neo4j starten: `neo4j start` ODER
- Docker: `docker start neo4j`

### Problem: "Database 'neo4j' not found"

**Lösung:** Ändere in Script:
```
http://192.168.178.94:7474/db/neo4j/tx/commit
→
http://192.168.178.94:7474/db/system/tx/commit
```

ODER erstelle Database `neo4j` in Neo4j Desktop.

---

## 📚 Nächste Schritte

Nach erfolgreichem Setup:

1. **Demo ausführen:**
   ```powershell
   python examples\demo_graph_rag.py
   ```

2. **Backend testen:**
   ```powershell
   python backend.py
   # Anderes Terminal:
   curl http://localhost:8000/graph-rag/search -X POST -H "Content-Type: application/json" -d '{"query":"Antrag Wohngeld","top_k":5}'
   ```

3. **Integration aktivieren:**
   - Siehe: `docs/GRAPH_RAG_TODO.md`
   - Task 2-5: ChromaDB, SQLite, Backend Integration

---

## 🎯 Was wurde erstellt?

**Nodes (17 total):**
- 4× Document (Formulare, Richtlinien, Bescheide)
- 4× LegalReference (§1 WoGG, §3 WoGG, §8 BAföG, §68 VwGO)
- 5× ProcessStep (Antrag → Prüfung → Bescheid → Versand → Widerspruch)
- 2× Person (Max Mustermann, Erika Musterfrau)
- 2× Organization (Stadt München, Studentenwerk)

**Relationships (13 total):**
- 4× REFERENCES (Document → LegalReference)
- 2× REQUIRES (Document → ProcessStep)
- 3× FOLLOWED_BY (ProcessStep → ProcessStep)
- 1× BASED_ON (Document → Document)
- 1× SUBMITS (Person → Document)
- 1× PROCESSES (Organization → Document)
- 1× WORKS_FOR (Person → Organization)

**Indexes & Constraints:**
- 5× Unique Constraints (IDs)
- 6× Performance Indexes
- 2× Full-Text Search Indexes

---

## 📖 Ressourcen

- **Cypher-Script:** `scripts/neo4j_schema_setup.cypher`
- **Dokumentation:** `docs/COVINA_GRAPH_RAG_ANALYSE.md`
- **Quick Start:** `docs/GRAPH_RAG_QUICKSTART.md`

---

**Version:** 1.0 (Manuelles Setup)  
**Datum:** 6. Oktober 2025  
**Status:** ✅ Bereit für Verwendung
