# VCC-Covina AI/ML Deployment Guide

Phase 3: AI/ML Modernization - Self-hosted LLM, RAG, and MLOps Infrastructure

**Version:** 1.0.0  
**Last Updated:** November 2025  
**Status:** Infrastructure Ready

---

## 📋 Overview

This guide covers the deployment of VCC-Covina's AI/ML infrastructure:

| Component | Technology | Purpose | Self-Hosted |
|-----------|------------|---------|-------------|
| LLM Inference | vLLM | Text generation | ✅ Yes |
| Embeddings | TEI | Vector generation | ✅ Yes |
| Reranking | TEI | Result reranking | ✅ Yes |
| RAG | Custom | Document Q&A | ✅ Yes |
| GraphRAG | Custom | Knowledge graph Q&A | ✅ Yes |
| Model Registry | MLflow | Model tracking | ✅ Yes |
| Pipelines | Argo Workflows | ML pipelines | ✅ Yes |
| Artifact Storage | MinIO | S3-compatible | ✅ Yes |

**❌ No external vendor dependencies or cloud APIs required.**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Covina AI/ML Layer                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    LLM Inference (vLLM)                   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐               │  │
│  │  │ Llama 3.1 8B    │  │ Mistral 7B      │               │  │
│  │  │ (Primary)       │  │ (Multilingual)  │               │  │
│  │  └─────────────────┘  └─────────────────┘               │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Embedding & Reranking (TEI)                 │  │
│  │  ┌─────────────────┐  ┌─────────────────┐               │  │
│  │  │ E5-Large        │  │ BGE Reranker    │               │  │
│  │  │ (Embeddings)    │  │ (Cross-Encoder) │               │  │
│  │  └─────────────────┘  └─────────────────┘               │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────┐  ┌───────────────────────────────┐ │
│  │   RAG Pipeline        │  │   GraphRAG Pipeline           │ │
│  │   • Semantic Search   │  │   • Entity Extraction        │ │
│  │   • Hybrid Retrieval  │  │   • Graph Traversal          │ │
│  │   • Context Synthesis │  │   • Community Search         │ │
│  └───────────────────────┘  └───────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    MLOps Platform                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │ MLflow      │  │ MinIO       │  │ Argo Workflows  │  │  │
│  │  │ (Tracking)  │  │ (Artifacts) │  │ (Pipelines)     │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Deployment

### Prerequisites

1. **Kubernetes Cluster** with GPU nodes (NVIDIA)
2. **GPU Operator** installed for NVIDIA support
3. **Storage Class** for PersistentVolumeClaims
4. **Namespace** `covina-llm` and `covina-mlops`

### Step 1: Deploy LLM Infrastructure

```bash
# Create namespace
kubectl create namespace covina-llm

# Deploy vLLM (Llama 3.1 + Mistral)
kubectl apply -f deploy/llm/vllm-deployment.yaml

# Deploy Embedding Service
kubectl apply -f deploy/llm/embedding-service.yaml

# Verify deployments
kubectl get pods -n covina-llm
```

### Step 2: Deploy MLOps Platform

```bash
# Create namespace
kubectl create namespace covina-mlops

# Deploy MLflow
kubectl apply -f deploy/mlops/mlflow.yaml

# Deploy Kubeflow Pipelines (Argo Workflows)
kubectl apply -f deploy/mlops/kubeflow-pipelines.yaml

# Verify deployments
kubectl get pods -n covina-mlops
```

### Step 3: Configure Secrets

```bash
# Update secrets with production values
kubectl edit secret vllm-secrets -n covina-llm
kubectl edit secret mlflow-secrets -n covina-mlops
kubectl edit secret minio-secrets -n covina-mlops
```

### Step 4: Verify Services

