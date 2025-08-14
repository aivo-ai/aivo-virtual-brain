# Model Providers Library

A unified interface for multi-cloud AI model providers supporting text generation, embeddings, content moderation, and fine-tuning across OpenAI, Google Vertex AI, and AWS Bedrock.

## Features

- **Unified Interface**: Single API for all provider operations
- **Multi-Cloud Support**: OpenAI, Vertex AI (Gemini), Bedrock (Anthropic Haiku)
- **Feature Flags**: Graceful degradation when provider credentials unavailable
- **Async/Await**: Full async support with proper resource management
- **Type Safety**: Complete Pydantic models for all operations
- **Comprehensive Testing**: Mock testing for all providers and error scenarios

## Providers

### OpenAI Provider

- **Models**: GPT-4, GPT-3.5-turbo, text-embedding-3-small/large
- **Features**: Text generation, embeddings, content moderation, fine-tuning
- **Fine-tuning**: Full OpenAI fine-tuning API support

### Vertex AI Provider (Gemini)

- **Models**: Gemini Pro, Gemini Pro Vision, Text Embedding 004
- **Features**: Text generation, embeddings, content moderation via safety settings
- **Fine-tuning**: Vertex AI tuning API (not direct Gemini API)

### Bedrock Provider (Anthropic)

- **Models**: Claude 3 Haiku, Claude 3 Sonnet, Titan Embeddings
- **Features**: Text generation, embeddings, content moderation
- **Fine-tuning**: Bedrock custom model fine-tuning

## Quick Start

```python
from aivo_model_providers import get_provider, ProviderType

# Auto-detect available provider
provider = await get_provider(ProviderType.AUTO)

# Generate text
response = await provider.generate(
    messages=[{"role": "user", "content": "Hello, world!"}],
    model="gpt-4",
    max_tokens=100
)

# Create embeddings
embeddings = await provider.embed(
    texts=["Hello, world!"],
    model="text-embedding-3-small"
)

# Content moderation
moderation = await provider.moderate(
    content="This is some text to moderate"
)
```

## Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=your_openai_key

# Vertex AI
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your_project_id

# AWS Bedrock
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

## Installation

```bash
pip install -e .
```

## Development

```bash
# Install with test dependencies
pip install -e ".[test]"

# Run tests
pytest

# Run with coverage
pytest --cov=aivo_model_providers
```

## Architecture

The library uses an abstract base class `Provider` with concrete implementations for each cloud provider. Feature flags enable graceful degradation when provider credentials are unavailable, returning 503 Service Unavailable responses.

All operations support async/await patterns and include comprehensive error handling with provider-specific error types mapped to common exceptions.
