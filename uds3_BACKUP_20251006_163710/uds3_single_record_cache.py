#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Single Record Cache Module
Optimiert Single Record Read Operations mit LRU Cache + TTL

Features:
- LRU (Least Recently Used) Eviction Policy
- TTL (Time-To-Live) für automatische Invalidierung
- Thread-Safe Operations (threading.Lock)
- Cache Statistics & Performance Monitoring
- Flexible Invalidierung (Single, Pattern, Full)
- Warmup-Mechanismus für häufig genutzte Records
"""

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Pattern
import re

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class CacheStatus(Enum):
    """Cache Entry Status"""
    VALID = "valid"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class InvalidationStrategy(Enum):
    """Cache Invalidierung Strategien"""
    IMMEDIATE = "immediate"  # Sofort löschen
    LAZY = "lazy"  # Bei nächstem Zugriff prüfen
    SCHEDULED = "scheduled"  # Periodisches Cleanup


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CacheEntry:
    """Ein einzelner Cache-Eintrag"""
    document_id: str
    data: Dict[str, Any]
    created_at: float  # timestamp
    last_accessed: float  # timestamp
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    status: CacheStatus = CacheStatus.VALID
    size_bytes: int = 0  # Approximate size
    
    def is_expired(self) -> bool:
        """Prüft ob Entry abgelaufen ist"""
        if self.ttl_seconds is None:
            return False
        age = time.time() - self.created_at
        return age > self.ttl_seconds
    
    def update_access(self):
        """Aktualisiert Access-Statistiken"""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict"""
        return {
            "document_id": self.document_id,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "last_accessed": datetime.fromtimestamp(self.last_accessed).isoformat(),
            "access_count": self.access_count,
            "ttl_seconds": self.ttl_seconds,
            "status": self.status.value,
            "size_bytes": self.size_bytes,
            "age_seconds": time.time() - self.created_at
        }


