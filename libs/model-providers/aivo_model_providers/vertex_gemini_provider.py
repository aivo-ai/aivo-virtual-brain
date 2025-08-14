"""
Vertex AI (Gemini) provider implementation.
"""

import os
import json
from typing import Dict, List, Optional, Any
import httpx
from google.cloud import aiplatform
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

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


class VertexGeminiProvider(Provider):
    """Vertex AI (Gemini) provider implementation."""

    def __init__(self):
        super().__init__(ProviderType.VERTEX_GEMINI)
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None

    async def _get_access_token(self) -> str:
        """Get Google Cloud access token."""
        if self._access_token:
            return self._access_token
        
        try:
            credentials, project = default()
            credentials.refresh(httpx.Request())
            self._access_token = credentials.token
            return self._access_token
        except DefaultCredentialsError as e:
            raise ProviderUnavailableError(
                f"Vertex AI credentials not found: {str(e)}",
                self.provider_type.value
            )

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if not self.client:
            self.client = httpx.AsyncClient()
        return self.client

    async def is_available(self) -> bool:
        """Check if Vertex AI provider is available."""
        try:
            if not self.project_id:
                return False
            
            # Try to get access token
            await self._get_access_token()
            return True
        except Exception as e:
            self.logger.warning("Vertex AI provider unavailable", error=str(e))
            return False

    def _map_vertex_error(self, error: Exception, response: Optional[httpx.Response] = None) -> ProviderError:
        """Map Vertex AI errors to provider errors."""
        error_msg = str(error)
        
        if response:
            if response.status_code == 429:
                return ProviderRateLimitError(
                    f"Vertex AI rate limit exceeded: {error_msg}",
                    self.provider_type.value
                )
            elif response.status_code == 403:
                return ProviderQuotaError(
                    f"Vertex AI quota exceeded: {error_msg}",
                    self.provider_type.value
                )
            elif response.status_code == 401:
                return ProviderConfigError(
                    f"Vertex AI authentication error: {error_msg}",
                    self.provider_type.value
                )
        
        if "quota" in error_msg.lower():
            return ProviderQuotaError(
                f"Vertex AI quota exceeded: {error_msg}",
                self.provider_type.value
            )
        elif "permission" in error_msg.lower() or "credentials" in error_msg.lower():
            return ProviderConfigError(
                f"Vertex AI configuration error: {error_msg}",
                self.provider_type.value
            )
        else:
            return ProviderError(
                f"Vertex AI error: {error_msg}",
                self.provider_type.value
            )

    def _convert_messages_to_gemini(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Convert chat messages to Gemini format."""
        gemini_messages = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Map roles to Gemini format
            if role == "system":
                # Gemini doesn't have system role, prepend to user message
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": f"System: {content}"}]
                })
            elif role == "user":
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                gemini_messages.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
        
        return gemini_messages

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate text using Vertex AI Gemini models."""
        try:
            client = await self._ensure_client()
            access_token = await self._get_access_token()
            
            # Convert messages to Gemini format
            contents = self._convert_messages_to_gemini(request.messages)
            
            # Prepare generation config
            generation_config = {}
            if request.max_tokens:
                generation_config["maxOutputTokens"] = request.max_tokens
            if request.temperature is not None:
                generation_config["temperature"] = request.temperature
            if request.top_p is not None:
                generation_config["topP"] = request.top_p
            if request.stop:
                stop_sequences = request.stop if isinstance(request.stop, list) else [request.stop]
                generation_config["stopSequences"] = stop_sequences

            # Prepare request payload
            payload = {
                "contents": contents,
                "generationConfig": generation_config,
            }

            # API endpoint
            endpoint = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{request.model}:generateContent"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = await client.post(endpoint, json=payload, headers=headers)
            
            if response.status_code != 200:
                raise self._map_vertex_error(Exception(f"HTTP {response.status_code}: {response.text}"), response)

            data = response.json()
            
            # Extract content
            candidates = data.get("candidates", [])
            if not candidates:
                raise ProviderError("No candidates returned", self.provider_type.value)
            
            candidate = candidates[0]
            content_parts = candidate.get("content", {}).get("parts", [])
            content = ""
            if content_parts:
                content = content_parts[0].get("text", "")

            # Extract usage metadata
            usage_metadata = data.get("usageMetadata", {})
            usage = {
                "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                "total_tokens": usage_metadata.get("totalTokenCount", 0),
            }

            return GenerateResponse(
                content=content,
                model=request.model,
                usage=usage,
                finish_reason=candidate.get("finishReason", "stop"),
                provider=self.provider_type.value,
                metadata={
                    "safety_ratings": candidate.get("safetyRatings", []),
                    "citation_metadata": candidate.get("citationMetadata"),
                }
            )

        except ProviderError:
            raise
        except Exception as e:
            raise self._map_vertex_error(e)

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Create embeddings using Vertex AI embedding models."""
        try:
            client = await self._ensure_client()
            access_token = await self._get_access_token()
            
            # Prepare instances for embedding
            instances = [{"content": text} for text in request.texts]
            
            payload = {
                "instances": instances,
            }
            
            # API endpoint for embeddings
            endpoint = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{request.model}:predict"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = await client.post(endpoint, json=payload, headers=headers)
            
            if response.status_code != 200:
                raise self._map_vertex_error(Exception(f"HTTP {response.status_code}: {response.text}"), response)

            data = response.json()
            
            # Extract embeddings
            predictions = data.get("predictions", [])
            embeddings = []
            
            for prediction in predictions:
                # Different models may have different response formats
                if "embeddings" in prediction:
                    embeddings.append(prediction["embeddings"]["values"])
                elif "values" in prediction:
                    embeddings.append(prediction["values"])
                else:
                    # Fallback for other formats
                    embeddings.append(prediction.get("embedding", []))

            # Estimate token usage (Vertex doesn't always provide this)
            estimated_tokens = sum(len(text.split()) for text in request.texts)
            usage = {
                "prompt_tokens": estimated_tokens,
                "total_tokens": estimated_tokens,
            }

            return EmbedResponse(
                embeddings=embeddings,
                model=request.model,
                usage=usage,
                provider=self.provider_type.value,
                metadata={
                    "predictions_count": len(predictions),
                }
            )

        except ProviderError:
            raise
        except Exception as e:
            raise self._map_vertex_error(e)

    def _evaluate_safety_ratings(self, safety_ratings: List[Dict[str, Any]]) -> List[ModerationResult]:
        """Convert Vertex AI safety ratings to moderation results."""
        category_mapping = {
            "HARM_CATEGORY_HATE_SPEECH": ModerationCategory.HATE,
            "HARM_CATEGORY_DANGEROUS_CONTENT": ModerationCategory.VIOLENCE,
            "HARM_CATEGORY_HARASSMENT": ModerationCategory.HARASSMENT,
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": ModerationCategory.SEXUAL,
        }
        
        # Threshold mapping (Vertex uses LOW, MEDIUM, HIGH, NEGLIGIBLE)
        threshold_scores = {
            "NEGLIGIBLE": 0.1,
            "LOW": 0.3,
            "MEDIUM": 0.6,
            "HIGH": 0.9,
        }
        
        results = []
        for rating in safety_ratings:
            category_name = rating.get("category", "")
            probability = rating.get("probability", "NEGLIGIBLE")
            
            if category_name in category_mapping:
                category = category_mapping[category_name]
                score = threshold_scores.get(probability, 0.0)
                flagged = probability in ["MEDIUM", "HIGH"]
                
                results.append(ModerationResult(
                    category=category,
                    score=score,
                    flagged=flagged
                ))
        
        return results

    async def moderate(self, request: ModerateRequest) -> ModerateResponse:
        """Moderate content using Vertex AI safety features."""
        try:
            # Generate content with safety settings to get safety ratings
            generate_request = GenerateRequest(
                messages=[{"role": "user", "content": request.content}],
                model="gemini-pro",
                max_tokens=1,  # Minimal generation just to get safety ratings
            )
            
            generate_response = await self.generate(generate_request)
            
            # Extract safety ratings from metadata
            safety_ratings = generate_response.metadata.get("safety_ratings", [])
            moderation_results = self._evaluate_safety_ratings(safety_ratings)
            
            # Check if any category was flagged
            flagged = any(result.flagged for result in moderation_results)

            return ModerateResponse(
                flagged=flagged,
                results=moderation_results,
                provider=self.provider_type.value,
                metadata={
                    "safety_ratings": safety_ratings,
                }
            )

        except ProviderError:
            raise
        except Exception as e:
            raise self._map_vertex_error(e)

    def _map_tuning_job_status(self, state: str) -> JobStatus:
        """Map Vertex AI tuning job state to our standard format."""
        status_mapping = {
            "JOB_STATE_PENDING": JobStatus.PENDING,
            "JOB_STATE_RUNNING": JobStatus.RUNNING,
            "JOB_STATE_SUCCEEDED": JobStatus.SUCCEEDED,
            "JOB_STATE_FAILED": JobStatus.FAILED,
            "JOB_STATE_CANCELLING": JobStatus.CANCELLED,
            "JOB_STATE_CANCELLED": JobStatus.CANCELLED,
        }
        return status_mapping.get(state, JobStatus.PENDING)

    async def fine_tune(self, request: FineTuneRequest) -> FineTuneResponse:
        """Start a fine-tuning job with Vertex AI."""
        try:
            client = await self._ensure_client()
            access_token = await self._get_access_token()
            
            # Vertex AI fine-tuning requires a different approach
            # This is a simplified version - actual implementation would need
            # to handle dataset preparation, training pipeline creation, etc.
            
            # Prepare tuning job
            tuning_job = {
                "displayName": f"tune-{request.model}-{request.suffix or 'custom'}",
                "baseModel": request.model,
                "tunedModelDisplayName": f"{request.model}-{request.suffix or 'tuned'}",
                "trainingTask": {
                    "inputs": {
                        "training_data": request.training_file_url,
                    }
                }
            }
            
            if request.validation_file_url:
                tuning_job["trainingTask"]["inputs"]["validation_data"] = request.validation_file_url
            
            if request.hyperparameters:
                tuning_job["trainingTask"]["hyperParameters"] = request.hyperparameters

            # API endpoint for tuning jobs
            endpoint = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/tuningJobs"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = await client.post(endpoint, json=tuning_job, headers=headers)
            
            if response.status_code != 200:
                raise self._map_vertex_error(Exception(f"HTTP {response.status_code}: {response.text}"), response)

            data = response.json()
            
            job_id = data.get("name", "").split("/")[-1]  # Extract job ID from resource name
            
            return FineTuneResponse(
                job_id=job_id,
                status=self._map_tuning_job_status(data.get("state", "JOB_STATE_PENDING")),
                model=request.model,
                estimated_completion_time=None,  # Vertex doesn't provide this
                provider=self.provider_type.value,
                metadata={
                    "resource_name": data.get("name"),
                    "display_name": data.get("displayName"),
                    "create_time": data.get("createTime"),
                }
            )

        except ProviderError:
            raise
        except Exception as e:
            raise self._map_vertex_error(e)

    async def job_status(self, request: JobStatusRequest) -> JobStatusResponse:
        """Get fine-tuning job status from Vertex AI."""
        try:
            client = await self._ensure_client()
            access_token = await self._get_access_token()
            
            # API endpoint for getting tuning job
            endpoint = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/tuningJobs/{request.job_id}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
            }

            response = await client.get(endpoint, headers=headers)
            
            if response.status_code != 200:
                raise self._map_vertex_error(Exception(f"HTTP {response.status_code}: {response.text}"), response)

            data = response.json()
            
            result = None
            if data.get("state") == "JOB_STATE_SUCCEEDED":
                result = {
                    "tuned_model": data.get("tunedModel"),
                    "tuned_model_display_name": data.get("tunedModelDisplayName"),
                }

            return JobStatusResponse(
                job_id=request.job_id,
                status=self._map_tuning_job_status(data.get("state", "JOB_STATE_PENDING")),
                error_message=data.get("error", {}).get("message") if data.get("error") else None,
                result=result,
                created_at=data.get("createTime"),
                completed_at=data.get("endTime"),
                provider=self.provider_type.value,
                metadata={
                    "resource_name": data.get("name"),
                    "display_name": data.get("displayName"),
                    "base_model": data.get("baseModel"),
                }
            )

        except ProviderError:
            raise
        except Exception as e:
            raise self._map_vertex_error(e)

    async def get_available_models(self) -> Dict[str, List[str]]:
        """Get available Vertex AI models by capability."""
        # Return known Vertex AI models
        # In practice, you could query the API for available models
        return {
            "generate": [
                "gemini-pro",
                "gemini-pro-vision",
                "gemini-1.0-pro",
                "gemini-1.5-pro",
                "text-bison",
                "text-bison@002",
                "code-bison",
                "code-bison@002",
            ],
            "embed": [
                "textembedding-gecko",
                "textembedding-gecko@003",
                "text-embedding-004",
                "text-multilingual-embedding-002",
            ],
            "moderate": [
                "gemini-pro",  # Uses safety ratings
            ],
        }

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up HTTP client."""
        if self.client:
            await self.client.aclose()
