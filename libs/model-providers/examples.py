"""
Example usage of the AIVO Model Providers library.

This example demonstrates how to use the unified provider interface
to interact with different AI model providers.
"""

import asyncio
import os
from typing import List, Dict, Any

from aivo_model_providers import (
    get_provider,
    get_available_providers,
    is_provider_available,
    get_feature_flags,
    ProviderType,
    GenerateRequest,
    EmbedRequest,
    ModerateRequest,
    FineTuneRequest,
    JobStatusRequest,
    ProviderUnavailableError,
)


async def example_auto_provider_selection():
    """Example of automatic provider selection."""
    print("🔍 Auto-selecting best available provider...")
    
    try:
        # Auto-select the best available provider
        async with await get_provider(ProviderType.AUTO) as provider:
            print(f"✅ Selected provider: {provider.provider_type.value}")
            
            # Test text generation
            request = GenerateRequest(
                messages=[{"role": "user", "content": "What is artificial intelligence?"}],
                model="gpt-4",  # This will be adapted by each provider
                max_tokens=100,
                temperature=0.7,
            )
            
            response = await provider.generate(request)
            print(f"📝 Generated text: {response.content[:100]}...")
            print(f"📊 Token usage: {response.usage}")
            
    except ProviderUnavailableError:
        print("❌ No providers are available. Please check your credentials.")


async def example_provider_comparison():
    """Example comparing multiple providers."""
    print("\n🔄 Comparing multiple providers...")
    
    # Get all available providers
    available_providers = await get_available_providers()
    print(f"🌐 Available providers: {[p.value for p in available_providers]}")
    
    # Test the same request with different providers
    request = GenerateRequest(
        messages=[{"role": "user", "content": "Explain machine learning in one sentence."}],
        model="gpt-4",  # Each provider will use their best equivalent model
        max_tokens=50,
        temperature=0.5,
    )
    
    for provider_type in available_providers:
        if provider_type == ProviderType.AUTO:
            continue
            
        try:
            async with await get_provider(provider_type) as provider:
                response = await provider.generate(request)
                print(f"\n{provider_type.value.upper()}:")
                print(f"  📝 Response: {response.content}")
                print(f"  🎯 Model: {response.model}")
                print(f"  📊 Tokens: {response.usage['total_tokens']}")
                
        except ProviderUnavailableError:
            print(f"\n{provider_type.value.upper()}: ❌ Not available")


async def example_embeddings():
    """Example of creating embeddings."""
    print("\n🔢 Creating embeddings...")
    
    try:
        async with await get_provider(ProviderType.AUTO) as provider:
            request = EmbedRequest(
                texts=[
                    "Artificial intelligence is transforming the world.",
                    "Machine learning enables computers to learn from data.",
                    "Natural language processing helps computers understand text.",
                ],
                model="text-embedding-3-small",
                dimensions=1536,
            )
            
            response = await provider.embed(request)
            print(f"✅ Created {len(response.embeddings)} embeddings")
            print(f"📐 Dimensions: {len(response.embeddings[0])}")
            print(f"📊 Token usage: {response.usage}")
            
            # Show similarity between first two embeddings
            import math
            
            def cosine_similarity(a: List[float], b: List[float]) -> float:
                dot_product = sum(x * y for x, y in zip(a, b))
                magnitude_a = math.sqrt(sum(x * x for x in a))
                magnitude_b = math.sqrt(sum(x * x for x in b))
                return dot_product / (magnitude_a * magnitude_b)
            
            similarity = cosine_similarity(response.embeddings[0], response.embeddings[1])
            print(f"📏 Similarity between first two texts: {similarity:.3f}")
            
    except ProviderUnavailableError:
        print("❌ No embedding providers are available.")


async def example_content_moderation():
    """Example of content moderation."""
    print("\n🛡️ Testing content moderation...")
    
    try:
        async with await get_provider(ProviderType.AUTO) as provider:
            test_contents = [
                "This is perfectly normal content about machine learning.",
                "I really dislike this particular approach to AI development.",
                "Let's discuss the ethical implications of artificial intelligence.",
            ]
            
            for i, content in enumerate(test_contents, 1):
                request = ModerateRequest(content=content)
                response = await provider.moderate(request)
                
                print(f"\n📝 Text {i}: {content[:50]}...")
                print(f"🚨 Flagged: {response.flagged}")
                
                if response.results:
                    flagged_categories = [r.category.value for r in response.results if r.flagged]
                    if flagged_categories:
                        print(f"⚠️  Flagged categories: {', '.join(flagged_categories)}")
                
    except ProviderUnavailableError:
        print("❌ No moderation providers are available.")


