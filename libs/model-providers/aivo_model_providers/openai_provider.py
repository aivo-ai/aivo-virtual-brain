"""
OpenAI provider implementation.
"""

import os
from typing import Dict, List, Optional, Any
import httpx
from openai import AsyncOpenAI
from openai.types import Moderation, CreateEmbeddingResponse
from openai.types.chat import ChatCompletion

from .base import (
    Provider,
    ProviderType,
    GenerateRequest,
    GenerateResponse,
    EmbedRequest,
    EmbedResponse,
    ModerateRequest,
    ModerateResponse,
    ModerationResult,
    ModerationCategory,
    FineTuneRequest,
    FineTuneResponse,
    JobStatusRequest,
    JobStatusResponse,
    JobStatus,
    ProviderError,
    ProviderUnavailableError,
    ProviderConfigError,
    ProviderRateLimitError,
    ProviderQuotaError,
)


class OpenAIProvider(Provider):
    """OpenAI provider implementation."""

    def __init__(self):
        super().__init__(ProviderType.OPENAI)
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client: Optional[AsyncOpenAI] = None

    async def _ensure_client(self) -> AsyncOpenAI:
        """Ensure OpenAI client is initialized."""
        if not self.api_key:
            raise ProviderUnavailableError(
                "OpenAI API key not found in environment variables",
                self.provider_type.value
            )
        
        if not self.client:
            self.client = AsyncOpenAI(api_key=self.api_key)
        
        return self.client

    async def is_available(self) -> bool:
        """Check if OpenAI provider is available."""
        try:
            if not self.api_key:
                return False
            
            client = await self._ensure_client()
            # Test with a simple models list call
            await client.models.list()
            return True
        except Exception as e:
            self.logger.warning("OpenAI provider unavailable", error=str(e))
            return False

    def _map_openai_error(self, error: Exception) -> ProviderError:
        """Map OpenAI errors to provider errors."""
        error_msg = str(error)
        
        if "rate_limit" in error_msg.lower():
            return ProviderRateLimitError(
                f"OpenAI rate limit exceeded: {error_msg}",
                self.provider_type.value
            )
        elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
            return ProviderQuotaError(
                f"OpenAI quota exceeded: {error_msg}",
                self.provider_type.value
            )
        elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            return ProviderConfigError(
                f"OpenAI authentication error: {error_msg}",
                self.provider_type.value
            )
        else:
            return ProviderError(
                f"OpenAI API error: {error_msg}",
                self.provider_type.value
            )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate text using OpenAI models."""
        try:
            client = await self._ensure_client()
            
            # Prepare chat completion request
            completion_kwargs = {
                "model": request.model,
                "messages": request.messages,
                "stream": request.stream,
            }
            
            # Add optional parameters
            if request.max_tokens is not None:
                completion_kwargs["max_tokens"] = request.max_tokens
            if request.temperature is not None:
                completion_kwargs["temperature"] = request.temperature
            if request.top_p is not None:
                completion_kwargs["top_p"] = request.top_p
            if request.frequency_penalty is not None:
                completion_kwargs["frequency_penalty"] = request.frequency_penalty
            if request.presence_penalty is not None:
                completion_kwargs["presence_penalty"] = request.presence_penalty
            if request.stop is not None:
                completion_kwargs["stop"] = request.stop

            completion: ChatCompletion = await client.chat.completions.create(**completion_kwargs)
            
            # Extract response data
            choice = completion.choices[0]
            content = choice.message.content or ""
            
            usage = {
                "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
                "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
                "total_tokens": completion.usage.total_tokens if completion.usage else 0,
            }

            return GenerateResponse(
                content=content,
                model=completion.model,
                usage=usage,
                finish_reason=choice.finish_reason,
                provider=self.provider_type.value,
                metadata={
                    "completion_id": completion.id,
                    "created": completion.created,
                }
            )

        except Exception as e:
            raise self._map_openai_error(e)

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Create embeddings using OpenAI models."""
        try:
            client = await self._ensure_client()
            
            embedding_kwargs = {
                "model": request.model,
                "input": request.texts,
            }
            
            if request.dimensions is not None:
                embedding_kwargs["dimensions"] = request.dimensions

            response: CreateEmbeddingResponse = await client.embeddings.create(**embedding_kwargs)
            
            embeddings = [embedding.embedding for embedding in response.data]
            
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            return EmbedResponse(
                embeddings=embeddings,
                model=response.model,
                usage=usage,
                provider=self.provider_type.value,
                metadata={
                    "object": response.object,
                }
            )

        except Exception as e:
            raise self._map_openai_error(e)

    def _map_moderation_categories(self, categories: Dict[str, bool], scores: Dict[str, float]) -> List[ModerationResult]:
        """Map OpenAI moderation categories to our standard format."""
        category_mapping = {
            "hate": ModerationCategory.HATE,
            "hate/threatening": ModerationCategory.HATE,
            "harassment": ModerationCategory.HARASSMENT,
            "harassment/threatening": ModerationCategory.HARASSMENT,
            "self-harm": ModerationCategory.SELF_HARM,
            "self-harm/intent": ModerationCategory.SELF_HARM,
            "self-harm/instructions": ModerationCategory.SELF_HARM,
            "sexual": ModerationCategory.SEXUAL,
            "sexual/minors": ModerationCategory.SEXUAL,
            "violence": ModerationCategory.VIOLENCE,
            "violence/graphic": ModerationCategory.VIOLENCE,
        }
        
        results = []
        for openai_category, flagged in categories.items():
            if openai_category in category_mapping:
                category = category_mapping[openai_category]
                score = scores.get(openai_category, 0.0)
                results.append(ModerationResult(
                    category=category,
                    score=score,
                    flagged=flagged
                ))
        
        return results

    async def moderate(self, request: ModerateRequest) -> ModerateResponse:
        """Moderate content using OpenAI moderation."""
        try:
            client = await self._ensure_client()
            
            moderation: Moderation = await client.moderations.create(
                input=request.content
            )
            
            result = moderation.results[0]
            moderation_results = self._map_moderation_categories(
                result.categories.model_dump(),
                result.category_scores.model_dump()
            )

            return ModerateResponse(
                flagged=result.flagged,
                results=moderation_results,
                provider=self.provider_type.value,
                metadata={
                    "moderation_id": moderation.id,
                    "model": moderation.model,
                }
            )

        except Exception as e:
            raise self._map_openai_error(e)

    def _map_job_status(self, openai_status: str) -> JobStatus:
        """Map OpenAI fine-tuning status to our standard format."""
        status_mapping = {
            "validating_files": JobStatus.PENDING,
            "queued": JobStatus.PENDING,
            "running": JobStatus.RUNNING,
            "succeeded": JobStatus.SUCCEEDED,
            "failed": JobStatus.FAILED,
            "cancelled": JobStatus.CANCELLED,
        }
        return status_mapping.get(openai_status, JobStatus.PENDING)

    async def fine_tune(self, request: FineTuneRequest) -> FineTuneResponse:
        """Start a fine-tuning job with OpenAI."""
        try:
            client = await self._ensure_client()
            
            # Upload training file if it's a URL
            # Note: In practice, you'd need to download and upload the file
            # This is simplified for the example
            
            fine_tune_kwargs = {
                "training_file": request.training_file_url,  # Assuming file ID format
                "model": request.model,
            }
            
            if request.validation_file_url:
                fine_tune_kwargs["validation_file"] = request.validation_file_url
            
            if request.hyperparameters:
                fine_tune_kwargs["hyperparameters"] = request.hyperparameters
            
            if request.suffix:
                fine_tune_kwargs["suffix"] = request.suffix

            job = await client.fine_tuning.jobs.create(**fine_tune_kwargs)
            
            return FineTuneResponse(
                job_id=job.id,
                status=self._map_job_status(job.status),
                model=job.model,
                estimated_completion_time=job.estimated_finish,
                provider=self.provider_type.value,
                metadata={
                    "object": job.object,
                    "created_at": job.created_at,
                    "organization_id": job.organization_id,
                }
            )

        except Exception as e:
            raise self._map_openai_error(e)

    async def job_status(self, request: JobStatusRequest) -> JobStatusResponse:
        """Get fine-tuning job status from OpenAI."""
        try:
            client = await self._ensure_client()
            
            job = await client.fine_tuning.jobs.retrieve(request.job_id)
            
            result = None
            if job.status == "succeeded" and job.fine_tuned_model:
                result = {
                    "fine_tuned_model": job.fine_tuned_model,
                    "result_files": job.result_files,
                }

            return JobStatusResponse(
                job_id=job.id,
                status=self._map_job_status(job.status),
                error_message=job.error.message if job.error else None,
                result=result,
                created_at=str(job.created_at) if job.created_at else None,
                completed_at=str(job.finished_at) if job.finished_at else None,
                provider=self.provider_type.value,
                metadata={
                    "object": job.object,
                    "organization_id": job.organization_id,
                    "training_file": job.training_file,
                    "validation_file": job.validation_file,
                }
            )

        except Exception as e:
            raise self._map_openai_error(e)

    async def get_available_models(self) -> Dict[str, List[str]]:
        """Get available OpenAI models by capability."""
        try:
            client = await self._ensure_client()
            models_response = await client.models.list()
            
            # Categorize models by capability
            generate_models = []
            embed_models = []
            moderate_models = ["text-moderation-latest", "text-moderation-stable"]
            
            for model in models_response.data:
                model_id = model.id
                
                # Chat/completion models
                if any(prefix in model_id for prefix in ["gpt-4", "gpt-3.5", "gpt-"]):
                    generate_models.append(model_id)
                
                # Embedding models
                elif "embedding" in model_id or "ada" in model_id:
                    embed_models.append(model_id)

            return {
                "generate": generate_models,
                "embed": embed_models,
                "moderate": moderate_models,
            }

        except Exception as e:
            self.logger.warning("Failed to fetch OpenAI models", error=str(e))
            # Return known model defaults
            return {
                "generate": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                "embed": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
                "moderate": ["text-moderation-latest", "text-moderation-stable"],
            }

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up OpenAI client."""
        if self.client:
            await self.client.close()
