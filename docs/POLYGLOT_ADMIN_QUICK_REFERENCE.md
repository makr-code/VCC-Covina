# Polyglot Admin Tool - Quick Reference

## 🚀 Launch
```powershell
python tools\polyglot_admin.py
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `F5` | Refresh All |
| `Ctrl+O` | Open Document |
| `Ctrl+F` | Focus Search |
| `Ctrl+Shift+S` | Focus SAGA View |
| `Ctrl+Shift+D` | Focus Document View |
| `Ctrl+Shift+G` | Focus Graph View |
| `Ctrl+Shift+V` | Focus Vector View |

## 📊 UI Layout

```
┌─────────────┬─────────────┐
│ Graph       │ Vector      │
│ (Neo4j)     │ (ChromaDB)  │
├─────────────┼─────────────┤
│ SAGA        │ Document    │
│ (UDS3)      │ (PostgreSQL)│
└─────────────┴─────────────┘
```

## 🔗 Document-to-SAGA Workflow

1. **Load Document:** Enter ID → "📄 Load by ID"
2. **Find SAGA:** Click "🔗 Find SAGA"
3. **View Steps:** Auto-switch to SAGA Events Tab
4. **Analyze:** Check step status (✅❌🔄⏳)

## 📊 SAGA Status Icons

| Icon | Status | Meaning |
|------|--------|---------|
| ✅ | Completed | Success |
| ❌ | Failed | Error |
| 🔄 | Compensated | Rolled back |
| ⏳ | Pending | Waiting |

## 🔍 SAGA ID Pattern

```python
saga_id = f"ingest_{document_id}"

# Example:
document_id = "doc_20241024_123456"
saga_id = "ingest_doc_20241024_123456"
```

## 📦 SAGA Execution Order

```
1. PostgreSQL → Metadata
2. CouchDB → Full Content
3. ChromaDB → Embeddings
4. Neo4j → Knowledge Graph
```

## 🛠️ Common Queries

### Cypher (Neo4j)
```cypher
// Find nodes
MATCH (n) RETURN n LIMIT 10

// Count relationships
MATCH ()-[r]->() RETURN count(r)
```

### SQL (PostgreSQL)
```sql
-- Recent SAGAs
SELECT * FROM saga_state 
ORDER BY created_at DESC 
LIMIT 10;

-- Failed steps
SELECT * FROM saga_steps 
WHERE status = 'failed';
```

## 🔌 Backend Ports

| Service | Port | URL |
|---------|------|-----|
| PostgreSQL | 5432 | localhost:5432 |
| ChromaDB | 8000 | http://localhost:8000 |
| Neo4j | 7687 | bolt://localhost:7687 |

## 📝 Quick Troubleshooting

**SAGA Errors:**
```powershell
# Check table exists
psql -c "SELECT COUNT(*) FROM saga_state;"

# Restart services
.\scripts\start_services.ps1
```

**Connection Issues:**
```powershell
# Test PostgreSQL
psql -h localhost -p 5432 -U postgres

# Test ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# Test Neo4j
cypher-shell -a bolt://localhost:7687
```

## 📚 Documentation

- **User Guide:** `polyglot_admin/README.md`
- **Dev Guide:** `docs/POLYGLOT_ADMIN_DEVELOPMENT.md`
- **SAGA Details:** `docs/SAGA_ARCHITECTURE.md`

---

**Covina System © 2025** | v2.0.0
