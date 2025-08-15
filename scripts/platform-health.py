#!/usr/bin/env python3

import requests
import sys
from concurrent.futures import ThreadPoolExecutor
import json

services = [
    {"name": "auth-svc", "url": "http://localhost:3001/health"},
    {"name": "user-svc", "url": "http://localhost:3002/health"},
    {"name": "learner-svc", "url": "http://localhost:3003/health"},
    {"name": "assessment-svc", "url": "http://localhost:3004/health"},
    {"name": "slp-svc", "url": "http://localhost:3005/health"},
    {"name": "inference-gateway-svc", "url": "http://localhost:3006/health"},
    {"name": "search-svc", "url": "http://localhost:3007/health"},
]

def check_service(service):
    try:
        response = requests.get(service["url"], timeout=5)
        if response.status_code == 200:
            return {"name": service["name"], "status": "✅ HEALTHY", "response": response.json()}
        else:
            return {"name": service["name"], "status": f"❌ HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"name": service["name"], "status": "❌ CONNECTION REFUSED"}
    except requests.exceptions.Timeout:
        return {"name": service["name"], "status": "❌ TIMEOUT"}
    except Exception as e:
        return {"name": service["name"], "status": f"❌ ERROR: {str(e)}"}

def main():
    print("🔍 Checking AIVO Platform Services...")
    print("=" * 50)
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(check_service, services))
    
    healthy_count = 0
    for result in results:
        print(f"{result['name']:20} - {result['status']}")
        if "✅" in result["status"]:
            healthy_count += 1
            if "response" in result:
                print(f"                     📊 {json.dumps(result['response'], indent=4)}")
    
    print("=" * 50)
    print(f"📊 Health Summary: {healthy_count}/{len(services)} services healthy")
    
    # Check infrastructure services
    print("\n🏗️  Infrastructure Services:")
    infra_services = [
        {"name": "PostgreSQL", "url": "http://localhost:5432"},
        {"name": "Redis", "url": "http://localhost:6379"},
        {"name": "OpenSearch", "url": "http://localhost:9200"},
        {"name": "Kong Gateway", "url": "http://localhost:8003"},
        {"name": "Grafana", "url": "http://localhost:3000"},
    ]
    
    for service in infra_services:
        try:
            # Use different check for different services
            if service["name"] == "PostgreSQL":
                # Can't HTTP check postgres, just note it's expected to be running
                print(f"{service['name']:15} - ⚠️  TCP only (check via docker)")
            elif service["name"] == "Redis":
                # Can't HTTP check redis, just note it's expected to be running  
                print(f"{service['name']:15} - ⚠️  TCP only (check via docker)")
            else:
                response = requests.get(service["url"], timeout=3)
                if response.status_code < 400:
                    print(f"{service['name']:15} - ✅ RESPONDING")
                else:
                    print(f"{service['name']:15} - ⚠️  HTTP {response.status_code}")
        except Exception as e:
            print(f"{service['name']:15} - ❌ {str(e)[:50]}")
    
    return 0 if healthy_count > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