```bash
# Check LLM health
kubectl port-forward svc/vllm-llama-service 8000:8000 -n covina-llm
curl http://localhost:8000/health

# Check Embedding service
kubectl port-forward svc/embedding-service 8080:8080 -n covina-llm
curl http://localhost:8080/health

# Check MLflow
kubectl port-forward svc/mlflow-server 5000:5000 -n covina-mlops
curl http://localhost:5000/health
```

---

## 💻 Python Module Usage

### LLM Service

```python
from ai_ml.llm import LLMService, LLMConfig

# Configure
config = LLMConfig(
    model_endpoint="http://vllm-llama-service.covina-llm:8000",
    model_name="meta-llama/Meta-Llama-3.1-8B-Instruct"
)

# Generate text
async with LLMService(config) as llm:
    response = await llm.generate("Erkläre DSGVO-Anforderungen")
    print(response.content)
    
    # Streaming
    async for chunk in llm.generate_stream("Was ist Compliance?"):
        print(chunk, end="")
```

### RAG Pipeline

```python
from ai_ml.rag import RAGPipeline, RAGConfig

# Configure
config = RAGConfig(
    llm_endpoint="http://vllm-llama-service.covina-llm:8000",
    embedding_endpoint="http://embedding-service.covina-llm:8080",
    chromadb_host="chromadb-service.covina"
)

# Query with RAG
async with RAGPipeline(config) as rag:
    response = await rag.query(
        "Was sind die Aufbewahrungsfristen?",
        filters={"category": "compliance"}
    )
    print(f"Answer: {response.answer}")
    print(f"Sources: {len(response.sources)}")
```

### GraphRAG Pipeline

```python
from ai_ml.graphrag import GraphRAGPipeline, GraphRAGConfig

# Configure
config = GraphRAGConfig(
    neo4j_uri="bolt://neo4j-service.covina:7687",
    llm_endpoint="http://vllm-llama-service.covina-llm:8000"
)

# Query with GraphRAG
async with GraphRAGPipeline(config) as graphrag:
    response = await graphrag.query(
        "Welche Unternehmen sind mit Vertrag X verbunden?"
    )
    print(f"Answer: {response.answer}")
    print(f"Entities: {len(response.graph_context.entities)}")
```

### Embedding Service

```python
from ai_ml.embeddings import EmbeddingService, EmbeddingConfig

# Configure
config = EmbeddingConfig(
    endpoint="http://embedding-service.covina-llm:8080"
)

# Generate embeddings
async with EmbeddingService(config) as embeddings:
    result = await embeddings.embed(["Document 1", "Document 2"])
    print(f"Dimensions: {result.dimensions}")
    
    # Similarity
    scores = await embeddings.similarity(
        "Query text",
        ["Doc 1", "Doc 2", "Doc 3"]
    )
    print(f"Similarity scores: {scores}")
```

---

## 🔧 Configuration

### LLM Models (Self-Hosted)

| Model | Size | GPU Memory | Use Case |
|-------|------|------------|----------|
| Llama 3.1 8B | 8B | 16GB | General |
| Llama 3.1 70B | 70B | 140GB | Complex |
| Mistral 7B | 7B | 14GB | Multilingual |
| DeepSeek Coder | 6.7B | 13GB | Code |

### Embedding Models (Self-Hosted)

| Model | Dimensions | Languages | Use Case |
|-------|------------|-----------|----------|
| E5-Large Multilingual | 1024 | 100+ | General |
| Legal-BERT | 768 | EN | Legal docs |
| German BERT | 768 | DE/EN | German |
| BGE-M3 | 1024 | 100+ | Multilingual |

### Resource Requirements

| Component | CPU | Memory | GPU |
|-----------|-----|--------|-----|
| vLLM (8B) | 8 | 32Gi | 1x A100 |
| vLLM (70B) | 16 | 256Gi | 4x A100 |
| TEI CPU | 2 | 4Gi | - |
| TEI GPU | 4 | 16Gi | 1x A100 |
| MLflow | 1 | 2Gi | - |
| Argo | 0.5 | 512Mi | - |

