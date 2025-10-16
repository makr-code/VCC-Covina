# Enhanced Covina Backend - Deployment Guide

## 🚀 Übersicht

Das Enhanced Covina Backend ist ein enterprise-ready Multi-Database Distribution System für Dokumentenverarbeitung mit adaptiven Fallback-Strategien. Es erweitert das bestehende Covina Backend um intelligente Verteilung über spezialisierte Datenbanken.

## 📋 System Anforderungen

### Minimale Anforderungen
- **Python**: 3.11+
- **Memory**: 2GB RAM
- **Storage**: 10GB freier Speicherplatz
- **Network**: Zugang zu konfigurierten Datenbank-Hosts

### Empfohlene Anforderungen (Production)
- **Python**: 3.11+
- **Memory**: 8GB RAM
- **Storage**: 100GB freier Speicherplatz (je nach Datenvolumen)
- **CPU**: 4+ Cores
- **Network**: Gigabit LAN für Multi-DB Operationen

## 🗄️ Unterstützte Datenbanken

Das System unterstützt folgende Datenbank-Konfigurationen:

| Datenbank | Zweck | Standard Port | Erforderlich |
|-----------|--------|---------------|-------------|
| **PostgreSQL** | Master Registry & Relational Data | 5432 | Empfohlen |
| **CouchDB** | Document Storage & Metadata | 32931 | Empfohlen |
| **ChromaDB** | Vector Storage for Embeddings | 32768 | Optional |
| **Neo4j** | Graph Database for Relationships | 7687 | Optional |
| **SQLite** | Fallback & Development | - | Immer verfügbar |

### Fallback-Strategien
1. **full_polyglot**: Alle 4 Datenbanken (PostgreSQL + CouchDB + ChromaDB + Neo4j)
2. **postgresql_couchdb_chromadb**: 3 Datenbanken ohne Graph
3. **postgresql_couchdb_hybrid**: 2 Hauptdatenbanken
4. **postgresql_monolith**: Nur PostgreSQL
5. **sqlite_monolith**: Nur SQLite (Development/Fallback)

## 📦 Installation

### Methode 1: Direkte Installation

```bash
# 1. Repository klonen
git clone <repository-url>
cd Covina

# 2. Python Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate     # Windows

# 3. Abhängigkeiten installieren
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Konfiguration erstellen
python deploy_config.py generate development
python deploy_config.py generate staging
python deploy_config.py generate production

# 5. System validieren
python deploy_config.py check
```

### Methode 2: Docker Installation

```bash
# 1. Docker Compose starten
docker-compose up -d

# 2. Backend Logs überprüfen
docker-compose logs -f covina-backend

# 3. System Status prüfen
docker-compose ps
```

## ⚙️ Konfiguration

### Umgebungsvariablen

```bash
# Basis-Konfiguration
export UDS3_ENVIRONMENT=production  # development|staging|production

# PostgreSQL
export POSTGRESQL_HOST=localhost
export POSTGRESQL_PORT=5432
export POSTGRESQL_DATABASE=covina_backend
export POSTGRESQL_USER=covina_user
export POSTGRESQL_PASSWORD=secure_password

# CouchDB  
export COUCHDB_HOST=localhost
export COUCHDB_PORT=32931
export COUCHDB_USER=admin
export COUCHDB_PASSWORD=secure_password

# ChromaDB
export CHROMADB_HOST=localhost
export CHROMADB_PORT=32768

# Neo4j
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=secure_password
```

### Konfigurationsdateien erstellen

```bash
# Development Umgebung
python deploy_config.py generate development

# Staging Umgebung  
python deploy_config.py generate staging

# Production Umgebung
python deploy_config.py generate production
```

## 🚀 Deployment

### Development Deployment

```bash
# 1. Development Konfiguration validieren
python deploy_config.py validate-environment development

# 2. Backend starten (SQLite Fallback)
python enhanced_covina_backend.py

# 3. Mit Multi-DB (falls verfügbar)
python enhanced_covina_backend.py --multi-db
```

### Staging Deployment

```bash
# 1. Staging Umgebung setzen
export UDS3_ENVIRONMENT=staging

# 2. Datenbank Connectivity prüfen
python deploy_config.py validate-environment staging

# 3. Backend starten
python enhanced_covina_backend.py --multi-db --performance
```

### Production Deployment

```bash
# 1. Production Umgebung setzen
export UDS3_ENVIRONMENT=production

# 2. Alle Datenbanken validieren
python deploy_config.py validate-environment production

# 3. Production Backend starten
python enhanced_covina_backend.py --multi-db --performance

# 4. Systemd Service (optional)
sudo systemctl enable covina-backend
sudo systemctl start covina-backend
```

### Docker Production Deployment

```bash
# 1. Production Environment setzen
echo "UDS3_ENVIRONMENT=production" > .env

# 2. Production Services starten
docker-compose -f docker-compose.yml up -d

# 3. Health Checks überprüfen
docker-compose ps
docker-compose logs covina-backend

# 4. Performance Test
docker-compose exec covina-backend python enhanced_covina_backend.py --benchmark
```

## 🔧 Database Setup

### PostgreSQL Setup

```sql
-- 1. Database und User erstellen
CREATE DATABASE covina_backend;
CREATE USER covina_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE covina_backend TO covina_user;

-- 2. Migrationen ausführen
-- (Automatisch beim ersten Start oder manuell)
psql -h localhost -U covina_user -d covina_backend -f uds3/database/migrations/001_master_registry.sql
```

