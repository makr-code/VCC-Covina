# Covina/UDS3 RAG-Verbesserungen - Implementierungs-Todo

**Basis:** Strategische Analyse RAG-Verbesserungen (docs/RAG_ANALYSE_UND_VERBESSERUNGEN.md)  
**Datum:** 6. Oktober 2025  
**Status:** Planung & Priorisierung

---

## 🎯 Executive Summary

**Ziel:** Covina/UDS3 von "gut" zu "exzellent" entwickeln durch systematische Schließung identifizierter RAG-Gaps.

**Strategie:** Inkrementelle Verbesserung (Szenario C) - On-Premise, souverän, keine Cloud-Migration.

**Timeline:** 4 Phasen über 12 Monate (Q1-Q4 2025)

---

## 📋 Todo-Übersicht (32 Tasks)

```
Phase 1: Hybrid Retrieval & Re-Ranking     [6 Tasks]  ⭐⭐⭐⭐⭐ Kritisch
Phase 2: Selbstoptimierende Kreisläufe    [9 Tasks]  ⭐⭐⭐⭐⭐ Kritisch  
Phase 3: Process Mining                   [6 Tasks]  ⭐⭐⭐⭐ Hoch
Phase 4: Agenten-Framework                 [6 Tasks]  ⭐⭐⭐ Mittel-Hoch
Continuous: RAGOps                         [5 Tasks]  ⭐⭐⭐ Mittel
```

---

Siehe vollständige Details in: **docs/RAG_VERBESSERUNGEN_TODO_DETAILLIERT.md**

---

## Quick Reference: Kritische Lücken

### Gap 1: Hybrid Retrieval & Re-Ranking ⭐⭐⭐⭐⭐
**Status:** Fehlt komplett  
**Impact:** Hoch (Retrieval-Qualität)  
**Aufwand:** 6-8 Wochen

**Was fehlt:**
- BM25 Keyword Search
- Reciprocal Rank Fusion (RRF)
- Cross-Encoder Re-Ranking

**Aktuelle Implementation:**
```python
# Nur Vector Search (ChromaDB)
async def vector_search(query: str):
    return await chromadb.search(query)
```

**Ziel-Implementation:**
```python
class HybridRetriever:
    async def retrieve(self, query):
        # 1. Parallel: Vector + BM25
        # 2. RRF Fusion
        # 3. Cross-Encoder Re-Rank
        # 4. Neo4j Context Enrichment
```

---

### Gap 2: Selbstoptimierende Kreisläufe ⭐⭐⭐⭐⭐
**Status:** Konzept vorhanden, nicht implementiert  
**Impact:** Sehr hoch (Continuous Learning)  
**Aufwand:** 8-10 Wochen

**Was fehlt:**
- **Veritas:** Feedback-Aggregation
- **Clara:** PEFT/LoRA Model-Tuning
- **Covina:** Gap-basierte Datenaufnahme

**Verfügbar:**
- ✅ AI Judge (Evaluation)
- ✅ Benchmark Database
- ❌ Feedback-Loop

---

### Gap 3: Prozessintelligenz ⭐⭐⭐⭐
**Status:** Nicht vorhanden  
**Impact:** Hoch (Proaktive Optimierung)  
**Aufwand:** 10-12 Wochen

**Was fehlt:**
- Process Mining (PM4Py)
- Bottleneck-Detection
- LLM-basierte Optimierungsvorschläge

---

### Gap 4: Agenten-Framework ⭐⭐⭐
**Status:** Rudimentär  
**Impact:** Mittel-Hoch  
**Aufwand:** 6-8 Wochen

**Was fehlt:**
- LangGraph-Integration
- Multi-Agent-Orchestrierung
- Tool-Calling

**Verfügbar:**
- ✅ Multi-LLM Judge (Agent-ähnlich)
- ❌ Framework

---

### Gap 5: RAGOps Automatisierung ⭐⭐⭐
**Status:** Manuell  
**Impact:** Mittel  
**Aufwand:** Kontinuierlich

**Was fehlt:**
- Retrieval-Quality-Metriken
- Automatic Evaluation
- Drift-Detection
- A/B Testing

---

## Priorisierte Roadmap

### Q1 2025: Hybrid Retrieval (6-8 Wochen)

