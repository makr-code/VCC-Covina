"""
Test Process Analytics Endpoints

Runs analytics endpoints on Main Backend.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:45678"


def run_frequent_steps():
    url = f"{BASE_URL}/processes/analytics/frequent-steps"
    try:
        r = requests.get(url, params={"limit": 10}, timeout=15)
        print("Frequent Steps:", r.status_code)
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print("Error:", e)


def run_frequent_transitions():
    url = f"{BASE_URL}/processes/analytics/frequent-transitions"
    try:
        r = requests.get(url, params={"limit": 10}, timeout=15)
        print("Frequent Transitions:", r.status_code)
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print("Error:", e)


def run_bottlenecks():
    url = f"{BASE_URL}/processes/analytics/bottlenecks"
    try:
        r = requests.get(url, params={"limit": 10}, timeout=15)
        print("Bottlenecks:", r.status_code)
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print("Error:", e)


def main():
    print("== PROCESS ANALYTICS TEST ==")
    run_frequent_steps()
    run_frequent_transitions()
    run_bottlenecks()


if __name__ == "__main__":
    main()
