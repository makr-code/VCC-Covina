# VCC-Covina Best Practices & Architecture Principles
# Stand der Technik Leitfaden

**Version:** 1.0.0  
**Erstellt:** 23. November 2025  
**Gültigkeit:** 2025-2027  
**Zielgruppe:** Entwickler, Architekten, DevOps

---

## 📋 Übersicht

Dieses Dokument definiert verbindliche Best Practices und architektonische Prinzipien für die VCC-Covina Entwicklung. Es dient als Leitfaden für technische Entscheidungen und Code-Qualität.

---

## 🏗️ Architektonische Prinzipien

### 1. Domain-Driven Design (DDD)

**Konzept:** Strukturierung der Software basierend auf Geschäftsdomänen

**Anwendung in Covina:**
```python
# Bounded Contexts
covina/
├── compliance/      # Compliance Domain
│   ├── models.py
│   ├── services.py
│   └── repositories.py
├── ingestion/       # Document Ingestion Domain
│   ├── models.py
│   ├── services.py
│   └── repositories.py
└── analytics/       # Analytics Domain
    ├── models.py
    ├── services.py
    └── repositories.py
```

**Best Practices:**
- Klare Domänengrenzen definieren
- Ubiquitous Language verwenden
- Aggregates für Konsistenz nutzen
- Domain Events für Kommunikation

### 2. SOLID Principles

**Single Responsibility:**
```python
# ❌ BAD: Class does too much
class DocumentProcessor:
    def upload(self): ...
    def classify(self): ...
    def store(self): ...
    def notify(self): ...

# ✅ GOOD: Separated responsibilities
class DocumentUploader:
    def upload(self): ...

class DocumentClassifier:
    def classify(self): ...

class DocumentRepository:
    def store(self): ...

class NotificationService:
    def notify(self): ...
```

**Open/Closed Principle:**
```python
# ✅ Open for extension, closed for modification
from abc import ABC, abstractmethod

class DocumentProcessor(ABC):
    @abstractmethod
    def process(self, document):
        pass

class PDFProcessor(DocumentProcessor):
    def process(self, document):
        # PDF-specific processing
        pass

class WordProcessor(DocumentProcessor):
    def process(self, document):
        # Word-specific processing
        pass
```

### 3. API-First Design

**Prinzip:** API-Contracts vor Implementation definieren

**OpenAPI 3.1 Spec:**
```yaml
openapi: 3.1.0
info:
  title: Covina API
  version: 5.0.0
  description: VCC-Covina Compliance Platform API

paths:
  /api/v1/documents:
    post:
      summary: Upload Document
      operationId: uploadDocument
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                metadata:
                  $ref: '#/components/schemas/DocumentMetadata'
      responses:
        '201':
          description: Document uploaded successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UploadResponse'
        '400':
          description: Invalid input
        '500':
          description: Internal server error
```

**Best Practices:**
- OpenAPI Spec generieren (aus Code oder manuell)
- Versionierung in URL (`/api/v1/`)
- Standardized Error Responses
- Pagination für Listen-Endpoints

### 4. Event-Driven Architecture

**Konzept:** Lose Kopplung durch Events

**Event Schema (Avro):**
```json
{
  "type": "record",
  "name": "DocumentIngested",
  "namespace": "com.vcc.covina.events",
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"},
    {"name": "document_id", "type": "string"},
    {"name": "user_id", "type": "string"},
    {"name": "status", "type": "enum", "symbols": ["processing", "completed", "failed"]},
    {"name": "metadata", "type": "map", "values": "string"}
  ]
}
```

**Event Publishing (Kafka):**
```python
from confluent_kafka import Producer

class EventPublisher:
    def __init__(self, bootstrap_servers):
        self.producer = Producer({'bootstrap.servers': bootstrap_servers})
    
    def publish(self, topic, event):
        self.producer.produce(
            topic,
            key=event.get('document_id'),
            value=json.dumps(event).encode('utf-8')
        )
        self.producer.flush()
```

---

## 🔒 Security Best Practices

### 1. Zero-Trust Principles

