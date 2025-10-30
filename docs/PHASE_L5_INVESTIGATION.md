# Phase L5 Investigation Report - Document Migration Blocker

**Date:** 18. Januar 2025  
**Status:** ❌ **BLOCKED** - Cannot proceed without domain information  
**Investigator:** GitHub Copilot

---

## Executive Summary

Phase L5 (Simple Document Migration) **cannot be implemented** as originally planned. Investigation revealed critical schema limitations:

1. **No Domain Information:** Documents have `classification = DOCUMENT_TYPE` (RECHTSPRECHUNG, VERTRAG), NOT legal domain
2. **No Content Storage:** PostgreSQL has NO `content` field, CouchDB has NO documents
3. **Migration Script Incompatible:** Existing `document_migration.py` requires full text content for NLP extraction

**Recommendation:** Implement **Alternative Phase L5A** (Rule-Based Domain Inference) or wait for Phase L4 (LLM Extraction) to become operational.

---

## Schema Analysis

### PostgreSQL `documents` Table

**Columns Found:**
```
document_id         - Primary key (NOT 'id'!)
file_path           - File system path
classification      - Document type (RECHTSPRECHUNG, VERTRAG, GESETZ, DOCUMENT)
content_length      - Size in bytes
legal_terms_count   - Number of legal terms extracted
created_at          - Timestamp
quality_score       - Document quality
processing_status   - Processing state
company_metadata    - JSON metadata
```

**Missing:**
- ❌ `content` field (full text)
- ❌ `domain` field (legal domain classification)
- ❌ `legal_domain_id` (foreign key to LegalDomain)

**Classification Distribution:**
```
RECHTSPRECHUNG  (Case Law):       61,241 docs (36%)
VERTRAG         (Contract):       47,231 docs (28%)
DOCUMENT        (Generic):        36,123 docs (21%)
GESETZ          (Statute):        23,606 docs (14%)
RECHTSTEXT      (Legal Text):        220 docs (<1%)
contract        (lowercase):          31 docs (<1%)
TEST            (Test):                2 docs (<1%)
─────────────────────────────────────────────────
Total with classification:       168,454 docs (100%)
```

**Key Finding:** `classification` field contains **document type**, NOT **legal domain**!

---

### Neo4j `Document` Nodes

**Properties Found:**
```
id                   - Document ID (matches PostgreSQL document_id!)
classification       - Document type (same as PostgreSQL)
file_path            - File system path
legal_terms_count    - Number of legal terms
quality_score        - Quality metric
created_at           - Timestamp
```

**Missing:**
- ❌ `domain` property (legal domain)
- ❌ `content` property (full text)

**Relationships:**
- ❌ **NO** `BELONGS_TO` relationships to `LegalDomain` nodes exist
- ⚠️  Neo4j query warned: "relationship type `BELONGS_TO` does not exist"

**Key Finding:** Neo4j has NO domain information either!

---

### CouchDB File Storage

**Status:** Backend available, but **NO documents found**

**Test Query:**
```python
backend.get_document("00002ee561bf6db3")  # Returns: None
```

**Key Finding:** CouchDB is **empty** or documents are stored differently!

---

## Blocker Analysis

### Original Phase L5 Plan (FAILED)

**Approach:**
```
Query PostgreSQL → Map classification → LegalDomain → Create BELONGS_TO
```

**Why it fails:**
1. ❌ `classification` is document TYPE, not domain
2. ❌ No mapping possible: "RECHTSPRECHUNG" → ??? (which domain?)
3. ❌ Document type is orthogonal to legal domain
   - A "RECHTSPRECHUNG" document can be about Baurecht, Arbeitsrecht, Strafrecht, etc.
   - Classification provides **NO domain information**!

**Classification Mapping Table (Useless):**
```python
MAPPINGS = {
    "baurecht": "baurecht",          # ✅ Would work
    "arbeitsrecht": "arbeitsrecht",  # ✅ Would work
    "RECHTSPRECHUNG": "???",         # ❌ CANNOT MAP!
    "VERTRAG": "???",                # ❌ CANNOT MAP!
    "GESETZ": "???",                 # ❌ CANNOT MAP!
}
```

**Result:** 9 out of 10 documents skipped (unmapped)!

---

### Existing `document_migration.py` (BLOCKED)

**Approach:**
```
Query PostgreSQL → Fetch CouchDB content → NLP extraction → Create entities
```

