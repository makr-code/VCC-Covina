"""
Test Process Query API Endpoints

Tests all process query endpoints in Main Backend.

Prerequisites:
- Main Backend running on port 45678
- At least one process ingested via POST /ingestion/processes
"""
import requests
import json


BASE_URL = "http://127.0.0.1:45678"


def test_list_processes():
    """Test GET /processes"""
    print("=" * 80)
    print("TEST: GET /processes")
    print("=" * 80)
    
    url = f"{BASE_URL}/processes"
    params = {
        "limit": 10,
        "offset": 0,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total: {data['total']}")
            print(f"Returned: {len(data['processes'])}")
            
            if data['processes']:
                print("\nFirst process:")
                print(json.dumps(data['processes'][0], indent=2, ensure_ascii=False))
                print("\n✅ Test passed")
            else:
                print("\n⚠️ No processes found (ingest a process first)")
        else:
            print(f"❌ Test failed: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is Main Backend running on port 45678?")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_get_process_details(process_id: str = None):
    """Test GET /processes/{process_id}"""
    print("\n" + "=" * 80)
    print("TEST: GET /processes/{process_id}")
    print("=" * 80)
    
    # Get first process if no ID provided
    if not process_id:
        try:
            response = requests.get(f"{BASE_URL}/processes", params={"limit": 1}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['processes']:
                    process_id = data['processes'][0]['id']
                    print(f"Using first process: {process_id}")
                else:
                    print("⚠️ No processes found, skipping test")
                    return
            else:
                print("⚠️ Could not get process list, skipping test")
                return
        except Exception as e:
            print(f"⚠️ Error getting process ID: {e}")
            return
    
    url = f"{BASE_URL}/processes/{process_id}"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nProcess: {data['process']['name']}")
            print(f"Steps: {data['stats']['steps_count']}")
            print(f"Roles: {data['stats']['roles_count']}")
            print(f"Systems: {data['stats']['systems_count']}")
            print(f"Controls: {data['stats']['controls_count']}")
            print(f"Legal Refs: {data['stats']['legal_refs_count']}")
            
            if data['steps']:
                print(f"\nFirst step: {data['steps'][0]['name']}")
            
            print("\n✅ Test passed")
        elif response.status_code == 404:
            print(f"❌ Process not found: {process_id}")
        else:
            print(f"❌ Test failed: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is Main Backend running on port 45678?")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_search_processes():
    """Test GET /processes/search/fulltext"""
    print("\n" + "=" * 80)
    print("TEST: GET /processes/search/fulltext")
    print("=" * 80)
    
    url = f"{BASE_URL}/processes/search/fulltext"
    params = {
        "q": "Bauleitplanung",
        "limit": 10,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Query: {data['query']}")
            print(f"Results: {data['count']}")
            
            if data['results']:
                print("\nTop result:")
                print(f"  Name: {data['results'][0]['name']}")
                print(f"  Score: {data['results'][0]['score']:.4f}")
                print("\n✅ Test passed")
            else:
                print("\n⚠️ No results found")
        else:
            print(f"❌ Test failed: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is Main Backend running on port 45678?")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_search_steps():
    """Test GET /processes/search/steps"""
    print("\n" + "=" * 80)
    print("TEST: GET /processes/search/steps")
    print("=" * 80)
    
    url = f"{BASE_URL}/processes/search/steps"
    params = {
        "q": "Genehmigung",
        "limit": 10,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Query: {data['query']}")
            print(f"Results: {data['count']}")
            
            if data['results']:
                print("\nTop result:")
                result = data['results'][0]
                print(f"  Step: {result['step']['name']}")
                print(f"  Process: {result['process']['name']}")
                print(f"  Score: {result['score']:.4f}")
                print("\n✅ Test passed")
            else:
                print("\n⚠️ No results found")
        else:
            print(f"❌ Test failed: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is Main Backend running on port 45678?")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_process_stats():
    """Test GET /processes/stats/overview"""
    print("\n" + "=" * 80)
    print("TEST: GET /processes/stats/overview")
    print("=" * 80)
    
    url = f"{BASE_URL}/processes/stats/overview"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total Processes: {data['total_processes']}")
            print(f"Total Steps: {data['total_steps']}")
            
            if data['by_domain']:
                print("\nBy Domain:")
                for item in data['by_domain'][:3]:
                    print(f"  {item['domain']}: {item['count']}")
            
            if data['by_status']:
                print("\nBy Status:")
                for item in data['by_status']:
                    print(f"  {item['status']}: {item['count']}")
            
            print("\n✅ Test passed")
        else:
            print(f"❌ Test failed: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is Main Backend running on port 45678?")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_semantic_search_steps():
    """Test POST /processes/steps/semantic-search"""
    print("\n" + "=" * 80)
    print("TEST: POST /processes/steps/semantic-search")
    print("=" * 80)
    
    url = f"{BASE_URL}/processes/steps/semantic-search"
    payload = {
        "query": "Genehmigung durch Gemeinderat",
        "limit": 5,
        "min_similarity": 0.5,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Query: {data['query']}")
            print(f"Results: {data['count']}")
            
            if data['results']:
                print("\nTop result:")
                result = data['results'][0]
                print(f"  Step: {result['step']['name']}")
                print(f"  Process: {result['process']['name']}")
                print(f"  Similarity: {result['similarity']:.4f}")
                print("\n✅ Test passed")
            else:
                print("\n⚠️ No results found (ChromaDB may not be populated)")
        elif response.status_code == 503:
            print("⚠️ Semantic search unavailable (ChromaDB not connected)")
        else:
            print(f"❌ Test failed: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is Main Backend running on port 45678?")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_similarity_search():
    """Test POST /processes/similarity"""
    print("\n" + "=" * 80)
    print("TEST: POST /processes/similarity")
    print("=" * 80)
    
    # Get first process ID
    try:
        response = requests.get(f"{BASE_URL}/processes", params={"limit": 1}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['processes']:
                process_id = data['processes'][0]['id']
                print(f"Using source process: {process_id}")
            else:
                print("⚠️ No processes found, skipping test")
                return
        else:
            print("⚠️ Could not get process list, skipping test")
            return
    except Exception as e:
        print(f"⚠️ Error getting process ID: {e}")
        return
    
    url = f"{BASE_URL}/processes/similarity"
    payload = {
        "process_id": process_id,
        "limit": 3,
        "min_similarity": 0.6,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Source Process: {data['source_process_id']}")
            print(f"Similar Processes: {data['count']}")
            
            if data['results']:
                print("\nTop similar process:")
                result = data['results'][0]
                print(f"  Name: {result['name']}")
                print(f"  Similarity: {result['similarity']:.4f}")
                print(f"  Matching Steps: {result['matching_steps']}")
                print("\n✅ Test passed")
            else:
                print("\n⚠️ No similar processes found")
        elif response.status_code == 503:
            print("⚠️ Similarity search unavailable (ChromaDB not connected)")
        else:
            print(f"❌ Test failed: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is Main Backend running on port 45678?")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "PROCESS QUERY API TEST SUITE" + " " * 30 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Basic queries
    test_list_processes()
    test_get_process_details()
    test_search_processes()
    test_search_steps()
    test_process_stats()
    
    # Semantic search (requires ChromaDB)
    test_semantic_search_steps()
    test_similarity_search()
    
    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
