# CouchDB Erweiterung für Binary File Storage - Änderungsanleitung

## Übersicht

CouchDB speichert aktuell nur den **extrahierten Text**-Content. Für vollständige Polyglot-Persistenz muss CouchDB auch die **Original-Binärdatei** als Attachment speichern.

## Aktueller Zustand

### Aktuelle CouchDB Speicherung (backend/ingestion.py, Lines 1817-1857)

```python
# AKTUELL (NUR TEXT):
doc_data = {
    "file_path": file_path,
    "content": content,  # ← NUR extrahierter Text!
    "classification": classification,
    "legal_terms_count": legal_count,
    "quality_score": quality_score,
    "timestamp": timestamp,
    "word_count": word_count
}

# Wird so in CouchDB gespeichert:
await asyncio.to_thread(
    job_manager.get_document_backend().create_document,
    doc_data,
    document_id
)
```

**Problem**: Original-Datei (PDF, DOCX, etc.) fehlt!

## Benötigte Änderungen

### 1. UDS3 CouchDB Backend erweitern

**Datei**: `uds3/database/` (oder wo auch immer das CouchDB Backend liegt)

**Neue Methode hinzufügen**:

```python
class CouchDBBackend:
    """UDS3 CouchDB Backend"""
    
    # BESTEHENDE Methode (bleibt):
    def create_document(self, doc_data: Dict[str, Any], doc_id: str) -> bool:
        """
        Create document with text content only.
        EXISTING METHOD - DO NOT CHANGE
        """
        # ... existing code ...
    
    # NEU: Erweiterte Methode mit Binary Attachment
    def create_document_with_binary(
        self, 
        doc_data: Dict[str, Any], 
        doc_id: str,
        binary_file_path: Optional[str] = None
    ) -> bool:
        """
        Create document with text content AND binary file attachment.
        
        Args:
            doc_data: Document data (text, metadata, etc.)
            doc_id: Document ID
            binary_file_path: Path to original binary file (PDF, DOCX, etc.)
            
        Returns:
            True if successful, False otherwise
            
        Example:
            backend.create_document_with_binary(
                doc_data={"content": "text...", "classification": "GESETZ"},
                doc_id="abc123",
                binary_file_path="/path/to/BImSchG.pdf"
            )
            
        CouchDB Structure:
            {
                "_id": "abc123",
                "content": "Extracted text...",
                "classification": "GESETZ",
                "_attachments": {
                    "original_file": {
                        "content_type": "application/pdf",
                        "data": "<base64-encoded-binary>"
                    }
                }
            }
        """
        try:
            # 1. Create base document (existing logic)
            response = self.db.save(doc_data)
            
            # 2. Add binary attachment if file path provided
            if binary_file_path and os.path.exists(binary_file_path):
                # Read binary file
                with open(binary_file_path, 'rb') as f:
                    binary_data = f.read()
                
                # Detect content type
                content_type = self._detect_content_type(binary_file_path)
                
                # Get document (needed for _rev)
                doc = self.db.get(doc_id)
                
                # Add attachment
                self.db.put_attachment(
                    doc=doc,
                    content=binary_data,
                    filename="original_file",  # Standard name
                    content_type=content_type
                )
                
                logger.info(f"[CouchDB] Binary attachment added: {binary_file_path} ({len(binary_data)} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"[CouchDB] Error creating document with binary: {e}")
            return False
    
    def _detect_content_type(self, file_path: str) -> str:
        """Detect MIME type from file extension"""
        import mimetypes
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or 'application/octet-stream'
    
    # NEU: Binary Attachment abrufen
    def get_binary_attachment(self, doc_id: str, attachment_name: str = "original_file") -> Optional[bytes]:
        """
        Retrieve binary attachment from document.
        
        Args:
            doc_id: Document ID
            attachment_name: Attachment name (default: "original_file")
            
        Returns:
            Binary data or None if not found
        """
        try:
            doc = self.db.get(doc_id)
            
            if '_attachments' not in doc:
                logger.warning(f"[CouchDB] No attachments found for {doc_id}")
                return None
            
            if attachment_name not in doc['_attachments']:
                logger.warning(f"[CouchDB] Attachment '{attachment_name}' not found")
                return None
            
            # Get attachment
            attachment = self.db.get_attachment(doc, attachment_name)
            
            return attachment.read() if attachment else None
            
        except Exception as e:
            logger.error(f"[CouchDB] Error getting binary attachment: {e}")
            return None
```

