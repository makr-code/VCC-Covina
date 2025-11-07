# Themis Adapter - Quick Reference

## 🚀 Quick Start

```bash
# 1. Enable Themis in .env.production
USE_THEMIS=true
THEMIS_URL=http://localhost:8765

# 2. Start backends
.\scripts\start_services.ps1

# 3. Verify
curl http://127.0.0.1:45678/themis/mode
```

---

## 📋 Key Endpoints

| Endpoint | Description | Response |
|----------|-------------|----------|
| `GET /themis/mode` | Configuration status | `{enabled, url, backends}` |
| `GET /themis/health` | Health check + latency | `{status, latency_ms}` |
| `GET /health` | General backend health | Standard health check |

**Both backends:** Port 45678 (Main), Port 45679 (Ingestion)

---

## 🔧 Configuration

```bash
# .env.production
USE_THEMIS=true                    # Enable Themis adapter
THEMIS_URL=http://localhost:8765   # Themis API endpoint
THEMIS_TIMEOUT=30                  # Request timeout (seconds)
THEMIS_MAX_RETRIES=3               # Retry attempts
```

---

## 🧪 Testing

```bash
# Smoke test
python tests/test_themis_smoke.py

# Full test with CRUD
python tests/test_themis_smoke.py --full

# Expected: ✅ ALL TESTS PASSED
```

---

## 🏗️ Architecture

```
Application Code
    ↓
Unified Getters (get_*_backend)
    ↓
Feature Flag Check (USE_THEMIS)
    ↓
┌─────────────┬─────────────┐
│   Themis    │    UDS3     │
│  (Active)   │ (Fallback)  │
└─────────────┴─────────────┘
```

---

## 💻 Code Examples

### Using Unified Getters

```python
# Works with Themis OR UDS3 (no code changes needed)
relational = get_relational_backend()
vector = get_vector_backend()
graph = get_graph_backend()
document = get_document_backend()

# Usage same as before
await relational.insert(doc_id, data)
await vector.add(vector_id, embedding, metadata)
```

### Transaction Support

```python
# Async context manager
async with themis_adapter.transaction() as txn:
    await relational.insert(...)
    await vector.add(...)
    # Auto-commit on success, rollback on error
```

---

## 🛠️ Troubleshooting

### Themis Not Available

```bash
# Check Themis server
curl http://localhost:8765/health

# Check backend logs
# Look for: "✅ ThemisAdapter aktiviert" or "❌ Initialisierung fehlgeschlagen"
```

### Performance Issues

```bash
# Check latency
curl http://127.0.0.1:45678/themis/health | jq .latency_ms

# Expected: < 50ms for local Themis
# If > 100ms: Check network/Themis server load
```

### Switch Back to UDS3

```bash
# Set USE_THEMIS=false in .env.production
# Restart backends
.\scripts\stop_services.ps1
.\scripts\start_services.ps1

# Verify: curl http://127.0.0.1:45678/themis/mode
# Should show: "enabled": false, "fallback": "UDS3"
```

---

## 📊 Status Check

```bash
# Quick status check (both backends)
curl -s http://127.0.0.1:45678/themis/mode | jq '{enabled, backends}'
curl -s http://127.0.0.1:45679/themis/mode | jq '{enabled, backends}'

# Health with latency
curl -s http://127.0.0.1:45678/themis/health | jq '{status, latency_ms}'
```

---

## 📚 Documentation

- **Integration Guide:** `docs/THEMIS_ADAPTER_INTEGRATION.md`
- **Gap Analysis:** `docs/THEMIS_ADAPTER_GAP_ANALYSIS.md`
- **Interface Design:** `docs/THEMIS_ADAPTER_INTERFACE_DESIGN.md`
- **Smoke Test:** `tests/test_themis_smoke.py`

---

## ✅ Integration Status

**P0 (Critical):**
- [x] Core adapter + 4 backends
- [x] Feature flag + ENV config
- [x] Unified backend getters
- [x] SAGA integration
- [x] Batch operations support

**P1 (Important):**
- [x] Health/debug endpoints
- [x] Shutdown hooks
- [x] Smoke test script
- [x] Documentation

**P2 (Optional):**
- [ ] Unit tests (mocked HTTP)
- [ ] Performance benchmarks

**Status:** ✅ **PRODUCTION READY**

---

**Last Updated:** 7. November 2025