---

## 📊 Monitoring

### Prometheus Metrics

All services export Prometheus metrics:

```yaml
# vLLM metrics
vllm_requests_running
vllm_requests_completed
vllm_time_to_first_token_seconds
vllm_time_per_output_token_seconds

# TEI metrics
tei_request_count
tei_request_latency_seconds
tei_batch_size

# MLflow metrics
mlflow_runs_total
mlflow_artifacts_size_bytes
```

### Grafana Dashboards

Import dashboards from `deploy/observability/grafana/`:

1. **AI/ML Overview** - Request rates, latencies, GPU utilization
2. **LLM Performance** - Token throughput, queue depth
3. **MLOps Pipeline** - Training runs, model versions

---

## 🔒 Security

### Network Policies

All AI/ML services are isolated with NetworkPolicies:

- Only Covina namespace can access LLM/Embedding services
- MLOps namespace can access model registry
- No external internet access (models must be pre-downloaded)

### Secrets Management

```bash
# Rotate LLM API key
kubectl create secret generic vllm-secrets \
  --from-literal=API_KEY=$(openssl rand -hex 32) \
  -n covina-llm --dry-run=client -o yaml | kubectl apply -f -

# Rotate MLflow password
kubectl create secret generic mlflow-secrets \
  --from-literal=MLFLOW_TRACKING_PASSWORD=$(openssl rand -hex 16) \
  -n covina-mlops --dry-run=client -o yaml | kubectl apply -f -
```

---

## 🔄 Model Updates

### Downloading Models (Air-Gapped)

For on-premise deployment without internet:

```bash
# On machine with internet access
huggingface-cli download meta-llama/Meta-Llama-3.1-8B-Instruct --local-dir ./llama-3.1-8b

# Transfer to cluster
kubectl cp ./llama-3.1-8b covina-llm/vllm-llama-0:/models/

# Restart deployment
kubectl rollout restart deployment vllm-llama -n covina-llm
```

### A/B Testing Models

```python
# Configure A/B test in Argo
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: llm-ab-test
spec:
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: {duration: 1h}
        - setWeight: 50
        - pause: {duration: 1h}
        - setWeight: 100
```

---

## 📈 Performance Tuning

### vLLM Optimization

```yaml
# Increase batch size
MAX_NUM_BATCHED_TOKENS: "16384"
MAX_NUM_SEQS: "512"

# Enable continuous batching
ENABLE_CHUNKED_PREFILL: "true"

# Use tensor parallelism for multi-GPU
TENSOR_PARALLEL_SIZE: "2"
```

### Embedding Optimization

```yaml
# Increase concurrency
MAX_CONCURRENT_REQUESTS: "1024"
MAX_BATCH_TOKENS: "32768"
```

---

## 🆘 Troubleshooting

### LLM Not Starting

```bash
# Check logs
kubectl logs -f deployment/vllm-llama -n covina-llm

# Common issues:
# - GPU not available: Check nvidia-smi
# - OOM: Reduce GPU_MEMORY_UTILIZATION
# - Model not found: Check HF_HOME mount
```

### Embedding Service Slow

```bash
# Check metrics
curl http://embedding-service:8080/metrics

# Optimize:
# - Enable GPU version
# - Increase batch size
# - Check network latency
```

### MLflow Connection Error

```bash
# Check PostgreSQL
kubectl logs deployment/mlflow-postgres -n covina-mlops

# Check service DNS
kubectl run debug --image=busybox --rm -it -- nslookup mlflow-server.covina-mlops
```

---

## 📚 References

- [vLLM Documentation](https://docs.vllm.ai/)
- [Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference)
- [MLflow Documentation](https://mlflow.org/docs/latest/)
- [Argo Workflows](https://argoproj.github.io/argo-workflows/)

---

**Status:** ✅ Phase 3 Infrastructure Ready for Deployment
