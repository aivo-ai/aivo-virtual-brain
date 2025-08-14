"""
AWS Bedrock (Anthropic) provider implementation.
"""

import os
import json
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

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


class BedrockAnthropicProvider(Provider):
    """AWS Bedrock (Anthropic) provider implementation."""

    def __init__(self):
        super().__init__(ProviderType.BEDROCK_ANTHROPIC)
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.session_token = os.getenv("AWS_SESSION_TOKEN")
        self.bedrock_client: Optional[boto3.client] = None
        self.bedrock_runtime_client: Optional[boto3.client] = None

    async def _ensure_clients(self) -> tuple[boto3.client, boto3.client]:
        """Ensure Bedrock clients are initialized."""
        if not self.access_key_id or not self.secret_access_key:
            raise ProviderUnavailableError(
                "AWS credentials not found in environment variables",
                self.provider_type.value
            )
        
        if not self.bedrock_client:
            session = boto3.Session(
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                aws_session_token=self.session_token,
                region_name=self.region
            )
            
            self.bedrock_client = session.client('bedrock')
            self.bedrock_runtime_client = session.client('bedrock-runtime')
        
        return self.bedrock_client, self.bedrock_runtime_client

    async def is_available(self) -> bool:
        """Check if Bedrock provider is available."""
        try:
            if not self.access_key_id or not self.secret_access_key:
                return False
            
            bedrock_client, _ = await self._ensure_clients()
            # Test with a simple list models call
            bedrock_client.list_foundation_models()
            return True
        except Exception as e:
            self.logger.warning("Bedrock provider unavailable", error=str(e))
            return False

    def _map_bedrock_error(self, error: Exception) -> ProviderError:
        """Map Bedrock errors to provider errors."""
        error_msg = str(error)
        
        if isinstance(error, ClientError):
            error_code = error.response.get("Error", {}).get("Code", "")
            
            if error_code in ["Throttling", "ThrottlingException"]:
                return ProviderRateLimitError(
                    f"Bedrock rate limit exceeded: {error_msg}",
                    self.provider_type.value
                )
            elif error_code in ["ServiceQuotaExceededException", "LimitExceededException"]:
                return ProviderQuotaError(
                    f"Bedrock quota exceeded: {error_msg}",
                    self.provider_type.value
                )
            elif error_code in ["UnauthorizedOperation", "AccessDenied", "InvalidUserID.NotFound"]:
                return ProviderConfigError(
                    f"Bedrock authentication error: {error_msg}",
                    self.provider_type.value
                )
        elif isinstance(error, NoCredentialsError):
            return ProviderUnavailableError(
                f"Bedrock credentials not found: {error_msg}",
                self.provider_type.value
            )
        
        return ProviderError(
            f"Bedrock error: {error_msg}",
            self.provider_type.value
        )

    def _convert_messages_to_anthropic(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to Anthropic prompt format."""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Ensure prompt ends with "Assistant:" for completion
        prompt = "\n\n".join(prompt_parts)
        if not prompt.endswith("Assistant:"):
            prompt += "\n\nAssistant:"
        
        return prompt

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate text using Bedrock Anthropic models."""
        try:
            _, bedrock_runtime = await self._ensure_clients()
            
            # Convert messages to Anthropic format
            prompt = self._convert_messages_to_anthropic(request.messages)
            
            # Prepare request body
            body = {
                "prompt": prompt,
                "max_tokens_to_sample": request.max_tokens or 100,
            }
            
            # Add optional parameters
            if request.temperature is not None:
                body["temperature"] = request.temperature
            if request.top_p is not None:
                body["top_p"] = request.top_p
            if request.stop:
                stop_sequences = request.stop if isinstance(request.stop, list) else [request.stop]
                body["stop_sequences"] = stop_sequences

            response = bedrock_runtime.invoke_model(
                modelId=request.model,
                body=json.dumps(body),
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            
            # Extract content
            content = response_body.get("completion", "")
            
            # Estimate token usage (Bedrock doesn't always provide exact counts)
            prompt_tokens = len(prompt.split()) * 1.3  # Rough approximation
            completion_tokens = len(content.split()) * 1.3
            
            usage = {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
                "total_tokens": int(prompt_tokens + completion_tokens),
            }

            return GenerateResponse(
                content=content.strip(),
                model=request.model,
                usage=usage,
                finish_reason=response_body.get("stop_reason", "stop"),
                provider=self.provider_type.value,
                metadata={
                    "response_metadata": response.get('ResponseMetadata', {}),
                }
            )

        except Exception as e:
            raise self._map_bedrock_error(e)

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Create embeddings using Bedrock embedding models."""
        try:
            _, bedrock_runtime = await self._ensure_clients()
            
            embeddings = []
            total_tokens = 0
            
            for text in request.texts:
                body = {
                    "inputText": text,
                }
                
                if request.dimensions:
                    body["dimensions"] = request.dimensions

                response = bedrock_runtime.invoke_model(
                    modelId=request.model,
                    body=json.dumps(body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                response_body = json.loads(response['body'].read())
                
                # Extract embedding based on model
                if "titan" in request.model.lower():
                    embedding = response_body.get("embedding", [])
                    token_count = response_body.get("inputTextTokenCount", len(text.split()))
                else:
                    # Handle other embedding model formats
                    embedding = response_body.get("embeddings", [response_body.get("embedding", [])])[0]
                    token_count = len(text.split())  # Estimate
                
                embeddings.append(embedding)
                total_tokens += token_count

            usage = {
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens,
            }

            return EmbedResponse(
                embeddings=embeddings,
                model=request.model,
                usage=usage,
                provider=self.provider_type.value,
                metadata={
                    "embedding_count": len(embeddings),
                }
            )

        except Exception as e:
            raise self._map_bedrock_error(e)

    def _analyze_content_safety(self, content: str) -> List[ModerationResult]:
        """Basic content safety analysis (simplified implementation)."""
        # This is a simplified implementation
        # In practice, you might use AWS Comprehend or other safety services
        
        results = []
        content_lower = content.lower()
        
        # Simple keyword-based detection (not production-ready)
        safety_checks = {
            ModerationCategory.HATE: ["hate", "racist", "discrimination"],
            ModerationCategory.HARASSMENT: ["harass", "bully", "threaten"],
            ModerationCategory.VIOLENCE: ["violence", "kill", "harm", "attack"],
            ModerationCategory.SEXUAL: ["sexual", "explicit", "inappropriate"],
        }
        
        for category, keywords in safety_checks.items():
            flagged = any(keyword in content_lower for keyword in keywords)
            score = 0.8 if flagged else 0.1
            
            results.append(ModerationResult(
                category=category,
                score=score,
                flagged=flagged
            ))
        
        return results

    async def moderate(self, request: ModerateRequest) -> ModerateResponse:
        """Moderate content using basic safety analysis."""
        try:
            # Bedrock doesn't have a built-in moderation API like OpenAI
            # This is a simplified implementation using basic content analysis
            
            moderation_results = self._analyze_content_safety(request.content)
            flagged = any(result.flagged for result in moderation_results)

            return ModerateResponse(
                flagged=flagged,
                results=moderation_results,
                provider=self.provider_type.value,
                metadata={
                    "analysis_method": "basic_keyword_detection",
                    "note": "This is a simplified moderation implementation",
                }
            )

        except Exception as e:
            raise self._map_bedrock_error(e)

    def _map_model_customization_status(self, status: str) -> JobStatus:
        """Map Bedrock model customization status to our standard format."""
        status_mapping = {
            "InProgress": JobStatus.RUNNING,
            "Completed": JobStatus.SUCCEEDED,
            "Failed": JobStatus.FAILED,
            "Stopping": JobStatus.CANCELLED,
            "Stopped": JobStatus.CANCELLED,
        }
        return status_mapping.get(status, JobStatus.PENDING)

    async def fine_tune(self, request: FineTuneRequest) -> FineTuneResponse:
        """Start a fine-tuning job with Bedrock."""
        try:
            bedrock_client, _ = await self._ensure_clients()
            
            # Prepare model customization job
            customization_config = {
                "modelName": f"{request.model}-{request.suffix or 'custom'}",
                "roleArn": os.getenv("AWS_BEDROCK_ROLE_ARN"),  # Required for Bedrock
                "baseModelIdentifier": request.model,
                "trainingDataConfig": {
                    "s3Uri": request.training_file_url,
                },
            }
            
            if request.validation_file_url:
                customization_config["validationDataConfig"] = {
                    "s3Uri": request.validation_file_url,
                }
            
            if request.hyperparameters:
                customization_config["hyperParameters"] = request.hyperparameters

            response = bedrock_client.create_model_customization_job(**customization_config)
            
            job_arn = response.get("jobArn", "")
            job_id = job_arn.split("/")[-1] if job_arn else ""
            
            return FineTuneResponse(
                job_id=job_id,
                status=JobStatus.PENDING,
                model=request.model,
                estimated_completion_time=None,  # Bedrock doesn't provide this
                provider=self.provider_type.value,
                metadata={
                    "job_arn": job_arn,
                    "model_name": customization_config["modelName"],
                }
            )

        except Exception as e:
            raise self._map_bedrock_error(e)

    async def job_status(self, request: JobStatusRequest) -> JobStatusResponse:
        """Get fine-tuning job status from Bedrock."""
        try:
            bedrock_client, _ = await self._ensure_clients()
            
            # Get model customization job details
            response = bedrock_client.get_model_customization_job(
                jobIdentifier=request.job_id
            )
            
            job_details = response
            status = job_details.get("status", "InProgress")
            
            result = None
            if status == "Completed":
                result = {
                    "custom_model_arn": job_details.get("outputModelArn"),
                    "custom_model_name": job_details.get("outputModelName"),
                }

            return JobStatusResponse(
                job_id=request.job_id,
                status=self._map_model_customization_status(status),
                error_message=job_details.get("failureMessage"),
                result=result,
                created_at=str(job_details.get("creationTime")) if job_details.get("creationTime") else None,
                completed_at=str(job_details.get("endTime")) if job_details.get("endTime") else None,
                provider=self.provider_type.value,
                metadata={
                    "job_arn": job_details.get("jobArn"),
                    "model_name": job_details.get("jobName"),
                    "base_model": job_details.get("baseModelArn"),
                }
            )

        except Exception as e:
            raise self._map_bedrock_error(e)

    async def get_available_models(self) -> Dict[str, List[str]]:
        """Get available Bedrock models by capability."""
        try:
            bedrock_client, _ = await self._ensure_clients()
            response = bedrock_client.list_foundation_models()
            
            generate_models = []
            embed_models = []
            
            for model in response.get("modelSummaries", []):
                model_id = model.get("modelId", "")
                modalities = model.get("inputModalities", [])
                
                # Categorize by model type and capabilities
                if "anthropic" in model_id.lower() and "TEXT" in modalities:
                    generate_models.append(model_id)
                elif "titan" in model_id.lower() and "embed" in model_id.lower():
                    embed_models.append(model_id)
                elif "cohere" in model_id.lower() and "embed" in model_id.lower():
                    embed_models.append(model_id)

            return {
                "generate": generate_models or [
                    "anthropic.claude-3-haiku-20240307-v1:0",
                    "anthropic.claude-3-sonnet-20240229-v1:0",
                    "anthropic.claude-v2:1",
                    "anthropic.claude-instant-v1",
                ],
                "embed": embed_models or [
                    "amazon.titan-embed-text-v1",
                    "cohere.embed-english-v3",
                    "cohere.embed-multilingual-v3",
                ],
                "moderate": [
                    "anthropic.claude-3-haiku-20240307-v1:0",  # Uses basic analysis
                ],
            }

        except Exception as e:
            self.logger.warning("Failed to fetch Bedrock models", error=str(e))
            # Return known model defaults
            return {
                "generate": [
                    "anthropic.claude-3-haiku-20240307-v1:0",
                    "anthropic.claude-3-sonnet-20240229-v1:0",
                    "anthropic.claude-v2:1",
                ],
                "embed": [
                    "amazon.titan-embed-text-v1",
                    "cohere.embed-english-v3",
                ],
                "moderate": [
                    "anthropic.claude-3-haiku-20240307-v1:0",
                ],
            }