**Verify Explicitly:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def verify_token(token: str = Depends(oauth2_scheme)):
    """Verify JWT token for every request"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/v1/documents/{doc_id}")
async def get_document(doc_id: str, user_id: str = Depends(verify_token)):
    # Authorization check
    if not has_permission(user_id, doc_id, "read"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_document_by_id(doc_id)
```

### 2. Input Validation

**Pydantic Models:**
```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class DocumentMetadata(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    classification: str = Field(..., regex="^(public|internal|confidential|secret)$")
    author: Optional[str] = Field(None, max_length=100)
    tags: list[str] = Field(default_factory=list, max_items=10)
    
    @validator('tags', each_item=True)
    def validate_tag(cls, v):
        if len(v) > 50:
            raise ValueError('Tag too long')
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Invalid tag format')
        return v
```

### 3. Secret Management

**HashiCorp Vault Integration:**
```python
import hvac

class SecretManager:
    def __init__(self, vault_addr, vault_token):
        self.client = hvac.Client(url=vault_addr, token=vault_token)
    
    def get_secret(self, path):
        """Retrieve secret from Vault"""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']
    
    def get_db_credentials(self, database):
        """Get database credentials"""
        secret = self.get_secret(f'database/{database}')
        return {
            'host': secret['host'],
            'port': secret['port'],
            'username': secret['username'],
            'password': secret['password']
        }

# Usage
secrets = SecretManager(VAULT_ADDR, VAULT_TOKEN)
pg_creds = secrets.get_db_credentials('postgresql')
```

### 4. Encryption

**At Rest (Field-Level):**
```python
from cryptography.fernet import Fernet

class FieldEncryption:
    def __init__(self, key):
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt sensitive field"""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt sensitive field"""
        return self.cipher.decrypt(ciphertext.encode()).decode()

# Usage: Encrypt PII before storing
encryptor = FieldEncryption(ENCRYPTION_KEY)
encrypted_ssn = encryptor.encrypt(user.social_security_number)
```

---

## 📊 Observability Best Practices

### 1. Structured Logging

**JSON Logging:**
```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', None),
            'user_id': getattr(record, 'user_id', None),
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure logger
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Usage
logger.info("Document processed", extra={
    'correlation_id': request_id,
    'user_id': user_id,
    'document_id': doc_id
})
```

### 2. Distributed Tracing

**OpenTelemetry:**
```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracer
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

tracer = trace.get_tracer(__name__)

# Usage
@tracer.start_as_current_span("process_document")
async def process_document(document_id: str):
    with tracer.start_as_current_span("classify"):
        classification = await classify_document(document_id)
    
    with tracer.start_as_current_span("store"):
        await store_document(document_id, classification)
    
    return classification
```

### 3. Metrics Collection

**Prometheus Metrics:**
```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
document_uploads_total = Counter(
    'covina_document_uploads_total',
    'Total number of document uploads',
    ['status', 'classification']
)

document_processing_duration = Histogram(
    'covina_document_processing_duration_seconds',
    'Document processing duration in seconds',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

active_jobs = Gauge(
    'covina_active_jobs',
    'Number of active processing jobs'
)

# Usage
async def process_document(document):
    start_time = time.time()
    active_jobs.inc()
    
    try:
        classification = await classify(document)
        await store(document, classification)
        
        document_uploads_total.labels(
            status='success',
            classification=classification
        ).inc()
    except Exception as e:
        document_uploads_total.labels(
            status='error',
            classification='unknown'
        ).inc()
        raise
    finally:
        duration = time.time() - start_time
        document_processing_duration.observe(duration)
        active_jobs.dec()
```

---

## 🧪 Testing Best Practices

### 1. Test Pyramid

**Structure:**
```
        /\
       /  \  E2E Tests (10%)
      /    \
     /------\ Integration Tests (30%)
    /        \
   /----------\ Unit Tests (60%)
  /______________\
```

**Unit Test Example:**
```python
import pytest
from unittest.mock import Mock, patch

class TestDocumentClassifier:
    @pytest.fixture
    def classifier(self):
        return DocumentClassifier(model_path="test_model")
    
    def test_classify_legal_document(self, classifier):
        # Arrange
        document = {"text": "This is a legal contract..."}
        
        # Act
        result = classifier.classify(document)
        
        # Assert
        assert result.classification == "legal_contract"
        assert result.confidence > 0.9
    
    @patch('classifier.model.predict')
    def test_classify_with_mock(self, mock_predict, classifier):
        # Arrange
        mock_predict.return_value = "legal_contract"
        document = {"text": "Test"}
        
        # Act
        result = classifier.classify(document)
        
        # Assert
        mock_predict.assert_called_once()
        assert result.classification == "legal_contract"
```

**Integration Test Example:**
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestDocumentAPI:
    async def test_upload_document_e2e(self):
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            files = {'file': ('test.pdf', b'test content', 'application/pdf')}
            
            # Act
            response = await client.post("/api/v1/documents", files=files)
            
            # Assert
            assert response.status_code == 201
            assert 'document_id' in response.json()
```

### 2. Test Coverage

**Minimum Coverage:** 80%

**pytest Configuration:**
```ini
# pytest.ini
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=src
    --cov-report=html
    --cov-report=term
    --cov-fail-under=80
    --strict-markers
```

---

## 🚀 Performance Best Practices

### 1. Async/Await

**Prefer Async:**
```python
# ❌ Synchronous (blocking)
def get_document(doc_id):
    response = requests.get(f"/api/documents/{doc_id}")
    return response.json()

# ✅ Asynchronous (non-blocking)
async def get_document(doc_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/api/documents/{doc_id}")
        return response.json()
```

### 2. Database Optimization

**Connection Pooling:**
```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool, QueuePool

# Production: Use connection pool
engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections
    echo=False
)
```

**Batch Operations:**
```python
# ❌ Individual inserts
for document in documents:
    await db.execute(insert_query, document)

# ✅ Batch insert
await db.execute_many(insert_query, documents)
```

### 3. Caching Strategy

**Redis Cache:**
```python
import redis.asyncio as redis
import json

class CacheService:
    def __init__(self, redis_url):
        self.redis = redis.from_url(redis_url)
    
    async def get(self, key):
        """Get cached value"""
        value = await self.redis.get(key)
        return json.loads(value) if value else None
    
    async def set(self, key, value, ttl=3600):
        """Set cached value with TTL"""
        await self.redis.setex(
            key,
            ttl,
            json.dumps(value)
        )
    
    async def invalidate(self, pattern):
        """Invalidate cache by pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

