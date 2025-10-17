"""
Test Suite for Governance Policy API Endpoints
==============================================

Tests the Governance Policy API (3rd Admin Tool) of the Main Backend.

Endpoints Tested:
    1. GET  /governance/policies - List all governance policies
    2. POST /governance/policies - Create new governance policy
    3. Direct Database Check - Verify data persistence

Expected Issues (Based on Golden Dataset & Graph Pattern API):
    - PostgreSQL cursor API mismatch (cursor.execute → execute_query)
    - Row access type errors (index → dict)
    - Config key issues (username → user)
    - Connection management (redundant connect() calls)

Author: GitHub Copilot
Date: 17. Oktober 2025, 19:45 Uhr
"""

import requests
import json
from datetime import datetime

# Test Configuration
BASE_URL = "http://127.0.0.1:45678"
GOVERNANCE_ENDPOINT = f"{BASE_URL}/governance/policies"

def test_list_governance_policies():
    """Test 1: GET /governance/policies - List all policies"""
    print("\n" + "="*80)
    print("TEST 1: GET /governance/policies - List All Policies")
    print("="*80)
    
    try:
        response = requests.get(
            GOVERNANCE_ENDPOINT,
            params={
                "active_only": "false",  # Get all policies, not just active ones (string for query param)
                "limit": 20
            }
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS - {data['count']} policies retrieved")
            print(f"Total Policies: {data['total']}")
            print(f"Filters: {data['filters']}")
            
            if data['policies']:
                policy = data['policies'][0]
                print(f"\nFirst Policy:")
                print(f"  - ID: {policy['id']}")
                print(f"  - Policy ID: {policy['policy_id']}")
                print(f"  - Name: {policy['name']}")
                print(f"  - Type: {policy['policy_type']}")
                print(f"  - Scope: {policy['scope']}")
                print(f"  - Status: {policy['status']}")
                print(f"  - Priority: {policy['priority']}")
            
            return True
        else:
            print(f"❌ FAILED - Status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

def test_create_governance_policy():
    """Test 2: POST /governance/policies - Create new policy"""
    print("\n" + "="*80)
    print("TEST 2: POST /governance/policies - Create New Policy")
    print("="*80)
    
    # Create test policy data
    test_policy = {
        "policy_id": f"TEST_RETENTION_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "name": "Test Retention Policy",
        "description": "Test policy for automated testing - can be deleted",
        "policy_type": "retention",
        "scope": "global",
        "rules": {
            "retention_period_days": 365,
            "document_types": ["invoice", "contract"],
            "actions": {
                "after_retention": "archive",
                "notification_days_before": 30
            }
        },
        "status": "draft",
        "priority": 50,
        "effective_from": None,
        "effective_until": None,
        "created_by": "test_automation",
        "approved_by": None,
        "approved_at": None,
        "metadata": {
            "test": True,
            "created_by_test": "test_governance_policy_api.py"
        }
    }
    
    print(f"Creating policy: {test_policy['policy_id']}")
    print(f"  - Name: {test_policy['name']}")
    print(f"  - Type: {test_policy['policy_type']}")
    print(f"  - Scope: {test_policy['scope']}")
    
    try:
        response = requests.post(
            GOVERNANCE_ENDPOINT,
            json=test_policy,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS - Policy Created!")
            print(f"  - Policy ID: {data['policy_id']}")
            print(f"  - Database ID: {data['id']}")
            print(f"  - Name: {data['name']}")
            print(f"  - Type: {data['policy_type']}")
            print(f"  - Scope: {data['scope']}")
            print(f"  - Priority: {data['priority']}")
            print(f"  - Status: {data['status']}")
            
            return data['policy_id']
        else:
            print(f"❌ FAILED - Status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return None

def test_verify_in_database(policy_id: str):
    """Test 3: Verify policy exists in database"""
    print("\n" + "="*80)
    print("TEST 3: Database Verification")
    print("="*80)
    
    try:
        # Get policy list and search for our test policy
        response = requests.get(
            GOVERNANCE_ENDPOINT,
            params={
                "active_only": "false",  # String "false" for query parameter
                "limit": 500  # Max allowed limit is 500
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            policies = data['policies']
            
            # Find our test policy
            found = None
            for policy in policies:
                if policy['policy_id'] == policy_id:
                    found = policy
                    break
            
            if found:
                print(f"✅ SUCCESS - Policy Found in Database!")
                print(f"  - Policy ID: {found['policy_id']}")
                print(f"  - Name: {found['name']}")
                print(f"  - Type: {found['policy_type']}")
                print(f"  - Scope: {found['scope']}")
                print(f"  - Priority: {found['priority']}")
                print(f"  - Status: {found['status']}")
                print(f"  - Created: {found['created_at']}")
                return True
            else:
                print(f"❌ FAILED - Policy '{policy_id}' not found in database")
                print(f"Total policies in DB: {len(policies)}")
                return False
        else:
            print(f"❌ FAILED - Could not query database (Status {response.status_code})")
            print(f"Response: {response.text[:500]}")  # Added error details
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("GOVERNANCE POLICY API TEST SUITE")
    print("="*80)
    print(f"Backend: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "test_list": False,
        "test_create": False,
        "test_verify": False
    }
    
    # Test 1: List policies
    results["test_list"] = test_list_governance_policies()
    
    # Test 2: Create policy
    created_policy_id = test_create_governance_policy()
    if created_policy_id:
        results["test_create"] = True
        
        # Test 3: Verify in database
        results["test_verify"] = test_verify_in_database(created_policy_id)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"  - List Policies:  {'✅ PASS' if results['test_list'] else '❌ FAIL'}")
    print(f"  - Create Policy:  {'✅ PASS' if results['test_create'] else '❌ FAIL'}")
    print(f"  - Verify in DB:   {'✅ PASS' if results['test_verify'] else '❌ FAIL'}")
    
    success_rate = (passed / total) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Governance Policy API is OPERATIONAL!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - API needs fixes")
        return 1

if __name__ == "__main__":
    exit(main())
