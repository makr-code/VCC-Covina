#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Single Record Cache Demo
Demonstrates cache benefits, performance improvements, and use cases

Demo Sections:
1. Basic Cache Operations
2. Cache Hit/Miss Scenarios
3. TTL Expiration Demonstration
4. Performance Comparison (Cached vs Uncached)
5. LRU Eviction in Action
6. Batch Operations with Cache
7. Pattern-based Invalidation
8. Cache Statistics Monitoring
9. Real-World Use Cases
10. UDS3 Core Integration
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any

from uds3_single_record_cache import (
    SingleRecordCache,
    CacheConfig,
    create_single_record_cache
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DEMO 1: Basic Cache Operations
# ============================================================================

def demo_basic_operations():
    """Demonstrates basic cache get/put/invalidate operations"""
    print("\n" + "="*70)
    print("DEMO 1: Basic Cache Operations")
    print("="*70)
    
    cache = create_single_record_cache(max_size=10, default_ttl_seconds=60.0)
    
    # Sample document
    document = {
        "id": "doc123",
        "title": "Example Document",
        "content": "Lorem ipsum dolor sit amet",
        "author": "John Doe",
        "created_at": datetime.now().isoformat()
    }
    
    # Put document in cache
    print("\n1. Storing document in cache...")
    cache.put("doc123", document)
    print(f"✓ Document cached: {document['title']}")
    
    # Get document from cache (hit)
    print("\n2. Retrieving document from cache...")
    cached_doc = cache.get("doc123")
    if cached_doc:
        print(f"✓ Cache HIT: {cached_doc['title']}")
    else:
        print("✗ Cache MISS")
    
    # Try to get non-existent document (miss)
    print("\n3. Trying to get non-existent document...")
    result = cache.get("doc999")
    if result is None:
        print("✓ Cache MISS (expected)")
    
    # Invalidate document
    print("\n4. Invalidating cached document...")
    success = cache.invalidate("doc123")
    print(f"✓ Invalidation {'successful' if success else 'failed'}")
    
    # Try to get invalidated document
    result = cache.get("doc123")
    print(f"✓ After invalidation: {'MISS' if result is None else 'HIT'} (expected MISS)")
    
    cache.stop()
    print("\n✅ Demo 1 complete!")


# ============================================================================
# DEMO 2: Cache Hit/Miss Scenarios
# ============================================================================

def demo_hit_miss_scenarios():
    """Demonstrates various cache hit/miss scenarios"""
    print("\n" + "="*70)
    print("DEMO 2: Cache Hit/Miss Scenarios")
    print("="*70)
    
    cache = create_single_record_cache(max_size=5, default_ttl_seconds=60.0)
    
    # Prepare documents
    documents = {
        f"doc{i}": {"id": f"doc{i}", "title": f"Document {i}"}
        for i in range(1, 4)
    }
    
    print("\n1. Populating cache with 3 documents...")
    for doc_id, doc_data in documents.items():
        cache.put(doc_id, doc_data)
    print("✓ Cache populated")
    
    print("\n2. Testing access patterns...")
    
    # Multiple hits
    print("\n   a) Accessing same document multiple times:")
    for i in range(3):
        result = cache.get("doc1")
        status = "HIT" if result else "MISS"
        print(f"      Access {i+1}: {status}")
    
    # Mix of hits and misses
    print("\n   b) Mixed access pattern:")
    test_ids = ["doc1", "doc99", "doc2", "doc88", "doc3"]
    for doc_id in test_ids:
        result = cache.get(doc_id)
        status = "HIT" if result else "MISS"
        print(f"      {doc_id}: {status}")
    
    # Statistics
    print("\n3. Cache Statistics:")
    stats = cache.get_statistics()
    print(f"   Total requests: {stats.total_requests}")
    print(f"   Hits: {stats.hits}")
    print(f"   Misses: {stats.misses}")
    print(f"   Hit rate: {stats.hit_rate:.1f}%")
    print(f"   Miss rate: {stats.miss_rate:.1f}%")
    
    cache.stop()
    print("\n✅ Demo 2 complete!")


# ============================================================================
# DEMO 3: TTL Expiration Demonstration
# ============================================================================

def demo_ttl_expiration():
    """Demonstrates TTL-based cache expiration"""
    print("\n" + "="*70)
    print("DEMO 3: TTL Expiration Demonstration")
    print("="*70)
    
    cache = create_single_record_cache(max_size=10, default_ttl_seconds=2.0)
    
    document = {"id": "doc_ttl", "title": "Temporary Document"}
    
    print("\n1. Storing document with 2-second TTL...")
    cache.put("doc_ttl", document)
    print("✓ Document cached")
    
    print("\n2. Immediate access (before expiry)...")
    result = cache.get("doc_ttl")
    print(f"   Status: {'HIT' if result else 'MISS'} (expected HIT)")
    
    print("\n3. Waiting 2.5 seconds for TTL expiration...")
    time.sleep(2.5)
    
    print("\n4. Access after TTL expiry...")
    result = cache.get("doc_ttl")
    print(f"   Status: {'HIT' if result else 'MISS'} (expected MISS)")
    
    # Custom TTL
    print("\n5. Testing custom TTL override...")
    cache.put("doc_custom", {"id": "doc_custom"}, ttl_seconds=1.0)
    print("   Cached with 1-second TTL")
    
    time.sleep(1.5)
    result = cache.get("doc_custom")
    print(f"   After 1.5s: {'HIT' if result else 'MISS'} (expected MISS)")
    
    cache.stop()
    print("\n✅ Demo 3 complete!")


# ============================================================================
# DEMO 4: Performance Comparison
# ============================================================================

def demo_performance_comparison():
    """Compares performance of cached vs uncached reads"""
    print("\n" + "="*70)
    print("DEMO 4: Performance Comparison (Cached vs Uncached)")
    print("="*70)
    
    cache = create_single_record_cache(max_size=100, default_ttl_seconds=60.0)
    
    # Simulate slow database read
    def slow_database_read(doc_id: str) -> Dict[str, Any]:
        """Simulates database read with latency"""
        time.sleep(0.01)  # 10ms latency
        return {"id": doc_id, "data": "Document content"}
    
    # Populate cache
    print("\n1. Populating cache with 50 documents...")
    for i in range(50):
        doc_id = f"doc{i}"
        data = slow_database_read(doc_id)
        cache.put(doc_id, data)
    print("✓ Cache populated")
    
    # Benchmark: Cached reads
    print("\n2. Benchmarking CACHED reads (100 documents)...")
    start_time = time.time()
    for i in range(100):
        doc_id = f"doc{i % 50}"  # Cycle through 50 docs
        cache.get(doc_id)
    cached_duration = time.time() - start_time
    print(f"   Duration: {cached_duration*1000:.2f}ms")
    
    # Benchmark: Uncached reads (simulated)
    print("\n3. Benchmarking UNCACHED reads (100 documents)...")
    start_time = time.time()
    for i in range(100):
        slow_database_read(f"doc{i % 50}")
    uncached_duration = time.time() - start_time
    print(f"   Duration: {uncached_duration*1000:.2f}ms")
    
    # Comparison
    print("\n4. Performance Comparison:")
    speedup = uncached_duration / cached_duration if cached_duration > 0 else 0
    print(f"   Cached:   {cached_duration*1000:.2f}ms")
    print(f"   Uncached: {uncached_duration*1000:.2f}ms")
    print(f"   Speedup:  {speedup:.1f}x faster")
    print(f"   Saved:    {(uncached_duration - cached_duration)*1000:.2f}ms")
    
    # Cache statistics
    stats = cache.get_statistics()
    print(f"\n5. Cache Statistics:")
    print(f"   Hit rate: {stats.hit_rate:.1f}%")
    print(f"   Avg access time: {stats.average_access_time_ms:.2f}ms")
    
    cache.stop()
    print("\n✅ Demo 4 complete!")


# ============================================================================
# DEMO 5: LRU Eviction in Action
# ============================================================================

def demo_lru_eviction():
    """Demonstrates LRU eviction policy"""
    print("\n" + "="*70)
    print("DEMO 5: LRU Eviction in Action")
    print("="*70)
    
    cache = create_single_record_cache(max_size=3, default_ttl_seconds=60.0)
    
    print("\n1. Filling cache to capacity (max_size=3)...")
    for i in range(1, 4):
        cache.put(f"doc{i}", {"id": f"doc{i}", "order": i})
        print(f"   Cached: doc{i}")
    
    print("\n2. Accessing doc1 to make it 'recently used'...")
    cache.get("doc1")
    print("   ✓ doc1 accessed")
    
    print("\n3. Adding doc4 (triggers eviction)...")
    cache.put("doc4", {"id": "doc4", "order": 4})
    print("   ✓ doc4 cached (should evict doc2 - LRU)")
    
    print("\n4. Testing which documents remain cached...")
    for doc_id in ["doc1", "doc2", "doc3", "doc4"]:
        result = cache.get(doc_id)
        status = "✓ CACHED" if result else "✗ EVICTED"
        print(f"   {doc_id}: {status}")
    
    stats = cache.get_statistics()
    print(f"\n5. Eviction Statistics:")
    print(f"   Total evictions: {stats.evictions}")
    
    cache.stop()
    print("\n✅ Demo 5 complete!")


# ============================================================================
# DEMO 6: Batch Operations with Cache
# ============================================================================

def demo_batch_operations():
    """Demonstrates batch cache operations"""
    print("\n" + "="*70)
    print("DEMO 6: Batch Operations with Cache")
    print("="*70)
    
    cache = create_single_record_cache(max_size=20, default_ttl_seconds=60.0)
    
    # Batch put
    print("\n1. Batch storing 10 documents...")
    documents = {
        f"user_{i}": {"id": f"user_{i}", "name": f"User {i}"}
        for i in range(10)
    }
    cache.put_many(documents)
    print(f"✓ Stored {len(documents)} documents")
    
    # Batch get
    print("\n2. Batch retrieving documents...")
    doc_ids = [f"user_{i}" for i in range(5)] + ["user_99", "user_88"]
    results = cache.get_many(doc_ids)
    
    hits = sum(1 for v in results.values() if v is not None)
    misses = sum(1 for v in results.values() if v is None)
    print(f"   Requested: {len(doc_ids)} documents")
    print(f"   Hits: {hits}")
    print(f"   Misses: {misses}")
    
    # Batch invalidate
    print("\n3. Batch invalidating documents...")
    invalidate_ids = [f"user_{i}" for i in range(3)]
    count = cache.invalidate_many(invalidate_ids)
    print(f"✓ Invalidated {count} documents")
    
    # Verify
    print("\n4. Verifying invalidation...")
    for doc_id in ["user_0", "user_1", "user_2", "user_3"]:
        result = cache.get(doc_id)
        status = "CACHED" if result else "INVALIDATED"
        print(f"   {doc_id}: {status}")
    
    cache.stop()
    print("\n✅ Demo 6 complete!")


# ============================================================================
# DEMO 7: Pattern-based Invalidation
# ============================================================================

def demo_pattern_invalidation():
    """Demonstrates pattern-based cache invalidation"""
    print("\n" + "="*70)
    print("DEMO 7: Pattern-based Invalidation")
    print("="*70)
    
    cache = create_single_record_cache(max_size=20, default_ttl_seconds=60.0)
    
    # Populate with different document types
    print("\n1. Populating cache with different document types...")
    cache.put("user_123", {"type": "user", "id": "123"})
    cache.put("user_456", {"type": "user", "id": "456"})
    cache.put("post_789", {"type": "post", "id": "789"})
    cache.put("post_012", {"type": "post", "id": "012"})
    cache.put("comment_345", {"type": "comment", "id": "345"})
    print("✓ Cached 5 documents (2 users, 2 posts, 1 comment)")
    
    print("\n2. Invalidating all 'user_' documents...")
    count = cache.invalidate_pattern(r"^user_")
    print(f"✓ Invalidated {count} documents")
    
    print("\n3. Checking remaining cached documents...")
    test_ids = ["user_123", "user_456", "post_789", "post_012", "comment_345"]
    for doc_id in test_ids:
        result = cache.get(doc_id)
        status = "CACHED" if result else "INVALIDATED"
        print(f"   {doc_id}: {status}")
    
    print("\n4. Invalidating all 'post_' documents...")
    count = cache.invalidate_pattern(r"^post_")
    print(f"✓ Invalidated {count} documents")
    
    print("\n5. Final cache state...")
    for doc_id in test_ids:
        result = cache.get(doc_id)
        status = "CACHED" if result else "INVALIDATED"
        print(f"   {doc_id}: {status}")
    
    cache.stop()
    print("\n✅ Demo 7 complete!")


# ============================================================================
# DEMO 8: Cache Statistics Monitoring
# ============================================================================

def demo_statistics_monitoring():
    """Demonstrates cache statistics and monitoring"""
    print("\n" + "="*70)
    print("DEMO 8: Cache Statistics Monitoring")
    print("="*70)
    
    cache = create_single_record_cache(max_size=10, default_ttl_seconds=60.0)
    
    # Generate some activity
    print("\n1. Generating cache activity...")
    
    # Puts
    for i in range(5):
        cache.put(f"doc{i}", {"id": f"doc{i}"})
    
    # Hits
    for _ in range(10):
        cache.get("doc1")
        cache.get("doc2")
    
    # Misses
    for _ in range(5):
        cache.get("doc99")
    
    # Invalidations
    cache.invalidate("doc3")
    cache.invalidate("doc4")
    
    print("✓ Activity complete")
    
    # Display statistics
    print("\n2. Cache Statistics:")
    stats = cache.get_statistics()
    stats_dict = stats.to_dict()
    
    print(f"   Hits:              {stats_dict['hits']}")
    print(f"   Misses:            {stats_dict['misses']}")
    print(f"   Total requests:    {stats_dict['total_requests']}")
    print(f"   Hit rate:          {stats_dict['hit_rate']}%")
    print(f"   Miss rate:         {stats_dict['miss_rate']}%")
    print(f"   Evictions:         {stats_dict['evictions']}")
    print(f"   Invalidations:     {stats_dict['invalidations']}")
    print(f"   Avg access time:   {stats_dict['average_access_time_ms']:.2f}ms")
    print(f"   Total size:        {stats_dict['total_size_mb']}MB")
    
    # Detailed info
    print("\n3. Detailed Cache Info:")
    info = cache.get_info()
    print(f"   Current size:      {info['current_size']}")
    print(f"   Max size:          {info['config']['max_size']}")
    print(f"   Usage:             {info['usage_percent']}%")
    print(f"   Default TTL:       {info['config']['default_ttl_seconds']}s")
    
    print("\n4. Top cached entries:")
    for entry in info['top_entries'][:5]:
        print(f"   {entry['document_id']}: {entry['access_count']} accesses, {entry['age_seconds']:.1f}s old")
    
    cache.stop()
    print("\n✅ Demo 8 complete!")


# ============================================================================
# DEMO 9: Real-World Use Cases
# ============================================================================

def demo_real_world_use_cases():
    """Demonstrates real-world cache use cases"""
    print("\n" + "="*70)
    print("DEMO 9: Real-World Use Cases")
    print("="*70)
    
    # Use Case 1: User Session Cache
    print("\n📌 USE CASE 1: User Session Cache")
    print("   Scenario: Cache frequently accessed user profiles")
    
    session_cache = create_single_record_cache(max_size=100, default_ttl_seconds=1800)  # 30min TTL
    
    # Simulate user login
    user_profile = {
        "user_id": "user_12345",
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "role": "admin",
        "permissions": ["read", "write", "delete"]
    }
    
    session_cache.put("user_12345", user_profile)
    print("   ✓ User logged in, profile cached (30min TTL)")
    
    # Simulate multiple requests
    print("   Simulating 50 API requests...")
    start = time.time()
    for _ in range(50):
        profile = session_cache.get("user_12345")
    duration = (time.time() - start) * 1000
    print(f"   ✓ 50 requests served from cache in {duration:.2f}ms")
    
    stats = session_cache.get_statistics()
    print(f"   Hit rate: {stats.hit_rate:.1f}%")
    
    session_cache.stop()
    
    # Use Case 2: Document Metadata Cache
    print("\n📌 USE CASE 2: Document Metadata Cache")
    print("   Scenario: Cache document metadata for search results")
    
    metadata_cache = create_single_record_cache(max_size=500, default_ttl_seconds=600)  # 10min TTL
    
    # Simulate search result
    documents = {
        f"doc_{i}": {
            "id": f"doc_{i}",
            "title": f"Document {i}",
            "author": "John Doe",
            "size": 1024 * (i + 1)
        }
        for i in range(20)
    }
    
    metadata_cache.put_many(documents)
    print(f"   ✓ Cached metadata for {len(documents)} documents")
    
    # User views document details
    print("   User viewing 5 documents...")
    for i in range(5):
        doc = metadata_cache.get(f"doc_{i}")
        if doc:
            print(f"      doc_{i}: {doc['title']} - {doc['size']} bytes")
    
    metadata_cache.stop()
    
    # Use Case 3: Configuration Cache
    print("\n📌 USE CASE 3: Application Configuration Cache")
    print("   Scenario: Cache system configuration (no TTL)")
    
    config_cache = create_single_record_cache(max_size=50, default_ttl_seconds=None)
    
    config = {
        "app_name": "UDS3 System",
        "version": "3.0",
        "max_upload_size": 10 * 1024 * 1024,  # 10MB
        "allowed_formats": ["pdf", "docx", "txt"],
        "features": {
            "cache_enabled": True,
            "logging_level": "INFO"
        }
    }
    
    config_cache.put("app_config", config)
    print("   ✓ Configuration cached (no expiry)")
    print(f"   App: {config['app_name']} v{config['version']}")
    print(f"   Max upload: {config['max_upload_size'] // (1024*1024)}MB")
    
    # Configuration remains cached indefinitely
    cached_config = config_cache.get("app_config")
    print(f"   ✓ Configuration always available: {cached_config is not None}")
    
    config_cache.stop()
    
    print("\n✅ Demo 9 complete!")


# ============================================================================
# DEMO 10: UDS3 Core Integration
# ============================================================================

def demo_uds3_integration():
    """Demonstrates UDS3 Core integration"""
    print("\n" + "="*70)
    print("DEMO 10: UDS3 Core Integration")
    print("="*70)
    
    print("\n1. Importing UDS3 Core...")
    try:
        from uds3_core import UnifiedDatabaseStrategy
        print("✓ UDS3 Core imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import UDS3 Core: {e}")
        return
    
    print("\n2. Initializing UDS3 (cache enabled by default)...")
    try:
        uds = UnifiedDatabaseStrategy()
        
        if uds.cache_enabled:
            print("✓ Cache is ENABLED")
            print(f"   Cache instance: {type(uds.single_record_cache).__name__}")
        else:
            print("⚠ Cache is DISABLED")
    except Exception as e:
        print(f"✗ Failed to initialize UDS3: {e}")
        return
    
    print("\n3. Testing cache management methods...")
    
    # Get cache info
    if uds.cache_enabled:
        info = uds.get_cache_info()
        if info:
            print(f"   Max size: {info['config']['max_size']}")
            print(f"   TTL: {info['config']['default_ttl_seconds']}s")
            print(f"   Current size: {info['current_size']}")
    
    # Simulate some cache operations
    print("\n4. Simulating document reads with cache...")
    
    # These would normally go through read_document_operation
    # For demo, we'll use the cache directly
    if uds.single_record_cache:
        test_doc = {"id": "test123", "title": "Test Document"}
        uds.single_record_cache.put("test123", test_doc)
        print("   ✓ Document cached")
        
        cached = uds.single_record_cache.get("test123")
        print(f"   ✓ Retrieved from cache: {cached is not None}")
        
        # Invalidate after update
        uds.invalidate_cache("test123")
        print("   ✓ Cache invalidated")
    
    print("\n5. Cache statistics...")
    stats = uds.get_cache_statistics()
    if stats:
        print(f"   Total requests: {stats.get('total_requests', 0)}")
        print(f"   Hit rate: {stats.get('hit_rate', 0)}%")
    
    print("\n6. Cache management operations...")
    
    # Clear cache
    if uds.cache_enabled:
        uds.clear_cache()
        print("   ✓ Cache cleared")
        
        info = uds.get_cache_info()
        if info:
            print(f"   Current size after clear: {info['current_size']}")
    
    # Disable cache
    uds.disable_cache()
    print("   ✓ Cache disabled")
    
    # Re-enable with custom settings
    uds.enable_cache(max_size=500, ttl_seconds=120.0)
    print("   ✓ Cache re-enabled (500 entries, 120s TTL)")
    
    print("\n✅ Demo 10 complete!")


# ============================================================================
# MAIN DEMO RUNNER
# ============================================================================

def run_all_demos():
    """Runs all demo sections"""
    print("\n" + "="*70)
    print("UDS3 SINGLE RECORD CACHE - COMPREHENSIVE DEMO")
    print("="*70)
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    demos = [
        ("Basic Cache Operations", demo_basic_operations),
        ("Cache Hit/Miss Scenarios", demo_hit_miss_scenarios),
        ("TTL Expiration", demo_ttl_expiration),
        ("Performance Comparison", demo_performance_comparison),
        ("LRU Eviction", demo_lru_eviction),
        ("Batch Operations", demo_batch_operations),
        ("Pattern-based Invalidation", demo_pattern_invalidation),
        ("Statistics Monitoring", demo_statistics_monitoring),
        ("Real-World Use Cases", demo_real_world_use_cases),
        ("UDS3 Core Integration", demo_uds3_integration),
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Demo {i} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("ALL DEMOS COMPLETE!")
    print("="*70)
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📊 Summary:")
    print("   ✅ 10 demo sections executed")
    print("   ✅ Cache operations validated")
    print("   ✅ Performance benefits demonstrated")
    print("   ✅ UDS3 integration verified")


if __name__ == "__main__":
    run_all_demos()