**Tasks:**
1. [ ] BM25-Indexer implementieren (1 Woche)
2. [ ] RRF-Fusion (3 Tage)
3. [ ] Cross-Encoder Re-Ranking (4 Tage)
4. [ ] Hybrid-Retriever-Orchestrierung (1 Woche)
5. [ ] Backend-API-Integration (3 Tage)
6. [ ] Evaluation & Benchmarks (1 Woche)

**Deliverable:** `/hybrid/search` Endpoint

---

### Q2 2025: Clara/Veritas/Covina (8-10 Wochen)

**Tasks:**

**Veritas (3 Wochen):**
1. [ ] Strukturiertes Feedback-Schema (1 Woche)
2. [ ] Feedback-Aggregation (4 Tage)
3. [ ] Veritas-Dashboard (1 Woche)

**Clara (4 Wochen):**
4. [ ] PEFT/LoRA-Integration (2 Wochen)
5. [ ] Training-Data-Generation (1 Woche)
6. [ ] Validation-Pipeline (4 Tage)
7. [ ] Model-Versioning (3 Tage)

**Covina (2 Wochen):**
8. [ ] Gap-Detection-Agent (1 Woche)
9. [ ] Source-Priorisierung (3 Tage)
10. [ ] Discovery-Integration (4 Tage)

**Deliverable:** End-to-End Feedback-Loop

---

### Q3 2025: Process Mining (10-12 Wochen)

**Tasks:**
1. [ ] PM4Py-Integration (1 Woche)
2. [ ] Event-Log-Extraktion (1 Woche)
3. [ ] Process-Discovery (2 Wochen)
4. [ ] Bottleneck-Detection (1 Woche)
5. [ ] LLM-Optimierung (2 Wochen)
6. [ ] Dashboard (2 Wochen)

**Deliverable:** Process-Mining-Dashboard

---

### Q4 2025: Agenten-Framework (6-8 Wochen)

**Tasks:**
1. [ ] LangGraph-Integration (1 Woche)
2. [ ] Agent-Definitionen (2 Wochen)
3. [ ] Supervisor-Pattern (1 Woche)
4. [ ] State-Management (1 Woche)
5. [ ] Tool-Calling (1 Woche)
6. [ ] Workflow-Definitionen (1 Woche)

**Deliverable:** Multi-Agent-Workflow

---

### Continuous: RAGOps

**Tasks:**
1. [ ] Retrieval-Metriken (1 Woche)
2. [ ] Auto-Evaluation (1 Woche)
3. [ ] Drift-Detection (1 Woche)
4. [ ] A/B Testing (2 Wochen)
5. [ ] Monitoring-Dashboards (1 Woche)

**Deliverable:** Production-Monitoring

---

## 📊 Ressourcen

### Team (Empfohlen)

| Role | FTE | Phasen |
|------|-----|--------|
| Senior ML Engineer | 1.0 | Phase 2, 4 |
| Backend Engineer | 1.0 | Phase 1, 5 |
| Data Engineer | 0.5 | Phase 2, 3 |
| DevOps | 0.5 | Phase 5 |

---

## 🎯 Erfolgskriterien

### Phase 1:
- MRR@10 > 0.8
- Latency < 500ms (p95)

### Phase 2:
- Model-Performance +10-15%
- Re-Training < 1 Woche

### Phase 3:
- Bottleneck-Detection > 90%

### Phase 4:
- Multi-Agent funktional

### Phase 5:
- Daily Auto-Evaluation

---

## ⚠️ Top-Risiken

1. **PEFT-Training instabil** → Validation & Rollback
2. **PM4Py komplex** → PoC & Expertise
3. **Performance** → Profiling & Caching
4. **Ressourcen** → Iterative Priorisierung

---

## 📅 Nächste Schritte

1. **Sofort:** Stakeholder-Review dieser Roadmap
2. **KW 41:** Team-Allokation für Phase 1
3. **KW 42:** Start Phase 1 (Hybrid Retrieval)
4. **Monatlich:** Roadmap-Review & Adjustment

---

**Detaillierte Task-Liste:** `docs/RAG_VERBESSERUNGEN_TODO_DETAILLIERT.md`  
**Strategische Analyse:** `docs/RAG_ANALYSE_UND_VERBESSERUNGEN.md`

---

*Erstellt: 6. Oktober 2025*  
*Status: Draft für Review*
