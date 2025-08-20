#!/usr/bin/env python3
"""
Edge Security Testing Suite for AIVO Platform
Tests WAF rules, rate limiting, bot detection, and geographic controls
"""

import requests
import time
import json
import concurrent.futures
from typing import Dict, List, Tuple
import argparse
import sys

class EdgeSecurityTester:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def test_waf_protection(self) -> Dict[str, bool]:
        """Test WAF rules against common attack patterns"""
        print("🛡️  Testing WAF Protection...")
        
        tests = {
            'sql_injection_union': {
                'url': f'{self.base_url}/api/auth/login',
                'data': {'username': "admin' UNION SELECT * FROM users--", 'password': 'test'},
                'method': 'POST'
            },
            'sql_injection_or': {
                'url': f'{self.base_url}/api/auth/login',
                'data': {'username': "admin' OR 1=1--", 'password': 'test'},
                'method': 'POST'
            },
            'xss_script_tag': {
                'url': f'{self.base_url}/api/users/profile',
                'params': {'name': '<script>alert("xss")</script>'},
                'method': 'GET'
            },
            'xss_javascript_protocol': {
                'url': f'{self.base_url}/api/users/profile',
                'params': {'redirect': 'javascript:alert("xss")'},
                'method': 'GET'
            },
            'path_traversal': {
                'url': f'{self.base_url}/api/files',
                'params': {'file': '../../../etc/passwd'},
                'method': 'GET'
            },
            'command_injection': {
                'url': f'{self.base_url}/api/system',
                'data': {'command': 'ls; cat /etc/passwd'},
                'method': 'POST'
            }
        }
        
        results = {}
        for test_name, test_config in tests.items():
            try:
                if test_config['method'] == 'POST':
                    response = self.session.post(
                        test_config['url'],
                        data=test_config.get('data', {}),
                        timeout=10
                    )
                else:
                    response = self.session.get(
                        test_config['url'],
                        params=test_config.get('params', {}),
                        timeout=10
                    )
                
                # WAF should block these requests (403) or challenge them (429)
                is_blocked = response.status_code in [403, 429]
                results[test_name] = is_blocked
                
                status = "✅ BLOCKED" if is_blocked else f"❌ ALLOWED ({response.status_code})"
                print(f"  {test_name}: {status}")
                
            except requests.RequestException as e:
                print(f"  {test_name}: ⚠️  ERROR - {e}")
                results[test_name] = False
        
        return results
    
    def test_rate_limiting(self) -> Dict[str, bool]:
        """Test rate limiting on sensitive endpoints"""
        print("\n🚦 Testing Rate Limiting...")
        
        endpoints = {
            'login': {
                'url': f'{self.base_url}/api/auth/login',
                'data': {'username': 'test', 'password': 'test'},
                'method': 'POST',
                'limit': 5,
                'window': 60
            },
            'inference': {
                'url': f'{self.base_url}/api/inference/generate',
                'data': {'prompt': 'test prompt', 'model': 'gpt-3.5'},
                'method': 'POST',
                'limit': 10,
                'window': 60
            }
        }
        
        results = {}
        for endpoint_name, config in endpoints.items():
            print(f"  Testing {endpoint_name} rate limiting...")
            
            # Send requests up to the limit + 2
            requests_to_send = config['limit'] + 2
            responses = []
            
            for i in range(requests_to_send):
                try:
                    if config['method'] == 'POST':
                        response = self.session.post(config['url'], data=config['data'], timeout=5)
                    else:
                        response = self.session.get(config['url'], timeout=5)
                    
                    responses.append(response.status_code)
                    print(f"    Request {i+1}: {response.status_code}")
                    
                    # Small delay between requests
                    time.sleep(0.1)
                    
                except requests.RequestException as e:
                    print(f"    Request {i+1}: ERROR - {e}")
                    responses.append(500)
            
            # Check if rate limiting kicked in
            rate_limited_responses = [code for code in responses if code == 429]
            is_rate_limited = len(rate_limited_responses) > 0
            
            results[endpoint_name] = is_rate_limited
            status = "✅ RATE LIMITED" if is_rate_limited else "❌ NO RATE LIMITING"
            print(f"    Result: {status} ({len(rate_limited_responses)} rate limited responses)")
        
        return results
    
    def test_bot_detection(self) -> Dict[str, bool]:
        """Test bot detection with malicious user agents"""
        print("\n🤖 Testing Bot Detection...")
        
        malicious_user_agents = [
            'sqlmap/1.0',
            'nikto/2.1.6',
            'Nessus',
            'w3af.org',
            'masscan/1.0',
            'ZmEu'
        ]
        
        results = {}
        for user_agent in malicious_user_agents:
            try:
                headers = {'User-Agent': user_agent}
                response = self.session.get(f'{self.base_url}/', headers=headers, timeout=10)
                
                # Should be blocked (403) or challenged (429)
                is_blocked = response.status_code in [403, 429]
                results[user_agent] = is_blocked
                
                status = "✅ BLOCKED" if is_blocked else f"❌ ALLOWED ({response.status_code})"
                print(f"  {user_agent}: {status}")
                
            except requests.RequestException as e:
                print(f"  {user_agent}: ⚠️  ERROR - {e}")
                results[user_agent] = False
        
        return results
    
    def test_geographic_controls(self) -> Dict[str, bool]:
        """Test geographic access controls"""
        print("\n🌍 Testing Geographic Controls...")
        
        # Simulate requests from different countries using CF-IPCountry header
        test_cases = {
            'allowed_country_admin': {
                'url': f'{self.base_url}/admin/',
                'headers': {'CF-IPCountry': 'US'},
                'expected_blocked': False
            },
            'blocked_country_admin': {
                'url': f'{self.base_url}/admin/',
                'headers': {'CF-IPCountry': 'CN'},
                'expected_blocked': True
            },
            'blocked_country_auth': {
                'url': f'{self.base_url}/api/auth/login',
                'headers': {'CF-IPCountry': 'RU'},
                'expected_blocked': True
            },
            'challenge_country_inference': {
                'url': f'{self.base_url}/api/inference/generate',
                'headers': {'CF-IPCountry': 'BR'},
                'expected_blocked': False  # Should challenge, not block
            }
        }
        
        results = {}
        for test_name, config in test_cases.items():
            try:
                response = self.session.get(config['url'], headers=config['headers'], timeout=10)
                
                is_blocked = response.status_code in [403, 429]
                expected_blocked = config['expected_blocked']
                
                # Check if result matches expectation
                test_passed = is_blocked == expected_blocked
                results[test_name] = test_passed
                
                if test_passed:
                    status = "✅ CORRECT"
                else:
                    status = f"❌ UNEXPECTED ({response.status_code})"
                
                print(f"  {test_name}: {status}")
                
            except requests.RequestException as e:
                print(f"  {test_name}: ⚠️  ERROR - {e}")
                results[test_name] = False
        
        return results
    
    def test_load_handling(self, concurrent_users: int = 20, duration: int = 30) -> Dict[str, float]:
        """Test system behavior under load"""
        print(f"\n📈 Testing Load Handling ({concurrent_users} users, {duration}s)...")
        
        def make_request():
            try:
                start_time = time.time()
                response = self.session.get(f'{self.base_url}/api/health', timeout=10)
                end_time = time.time()
                return {
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'success': response.status_code == 200
                }
            except requests.RequestException:
                return {
                    'status_code': 500,
                    'response_time': 10.0,
                    'success': False
                }
        
        start_time = time.time()
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            while time.time() - start_time < duration:
                futures = [executor.submit(make_request) for _ in range(concurrent_users)]
                batch_results = [f.result() for f in concurrent.futures.as_completed(futures)]
                results.extend(batch_results)
                time.sleep(1)  # 1 second between batches
        
        # Calculate metrics
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r['success'])
        rate_limited_requests = sum(1 for r in results if r['status_code'] == 429)
        avg_response_time = sum(r['response_time'] for r in results) / total_requests
        success_rate = (successful_requests / total_requests) * 100
        
        metrics = {
            'total_requests': total_requests,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'rate_limited_requests': rate_limited_requests
        }
        
        print(f"  Total Requests: {total_requests}")
        print(f"  Success Rate: {success_rate:.2f}%")
        print(f"  Avg Response Time: {avg_response_time:.3f}s")
        print(f"  Rate Limited: {rate_limited_requests}")
        
        return metrics
    
    def run_all_tests(self) -> Dict:
        """Run all security tests"""
        print("🔒 AIVO Edge Security Test Suite")
        print("=" * 50)
        
        all_results = {
            'waf_protection': self.test_waf_protection(),
            'rate_limiting': self.test_rate_limiting(),
            'bot_detection': self.test_bot_detection(),
            'geographic_controls': self.test_geographic_controls(),
            'load_handling': self.test_load_handling()
        }
        
        # Summary
        print("\n📊 Test Summary")
        print("=" * 30)
        
        for category, results in all_results.items():
            if category == 'load_handling':
                continue  # Skip load test in summary
                
            if isinstance(results, dict):
                passed = sum(1 for result in results.values() if result)
                total = len(results)
                print(f"{category}: {passed}/{total} tests passed")
        
        return all_results

def main():
    parser = argparse.ArgumentParser(description='AIVO Edge Security Test Suite')
    parser.add_argument('--url', required=True, help='Base URL to test (e.g., https://api.aivo.dev)')
    parser.add_argument('--api-key', help='API key for authenticated tests')
    parser.add_argument('--output', help='Output file for results (JSON format)')
    
    args = parser.parse_args()
    
    tester = EdgeSecurityTester(args.url, args.api_key)
    results = tester.run_all_tests()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")
    
    # Exit with error code if any critical tests failed
    critical_failures = 0
    for category, test_results in results.items():
        if category == 'load_handling':
            continue
        if isinstance(test_results, dict):
            critical_failures += sum(1 for result in test_results.values() if not result)
    
    if critical_failures > 0:
        print(f"\n❌ {critical_failures} critical security tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All security tests passed!")
        sys.exit(0)

if __name__ == '__main__':
    main()
