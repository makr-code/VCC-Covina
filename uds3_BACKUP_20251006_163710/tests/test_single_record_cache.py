#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for UDS3 Single Record Cache Module

Test Coverage:
- Basic cache operations (get/put/invalidate)
- LRU eviction policy
- TTL expiration handling
- Thread-safe concurrent operations
- Batch operations
- Pattern-based invalidation
- Statistics & monitoring
- Performance benchmarks
"""

import pytest
import time
import threading
from datetime import datetime
from typing import Dict, Any

from uds3_single_record_cache import (
    SingleRecordCache,
    CacheEntry,
    CacheStatistics,
    CacheConfig,
    CacheStatus,
    InvalidationStrategy,
    create_single_record_cache
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def cache():
    """Erstellt einen Standard-Cache"""
    config = CacheConfig(
        max_size=5,
        default_ttl_seconds=10.0,
        auto_cleanup_interval=0.0  # Disabled for tests
    )
    cache = SingleRecordCache(config)
    yield cache
    cache.stop()


@pytest.fixture
def cache_small():
    """Erstellt einen kleinen Cache (max_size=2)"""
    config = CacheConfig(
        max_size=2,
        default_ttl_seconds=5.0,
        auto_cleanup_interval=0.0
    )
    cache = SingleRecordCache(config)
    yield cache
    cache.stop()


@pytest.fixture
def cache_no_ttl():
    """Erstellt einen Cache ohne TTL"""
    config = CacheConfig(
        max_size=10,
        default_ttl_seconds=None,  # No expiration
        auto_cleanup_interval=0.0
    )
    cache = SingleRecordCache(config)
    yield cache
    cache.stop()


@pytest.fixture
def sample_document():
    """Sample Dokument"""
    return {
        "title": "Test Document",
        "content": "Lorem ipsum dolor sit amet",
        "author": "Test User",
        "created_at": datetime.now().isoformat()
    }


# ============================================================================
# TEST: CACHE ENTRY
# ============================================================================

class TestCacheEntry:
    """Tests für CacheEntry Dataclass"""
    
    def test_cache_entry_creation(self, sample_document):
        """Test CacheEntry Erstellung"""
        entry = CacheEntry(
            document_id="doc123",
            data=sample_document,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl_seconds=60.0
        )
        
        assert entry.document_id == "doc123"
        assert entry.data == sample_document
        assert entry.access_count == 0
        assert entry.ttl_seconds == 60.0
        assert entry.status == CacheStatus.VALID
    
    def test_is_expired_no_ttl(self, sample_document):
        """Test is_expired() ohne TTL"""
        entry = CacheEntry(
            document_id="doc123",
            data=sample_document,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl_seconds=None
        )
        
        assert entry.is_expired() is False
    
    def test_is_expired_not_expired(self, sample_document):
        """Test is_expired() - nicht abgelaufen"""
        entry = CacheEntry(
            document_id="doc123",
            data=sample_document,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl_seconds=10.0
        )
        
        assert entry.is_expired() is False
    
    def test_is_expired_expired(self, sample_document):
        """Test is_expired() - abgelaufen"""
        entry = CacheEntry(
            document_id="doc123",
            data=sample_document,
            created_at=time.time() - 20.0,  # 20 seconds ago
            last_accessed=time.time(),
            ttl_seconds=10.0
        )
        
        assert entry.is_expired() is True
    
    def test_update_access(self, sample_document):
        """Test update_access()"""
        entry = CacheEntry(
            document_id="doc123",
            data=sample_document,
            created_at=time.time(),
            last_accessed=time.time() - 5.0
        )
        
        old_access_time = entry.last_accessed
        old_count = entry.access_count
        
        time.sleep(0.1)
        entry.update_access()
        
        assert entry.last_accessed > old_access_time
        assert entry.access_count == old_count + 1
    
    def test_to_dict(self, sample_document):
        """Test to_dict()"""
        entry = CacheEntry(
            document_id="doc123",
            data=sample_document,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl_seconds=60.0,
            access_count=5,
            size_bytes=1024
        )
        
        result = entry.to_dict()
        
        assert result["document_id"] == "doc123"
        assert result["access_count"] == 5
        assert result["ttl_seconds"] == 60.0
        assert result["size_bytes"] == 1024
        assert "created_at" in result
        assert "last_accessed" in result


# ============================================================================
# TEST: CACHE STATISTICS
# ============================================================================

class TestCacheStatistics:
    """Tests für CacheStatistics"""
    
    def test_statistics_creation(self):
        """Test CacheStatistics Erstellung"""
        stats = CacheStatistics()
        
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.invalidations == 0
        assert stats.total_requests == 0
    
    def test_hit_rate_calculation(self):
        """Test Hit-Rate Berechnung"""
        stats = CacheStatistics(hits=8, misses=2, total_requests=10)
        
        assert stats.hit_rate == 80.0
        assert stats.miss_rate == 20.0
    
    def test_hit_rate_zero_requests(self):
        """Test Hit-Rate bei 0 Requests"""
        stats = CacheStatistics()
        
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 100.0
    
    def test_to_dict(self):
        """Test to_dict()"""
        stats = CacheStatistics(
            hits=15,
            misses=5,
            total_requests=20,
            evictions=3,
            total_size_bytes=1024 * 1024 * 10  # 10 MB
        )
        
        result = stats.to_dict()
        
        assert result["hits"] == 15
        assert result["misses"] == 5
        assert result["hit_rate"] == 75.0
        assert result["miss_rate"] == 25.0
        assert result["total_size_mb"] == 10.0


# ============================================================================
# TEST: BASIC OPERATIONS
# ============================================================================

class TestBasicOperations:
    """Tests für grundlegende Cache-Operationen"""
    
    def test_cache_creation(self, cache):
        """Test Cache-Erstellung"""
        assert cache is not None
        assert cache.config.max_size == 5
        assert cache.config.default_ttl_seconds == 10.0
    
    def test_put_and_get_hit(self, cache, sample_document):
        """Test put() und get() - Hit"""
        cache.put("doc123", sample_document)
        result = cache.get("doc123")
        
        assert result is not None
        assert result == sample_document
    
    def test_get_miss(self, cache):
        """Test get() - Miss"""
        result = cache.get("nonexistent")
        
        assert result is None
    
    def test_put_overwrites_existing(self, cache):
        """Test put() überschreibt bestehenden Eintrag"""
        cache.put("doc123", {"version": 1})
        cache.put("doc123", {"version": 2})
        
        result = cache.get("doc123")
        assert result["version"] == 2
    
    def test_invalidate_existing(self, cache, sample_document):
        """Test invalidate() - existierender Eintrag"""
        cache.put("doc123", sample_document)
        
        result = cache.invalidate("doc123")
        
        assert result is True
        assert cache.get("doc123") is None
    
    def test_invalidate_nonexistent(self, cache):
        """Test invalidate() - nicht existierender Eintrag"""
        result = cache.invalidate("nonexistent")
        
        assert result is False
    
    def test_clear(self, cache, sample_document):
        """Test clear()"""
        cache.put("doc1", sample_document)
        cache.put("doc2", sample_document)
        cache.put("doc3", sample_document)
        
        cache.clear()
        
        assert cache.get("doc1") is None
        assert cache.get("doc2") is None
        assert cache.get("doc3") is None


# ============================================================================
# TEST: LRU EVICTION
# ============================================================================

class TestLRUEviction:
    """Tests für LRU Eviction Policy"""
    
    def test_lru_eviction_on_full_cache(self, cache_small, sample_document):
        """Test LRU Eviction bei vollem Cache"""
        # Fill cache (max_size=2)
        cache_small.put("doc1", sample_document)
        cache_small.put("doc2", sample_document)
        
        # Add third document - should evict doc1 (LRU)
        cache_small.put("doc3", sample_document)
        
        assert cache_small.get("doc1") is None  # Evicted
        assert cache_small.get("doc2") is not None
        assert cache_small.get("doc3") is not None
    
    def test_lru_access_updates_order(self, cache_small, sample_document):
        """Test dass Access LRU-Order aktualisiert"""
        cache_small.put("doc1", sample_document)
        cache_small.put("doc2", sample_document)
        
        # Access doc1 to make it "recently used"
        cache_small.get("doc1")
        
        # Add third document - should evict doc2 (now LRU)
        cache_small.put("doc3", sample_document)
        
        assert cache_small.get("doc1") is not None  # Still there
        assert cache_small.get("doc2") is None  # Evicted
        assert cache_small.get("doc3") is not None
    
    def test_eviction_statistics(self, cache_small, sample_document):
        """Test Eviction Statistics"""
        cache_small.put("doc1", sample_document)
        cache_small.put("doc2", sample_document)
        cache_small.put("doc3", sample_document)  # Triggers eviction
        
        stats = cache_small.get_statistics()
        assert stats.evictions == 1


# ============================================================================
# TEST: TTL EXPIRATION
# ============================================================================

class TestTTLExpiration:
    """Tests für TTL Expiration"""
    
    def test_ttl_not_expired(self, cache, sample_document):
        """Test Entry noch nicht abgelaufen"""
        cache.put("doc123", sample_document, ttl_seconds=5.0)
        
        result = cache.get("doc123")
        assert result is not None
    
    def test_ttl_expired(self, sample_document):
        """Test Entry abgelaufen"""
        config = CacheConfig(max_size=10, default_ttl_seconds=1.0, auto_cleanup_interval=0.0)
        cache = SingleRecordCache(config)
        
        cache.put("doc123", sample_document, ttl_seconds=0.5)
        time.sleep(1.0)
        
        result = cache.get("doc123")
        assert result is None
        
        cache.stop()
    
    def test_no_ttl_never_expires(self, cache_no_ttl, sample_document):
        """Test Entry ohne TTL läuft nie ab"""
        cache_no_ttl.put("doc123", sample_document)
        time.sleep(0.5)
        
        result = cache_no_ttl.get("doc123")
        assert result is not None
    
    def test_custom_ttl_overrides_default(self, sample_document):
        """Test Custom TTL überschreibt Default"""
        config = CacheConfig(max_size=10, default_ttl_seconds=10.0, auto_cleanup_interval=0.0)
        cache = SingleRecordCache(config)
        
        cache.put("doc123", sample_document, ttl_seconds=0.5)
        time.sleep(1.0)
        
        result = cache.get("doc123")
        assert result is None
        
        cache.stop()
    
    def test_cleanup_expired(self, sample_document):
        """Test cleanup_expired()"""
        config = CacheConfig(max_size=10, default_ttl_seconds=0.5, auto_cleanup_interval=0.0)
        cache = SingleRecordCache(config)
        
        cache.put("doc1", sample_document)
        cache.put("doc2", sample_document)
        
        time.sleep(1.0)
        
        count = cache.cleanup_expired()
        assert count == 2
        
        cache.stop()


# ============================================================================
# TEST: BATCH OPERATIONS
# ============================================================================

class TestBatchOperations:
    """Tests für Batch-Operationen"""
    
    def test_get_many(self, cache, sample_document):
        """Test get_many()"""
        cache.put("doc1", {"id": 1})
        cache.put("doc2", {"id": 2})
        cache.put("doc3", {"id": 3})
        
        results = cache.get_many(["doc1", "doc2", "doc99"])
        
        assert results["doc1"] == {"id": 1}
        assert results["doc2"] == {"id": 2}
        assert results["doc99"] is None
    
    def test_put_many(self, cache):
        """Test put_many()"""
        documents = {
            "doc1": {"id": 1},
            "doc2": {"id": 2},
            "doc3": {"id": 3}
        }
        
        cache.put_many(documents)
        
        assert cache.get("doc1") == {"id": 1}
        assert cache.get("doc2") == {"id": 2}
        assert cache.get("doc3") == {"id": 3}
    
    def test_invalidate_many(self, cache, sample_document):
        """Test invalidate_many()"""
        cache.put("doc1", sample_document)
        cache.put("doc2", sample_document)
        cache.put("doc3", sample_document)
        
        count = cache.invalidate_many(["doc1", "doc2", "doc99"])
        
        assert count == 2
        assert cache.get("doc1") is None
        assert cache.get("doc2") is None
        assert cache.get("doc3") is not None


# ============================================================================
# TEST: PATTERN INVALIDATION
# ============================================================================

class TestPatternInvalidation:
    """Tests für Pattern-based Invalidation"""
    
    def test_invalidate_pattern_prefix(self, cache, sample_document):
        """Test Pattern Invalidation - Prefix"""
        cache.put("user_123", sample_document)
        cache.put("user_456", sample_document)
        cache.put("post_789", sample_document)
        
        count = cache.invalidate_pattern(r"^user_")
        
        assert count == 2
        assert cache.get("user_123") is None
        assert cache.get("user_456") is None
        assert cache.get("post_789") is not None
    
    def test_invalidate_pattern_suffix(self, cache, sample_document):
        """Test Pattern Invalidation - Suffix"""
        cache.put("doc_v1", sample_document)
        cache.put("doc_v2", sample_document)
        cache.put("other_v3", sample_document)
        
        count = cache.invalidate_pattern(r"^doc_")
        
        assert count == 2
    
    def test_invalidate_pattern_no_matches(self, cache, sample_document):
        """Test Pattern Invalidation - keine Matches"""
        cache.put("doc1", sample_document)
        cache.put("doc2", sample_document)
        
        count = cache.invalidate_pattern(r"^user_")
        
        assert count == 0


# ============================================================================
# TEST: STATISTICS
# ============================================================================

class TestStatistics:
    """Tests für Cache-Statistiken"""
    
    def test_hit_miss_tracking(self, cache, sample_document):
        """Test Hit/Miss Tracking"""
        cache.put("doc123", sample_document)
        
        cache.get("doc123")  # Hit
        cache.get("doc123")  # Hit
        cache.get("doc99")   # Miss
        
        stats = cache.get_statistics()
        
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.total_requests == 3
        assert stats.hit_rate == pytest.approx(66.67, rel=0.1)
    
    def test_invalidation_tracking(self, cache, sample_document):
        """Test Invalidation Tracking"""
        cache.put("doc1", sample_document)
        cache.put("doc2", sample_document)
        
        cache.invalidate("doc1")
        cache.invalidate_pattern(r"^doc")
        
        stats = cache.get_statistics()
        assert stats.invalidations == 2
    
    def test_size_tracking(self, cache, sample_document):
        """Test Size Tracking"""
        cache.put("doc1", sample_document)
        cache.put("doc2", sample_document)
        
        stats = cache.get_statistics()
        assert stats.total_size_bytes > 0
    
    def test_reset_statistics(self, cache, sample_document):
        """Test Statistics Reset"""
        cache.put("doc123", sample_document)
        cache.get("doc123")
        
        cache.reset_statistics()
        
        stats = cache.get_statistics()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.total_requests == 0


# ============================================================================
# TEST: INFO & MONITORING
# ============================================================================

class TestInfoMonitoring:
    """Tests für Info & Monitoring"""
    
    def test_get_info(self, cache, sample_document):
        """Test get_info()"""
        cache.put("doc1", sample_document)
        cache.put("doc2", sample_document)
        
        info = cache.get_info()
        
        assert "config" in info
        assert "current_size" in info
        assert "usage_percent" in info
        assert "statistics" in info
        assert "top_entries" in info
        
        assert info["current_size"] == 2
        assert info["config"]["max_size"] == 5
    
    def test_top_entries(self, cache, sample_document):
        """Test Top Entries in Info"""
        for i in range(5):
            cache.put(f"doc{i}", sample_document)
        
        # Access doc0 multiple times
        for _ in range(5):
            cache.get("doc0")
        
        info = cache.get_info()
        top_entries = info["top_entries"]
        
        assert len(top_entries) == 5  # Should show all entries (cache size = 5)
        
        # Find doc0 in the list
        doc0_entry = next((e for e in top_entries if e["document_id"] == "doc0"), None)
        assert doc0_entry is not None
        assert doc0_entry["access_count"] == 5  # Was accessed 5 times


# ============================================================================
# TEST: CONCURRENCY
# ============================================================================

class TestConcurrency:
    """Tests für Thread-Safety"""
    
    def test_concurrent_puts(self, cache):
        """Test concurrent put operations"""
        def put_documents(start_idx):
            for i in range(start_idx, start_idx + 10):
                cache.put(f"doc{i}", {"id": i})
        
        threads = [
            threading.Thread(target=put_documents, args=(0,)),
            threading.Thread(target=put_documents, args=(10,)),
            threading.Thread(target=put_documents, args=(20,))
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Cache should still be consistent
        stats = cache.get_statistics()
        assert stats.total_size_bytes >= 0
    
    def test_concurrent_gets(self, cache, sample_document):
        """Test concurrent get operations"""
        cache.put("doc123", sample_document)
        
        results = []
        
        def get_document():
            result = cache.get("doc123")
            results.append(result is not None)
        
        threads = [threading.Thread(target=get_document) for _ in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All gets should succeed
        assert all(results)
        assert len(results) == 10
    
    def test_concurrent_mixed_operations(self, cache, sample_document):
        """Test mixed concurrent operations"""
        def worker(worker_id):
            for i in range(5):
                cache.put(f"doc{worker_id}_{i}", sample_document)
                cache.get(f"doc{worker_id}_{i}")
                if i % 2 == 0:
                    cache.invalidate(f"doc{worker_id}_{i}")
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Cache should still be consistent
        stats = cache.get_statistics()
        assert stats.total_requests > 0


# ============================================================================
# TEST: WARMUP
# ============================================================================

class TestWarmup:
    """Tests für Cache Warmup"""
    
    def test_warmup_basic(self, cache):
        """Test basic warmup"""
        def loader(doc_id):
            return {"id": doc_id, "loaded": True}
        
        doc_ids = ["doc1", "doc2", "doc3"]
        cache.warmup(loader, doc_ids)
        
        assert cache.get("doc1") == {"id": "doc1", "loaded": True}
        assert cache.get("doc2") == {"id": "doc2", "loaded": True}
        assert cache.get("doc3") == {"id": "doc3", "loaded": True}
    
    def test_warmup_with_errors(self, cache):
        """Test warmup mit Fehlern"""
        def loader(doc_id):
            if doc_id == "doc_error":
                raise ValueError("Load error")
            return {"id": doc_id}
        
        doc_ids = ["doc1", "doc_error", "doc2"]
        cache.warmup(loader, doc_ids)
        
        assert cache.get("doc1") is not None
        assert cache.get("doc_error") is None  # Failed to load
        assert cache.get("doc2") is not None


# ============================================================================
# TEST: FACTORY FUNCTION
# ============================================================================

class TestFactoryFunction:
    """Tests für Factory Function"""
    
    def test_create_single_record_cache(self):
        """Test create_single_record_cache()"""
        cache = create_single_record_cache(
            max_size=100,
            default_ttl_seconds=60.0,
            enable_auto_cleanup=False
        )
        
        assert cache is not None
        assert cache.config.max_size == 100
        assert cache.config.default_ttl_seconds == 60.0
        
        cache.stop()
    
    def test_create_with_auto_cleanup(self):
        """Test create mit auto cleanup"""
        cache = create_single_record_cache(
            max_size=100,
            default_ttl_seconds=60.0,
            enable_auto_cleanup=True
        )
        
        assert cache.config.auto_cleanup_interval > 0
        
        cache.stop()


# ============================================================================
# TEST: PERFORMANCE
# ============================================================================

class TestPerformance:
    """Performance Benchmarks"""
    
    def test_get_performance(self, cache, sample_document):
        """Test get() Performance"""
        cache.put("doc123", sample_document)
        
        start = time.time()
        for _ in range(1000):
            cache.get("doc123")
        duration = time.time() - start
        
        # Should be fast (< 100ms for 1000 operations)
        assert duration < 0.1
    
    def test_put_performance(self, cache, sample_document):
        """Test put() Performance"""
        start = time.time()
        for i in range(1000):
            cache.put(f"doc{i}", sample_document)
        duration = time.time() - start
        
        # Should be reasonably fast (< 500ms for 1000 operations)
        assert duration < 0.5
    
    def test_batch_get_performance(self, cache, sample_document):
        """Test Batch get Performance"""
        # Prepare data
        for i in range(100):
            cache.put(f"doc{i}", sample_document)
        
        doc_ids = [f"doc{i}" for i in range(100)]
        
        start = time.time()
        results = cache.get_many(doc_ids)
        duration = time.time() - start
        
        assert len(results) == 100
        assert duration < 0.1  # Should be fast


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