async def example_fine_tuning():
    """Example of fine-tuning workflow."""
    print("\n🎯 Fine-tuning workflow example...")
    
    try:
        async with await get_provider(ProviderType.AUTO) as provider:
            # Start fine-tuning job
            fine_tune_request = FineTuneRequest(
                training_file_url="https://example.com/training_data.jsonl",
                model="gpt-3.5-turbo",
                validation_file_url="https://example.com/validation_data.jsonl",
                suffix="custom-model",
                hyperparameters={"n_epochs": 3, "batch_size": 1},
            )
            
            print("🚀 Starting fine-tuning job...")
            fine_tune_response = await provider.fine_tune(fine_tune_request)
            
            print(f"✅ Fine-tuning job created: {fine_tune_response.job_id}")
            print(f"📊 Status: {fine_tune_response.status.value}")
            print(f"🎯 Base model: {fine_tune_response.model}")
            
            # Check job status
            status_request = JobStatusRequest(job_id=fine_tune_response.job_id)
            status_response = await provider.job_status(status_request)
            
            print(f"\n📈 Job status: {status_response.status.value}")
            if status_response.progress:
                print(f"⏳ Progress: {status_response.progress * 100:.1f}%")
            if status_response.error_message:
                print(f"❌ Error: {status_response.error_message}")
            if status_response.result:
                print(f"🎉 Result: {status_response.result}")
                
    except ProviderUnavailableError:
        print("❌ No fine-tuning providers are available.")
    except Exception as e:
        print(f"⚠️ Fine-tuning example failed (this is normal for demo): {str(e)}")


async def example_provider_capabilities():
    """Example of checking provider capabilities."""
    print("\n🔍 Checking provider capabilities...")
    
    # Check feature flags
    flags = get_feature_flags()
    print("Feature flags:")
    for flag, enabled in flags.items():
        status = "✅" if enabled else "❌"
        print(f"  {status} {flag}: {enabled}")
    
    # Check individual provider availability
    print("\nProvider availability:")
    for provider_type in [ProviderType.OPENAI, ProviderType.VERTEX_GEMINI, ProviderType.BEDROCK_ANTHROPIC]:
        is_available = await is_provider_available(provider_type)
        status = "✅" if is_available else "❌"
        print(f"  {status} {provider_type.value}: {is_available}")
    
    # Get available models for each provider
    available_providers = await get_available_providers()
    for provider_type in available_providers:
        if provider_type == ProviderType.AUTO:
            continue
            
        try:
            async with await get_provider(provider_type) as provider:
                models = await provider.get_available_models()
                print(f"\n📋 {provider_type.value.upper()} available models:")
                for capability, model_list in models.items():
                    print(f"  {capability}: {', '.join(model_list[:3])}{'...' if len(model_list) > 3 else ''}")
                    
        except ProviderUnavailableError:
            pass


async def example_error_handling():
    """Example of error handling with graceful degradation."""
    print("\n⚠️ Error handling and graceful degradation...")
    
    # Try to use a specific provider that might not be available
    for provider_type in [ProviderType.OPENAI, ProviderType.VERTEX_GEMINI, ProviderType.BEDROCK_ANTHROPIC]:
        try:
            print(f"\n🧪 Testing {provider_type.value}...")
            async with await get_provider(provider_type) as provider:
                request = GenerateRequest(
                    messages=[{"role": "user", "content": "Hello!"}],
                    model="gpt-4",
                    max_tokens=10,
                )
                
                response = await provider.generate(request)
                print(f"✅ {provider_type.value} responded: {response.content}")
                
        except ProviderUnavailableError as e:
            print(f"⏭️ {provider_type.value} not available: {e.message}")
            print("   Gracefully continuing with other providers...")
            
        except Exception as e:
            print(f"❌ Unexpected error with {provider_type.value}: {str(e)}")


async def main():
    """Main example function."""
    print("🚀 AIVO Model Providers Library Examples")
    print("=" * 50)
    
    # Set up environment variables info
    env_vars = {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "GOOGLE_APPLICATION_CREDENTIALS": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
        "GOOGLE_CLOUD_PROJECT": bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
        "AWS_ACCESS_KEY_ID": bool(os.getenv("AWS_ACCESS_KEY_ID")),
        "AWS_SECRET_ACCESS_KEY": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
    }
    
    print("🔧 Environment configuration:")
    for var, is_set in env_vars.items():
        status = "✅" if is_set else "❌"
        print(f"  {status} {var}: {'Set' if is_set else 'Not set'}")
    
    # Run examples
    await example_provider_capabilities()
    await example_auto_provider_selection()
    await example_embeddings()
    await example_content_moderation()
    await example_fine_tuning()
    await example_provider_comparison()
    await example_error_handling()
    
    print("\n✨ Examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