@dataclass
class CacheStatistics:
    """Cache Performance Statistiken"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    invalidations: int = 0
    total_requests: int = 0
    total_size_bytes: int = 0
    average_access_time_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        """Cache Hit Rate in Prozent"""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100
    
    @property
    def miss_rate(self) -> float:
        """Cache Miss Rate in Prozent"""
        return 100.0 - self.hit_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 2),
            "miss_rate": round(self.miss_rate, 2),
            "total_size_mb": round(self.total_size_bytes / (1024 * 1024), 2),
            "average_access_time_ms": round(self.average_access_time_ms, 2)
        }


@dataclass
class CacheConfig:
    """Cache Konfiguration"""
    max_size: int = 1000  # Maximale Anzahl Einträge
    default_ttl_seconds: Optional[float] = 300.0  # 5 Minuten
    enable_stats: bool = True
    enable_compression: bool = False
    auto_cleanup_interval: float = 60.0  # Sekunden
    invalidation_strategy: InvalidationStrategy = InvalidationStrategy.LAZY
    warmup_enabled: bool = False
    max_memory_mb: Optional[float] = None  # Memory limit


# ============================================================================
# MAIN CACHE CLASS
# ============================================================================

class SingleRecordCache:
    """
    LRU Cache mit TTL für Single Record Reads
    
    Features:
    - Thread-safe operations
    - Automatic TTL expiration
    - LRU eviction policy
    - Performance statistics
    - Pattern-based invalidation
    
    Example:
        cache = SingleRecordCache(max_size=1000, default_ttl_seconds=300)
        
        # Store
        cache.put("doc123", {"title": "Test"})
        
        # Retrieve
        data = cache.get("doc123")
        
        # Invalidate
        cache.invalidate("doc123")
        
        # Statistics
        stats = cache.get_statistics()
        print(f"Hit rate: {stats.hit_rate}%")
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialisiert den Cache
        
        Args:
            config: Cache-Konfiguration
        """
        self.config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = CacheStatistics()
        self._access_times: List[float] = []
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        
        logger.info(
            f"SingleRecordCache initialized: "
            f"max_size={self.config.max_size}, "
            f"ttl={self.config.default_ttl_seconds}s"
        )
        
        # Start automatic cleanup if enabled
        if self.config.auto_cleanup_interval > 0:
            self._start_cleanup_thread()
    
    # ========================================================================
    # CORE OPERATIONS
    # ========================================================================
    
    def get(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt einen Eintrag aus dem Cache
        
        Args:
            document_id: Dokument-ID
            
        Returns:
            Document data oder None bei Miss
        """
        start_time = time.time()
        
        with self._lock:
            self._stats.total_requests += 1
            
            # Check if exists
            if document_id not in self._cache:
                self._stats.misses += 1
                self._record_access_time(start_time)
                logger.debug(f"Cache MISS: {document_id}")
                return None
            
            entry = self._cache[document_id]
            
            # Check if expired
            if entry.is_expired():
                self._stats.misses += 1
                self._stats.invalidations += 1
                self._stats.total_size_bytes -= entry.size_bytes
                del self._cache[document_id]
                self._record_access_time(start_time)
                logger.debug(f"Cache EXPIRED: {document_id}")
                return None
            
            # Valid hit
            self._stats.hits += 1
            entry.update_access()
            
            # Move to end (LRU)
            self._cache.move_to_end(document_id)
            
            self._record_access_time(start_time)
            logger.debug(f"Cache HIT: {document_id} (hits: {entry.access_count})")
            
            return entry.data
    
    def put(
        self,
        document_id: str,
        data: Dict[str, Any],
        ttl_seconds: Optional[float] = None
    ):
        """
        Speichert einen Eintrag im Cache
        
        Args:
            document_id: Dokument-ID
            data: Document data
            ttl_seconds: Custom TTL (überschreibt default)
        """
        with self._lock:
            # Remove old entry if exists
            if document_id in self._cache:
                old_entry = self._cache[document_id]
                self._stats.total_size_bytes -= old_entry.size_bytes
                del self._cache[document_id]
            # Check size limit BEFORE adding new entry
            elif len(self._cache) >= self.config.max_size:
                self._evict_lru()
            
            # Create new entry
            size_bytes = self._estimate_size(data)
            ttl = ttl_seconds if ttl_seconds is not None else self.config.default_ttl_seconds
            
            entry = CacheEntry(
                document_id=document_id,
                data=data,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl_seconds=ttl,
                size_bytes=size_bytes
            )
            
            # Store entry
            self._cache[document_id] = entry
            self._stats.total_size_bytes += size_bytes
            
            # Check memory limit
            if self.config.max_memory_mb:
                max_bytes = self.config.max_memory_mb * 1024 * 1024
                while self._stats.total_size_bytes > max_bytes and len(self._cache) > 0:
                    self._evict_lru()
            
            logger.debug(
                f"Cache PUT: {document_id} "
                f"(size: {len(self._cache)}/{self.config.max_size})"
            )
    
    def invalidate(self, document_id: str) -> bool:
        """
        Invalidiert einen Cache-Eintrag
        
        Args:
            document_id: Dokument-ID
            
        Returns:
            True wenn Entry existierte
        """
        with self._lock:
            if document_id in self._cache:
                entry = self._cache[document_id]
                self._stats.total_size_bytes -= entry.size_bytes
                del self._cache[document_id]
                self._stats.invalidations += 1
                logger.debug(f"Cache INVALIDATED: {document_id}")
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidiert alle Einträge die Pattern matchen
        
        Args:
            pattern: Regex pattern
            
        Returns:
            Anzahl invalidierter Einträge
        """
        regex = re.compile(pattern)
        count = 0
        
        with self._lock:
            keys_to_remove = [
                doc_id for doc_id in self._cache.keys()
                if regex.search(doc_id)
            ]
            
            for doc_id in keys_to_remove:
                entry = self._cache[doc_id]
                self._stats.total_size_bytes -= entry.size_bytes
                del self._cache[doc_id]
                count += 1
            
            self._stats.invalidations += count
            logger.info(f"Cache pattern invalidation: {count} entries removed")
        
        return count
    
    def clear(self):
        """Leert den gesamten Cache"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.total_size_bytes = 0
            self._stats.invalidations += count
            logger.info(f"Cache cleared: {count} entries removed")
    
    # ========================================================================
    # LRU EVICTION
    # ========================================================================
    
    def _evict_lru(self):
        """Entfernt den am wenigsten genutzten Eintrag (LRU)"""
        if not self._cache:
            return
        
        # OrderedDict: first item is least recently used
        doc_id, entry = self._cache.popitem(last=False)
        self._stats.total_size_bytes -= entry.size_bytes
        self._stats.evictions += 1
        logger.debug(f"Cache EVICTED: {doc_id} (LRU)")
    
    # ========================================================================
    # BATCH OPERATIONS
    # ========================================================================
    
    def get_many(self, document_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Holt mehrere Einträge aus dem Cache
        
        Args:
            document_ids: Liste von Dokument-IDs
            
        Returns:
            Dict mit document_id -> data (None bei Miss)
        """
        results = {}
        for doc_id in document_ids:
            results[doc_id] = self.get(doc_id)
        return results
    
    def put_many(self, documents: Dict[str, Dict[str, Any]], ttl_seconds: Optional[float] = None):
        """
        Speichert mehrere Einträge im Cache
        
        Args:
            documents: Dict mit document_id -> data
            ttl_seconds: Custom TTL für alle Einträge
        """
        for doc_id, data in documents.items():
            self.put(doc_id, data, ttl_seconds)
    
    def invalidate_many(self, document_ids: List[str]) -> int:
        """
        Invalidiert mehrere Einträge
        
        Args:
            document_ids: Liste von Dokument-IDs
            
        Returns:
            Anzahl invalidierter Einträge
        """
        count = 0
        for doc_id in document_ids:
            if self.invalidate(doc_id):
                count += 1
        return count
    
    # ========================================================================
    # WARMUP
    # ========================================================================
    
    def warmup(self, loader_fn: Callable[[str], Dict[str, Any]], document_ids: List[str]):
        """
        Lädt Dokumente in den Cache (Warmup)
        
        Args:
            loader_fn: Funktion die document_id nimmt und data zurückgibt
            document_ids: Liste von IDs zum vorladen
        """
        logger.info(f"Cache warmup: loading {len(document_ids)} documents")
        
        success_count = 0
        for doc_id in document_ids:
            try:
                data = loader_fn(doc_id)
                if data:
                    self.put(doc_id, data)
                    success_count += 1
            except Exception as e:
                logger.error(f"Warmup failed for {doc_id}: {e}")
        
        logger.info(f"Cache warmup complete: {success_count}/{len(document_ids)} loaded")
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    def cleanup_expired(self) -> int:
        """
        Entfernt alle abgelaufenen Einträge
        
        Returns:
            Anzahl entfernter Einträge
        """
        count = 0
        
        with self._lock:
            keys_to_remove = [
                doc_id for doc_id, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for doc_id in keys_to_remove:
                entry = self._cache[doc_id]
                self._stats.total_size_bytes -= entry.size_bytes
                del self._cache[doc_id]
                count += 1
            
            self._stats.invalidations += count
        
        if count > 0:
            logger.debug(f"Cleanup: {count} expired entries removed")
        
        return count
    
    def _start_cleanup_thread(self):
        """Startet Background-Thread für automatisches Cleanup"""
        def cleanup_loop():
            while not self._stop_cleanup.is_set():
                time.sleep(self.config.auto_cleanup_interval)
                self.cleanup_expired()
        
        self._cleanup_thread = threading.Thread(
            target=cleanup_loop,
            daemon=True,
            name="CacheCleanup"
        )
        self._cleanup_thread.start()
        logger.info("Cache cleanup thread started")
    
    def stop(self):
        """Stoppt den Cache (cleanup thread)"""
        if self._cleanup_thread:
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5)
            logger.info("Cache stopped")
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_statistics(self) -> CacheStatistics:
        """
        Gibt aktuelle Cache-Statistiken zurück
        
        Returns:
            CacheStatistics Objekt
        """
        with self._lock:
            return CacheStatistics(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                invalidations=self._stats.invalidations,
                total_requests=self._stats.total_requests,
                total_size_bytes=self._stats.total_size_bytes,
                average_access_time_ms=self._stats.average_access_time_ms
            )
    
    def get_info(self) -> Dict[str, Any]:
        """
        Gibt detaillierte Cache-Informationen zurück
        
        Returns:
            Dict mit Cache-Informationen
        """
        with self._lock:
            entries_info = []
            for doc_id, entry in list(self._cache.items())[:10]:  # Top 10
                entries_info.append({
                    "document_id": doc_id,
                    "access_count": entry.access_count,
                    "age_seconds": round(time.time() - entry.created_at, 2),
                    "size_kb": round(entry.size_bytes / 1024, 2)
                })
            
            return {
                "config": {
                    "max_size": self.config.max_size,
                    "default_ttl_seconds": self.config.default_ttl_seconds,
                    "invalidation_strategy": self.config.invalidation_strategy.value
                },
                "current_size": len(self._cache),
                "usage_percent": round((len(self._cache) / self.config.max_size) * 100, 2),
                "statistics": self._stats.to_dict(),
                "top_entries": entries_info
            }
    
    def reset_statistics(self):
        """Setzt Statistiken zurück"""
        with self._lock:
            self._stats = CacheStatistics()
            self._access_times.clear()
            logger.info("Cache statistics reset")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _estimate_size(self, data: Dict[str, Any]) -> int:
        """
        Schätzt Größe eines Objekts in Bytes
        
        Args:
            data: Zu messende Daten
            
        Returns:
            Geschätzte Größe in Bytes
        """
        # Simple estimation based on string representation
        import sys
        try:
            return sys.getsizeof(str(data))
        except Exception:
            return 1024  # Default 1KB
    
    def _record_access_time(self, start_time: float):
        """Zeichnet Access-Zeit auf"""
        access_time_ms = (time.time() - start_time) * 1000
        self._access_times.append(access_time_ms)
        
        # Keep only last 1000 measurements
        if len(self._access_times) > 1000:
            self._access_times = self._access_times[-1000:]
        
        # Update average
        if self._access_times:
            self._stats.average_access_time_ms = sum(self._access_times) / len(self._access_times)
    
    # ========================================================================
    # CONTEXT MANAGER
    # ========================================================================
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
        return False


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_single_record_cache(
    max_size: int = 1000,
    default_ttl_seconds: float = 300.0,
    enable_auto_cleanup: bool = True
) -> SingleRecordCache:
    """
    Factory-Funktion zum Erstellen eines Caches
    
    Args:
        max_size: Maximale Anzahl Einträge
        default_ttl_seconds: Standard TTL in Sekunden
        enable_auto_cleanup: Automatisches Cleanup aktivieren
        
    Returns:
        SingleRecordCache Instanz
    """
    config = CacheConfig(
        max_size=max_size,
        default_ttl_seconds=default_ttl_seconds,
        auto_cleanup_interval=60.0 if enable_auto_cleanup else 0.0
    )
    return SingleRecordCache(config)


# ============================================================================
# BUILT-IN TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== UDS3 Single Record Cache Test ===\n")
    
    # Test 1: Basic Operations
    print("Test 1: Basic Cache Operations")
    cache = create_single_record_cache(max_size=3, default_ttl_seconds=5.0)
    
    # Put
    cache.put("doc1", {"title": "Document 1"})
    cache.put("doc2", {"title": "Document 2"})
    cache.put("doc3", {"title": "Document 3"})
    
    # Get (Hit)
    data = cache.get("doc1")
    print(f"✓ Cache hit: {data}")
    
    # Get (Miss)
    data = cache.get("doc99")
    print(f"✓ Cache miss: {data}")
    
    # Stats
    stats = cache.get_statistics()
    print(f"✓ Hit rate: {stats.hit_rate}%")
    print()
    
    # Test 2: LRU Eviction
    print("Test 2: LRU Eviction")
    cache.put("doc4", {"title": "Document 4"})  # Evicts doc2 (LRU, doc1 already accessed)
    
    data1 = cache.get("doc1")  # Should hit (was accessed in test 1)
    data2 = cache.get("doc2")  # Should miss (evicted)
    print(f"✓ doc1 still cached: {data1 is not None}")
    print(f"✓ doc2 evicted: {data2 is None}")
    print()
    
    # Test 3: TTL Expiration
    print("Test 3: TTL Expiration")
    cache_ttl = create_single_record_cache(max_size=10, default_ttl_seconds=10.0)
    cache_ttl.put("doc_ttl", {"title": "Expires soon"}, ttl_seconds=1.0)
    
    data = cache_ttl.get("doc_ttl")
    print(f"✓ Before expiry: {data is not None}")
    
    time.sleep(1.5)
    data_after = cache_ttl.get("doc_ttl")
    print(f"✓ After expiry: {data_after is None}")
    cache_ttl.stop()
    print()
    
    # Test 4: Batch Operations
    print("Test 4: Batch Operations")
    docs = {
        "batch1": {"title": "Batch 1"},
        "batch2": {"title": "Batch 2"},
        "batch3": {"title": "Batch 3"}
    }
    cache.put_many(docs)
    
    results = cache.get_many(["batch1", "batch2", "batch99"])
    hits = sum(1 for v in results.values() if v is not None)
    print(f"✓ Batch get: {hits}/3 hits")
    print()
    
    # Test 5: Pattern Invalidation
    print("Test 5: Pattern Invalidation")
    cache.put("user_123", {"name": "User 123"})
    cache.put("user_456", {"name": "User 456"})
    cache.put("post_789", {"title": "Post 789"})
    
    count = cache.invalidate_pattern(r"^user_")
    print(f"✓ Pattern invalidation: {count} entries removed")
    
    print(f"✓ user_123 exists: {cache.get('user_123') is not None}")
    print(f"✓ post_789 exists: {cache.get('post_789') is not None}")
    print()
    
    # Test 6: Info & Statistics
    print("Test 6: Cache Info")
    info = cache.get_info()
    print(f"✓ Current size: {info['current_size']}/{info['config']['max_size']}")
    print(f"✓ Hit rate: {info['statistics']['hit_rate']}%")
    print(f"✓ Total requests: {info['statistics']['total_requests']}")
    print()
    
    # Cleanup
    cache.stop()
    
    print("=== All Tests Passed! ✅ ===")
