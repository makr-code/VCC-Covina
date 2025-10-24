"""
Test Script: JSON Structured Logging

Tests:
1. JsonFormatter - validate JSON output structure
2. Correlation ID - verify correlation ID propagation
3. Standard Fields - timestamp, level, logger, message
4. Custom Fields - service_name, environment, version
5. Multiple Contexts - different correlation IDs

Author: Covina Team
Date: 2025-01-17
"""

import sys
import json
import logging
from io import StringIO

# Add parent directory to path
sys.path.insert(0, "c:\\VCC\\Covina")

from utils.json_logging import setup_json_logging, set_correlation_id, get_correlation_id


def test_json_formatter():
    """Test 1: JsonFormatter produces valid JSON output."""
    print("=" * 70)
    print("TEST 1: JSON Formatter - Valid JSON Output")
    print("=" * 70)
    
    # Capture stdout
    captured = StringIO()
    handler = logging.StreamHandler(captured)
    
    # Import after sys.path modification
    from utils.json_logging import CustomJsonFormatter, CorrelationIdFilter
    
    formatter = CustomJsonFormatter(
        service_name="test_service",
        environment="test",
        version="1.0.0"
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    
    logger = logging.getLogger("test_json")
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Generate logs
    set_correlation_id("test-correlation-123")
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    
    # Parse JSON
    output = captured.getvalue()
    lines = output.strip().split("\n")
    
    passed = 0
    failed = 0
    
    for i, line in enumerate(lines, 1):
        try:
            log_obj = json.loads(line)
            
            # Check required fields
            required_fields = ["timestamp", "level", "logger", "message", 
                             "service_name", "environment", "version", "correlation_id"]
            missing = [f for f in required_fields if f not in log_obj]
            
            if missing:
                print(f"❌ Log {i}: Missing fields: {missing}")
                failed += 1
            else:
                print(f"✅ Log {i}: Valid JSON with all fields")
                print(f"   {json.dumps(log_obj, indent=2)[:200]}...")
                passed += 1
                
        except json.JSONDecodeError as e:
            print(f"❌ Log {i}: Invalid JSON - {e}")
            print(f"   {line[:100]}")
            failed += 1
    
    print(f"\n📊 Test 1 Result: {passed}/{passed+failed} logs are valid JSON")
    return passed, failed


def test_correlation_id():
    """Test 2: Correlation ID propagation."""
    print("\n" + "=" * 70)
    print("TEST 2: Correlation ID - Context Propagation")
    print("=" * 70)
    
    # Test cases
    test_cases = [
        ("corr-id-111", "First request"),
        ("corr-id-222", "Second request"),
        ("corr-id-333", "Third request"),
        (None, "Request without correlation ID")
    ]
    
    passed = 0
    failed = 0
    
    for correlation_id, description in test_cases:
        # Set correlation ID
        if correlation_id:
            set_correlation_id(correlation_id)
        else:
            set_correlation_id(None)
        
        # Get back
        retrieved_id = get_correlation_id()
        
        if correlation_id:
            if retrieved_id == correlation_id:
                print(f"✅ {description}: Correlation ID = {retrieved_id}")
                passed += 1
            else:
                print(f"❌ {description}: Expected {correlation_id}, got {retrieved_id}")
                failed += 1
        else:
            if retrieved_id is None:
                print(f"✅ {description}: Correlation ID = None (expected)")
                passed += 1
            else:
                print(f"❌ {description}: Expected None, got {retrieved_id}")
                failed += 1
    
    print(f"\n📊 Test 2 Result: {passed}/{passed+failed} correlation IDs correct")
    return passed, failed


def test_standard_fields():
    """Test 3: Standard log fields."""
    print("\n" + "=" * 70)
    print("TEST 3: Standard Fields - timestamp, level, logger, message")
    print("=" * 70)
    
    # Capture stdout
    captured = StringIO()
    handler = logging.StreamHandler(captured)
    
    from utils.json_logging import CustomJsonFormatter, CorrelationIdFilter
    
    formatter = CustomJsonFormatter(
        service_name="field_test",
        environment="test",
        version="1.0.0"
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    
    logger = logging.getLogger("test_fields")
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    # Generate logs with different levels
    test_cases = [
        (logging.DEBUG, "Debug message", "DEBUG"),
        (logging.INFO, "Info message", "INFO"),
        (logging.WARNING, "Warning message", "WARNING"),
        (logging.ERROR, "Error message", "ERROR"),
        (logging.CRITICAL, "Critical message", "CRITICAL")
    ]
    
    set_correlation_id("field-test-123")
    
    for level, message, expected_level_name in test_cases:
        logger.log(level, message)
    
    # Parse and validate
    output = captured.getvalue()
    lines = output.strip().split("\n")
    
    passed = 0
    failed = 0
    
    for i, (line, (_, expected_msg, expected_level)) in enumerate(zip(lines, test_cases), 1):
        try:
            log_obj = json.loads(line)
            
            # Validate fields
            checks = [
                ("timestamp", log_obj.get("timestamp") is not None),
                ("level", log_obj.get("level") == expected_level),
                ("logger", log_obj.get("logger") == "test_fields"),
                ("message", log_obj.get("message") == expected_msg)
            ]
            
            all_passed = all(passed for _, passed in checks)
            
            if all_passed:
                print(f"✅ Log {i} ({expected_level}): All standard fields correct")
                passed += 1
            else:
                print(f"❌ Log {i} ({expected_level}): Field validation failed")
                for field, check_passed in checks:
                    if not check_passed:
                        print(f"   {field}: FAILED (got {log_obj.get(field)})")
                failed += 1
                
        except json.JSONDecodeError:
            print(f"❌ Log {i}: Invalid JSON")
            failed += 1
    
    print(f"\n📊 Test 3 Result: {passed}/{passed+failed} logs have correct standard fields")
    return passed, failed


def test_custom_fields():
    """Test 4: Custom fields (service_name, environment, version)."""
    print("\n" + "=" * 70)
    print("TEST 4: Custom Fields - service_name, environment, version")
    print("=" * 70)
    
    # Test different service configurations
    test_configs = [
        ("main_backend", "production", "3.4.10"),
        ("ingestion_backend", "staging", "2.1.5"),
        ("test_service", "development", "1.0.0")
    ]
    
    passed = 0
    failed = 0
    
    for service_name, environment, version in test_configs:
        captured = StringIO()
        handler = logging.StreamHandler(captured)
        
        from utils.json_logging import CustomJsonFormatter, CorrelationIdFilter
        
        formatter = CustomJsonFormatter(
            service_name=service_name,
            environment=environment,
            version=version
        )
        handler.setFormatter(formatter)
        handler.addFilter(CorrelationIdFilter())
        
        logger = logging.getLogger(f"test_{service_name}")
        logger.handlers = []
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        logger.info("Test message")
        
        # Parse and validate
        output = captured.getvalue()
        log_obj = json.loads(output.strip())
        
        checks = [
            ("service_name", log_obj.get("service_name") == service_name),
            ("environment", log_obj.get("environment") == environment),
            ("version", log_obj.get("version") == version)
        ]
        
        all_passed = all(check_passed for _, check_passed in checks)
        
        if all_passed:
            print(f"✅ {service_name}: Custom fields correct")
            print(f"   service_name={log_obj['service_name']}, "
                  f"environment={log_obj['environment']}, "
                  f"version={log_obj['version']}")
            passed += 1
        else:
            print(f"❌ {service_name}: Custom fields failed")
            for field, check_passed in checks:
                if not check_passed:
                    print(f"   {field}: Expected {locals()[field]}, got {log_obj.get(field)}")
            failed += 1
    
    print(f"\n📊 Test 4 Result: {passed}/{passed+failed} configs have correct custom fields")
    return passed, failed


def test_multiple_contexts():
    """Test 5: Multiple correlation ID contexts."""
    print("\n" + "=" * 70)
    print("TEST 5: Multiple Contexts - Different Correlation IDs")
    print("=" * 70)
    
    captured = StringIO()
    handler = logging.StreamHandler(captured)
    
    from utils.json_logging import CustomJsonFormatter, CorrelationIdFilter
    
    formatter = CustomJsonFormatter(
        service_name="multi_context",
        environment="test",
        version="1.0.0"
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    
    logger = logging.getLogger("test_multi")
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Simulate multiple requests
    contexts = [
        ("request-1-uuid", "First request processing"),
        ("request-2-uuid", "Second request processing"),
        ("request-3-uuid", "Third request processing")
    ]
    
    for correlation_id, message in contexts:
        set_correlation_id(correlation_id)
        logger.info(message)
    
    # Parse and validate
    output = captured.getvalue()
    lines = output.strip().split("\n")
    
    passed = 0
    failed = 0
    
    for i, (line, (expected_id, expected_msg)) in enumerate(zip(lines, contexts), 1):
        try:
            log_obj = json.loads(line)
            
            checks = [
                ("correlation_id", log_obj.get("correlation_id") == expected_id),
                ("message", log_obj.get("message") == expected_msg)
            ]
            
            all_passed = all(check_passed for _, check_passed in checks)
            
            if all_passed:
                print(f"✅ Context {i}: correlation_id={log_obj['correlation_id']}")
                passed += 1
            else:
                print(f"❌ Context {i}: Mismatch")
                for field, check_passed in checks:
                    if not check_passed:
                        print(f"   {field}: Expected {locals()[f'expected_{field.split('_')[-1]}']}, "
                              f"got {log_obj.get(field)}")
                failed += 1
                
        except json.JSONDecodeError:
            print(f"❌ Context {i}: Invalid JSON")
            failed += 1
    
    print(f"\n📊 Test 5 Result: {passed}/{passed+failed} contexts have correct correlation IDs")
    return passed, failed


def main():
    """Run all tests."""
    print("\n" + "🧪" * 35)
    print("JSON STRUCTURED LOGGING - TEST SUITE")
    print("🧪" * 35 + "\n")
    
    total_passed = 0
    total_failed = 0
    
    # Run tests
    tests = [
        test_json_formatter,
        test_correlation_id,
        test_standard_fields,
        test_custom_fields,
        test_multiple_contexts
    ]
    
    for test_func in tests:
        passed, failed = test_func()
        total_passed += passed
        total_failed += failed
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"✅ Total Passed: {total_passed}")
    print(f"❌ Total Failed: {total_failed}")
    print(f"📊 Success Rate: {total_passed}/{total_passed+total_failed} "
          f"({100*total_passed/(total_passed+total_failed):.1f}%)")
    
    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED! JSON Structured Logging is PRODUCTION READY!")
    else:
        print(f"\n⚠️  {total_failed} test(s) failed. Review implementation.")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
