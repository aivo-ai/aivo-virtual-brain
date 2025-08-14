#!/usr/bin/env python3
"""
AIVO Inference Gateway - Test Script
S2-01 Implementation: Simple test script to verify service functionality
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any


class InferenceGatewayTester:
    """Test client for AIVO Inference Gateway"""
    
    def __init__(self, base_url: str = "http://localhost:8020"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def test_health(self) -> Dict[str, Any]:
        """Test health endpoint"""
        print("🏥 Testing health endpoint...")
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            result = response.json()
            
            if response.status_code == 200 and result.get("status") in ["healthy", "degraded"]:
                print(f"✅ Health check passed: {result['status']}")
                print(f"   Providers: {result['providers']}")
                return result
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return {"error": "Health check failed"}
        
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return {"error": str(e)}
    
    async def test_providers(self) -> Dict[str, Any]:
        """Test providers endpoint"""
        print("\n🤖 Testing providers endpoint...")
        
        try:
            response = await self.client.get(f"{self.base_url}/providers")
            result = response.json()
            
            if response.status_code == 200:
                print(f"✅ Found {result['count']} provider(s)")
                for name, info in result["providers"].items():
                    status = "✅" if info["healthy"] else "❌"
                    print(f"   {status} {name}: {info.get('type', 'unknown')}")
                return result
            else:
                print(f"❌ Providers check failed: {response.status_code}")
                return {"error": "Providers check failed"}
        
        except Exception as e:
            print(f"❌ Providers check error: {e}")
            return {"error": str(e)}
    
    async def test_generation(self) -> Dict[str, Any]:
        """Test text generation"""
        print("\n💬 Testing text generation...")
        
        request = {
            "messages": [
                {"role": "user", "content": "Hello! My email is test@example.com. Can you help me?"}
            ],
            "model": "gpt-4o-mini",
            "max_tokens": 50,
            "temperature": 0.7,
            "subject": "test/demo",
            "scrub_pii": True,
            "moderate_content": True
        }
        
        try:
            start_time = time.time()
            response = await self.client.post(
                f"{self.base_url}/v1/generate/chat/completions",
                json=request,
                headers={"X-Request-ID": "test-gen-001"}
            )
            
            if response.status_code == 200:
                result = response.json()
                duration = time.time() - start_time
                
                print(f"✅ Generation successful ({duration:.2f}s)")
                print(f"   Content: {result['content'][:100]}...")
                print(f"   Provider: {result['provider']}")
                print(f"   Tokens: {result['usage']['total_tokens']}")
                print(f"   Cost: ${result['cost_usd']:.4f}")
                print(f"   PII Detected: {result['pii_detected']}")
                print(f"   PII Scrubbed: {result['pii_scrubbed']}")
                
                return result
            else:
                print(f"❌ Generation failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return {"error": response.text}
        
        except Exception as e:
            print(f"❌ Generation error: {e}")
            return {"error": str(e)}
    
    async def test_streaming(self) -> bool:
        """Test streaming generation"""
        print("\n🔄 Testing streaming generation...")
        
        request = {
            "messages": [
                {"role": "user", "content": "Write a short haiku about testing"}
            ],
            "model": "gpt-4o-mini",
            "max_tokens": 100,
            "stream": True,
            "subject": "test/streaming"
        }
        
        try:
            chunks_received = 0
            content_length = 0
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/v1/generate/chat/completions",
                json=request,
                headers={"X-Request-ID": "test-stream-001"}
            ) as response:
                
                if response.status_code != 200:
                    print(f"❌ Streaming failed: {response.status_code}")
                    return False
                
                async for chunk in response.aiter_bytes():
                    chunk_str = chunk.decode()
                    if chunk_str.strip():
                        chunks_received += 1
                        if "data:" in chunk_str and not "[DONE]" in chunk_str:
                            try:
                                # Parse SSE chunk
                                data_line = [line for line in chunk_str.split('\n') if line.startswith('data:')][0]
                                json_data = data_line[5:].strip()  # Remove "data:"
                                chunk_data = json.loads(json_data)
                                delta = chunk_data.get('delta', '')
                                content_length += len(delta)
                                print(f"   Chunk: '{delta}'", end='', flush=True)
                            except:
                                pass
                
                print(f"\n✅ Streaming successful")
                print(f"   Chunks received: {chunks_received}")
                print(f"   Content length: {content_length} chars")
                
                return True
        
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            return False
    
    async def test_embeddings(self) -> Dict[str, Any]:
        """Test embeddings generation"""
        print("\n🔢 Testing embeddings...")
        
        request = {
            "input": ["Hello world", "Test embedding with email: user@example.com"],
            "model": "text-embedding-3-small",
            "scrub_pii": True
        }
        
        try:
            start_time = time.time()
            response = await self.client.post(
                f"{self.base_url}/v1/embeddings",
                json=request,
                headers={"X-Request-ID": "test-embed-001"}
            )
            
            if response.status_code == 200:
                result = response.json()
                duration = time.time() - start_time
                
                print(f"✅ Embeddings successful ({duration:.2f}s)")
                print(f"   Embeddings: {len(result['data'])}")
                print(f"   Dimensions: {len(result['data'][0]['embedding']) if result['data'] else 0}")
                print(f"   Provider: {result['provider']}")
                print(f"   PII Detected: {result['pii_detected']}")
                print(f"   PII Scrubbed: {result['pii_scrubbed']}")
                
                return result
            else:
                print(f"❌ Embeddings failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return {"error": response.text}
        
        except Exception as e:
            print(f"❌ Embeddings error: {e}")
            return {"error": str(e)}
    
    async def test_moderation(self) -> Dict[str, Any]:
        """Test content moderation"""
        print("\n🛡️  Testing content moderation...")
        
        request = {
            "input": "This is a test message for content moderation"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/moderations",
                json=request,
                headers={"X-Request-ID": "test-mod-001"}
            )
            
            if response.status_code == 200:
                result = response.json()
                mod_result = result["results"][0]
                
                print(f"✅ Moderation successful")
                print(f"   Flagged: {mod_result['flagged']}")
                print(f"   Provider: {result['provider']}")
                
                # Show category scores
                scores = mod_result.get("category_scores", {})
                if scores:
                    print("   Category scores:")
                    for category, score in scores.items():
                        print(f"     {category}: {score:.3f}")
                
                return result
            else:
                print(f"❌ Moderation failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return {"error": response.text}
        
        except Exception as e:
            print(f"❌ Moderation error: {e}")
            return {"error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary"""
        print("🚀 Starting AIVO Inference Gateway Tests\n")
        
        results = {
            "health": await self.test_health(),
            "providers": await self.test_providers(),
            "generation": await self.test_generation(),
            "streaming": await self.test_streaming(),
            "embeddings": await self.test_embeddings(),
            "moderation": await self.test_moderation()
        }
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            if isinstance(result, bool):
                status = "✅ PASS" if result else "❌ FAIL"
                if result:
                    passed += 1
            elif isinstance(result, dict) and "error" not in result:
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
            
            print(f"{test_name.upper():>12}: {status}")
        
        print("-" * 60)
        print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All tests passed! Service is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the errors above.")
        
        return results
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test AIVO Inference Gateway")
    parser.add_argument("--url", default="http://localhost:8020", help="Service URL")
    parser.add_argument("--test", choices=["health", "providers", "generation", "streaming", "embeddings", "moderation"], help="Run specific test")
    args = parser.parse_args()
    
    tester = InferenceGatewayTester(base_url=args.url)
    
    try:
        if args.test:
            # Run specific test
            if args.test == "health":
                await tester.test_health()
            elif args.test == "providers":
                await tester.test_providers()
            elif args.test == "generation":
                await tester.test_generation()
            elif args.test == "streaming":
                await tester.test_streaming()
            elif args.test == "embeddings":
                await tester.test_embeddings()
            elif args.test == "moderation":
                await tester.test_moderation()
        else:
            # Run all tests
            await tester.run_all_tests()
    
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