### 2. Ingestion Backend anpassen

**Datei**: `backend/ingestion.py`

**Änderung in `process_document_with_uds3()`** (ca. Line 1836):

```python
# VORHER (Lines 1836-1857):
if job_manager.get_document_backend():
    try:
        doc_data = {
            "file_path": file_path,
            "content": content,  # Nur Text
            "classification": classification,
            ...
        }
        await asyncio.to_thread(
            job_manager.get_document_backend().create_document,
            doc_data,
            document_id
        )
        db_results["document"] = "success"

# NACHHER (mit Binary Support):
if job_manager.get_document_backend():
    try:
        doc_data = {
            "file_path": file_path,
            "content": content,  # Text
            "classification": classification,
            "legal_terms_count": legal_count,
            "quality_score": quality_score,
            "timestamp": timestamp,
            "word_count": word_count
        }
        
        # Check if backend supports binary attachments
        backend = job_manager.get_document_backend()
        
        if hasattr(backend, 'create_document_with_binary'):
            # NEU: Use enhanced method with binary file
            await asyncio.to_thread(
                backend.create_document_with_binary,
                doc_data,
                document_id,
                file_path  # ← Original-Datei!
            )
            db_results["document"] = "success (with binary)"
            logger.info(f"[CouchDB] Document + Binary stored: {document_id}")
        else:
            # FALLBACK: Use old method (text only)
            await asyncio.to_thread(
                backend.create_document,
                doc_data,
                document_id
            )
            db_results["document"] = "success (text only)"
            logger.warning(f"[CouchDB] Only text stored (binary not supported)")
```

### 3. Alternative: Batch Mode erweitern

**Falls Batch Mode verwendet wird** (Lines 1814-1835):

```python
# VORHER:
if couchdb_batch:
    doc_data = {
        "file_path": file_path,
        "content": content,
        ...
    }
    await asyncio.to_thread(
        couchdb_batch.add,
        doc=doc_data,
        doc_id=document_id
    )

# NACHHER:
if couchdb_batch:
    doc_data = {
        "file_path": file_path,
        "content": content,
        "classification": classification,
        ...
    }
    
    # NEU: Pass binary file path to batch
    await asyncio.to_thread(
        couchdb_batch.add,
        doc=doc_data,
        doc_id=document_id,
        binary_file_path=file_path  # ← NEU!
    )
```

**Dann CouchDBBatch anpassen**:

```python
class CouchDBBatch:
    def add(self, doc: Dict, doc_id: str, binary_file_path: Optional[str] = None):
        """
        Add document to batch with optional binary file.
        
        Args:
            doc: Document data
            doc_id: Document ID
            binary_file_path: Optional path to binary file
        """
        # Store binary path for later
        self.buffer.append({
            'doc': doc,
            'doc_id': doc_id,
            'binary_path': binary_file_path  # ← NEU
        })
        
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
    def flush(self):
        """Flush batch to CouchDB"""
        for item in self.buffer:
            # Create document
            self.backend.create_document(item['doc'], item['doc_id'])
            
            # Add binary if provided
            if item.get('binary_path'):
                # Add attachment separately
                self.backend.put_attachment(
                    doc_id=item['doc_id'],
                    file_path=item['binary_path']
                )
```

## Benötigte Dateien zum Ändern

### Priorität 1: UDS3 CouchDB Backend

**Datei**: `uds3/database/couchdb_backend.py` (oder ähnlich)

**Änderungen**:
1. ✅ Neue Methode: `create_document_with_binary()`
2. ✅ Neue Methode: `get_binary_attachment()`
3. ✅ Helper: `_detect_content_type()`

**Code-Snippet für UDS3**:
```python
def create_document_with_binary(self, doc_data, doc_id, binary_file_path=None):
    """See detailed implementation above"""
    
def get_binary_attachment(self, doc_id, attachment_name="original_file"):
    """See detailed implementation above"""
    
def _detect_content_type(self, file_path):
    """See detailed implementation above"""
```

### Priorität 2: Ingestion Backend

**Datei**: `backend/ingestion.py`

**Line**: ~1836-1857 (CouchDB Single Mode)

**Änderung**:
```python
# Replace:
backend.create_document(doc_data, document_id)

# With:
if hasattr(backend, 'create_document_with_binary'):
    backend.create_document_with_binary(doc_data, document_id, file_path)
else:
    backend.create_document(doc_data, document_id)  # Fallback
```

