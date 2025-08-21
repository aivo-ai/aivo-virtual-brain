"""
Test the Config Service API endpoints
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8080"

def test_endpoint(endpoint, method="GET", headers=None, data=None):
    """Test an API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*50}")
    print(f"Testing: {method} {endpoint}")
    print('='*50)
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"Response Body: {json.dumps(response_json, indent=2)}")
        except:
            print(f"Response Body: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Config Service API")
    
    tests = [
        # Basic health checks
        ("/health", "GET"),
        ("/ready", "GET"),
        
        # API routes
        ("/api/v1/flags", "GET"),
        ("/api/v1/flags/chat.streaming", "GET"),
        ("/api/v1/flags/game.enabled/evaluate", "GET", {"x-grade-band": "k-5"}),
        
        # Config endpoints
        ("/api/v1/config/chat", "GET", {"x-user-id": "test-user", "x-role": "teacher"}),
        ("/api/v1/config/games", "GET", {"x-grade-band": "k-5"}),
        
        # Evaluation endpoint
        ("/api/v1/flags/evaluate", "POST", 
         {"Content-Type": "application/json"}, 
         {
             "flags": ["chat.streaming", "game.enabled"],
             "context": {
                 "userId": "test-user",
                 "role": "teacher",
                 "gradeBand": "k-5"
             }
         }),
        
        # Debug endpoints
        ("/api/v1/debug/context", "GET", {"x-user-id": "test-user", "x-role": "teacher"}),
        ("/api/v1/debug/flags", "GET"),
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        endpoint = test[0]
        method = test[1]
        headers = test[2] if len(test) > 2 else None
        data = test[3] if len(test) > 3 else None
        
        if test_endpoint(endpoint, method, headers, data):
            passed += 1
    
    print(f"\n🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