**Why it fails:**
1. ❌ CouchDB has NO content (`get_document()` returns None)
2. ❌ PostgreSQL has NO `content` column
3. ❌ Cannot run NLP extraction without text!

**Test Result:**
```
[WARN] No content found for 00002ee561bf6db3
[WARN] No content found for 0000a9f892cc7019
[WARN] No content found for 00010cea4a2c615c
[WARN] No content found for 0001131132897d11
[WARN] No content found for 0002318aff70bb16
[BATCH 1] Complete: 5 docs, 0 entities, 0 errors
```

**Result:** 0 entities extracted, migration useless!

---

## Alternative Approaches

### Option A: Rule-Based Domain Inference (Recommended)

**Approach:** Infer domain from file_path, metadata, classification patterns

**Heuristics:**
1. **File Path Keywords:**
   - `"baurecht"` in path → `baurecht` domain
   - `"arbeitsrecht"` in path → `arbeitsrecht` domain
   - `"strafrecht"` in path → `strafrecht` domain

2. **Legal Terms Analysis:**
   - High `legal_terms_count` + "BauGB" references → `baurecht`
   - High `legal_terms_count` + "BGB" references → `zivilrecht`
   - High `legal_terms_count` + "StGB" references → `strafrecht`

3. **Classification Combinations:**
   - `RECHTSPRECHUNG` + path contains "verwaltungsgericht" → `verwaltungsrecht`
   - `GESETZ` + path contains "umwelt" → `immissionsschutzrecht`

**Implementation:**
```python
def infer_domain_from_metadata(doc: Dict) -> Optional[str]:
    file_path = doc.get("file_path", "").lower()
    classification = doc.get("classification", "").lower()
    
    # Check file path for domain keywords
    for domain_keyword, domain_id in DOMAIN_KEYWORDS.items():
        if domain_keyword in file_path:
            return domain_id
    
    # Check legal terms for statutory references
    # (requires additional PostgreSQL columns or analysis)
    
    # Fallback: Cannot infer
    return None
```

**Pros:**
- ✅ No NLP needed
- ✅ No content storage needed
- ✅ Fast (simple string matching)
- ✅ Can start immediately

**Cons:**
- ⚠️ Lower accuracy than NLP
- ⚠️ Requires domain keyword database
- ⚠️ May miss ~20-40% of documents

---

### Option B: PostgreSQL Schema Extension

**Approach:** Add `domain` column to `documents` table, backfill from external source

**Schema Change:**
```sql
ALTER TABLE documents ADD COLUMN legal_domain VARCHAR(100);
ALTER TABLE documents ADD COLUMN domain_confidence FLOAT DEFAULT 0.0;

CREATE INDEX idx_documents_legal_domain ON documents(legal_domain);
```

**Backfill Strategy:**
1. **External Metadata:** If original source has domain info, re-import
2. **Manual Classification:** Human review of top 1000 documents, extrapolate
3. **ML Classification:** Train classifier on labeled subset, predict rest

**Pros:**
- ✅ Clean schema solution
- ✅ Reusable for future documents
- ✅ Fast queries once backfilled

**Cons:**
- ❌ Requires data source with domain info
- ❌ Time-consuming backfill process
- ❌ May not be possible if source data lacks domains

---

### Option C: Wait for Phase L4 (LLM Extraction)

**Approach:** Use LLM to extract domain from document text

**Requirements:**
1. **Content Storage:** Fix CouchDB integration or add `content` to PostgreSQL
2. **LLM Integration:** OpenAI/Anthropic API or local model
3. **Prompt Engineering:** Design prompts for domain classification

**Example Prompt:**
```
Analyze this legal document excerpt and classify it into one of these domains:
- Baurecht (Construction Law)
- Arbeitsrecht (Labor Law)
- Strafrecht (Criminal Law)
- Zivilrecht (Civil Law)
- Verwaltungsrecht (Administrative Law)
...

Document excerpt:
[first 500 words]

Respond with ONLY the domain ID (e.g., "baurecht").
```

**Pros:**
- ✅ High accuracy (~80-95%)
- ✅ Works for all documents
- ✅ Can extract multiple domains per doc

**Cons:**
- ❌ Requires content storage fix
- ❌ Slow (LLM API latency)
- ❌ Expensive (API costs for 161k docs)
- ❌ Complex implementation