### Priorität 3: Batch Mode (Optional)

**Datei**: Wo auch immer `CouchDBBatch` definiert ist

**Änderung**:
- `add()` Methode: Parameter `binary_file_path` hinzufügen
- `flush()` Methode: Attachments nach Document-Creation hinzufügen

## Testing

### Test 1: Single Upload

```python
# Test: Upload PDF
# Expected: CouchDB Document mit Attachment

doc = couchdb.get("abc123")
assert "_attachments" in doc
assert "original_file" in doc["_attachments"]
assert doc["_attachments"]["original_file"]["content_type"] == "application/pdf"

# Retrieve binary
binary = couchdb.get_binary_attachment("abc123")
assert binary is not None
assert len(binary) > 0
```

### Test 2: Batch Upload

```python
# Test: Upload 10 PDFs
# Expected: All 10 haben Attachments

for doc_id in doc_ids:
    doc = couchdb.get(doc_id)
    assert "_attachments" in doc
```

### Test 3: Binary Retrieval

```python
# Test: Download und vergleich
original_hash = hash_file("original.pdf")

# Upload
couchdb.create_document_with_binary({...}, "test", "original.pdf")

# Download
binary = couchdb.get_binary_attachment("test")
with open("downloaded.pdf", "wb") as f:
    f.write(binary)

downloaded_hash = hash_file("downloaded.pdf")
assert original_hash == downloaded_hash
```

## CouchDB API Referenz

### Put Attachment

```python
# CouchDB Python API:
db.put_attachment(
    doc,              # Document object (must have _rev)
    content,          # Binary data (bytes)
    filename,         # Attachment name (string)
    content_type      # MIME type (string)
)
```

### Get Attachment

```python
# CouchDB Python API:
attachment = db.get_attachment(doc, attachment_name)
binary_data = attachment.read()
```

### Document Structure

```json
{
  "_id": "abc123",
  "_rev": "1-xyz",
  "content": "Extracted text...",
  "classification": "GESETZ",
  "_attachments": {
    "original_file": {
      "content_type": "application/pdf",
      "revpos": 2,
      "digest": "md5-...",
      "length": 524288,
      "stub": true
    }
  }
}
```

## Vorteile

### 1. Vollständige Polyglot-Persistenz
✅ **4 Datenbanken** + **Original-Datei** in CouchDB  
✅ Kein Filesystem-Dependency mehr  
✅ Backup/Recovery über CouchDB

### 2. Themis-Ready
✅ CouchDB wird zum **Single Source of Truth** für Files  
✅ Themis kann direkt aus CouchDB lesen  
✅ Keine Filesystem-Zugriffe nötig

### 3. Skalierbarkeit
✅ CouchDB Replication funktioniert mit Attachments  
✅ Distributed Storage möglich  
✅ Cloud-Ready

## Migration

### Bestehende Dokumente

**Option 1: Re-Processing**
```python
# Alle Dateien neu verarbeiten
for file_path in existing_files:
    process_document_with_uds3(file_path, ...)
    # → Speichert Binary in CouchDB
```

**Option 2: Attachment-Only Update**
```python
# Nur Attachments hinzufügen (ohne Re-Processing)
for doc_id, file_path in existing_docs:
    backend.put_attachment(doc_id, file_path)
```

## Zusammenfassung

### Was du implementieren musst:

1. **UDS3 CouchDB Backend** erweitern:
   - `create_document_with_binary()` Methode
   - `get_binary_attachment()` Methode
   - `_detect_content_type()` Helper

2. **Ingestion Backend** anpassen:
   - Binary file path an CouchDB übergeben
   - Fallback für alte Backend-Versionen

3. **(Optional) Batch Mode** erweitern:
   - Binary paths in Buffer speichern
   - Nach flush Attachments hinzufügen

### Erwartetes Ergebnis:

```
Upload BImSchG.pdf → Ingestion → CouchDB:
  {
    "_id": "abc123",
    "content": "§ 1 Zweck des Gesetzes...",  ← Text
    "_attachments": {
      "original_file": {
        "content_type": "application/pdf",
        "length": 524288  ← Binary PDF
      }
    }
  }
```

### Fragen?

Wenn du Fragen hast oder die UDS3-Dateistruktur anders ist, gib mir Bescheid und ich passe die Anleitung an!
