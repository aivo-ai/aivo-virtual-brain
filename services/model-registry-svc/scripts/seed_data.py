#!/usr/bin/env python3
"""
AIVO Model Registry - Seed Test Data
S2-02 Implementation: Load sample models, versions, and bindings for testing
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Dict, Any

import httpx


class ModelRegistrySeeder:
    """Utility class to seed the model registry with test data"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def create_model(self, model_data: Dict[str, Any]) -> int:
        """Create a model and return its ID"""
        response = await self.client.post(f"{self.base_url}/models", json=model_data)
        response.raise_for_status()
        return response.json()["id"]
    
    async def create_version(self, version_data: Dict[str, Any]) -> int:
        """Create a model version and return its ID"""
        response = await self.client.post(f"{self.base_url}/versions", json=version_data)
        response.raise_for_status()
        return response.json()["id"]
    
    async def create_binding(self, binding_data: Dict[str, Any]) -> int:
        """Create a provider binding and return its ID"""
        response = await self.client.post(f"{self.base_url}/bindings", json=binding_data)
        response.raise_for_status()
        return response.json()["id"]
    
    def generate_hash(self, model_name: str, version: str) -> str:
        """Generate a SHA-256 hash for a model version"""
        content = f"{model_name}-{version}-{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def seed_llm_models(self):
        """Seed LLM models with multiple versions and provider bindings"""
        print("🤖 Seeding LLM models...")
        
        # GPT-4 Turbo model
        gpt4_id = await self.create_model({
            "name": "gpt-4-turbo",
            "task": "generation",
            "subject": "general",
            "description": "GPT-4 Turbo model for high-quality text generation"
        })
        
        # Create multiple versions for GPT-4
        versions = ["1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0"]
        eval_scores = [0.88, 0.90, 0.92, 0.94, 0.93]
        costs = [0.01, 0.009, 0.008, 0.008, 0.007]
        
        gpt4_version_ids = []
        for i, (version, eval_score, cost) in enumerate(zip(versions, eval_scores, costs)):
            version_id = await self.create_version({
                "model_id": gpt4_id,
                "hash": self.generate_hash("gpt-4-turbo", version),
                "version": version,
                "region": "us-east-1",
                "cost_per_1k": cost,
                "eval_score": eval_score,
                "slo_ok": True,
                "artifact_uri": f"s3://aivo-models/gpt-4-turbo/v{version}/model.bin",
                "size_bytes": 800000000000,  # 800GB
                "model_type": "transformer",
                "framework": "openai"
            })
            gpt4_version_ids.append(version_id)
            
            # Create provider binding for OpenAI
            await self.create_binding({
                "version_id": version_id,
                "provider": "openai",
                "provider_model_id": f"gpt-4-0125-preview",
                "status": "active",
                "config": {
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "top_p": 1.0,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
                },
                "avg_latency_ms": 2000 - i * 100,  # Improving latency
                "success_rate": 0.98 + i * 0.003
            })
        
        print(f"✅ Created GPT-4 Turbo model with {len(versions)} versions")
        
        # Claude 3 Sonnet model
        claude_id = await self.create_model({
            "name": "claude-3-sonnet",
            "task": "generation",
            "subject": "general",
            "description": "Claude 3 Sonnet model for conversational AI and text generation"
        })
        
        # Create versions for Claude
        claude_versions = ["1.0.0", "1.1.0", "1.2.0"]
        claude_scores = [0.89, 0.91, 0.93]
        claude_costs = [0.003, 0.003, 0.003]
        
        for version, eval_score, cost in zip(claude_versions, claude_scores, claude_costs):
            version_id = await self.create_version({
                "model_id": claude_id,
                "hash": self.generate_hash("claude-3-sonnet", version),
                "version": version,
                "region": "us-west-2",
                "cost_per_1k": cost,
                "eval_score": eval_score,
                "slo_ok": True,
                "artifact_uri": f"s3://aivo-models/claude-3-sonnet/v{version}/model.bin",
                "size_bytes": 700000000000,  # 700GB
                "model_type": "transformer",
                "framework": "anthropic"
            })
            
            # Create provider binding for Anthropic
            await self.create_binding({
                "version_id": version_id,
                "provider": "anthropic",
                "provider_model_id": "claude-3-sonnet-20240229",
                "status": "active",
                "config": {
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "top_p": 1.0
                },
                "avg_latency_ms": 1800,
                "success_rate": 0.99
            })
        
        print(f"✅ Created Claude 3 Sonnet model with {len(claude_versions)} versions")
    
    async def seed_embedding_models(self):
        """Seed embedding models"""
        print("📊 Seeding embedding models...")
        
        # OpenAI text-embedding-3-large
        embedding_id = await self.create_model({
            "name": "text-embedding-3-large",
            "task": "embedding",
            "subject": "general",
            "description": "OpenAI's latest and most capable embedding model"
        })
        
        version_id = await self.create_version({
            "model_id": embedding_id,
            "hash": self.generate_hash("text-embedding-3-large", "1.0.0"),
            "version": "1.0.0",
            "region": "us-east-1",
            "cost_per_1k": 0.00013,
            "eval_score": 0.96,
            "slo_ok": True,
            "artifact_uri": "s3://aivo-models/text-embedding-3-large/v1.0.0/model.bin",
            "size_bytes": 50000000000,  # 50GB
            "model_type": "embedding",
            "framework": "openai"
        })
        
        # Create provider bindings for multiple providers
        providers = [
            {"provider": "openai", "model_id": "text-embedding-3-large", "latency": 300, "success_rate": 0.999},
            {"provider": "azure", "model_id": "text-embedding-3-large", "latency": 350, "success_rate": 0.998}
        ]
        
        for provider_info in providers:
            await self.create_binding({
                "version_id": version_id,
                "provider": provider_info["provider"],
                "provider_model_id": provider_info["model_id"],
                "status": "active",
                "config": {"dimensions": 3072},
                "avg_latency_ms": provider_info["latency"],
                "success_rate": provider_info["success_rate"]
            })
        
        print("✅ Created text-embedding-3-large model")
        
        # Vertex AI embedding model
        vertex_embedding_id = await self.create_model({
            "name": "text-embedding-gecko-003",
            "task": "embedding",
            "subject": "multilingual",
            "description": "Google's multilingual text embedding model"
        })
        
        vertex_version_id = await self.create_version({
            "model_id": vertex_embedding_id,
            "hash": self.generate_hash("text-embedding-gecko-003", "1.0.0"),
            "version": "1.0.0",
            "region": "us-central1",
            "cost_per_1k": 0.000025,
            "eval_score": 0.94,
            "slo_ok": True,
            "artifact_uri": "s3://aivo-models/text-embedding-gecko-003/v1.0.0/model.bin",
            "size_bytes": 45000000000,  # 45GB
            "model_type": "embedding",
            "framework": "tensorflow"
        })
        
        await self.create_binding({
            "version_id": vertex_version_id,
            "provider": "vertex",
            "provider_model_id": "textembedding-gecko@003",
            "status": "active",
            "config": {"auto_truncate": True},
            "avg_latency_ms": 400,
            "success_rate": 0.997
        })
        
        print("✅ Created text-embedding-gecko-003 model")
    
    async def seed_moderation_models(self):
        """Seed content moderation models"""
        print("🛡️ Seeding moderation models...")
        
        # OpenAI moderation model
        mod_id = await self.create_model({
            "name": "text-moderation-stable",
            "task": "moderation",
            "subject": "safety",
            "description": "OpenAI's content moderation model for safety filtering"
        })
        
        version_id = await self.create_version({
            "model_id": mod_id,
            "hash": self.generate_hash("text-moderation-stable", "1.0.0"),
            "version": "1.0.0",
            "region": "us-east-1",
            "cost_per_1k": 0.0002,
            "eval_score": 0.97,
            "slo_ok": True,
            "artifact_uri": "s3://aivo-models/text-moderation-stable/v1.0.0/model.bin",
            "size_bytes": 5000000000,  # 5GB
            "model_type": "classifier",
            "framework": "openai"
        })
        
        await self.create_binding({
            "version_id": version_id,
            "provider": "openai",
            "provider_model_id": "text-moderation-stable",
            "status": "active",
            "config": {},
            "avg_latency_ms": 150,
            "success_rate": 0.999
        })
        
        print("✅ Created text-moderation-stable model")
    
    async def seed_specialized_models(self):
        """Seed specialized domain models"""
        print("🎯 Seeding specialized models...")
        
        # Code generation model
        code_id = await self.create_model({
            "name": "codellama-34b-instruct",
            "task": "generation",
            "subject": "code",
            "description": "Code Llama model fine-tuned for instruction following"
        })
        
        version_id = await self.create_version({
            "model_id": code_id,
            "hash": self.generate_hash("codellama-34b-instruct", "1.0.0"),
            "version": "1.0.0",
            "region": "us-west-2",
            "cost_per_1k": 0.0015,
            "eval_score": 0.91,
            "slo_ok": True,
            "artifact_uri": "s3://aivo-models/codellama-34b-instruct/v1.0.0/model.bin",
            "size_bytes": 68000000000,  # 68GB
            "model_type": "transformer",
            "framework": "pytorch"
        })
        
        await self.create_binding({
            "version_id": version_id,
            "provider": "bedrock",
            "provider_model_id": "meta.llama2-13b-chat-v1",
            "status": "active",
            "config": {
                "temperature": 0.1,
                "top_p": 0.9,
                "max_gen_len": 2048
            },
            "avg_latency_ms": 3000,
            "success_rate": 0.995
        })
        
        print("✅ Created CodeLlama model")
        
        # Medical domain model
        medical_id = await self.create_model({
            "name": "meditron-70b",
            "task": "generation",
            "subject": "medical",
            "description": "Medical domain-specific language model for healthcare applications"
        })
        
        version_id = await self.create_version({
            "model_id": medical_id,
            "hash": self.generate_hash("meditron-70b", "1.0.0"),
            "version": "1.0.0",
            "region": "us-east-1",
            "cost_per_1k": 0.003,
            "eval_score": 0.89,
            "slo_ok": True,
            "artifact_uri": "s3://aivo-models/meditron-70b/v1.0.0/model.bin",
            "size_bytes": 140000000000,  # 140GB
            "model_type": "transformer",
            "framework": "pytorch"
        })
        
        await self.create_binding({
            "version_id": version_id,
            "provider": "vertex",
            "provider_model_id": "meditron-70b@001",
            "status": "active",
            "config": {
                "temperature": 0.3,
                "top_p": 0.8,
                "max_output_tokens": 1024
            },
            "avg_latency_ms": 4000,
            "success_rate": 0.992
        })
        
        print("✅ Created Meditron medical model")
    
    async def apply_retention_policies(self):
        """Apply retention policies to models with many versions"""
        print("🗄️ Applying retention policies...")
        
        # Get models and apply retention
        response = await self.client.get(f"{self.base_url}/models")
        models = response.json()["models"]
        
        for model in models:
            model_id = model["id"]
            if model["version_count"] and model["version_count"] > 3:
                retention_response = await self.client.post(
                    f"{self.base_url}/retention/apply",
                    json={"model_id": model_id, "retention_count": 3}
                )
                if retention_response.status_code == 200:
                    result = retention_response.json()
                    if result["versions_archived"] > 0:
                        print(f"  📦 Archived {result['versions_archived']} versions for model '{model['name']}'")
        
        print("✅ Retention policies applied")
    
    async def print_summary(self):
        """Print summary of seeded data"""
        print("\n📈 Model Registry Summary:")
        
        stats_response = await self.client.get(f"{self.base_url}/stats")
        stats = stats_response.json()
        
        print(f"  Models: {stats['model_count']}")
        print(f"  Versions: {stats['version_count']} ({stats['active_version_count']} active, {stats['archived_version_count']} archived)")
        print(f"  Provider Bindings: {stats['provider_binding_count']}")
        print(f"  Average Eval Score: {stats['avg_eval_score']:.3f}" if stats['avg_eval_score'] else "  Average Eval Score: N/A")
        print(f"  Average Cost/1K: ${stats['avg_cost_per_1k']:.4f}" if stats['avg_cost_per_1k'] else "  Average Cost/1K: N/A")
        
        print("\n📊 Task Distribution:")
        for task, count in stats['task_distribution'].items():
            print(f"  {task}: {count}")
        
        print("\n🔗 Provider Distribution:")
        for provider, count in stats['provider_distribution'].items():
            print(f"  {provider}: {count}")
    
    async def seed_all(self):
        """Seed all test data"""
        print("🌱 Starting Model Registry data seeding...")
        
        try:
            await self.seed_llm_models()
            await self.seed_embedding_models()
            await self.seed_moderation_models()
            await self.seed_specialized_models()
            await self.apply_retention_policies()
            await self.print_summary()
            
            print("\n🎉 Model Registry seeding completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during seeding: {e}")
            raise
        finally:
            await self.client.aclose()


async def main():
    """Main seeding function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed AIVO Model Registry with test data")
    parser.add_argument("--url", default="http://localhost:8003", help="Model Registry service URL")
    parser.add_argument("--check-health", action="store_true", help="Check service health first")
    
    args = parser.parse_args()
    
    seeder = ModelRegistrySeeder(args.url)
    
    if args.check_health:
        try:
            response = await seeder.client.get(f"{args.url}/health")
            response.raise_for_status()
            health = response.json()
            print(f"✅ Service is healthy: {health['status']}")
        except Exception as e:
            print(f"❌ Service health check failed: {e}")
            return 1
    
    try:
        await seeder.seed_all()
        return 0
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