# Usage with decorator
from functools import wraps

def cached(ttl=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            cached_value = await cache.get(cache_key)
            
            if cached_value:
                return cached_value
            
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

@cached(ttl=600)
async def get_document_metadata(doc_id):
    # Expensive operation
    return await db.query(...)
```

---

## 📦 Deployment Best Practices

### 1. Docker Multi-Stage Build

**Dockerfile:**
```dockerfile
# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Non-root user
RUN useradd -m appuser
USER appuser

ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Kubernetes Deployment

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: covina-main
  labels:
    app: covina-main
    version: v5.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: covina-main
  template:
    metadata:
      labels:
        app: covina-main
        version: v5.0.0
    spec:
      containers:
      - name: covina-main
        image: registry.vcc.com/covina-main:v5.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: covina-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## 🎯 Code Quality Standards

### 1. Linting & Formatting

**Tools:**
- **ruff:** Fast Python linter
- **black:** Code formatter
- **mypy:** Static type checker

**pyproject.toml:**
```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "N"]
ignore = []

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

### 2. Pre-commit Hooks

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
  
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
  
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

---

## 📚 Documentation Standards

### 1. Code Documentation

**Docstring Format (Google Style):**
```python
async def process_document(
    document_id: str,
    classification: str,
    metadata: dict[str, Any]
) -> DocumentResult:
    """Process a document with classification and metadata.
    
    Args:
        document_id: Unique identifier for the document
        classification: Document classification (e.g., 'legal_contract')
        metadata: Additional metadata as key-value pairs
    
    Returns:
        DocumentResult object containing processing results
    
    Raises:
        DocumentNotFoundException: If document_id not found
        ClassificationError: If classification fails
        DatabaseError: If database operation fails
    
    Example:
        >>> result = await process_document(
        ...     "doc-123",
        ...     "legal_contract",
        ...     {"author": "John Doe"}
        ... )
        >>> print(result.status)
        'completed'
    """
    # Implementation
    pass
```

### 2. API Documentation

**Auto-generate from OpenAPI:**
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

### 3. Architecture Decision Records (ADRs)

**Template:**
```markdown
# ADR-001: Use Kubernetes for Container Orchestration

## Status
Accepted

## Context
Need scalable, reliable container orchestration for production deployment.

## Decision
Use Kubernetes as primary container orchestration platform.

## Consequences
**Positive:**
- Industry standard with large ecosystem
- Auto-scaling capabilities
- Service discovery built-in

**Negative:**
- Steep learning curve
- Operational complexity
- Higher infrastructure costs

## Alternatives Considered
- Docker Swarm: Simpler but less features
- Nomad: Good but smaller ecosystem
```

---

## 🎉 Zusammenfassung

Dieses Dokument definiert verbindliche Standards für:
- ✅ Architektonische Prinzipien (DDD, SOLID, API-First)
- ✅ Security Best Practices (Zero-Trust, Encryption, Secrets)
- ✅ Observability (Logging, Tracing, Metrics)
- ✅ Testing (Pyramid, Coverage, Fixtures)
- ✅ Performance (Async, Pooling, Caching)
- ✅ Deployment (Docker, Kubernetes, CI/CD)
- ✅ Code Quality (Linting, Formatting, Type Checking)
- ✅ Documentation (Docstrings, APIs, ADRs)

**Compliance:** Alle neuen Features müssen diese Standards erfüllen.

---

*Letzte Aktualisierung: 23. November 2025*  
*Review Cycle: Quarterly*
