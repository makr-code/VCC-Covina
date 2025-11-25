# VCC-Covina Phase 1 Deployment Guide
# Foundation Enhancement - On-Premise Kubernetes Deployment

**Phase:** 1 - Foundation Enhancement  
**Status:** Ready for Deployment  
**Target:** Q1 2026  

---

## 📋 Overview

Phase 1 implements the foundational infrastructure for VCC-Covina on-premise deployment, including:

1. **Kubernetes Deployment** - Container orchestration on bare-metal/private datacenter
2. **API Gateway (Kong)** - Centralized routing, rate limiting, authentication
3. **Observability Stack** - Prometheus, Grafana, Jaeger (all self-hosted)
4. **Service Discovery** - Kubernetes-native DNS and service mesh preparation

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    On-Premise Kubernetes Cluster                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    Kong API Gateway                      │  │
│  │  (Rate Limiting, Auth, Routing, Metrics)                │  │
│  └────────────┬────────────────────────────┬───────────────┘  │
│               │                            │                   │
│  ┌────────────▼────────────┐  ┌───────────▼────────────────┐ │
│  │   Main Backend (3x)     │  │  Ingestion Backend (2x)    │ │
│  │   Port: 45678           │  │  Port: 45679               │ │
│  │   - Query API           │  │  - Upload API              │ │
│  │   - DSGVO               │  │  - Processing              │ │
│  │   - Review Queue        │  │  - Worker Pool             │ │
│  └────────────┬────────────┘  └───────────┬────────────────┘ │
│               │                            │                   │
│  ┌────────────▼────────────────────────────▼───────────────┐  │
│  │                    Data Layer                            │  │
│  │  PostgreSQL │ ChromaDB │ Neo4j │ CouchDB │ Redis       │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │               Observability Stack                        │  │
│  │  Prometheus │ Grafana │ Jaeger │ ELK (optional)         │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Directory Structure

```
deploy/
├── kubernetes/
│   ├── base/                          # Base Kubernetes manifests
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── secrets.yaml
│   │   ├── storage.yaml
│   │   ├── main-backend-deployment.yaml
│   │   └── ingestion-backend-deployment.yaml
│   └── overlays/
│       ├── development/               # Dev environment overrides
│       ├── staging/                   # Staging environment overrides
│       └── production/                # Production environment overrides
│           ├── kustomization.yaml
│           ├── replicas-patch.yaml
│           └── resources-patch.yaml
├── api-gateway/
│   ├── kong-deployment.yaml           # Kong API Gateway
│   └── kong-config.yaml               # Kong declarative configuration
├── observability/
│   ├── prometheus/
│   │   └── prometheus.yaml            # Prometheus configuration & deployment
│   ├── grafana/
│   │   └── grafana.yaml               # Grafana dashboards & configuration
│   └── jaeger/
│       └── jaeger.yaml                # Distributed tracing
└── pgbouncer/                         # Connection pooling (existing)
    ├── pgbouncer.ini
    └── userlist.txt
```

---

## 🚀 Deployment Steps

### Prerequisites

1. **Kubernetes Cluster** (v1.25+) running on-premise
2. **kubectl** configured with cluster access
3. **kustomize** installed (or use `kubectl -k`)
4. **StorageClass** named `local-storage` configured
5. **Private Container Registry** with Covina images

### Step 1: Create Namespaces

```bash
kubectl apply -f deploy/kubernetes/base/namespace.yaml
```

### Step 2: Update Secrets

Edit `deploy/kubernetes/base/secrets.yaml` and replace placeholder values:

```yaml
# Replace these values:
POSTGRES_PASSWORD: "YOUR_SECURE_PASSWORD"
NEO4J_PASSWORD: "YOUR_SECURE_PASSWORD"
COUCHDB_PASSWORD: "YOUR_SECURE_PASSWORD"
REDIS_PASSWORD: "YOUR_SECURE_PASSWORD"
JWT_SECRET: "YOUR_32_CHAR_SECRET"
```

### Step 3: Deploy Observability Stack

```bash
# Deploy Prometheus
kubectl apply -f deploy/observability/prometheus/prometheus.yaml

# Deploy Grafana
kubectl apply -f deploy/observability/grafana/grafana.yaml

# Deploy Jaeger
kubectl apply -f deploy/observability/jaeger/jaeger.yaml
```

### Step 4: Deploy API Gateway

```bash
kubectl apply -f deploy/api-gateway/kong-config.yaml
kubectl apply -f deploy/api-gateway/kong-deployment.yaml
```

### Step 5: Deploy Application

```bash
# Development
kubectl apply -k deploy/kubernetes/overlays/development/

# OR Production
kubectl apply -k deploy/kubernetes/overlays/production/
```