### CouchDB Setup

```bash
# 1. CouchDB Admin erstellen
curl -X PUT http://localhost:32931/_config/admins/admin -d '"secure_password"'

# 2. Datenbank erstellen
curl -X PUT http://admin:secure_password@localhost:32931/covina_backend
```

### ChromaDB Setup

```bash
# 1. ChromaDB Collection erstellen (automatisch beim ersten Zugriff)
# 2. Persistence Directory konfigurieren
mkdir -p data/chromadb
```

### Neo4j Setup

```bash
# 1. Neo4j initial password setzen
docker exec covina_neo4j cypher-shell -u neo4j -p neo4j "ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'secure_password'"

# 2. Plugins installieren (APOC, GDS)
# Bereits in docker-compose.yml konfiguriert
```

## 📊 Monitoring & Performance

### Performance Testing

```bash
# Quick Performance Test
python enhanced_covina_backend.py --quick-test

# Full Benchmark Suite
python enhanced_covina_backend.py --benchmark

# Continuous Performance Monitoring
python enhanced_covina_backend.py --performance
```

### Logs und Debugging

```bash
# Application Logs
tail -f enhanced_covina_backend.log

# Docker Logs
docker-compose logs -f covina-backend

# Database-specific Logs
docker-compose logs postgresql
docker-compose logs couchdb
docker-compose logs chromadb
docker-compose logs neo4j
```

### Health Checks

```bash
# System Health Check
python deploy_config.py check

# Environment Validation  
python deploy_config.py validate-environment production

# Database Connectivity
curl http://localhost:8080/health  # Über Docker
```

## 🔒 Sicherheit

### Produktionsumgebung

1. **Datenbank Passwörter**: Sichere, zufällige Passwörter verwenden
2. **SSL/TLS**: Verschlüsselte Verbindungen für alle Datenbanken
3. **Firewall**: Nur notwendige Ports öffnen
4. **User Permissions**: Minimale Datenbankberechtigungen
5. **Backup Strategy**: Regelmäßige, automatisierte Backups

### Docker Security

```bash
# Non-root Container User
USER covina

# Read-only Container Filesystem
docker run --read-only --tmpfs /tmp enhanced-covina-backend

# Secrets Management
docker secret create postgres_password /path/to/password/file
```

## 🚨 Troubleshooting

### Häufige Probleme

#### 1. Datenbank Verbindungsfehler

```bash
# Problem: PostgreSQL Connection refused
# Lösung: 
python deploy_config.py validate-environment production
# Überprüfung der Connectivity und Fallback-Strategie

# Problem: CouchDB Authentication failed
# Lösung:
curl http://admin:password@localhost:32931/_session
```

#### 2. Performance Probleme

```bash
# Problem: Langsame Multi-DB Distribution
# Lösung:
python enhanced_covina_backend.py --benchmark
# Analysiert Performance-Bottlenecks und Optimierungsmöglichkeiten

# Problem: Memory Leaks
# Lösung: 
# Monitoring mit Performance Suite aktivieren
python enhanced_covina_backend.py --performance
```

#### 3. Fallback-Strategien

```bash
# Problem: Nicht alle Datenbanken verfügbar
# Lösung: System nutzt automatisch Fallback-Strategien
# Überprüfung der aktuellen Strategie in den Logs

# Problem: SQLite Fallback in Production
# Lösung: Database Services überprüfen und neu starten
docker-compose restart postgresql couchdb
```

### Debug Mode

```bash
# Debug Logging aktivieren
export LOG_LEVEL=DEBUG
python enhanced_covia_backend.py --multi-db

# Enhanced Debug mit Performance Monitoring
python enhanced_covina_backend.py --multi-db --performance
```

## 📈 Skalierung

### Horizontale Skalierung

```bash
# Mehrere Backend Instanzen
docker-compose up --scale covina-backend=3

# Load Balancer Konfiguration
# Nginx ist bereits im docker-compose.yml konfiguriert
```

### Vertikale Skalierung

```yaml
# Docker Resource Limits anpassen
services:
  covina-backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## 🔄 Backup & Recovery

### Automatische Backups

```bash
# PostgreSQL Backup
pg_dump -h localhost -U covina_user covina_backend > backup_$(date +%Y%m%d).sql

# CouchDB Backup
curl http://admin:password@localhost:32931/covina_backend/_all_docs?include_docs=true > couchdb_backup.json

# ChromaDB Backup
cp -r data/chromadb backup_chromadb_$(date +%Y%m%d)

# Neo4j Backup
docker exec covina_neo4j neo4j-admin database dump neo4j --to=/backups/neo4j_$(date +%Y%m%d).dump
```

## 📞 Support

### Logs sammeln

```bash
# Alle relevanten Logs sammeln
python deploy_config.py check > system_info.txt
docker-compose logs > docker_logs.txt
tail -100 enhanced_covina_backend.log > app_logs.txt
```

### Performance Report

```bash
# Performance Benchmark erstellen
python enhanced_covina_backend.py --benchmark > performance_report.txt
```

---

**Entwickelt von**: Covina Development Team  
**Version**: 1.0.0  
**Datum**: 3. Oktober 2025  
**Lizenz**: Internal Use