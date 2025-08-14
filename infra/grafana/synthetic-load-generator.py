#!/usr/bin/env python3
"""
Synthetic Load Generator for AIVO Services
Generates load to test Grafana dashboards and alert rules.
"""

import asyncio
import aiohttp
import random
import time
from typing import List, Dict
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyntheticLoadGenerator:
    def __init__(self, base_url: str = "http://localhost:8000", concurrent_users: int = 10):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.services = {
            "auth-svc": {
                "endpoints": ["/auth/login", "/auth/verify", "/auth/refresh", "/auth/logout"],
                "methods": ["POST", "GET", "POST", "POST"]
            },
            "user-svc": {
                "endpoints": ["/users", "/users/{id}", "/users/{id}/profile", "/users/search"],
                "methods": ["GET", "GET", "PUT", "GET"]
            },
            "learner-svc": {
                "endpoints": ["/learners", "/learners/{id}", "/learners/{id}/persona", "/learners/{id}/progress"],
                "methods": ["GET", "GET", "GET", "GET"]
            },
            "payment-svc": {
                "endpoints": ["/payments", "/payments/{id}", "/payments/process", "/payments/webhooks"],
                "methods": ["GET", "GET", "POST", "POST"]
            },
            "assessment-svc": {
                "endpoints": ["/assessments", "/assessments/{id}/submit", "/assessments/{id}/score", "/assessments/bulk"],
                "methods": ["GET", "POST", "GET", "GET"]
            },
            "iep-svc": {
                "endpoints": ["/iep", "/iep/{id}", "/iep/{id}/generate", "/iep/{id}/approve"],
                "methods": ["GET", "GET", "POST", "PUT"]
            }
        }

    async def generate_request(self, session: aiohttp.ClientSession, service: str, endpoint: str, method: str) -> Dict:
        """Generate a single request to a service endpoint"""
        # Replace placeholders with random IDs
        endpoint = endpoint.replace("{id}", f"user_{random.randint(1, 1000)}")
        url = f"{self.base_url}/{service.replace('-svc', '')}{endpoint}"
        
        # Simulate different response scenarios
        scenario = random.choices(
            ["success", "error_4xx", "error_5xx", "slow"],
            weights=[85, 10, 3, 2],  # 85% success, 10% 4xx, 3% 5xx, 2% slow
            k=1
        )[0]
        
        headers = {
            "Authorization": f"Bearer mock_token_{random.randint(1, 100)}",
            "Content-Type": "application/json",
            "X-Request-ID": f"req_{int(time.time())}_{random.randint(1000, 9999)}",
            "X-Service": service,
            "X-Scenario": scenario  # For mock server to handle different scenarios
        }
        
        payload = {}
        if method in ["POST", "PUT", "PATCH"]:
            payload = {
                "data": f"mock_data_{random.randint(1, 100)}",
                "timestamp": int(time.time()),
                "scenario": scenario
            }
        
        start_time = time.time()
        try:
            async with session.request(method, url, json=payload if payload else None, headers=headers, timeout=30) as response:
                duration = time.time() - start_time
                await response.text()  # Consume response body
                
                return {
                    "service": service,
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": response.status,
                    "duration": duration,
                    "scenario": scenario,
                    "timestamp": int(time.time())
                }
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed: {service} {method} {endpoint} - {str(e)}")
            return {
                "service": service,
                "endpoint": endpoint,
                "method": method,
                "status_code": 500,  # Treat as 5xx error
                "duration": duration,
                "scenario": "error_5xx",
                "error": str(e),
                "timestamp": int(time.time())
            }

    async def user_simulation(self, user_id: int, session: aiohttp.ClientSession, duration: int):
        """Simulate a single user's behavior for the specified duration"""
        end_time = time.time() + duration
        request_count = 0
        
        while time.time() < end_time:
            # Pick a random service and endpoint
            service = random.choice(list(self.services.keys()))
            service_config = self.services[service]
            endpoint_index = random.randint(0, len(service_config["endpoints"]) - 1)
            endpoint = service_config["endpoints"][endpoint_index]
            method = service_config["methods"][endpoint_index]
            
            result = await self.generate_request(session, service, endpoint, method)
            request_count += 1
            
            # Log interesting results
            if result["status_code"] >= 500:
                logger.warning(f"User {user_id}: 5xx error - {service} {method} {endpoint} - {result['status_code']}")
            elif result["duration"] > 1.0:
                logger.info(f"User {user_id}: Slow request - {service} {method} {endpoint} - {result['duration']:.2f}s")
            
            # Simulate realistic user behavior with pauses
            pause = random.uniform(0.5, 3.0)  # 0.5-3 second pauses between requests
            await asyncio.sleep(pause)
        
        logger.info(f"User {user_id} completed {request_count} requests")

    async def run_load_test(self, duration: int = 300):
        """Run the load test for specified duration (seconds)"""
        logger.info(f"Starting load test with {self.concurrent_users} users for {duration} seconds")
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Start all user simulations concurrently
            tasks = []
            for user_id in range(self.concurrent_users):
                task = asyncio.create_task(self.user_simulation(user_id, session, duration))
                tasks.append(task)
            
            # Wait for all users to complete
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Load test completed")

    async def spike_test(self, service: str, duration: int = 60):
        """Generate a spike in errors for a specific service to test alerts"""
        logger.info(f"Starting spike test for {service} - generating high error rate for {duration} seconds")
        
        async with aiohttp.ClientSession() as session:
            end_time = time.time() + duration
            
            while time.time() < end_time:
                # Force 5xx errors by sending malformed requests
                endpoint = random.choice(self.services[service]["endpoints"])
                endpoint = endpoint.replace("{id}", "invalid_id_to_trigger_error")
                url = f"{self.base_url}/{service.replace('-svc', '')}{endpoint}"
                
                headers = {
                    "X-Force-Error": "5xx",
                    "X-Service": service
                }
                
                try:
                    async with session.get(url, headers=headers, timeout=5) as response:
                        logger.debug(f"Spike test: {service} - Status: {response.status}")
                except Exception as e:
                    logger.debug(f"Spike test error (expected): {str(e)}")
                
                await asyncio.sleep(0.1)  # High frequency to trigger alerts quickly
        
        logger.info(f"Spike test for {service} completed")

async def main():
    parser = argparse.ArgumentParser(description="AIVO Synthetic Load Generator")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for services")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--spike-service", help="Run spike test on specific service (auth-svc, user-svc, etc.)")
    parser.add_argument("--spike-duration", type=int, default=60, help="Spike test duration in seconds")
    
    args = parser.parse_args()
    
    generator = SyntheticLoadGenerator(args.base_url, args.users)
    
    if args.spike_service:
        if args.spike_service in generator.services:
            await generator.spike_test(args.spike_service, args.spike_duration)
        else:
            logger.error(f"Invalid service: {args.spike_service}. Available: {list(generator.services.keys())}")
    else:
        await generator.run_load_test(args.duration)

if __name__ == "__main__":
    asyncio.run(main())