### Step 6: Verify Deployment

```bash
# Check pods
kubectl get pods -n covina

# Check services
kubectl get svc -n covina

# Check ingress
kubectl get ingress -n covina

# View logs
kubectl logs -f deployment/covina-main-backend -n covina
```

---

## 🔧 Configuration

### Environment Variables

All configuration is managed via ConfigMaps and Secrets:

| Variable | Description | Default |
|----------|-------------|---------|
| `WORKERS_IO` | I/O worker count | 36 |
| `WORKERS_CPU` | CPU worker count | 36 |
| `LOG_LEVEL` | Logging verbosity | INFO |
| `POSTGRES_HOST` | PostgreSQL hostname | kubernetes service |
| `CHROMA_HOST` | ChromaDB hostname | kubernetes service |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry endpoint | jaeger-collector |

### Scaling

Adjust replicas in production overlay:

```yaml
# deploy/kubernetes/overlays/production/replicas-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: covina-main-backend
spec:
  replicas: 5  # Adjust as needed
```

### Resource Limits

```yaml
# deploy/kubernetes/overlays/production/resources-patch.yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "4000m"
```

---

## 📊 Monitoring

### Prometheus Metrics

Access Prometheus UI:
```bash
kubectl port-forward svc/prometheus 9090:9090 -n covina-observability
# Open http://localhost:9090
```

### Grafana Dashboards

Access Grafana:
```bash
kubectl port-forward svc/grafana 3000:3000 -n covina-observability
# Open http://localhost:3000
# Default: admin / (see grafana-secrets)
```

Pre-configured dashboards:
- **VCC-Covina Overview** - Request rates, latency, errors
- **Resource Usage** - CPU, memory, disk
- **Database Metrics** - PostgreSQL, Redis stats

### Jaeger Tracing

Access Jaeger UI:
```bash
kubectl port-forward svc/jaeger-query 16686:16686 -n covina-observability
# Open http://localhost:16686
```

---

## 🔒 Security

### On-Premise Security Measures

1. **No External Dependencies** - All services run on-premise
2. **Secrets Management** - Kubernetes Secrets (consider HashiCorp Vault for production)
3. **Network Policies** - Restrict pod-to-pod communication
4. **RBAC** - Role-based access control for Kubernetes
5. **TLS** - Enable TLS for all services in production

### Network Policies (Example)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: covina-network-policy
  namespace: covina
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: covina
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: covina
```

---

## 🧪 Testing

### Health Checks

```bash
# Main Backend
curl http://localhost:45678/health

# Ingestion Backend
curl http://localhost:45679/health

# Kong Gateway
curl http://localhost:8001/status
```

### Load Testing

```bash
# Install k6 (on-premise load testing)
# Run load test
k6 run scripts/load-test.js
```

---

## 🐛 Troubleshooting

### Common Issues

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n covina
kubectl logs <pod-name> -n covina
```

**Service unreachable:**
```bash
kubectl get endpoints -n covina
kubectl get svc -n covina
```

**Storage issues:**
```bash
kubectl get pvc -n covina
kubectl describe pvc <pvc-name> -n covina
```

### Log Aggregation

```bash
# Stream all logs
kubectl logs -f -l app.kubernetes.io/name=covina -n covina --all-containers

# Specific component
kubectl logs -f deployment/covina-main-backend -n covina
```

---

## 📅 Phase 1 Checklist

- [ ] Kubernetes cluster provisioned (on-premise)
- [ ] Storage class configured (`local-storage`)
- [ ] Container images pushed to private registry
- [ ] Secrets configured with secure values
- [ ] Observability stack deployed (Prometheus, Grafana, Jaeger)
- [ ] API Gateway deployed (Kong)
- [ ] Main Backend deployed (3+ replicas)
- [ ] Ingestion Backend deployed (2+ replicas)
- [ ] Health checks verified
- [ ] Grafana dashboards configured
- [ ] Alerts configured in Prometheus
- [ ] Documentation updated

---

## 📚 Related Documents

- [VCC-Covina Evolution Strategy](docs/VCC_COVINA_EVOLUTION_STRATEGY.md)
- [Implementation Roadmap 2026-2027](docs/IMPLEMENTATION_ROADMAP_2026_2027.md)
- [Best Practices & Architecture Principles](docs/BEST_PRACTICES_ARCHITECTURE_PRINCIPLES.md)

---

**Phase 1 Success Criteria:**
- ✅ Service Discovery latency: <10ms
- ✅ API Gateway throughput: >10K req/sec
- ✅ Metrics collection: 100% services instrumented
- ✅ Deployment time: <5 minutes

---

*Last Updated: November 2025*
*Version: Phase 1 - Foundation Enhancement*