---

## Recommendations

### Immediate Next Steps (This Sprint)

1. **Investigate Content Storage:**
   - Where is full document text stored?
   - CouchDB empty → files on disk? Different CouchDB database?
   - Can we add `content` column to PostgreSQL?

2. **Implement Rule-Based Domain Inference (Option A):**
   - Create `ingestion/graph/document_migration_rulebased.py`
   - Build keyword → domain mapping table
   - Test on 1000 document sample
   - Measure accuracy (manual review of 100 docs)

3. **Document Findings:**
   - Create `docs/PHASE_L5_INVESTIGATION.md` (this document)
   - Update `docs/LEGAL_KG_FINAL_SUMMARY.md` with blockers
   - Add to `copilot-todo.md` with priority

### Medium-Term (Next 2-4 Weeks)

4. **Fix Content Storage:**
   - Identify correct content retrieval method
   - Test with sample documents
   - Update `document_migration.py` if needed

5. **Evaluate LLM Approach:**
   - Test LLM classification on 100 documents
   - Measure accuracy vs. rule-based
   - Estimate cost for full 161k corpus

6. **Implement Hybrid Approach:**
   - Rule-based for high-confidence matches (50-60%)
   - LLM for uncertain cases (40-50%)
   - Manual review for errors (<5%)

### Long-Term (Phase L6+)

7. **Schema Migration:**
   - Add `legal_domain` column to PostgreSQL
   - Backfill from successful domain classification
   - Create foreign key to `dim_domain` (analytics)

8. **Quality Metrics:**
   - Track domain classification accuracy
   - Monitor domain distribution (balanced?)
   - Flag documents with conflicting domains

---

## Impact Assessment

### Phase L5 Original Goals (NOT MET)

- ❌ Link 161k documents to Legal Knowledge Graph
- ❌ Enable domain-based filtering in queries
- ❌ Populate analytics layer (legal_stats_daily)
- ❌ Simple classification mapping (blocked)

### What We Learned

- ✅ Document schema analysis complete
- ✅ Blocker identified (no domain info)
- ✅ Alternative approaches designed
- ✅ Investigation findings documented

### Revised Timeline

```
Original Plan:
  Phase L5 (Simple Migration):  2-3 days

Revised Plan:
  Phase L5A (Rule-Based):       3-5 days
  Phase L5B (Content Fix):      1-2 days
  Phase L4 (LLM Extraction):    7-10 days
  Phase L5C (Hybrid Approach):  3-5 days
  ────────────────────────────────────────
  Total:                        14-22 days
```

---

## Code Changes Made

### Files Modified

1. **`ingestion/graph/document_migration_simple.py`** (Created, but blocked)
   - Simple classification → domain mapping
   - Batch UNWIND relationship creation
   - Checkpointing & resume logic
   - **Status:** Cannot run (no domain info)

2. **`ingestion/graph/document_migration.py`** (Fixed)
   - Changed `id` → `document_id` (PostgreSQL column name)
   - Added `fetch=True` to execute_query() calls
   - Fixed Neo4j MATCH query (`doc_id` → `id` property)
   - **Status:** Runs but extracts 0 entities (no content)

3. **`check_classifications.py`** (Created, temporary)
   - PostgreSQL classification distribution analysis
   - **Result:** 168k docs, 7 distinct types

4. **`check_neo4j_docs.py`** (Created, temporary)
   - Neo4j Document node property inspection
   - **Result:** No domain info, no BELONGS_TO relationships

### Database Fixes Applied

- ✅ `document_id` instead of `id` (3 locations)
- ✅ `fetch=True` parameter added (2 locations)
- ✅ Neo4j property mapping corrected (1 location)

---

## Conclusion

**Phase L5 (Simple Migration) is BLOCKED** due to missing domain information in document properties.

**Recommended Path Forward:**
1. Implement **Phase L5A (Rule-Based Inference)** as interim solution
2. Investigate **content storage** for future NLP extraction
3. Plan **Phase L4 (LLM Extraction)** for high-accuracy domain classification

**Expected Outcome:**
- Rule-based: 50-70% of documents linked (80-100k docs)
- LLM-based: 90-95% of documents linked (145-155k docs)
- Combined: 95-98% coverage (155-165k docs)

**Next Task:** Create `ingestion/graph/document_migration_rulebased.py` with keyword matching logic.

---

**Report End**
