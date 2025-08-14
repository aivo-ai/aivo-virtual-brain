"""
OpenAI Fine-Tuning Integration
"""

import asyncio
from datetime import datetime
from typing import Optional

import openai
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import JobStatus, TrainingJob


class OpenAITrainer:
    """OpenAI fine-tuning trainer"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            organization=settings.openai_organization,
        )
    
    async def train(self, job: TrainingJob, db: AsyncSession):
        """Start OpenAI fine-tuning job"""
        try:
            logger.info(f"Starting OpenAI training for job {job.id}")
            
            # Update job status to training
            job.status = JobStatus.TRAINING
            job.started_at = datetime.utcnow()
            await db.commit()
            
            # Prepare training data
            training_file = await self._prepare_training_data(job)
            
            # Create fine-tuning job
            fine_tune_job = await self.client.fine_tuning.jobs.create(
                training_file=training_file["id"],
                model=job.base_model,
                hyperparameters={
                    "n_epochs": job.config.get("n_epochs", 3),
                    "batch_size": job.config.get("batch_size", 1),
                    "learning_rate_multiplier": job.config.get("learning_rate_multiplier", 0.1),
                },
                suffix=f"aivo-{job.id.hex[:8]}",
            )
            
            # Update job with provider details
            job.provider_job_id = fine_tune_job.id
            job.provider_metadata = {
                "training_file_id": training_file["id"],
                "openai_job_id": fine_tune_job.id,
                "hyperparameters": fine_tune_job.hyperparameters,
            }
            await db.commit()
            
            logger.info(f"Created OpenAI fine-tuning job {fine_tune_job.id} for job {job.id}")
            
            # Monitor training progress
            await self._monitor_training(job, db)
            
        except Exception as e:
            logger.error(f"OpenAI training failed for job {job.id}: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await db.commit()
            raise
    
    async def sync_status(self, job: TrainingJob, db: AsyncSession):
        """Sync job status with OpenAI"""
        if not job.provider_job_id:
            return
        
        try:
            fine_tune_job = await self.client.fine_tuning.jobs.retrieve(job.provider_job_id)
            
            # Map OpenAI status to our status
            status_mapping = {
                "validating_files": JobStatus.VALIDATING,
                "queued": JobStatus.PENDING,
                "running": JobStatus.TRAINING,
                "succeeded": JobStatus.COMPLETED,
                "failed": JobStatus.FAILED,
                "cancelled": JobStatus.CANCELLED,
            }
            
            new_status = status_mapping.get(fine_tune_job.status, job.status)
            
            if new_status != job.status:
                job.status = new_status
                job.updated_at = datetime.utcnow()
                
                if new_status == JobStatus.COMPLETED:
                    job.provider_model_id = fine_tune_job.fine_tuned_model
                    job.training_tokens = fine_tune_job.trained_tokens
                    job.training_cost = self._calculate_cost(fine_tune_job)
                    job.completed_at = datetime.utcnow()
                    
                    if job.started_at:
                        duration = (job.completed_at - job.started_at).total_seconds()
                        job.training_duration = int(duration)
                
                elif new_status in [JobStatus.FAILED, JobStatus.CANCELLED]:
                    job.error_message = fine_tune_job.error.message if fine_tune_job.error else "Unknown error"
                    job.completed_at = datetime.utcnow()
                
                await db.commit()
                logger.info(f"Updated job {job.id} status to {new_status}")
            
        except Exception as e:
            logger.error(f"Failed to sync status for job {job.id}: {e}")
    
    async def cancel(self, job: TrainingJob, db: AsyncSession):
        """Cancel OpenAI fine-tuning job"""
        if not job.provider_job_id:
            return
        
        try:
            await self.client.fine_tuning.jobs.cancel(job.provider_job_id)
            logger.info(f"Cancelled OpenAI job {job.provider_job_id} for job {job.id}")
        except Exception as e:
            logger.error(f"Failed to cancel OpenAI job for {job.id}: {e}")
    
    async def _prepare_training_data(self, job: TrainingJob) -> dict:
        """Prepare and upload training data to OpenAI"""
        # Download dataset from URI
        dataset_content = await self._download_dataset(job.dataset_uri)
        
        # Validate JSONL format
        self._validate_jsonl_format(dataset_content)
        
        # Upload to OpenAI
        training_file = await self.client.files.create(
            file=dataset_content,
            purpose="fine-tune"
        )
        
        logger.info(f"Uploaded training file {training_file.id} for job {job.id}")
        return training_file.dict()
    
    async def _download_dataset(self, dataset_uri: str) -> bytes:
        """Download dataset from URI"""
        # TODO: Implement dataset download from S3/GCS/HTTP
        # For now, return mock data
        mock_data = b'''{"messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Hello!"}, {"role": "assistant", "content": "Hi there!"}]}
{"messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "How are you?"}, {"role": "assistant", "content": "I'm doing well, thank you!"}]}'''
        return mock_data
    
    def _validate_jsonl_format(self, content: bytes):
        """Validate JSONL format for OpenAI fine-tuning"""
        import json
        
        lines = content.decode('utf-8').strip().split('\n')
        
        for i, line in enumerate(lines):
            try:
                data = json.loads(line)
                if "messages" not in data:
                    raise ValueError(f"Line {i+1}: Missing 'messages' field")
                if not isinstance(data["messages"], list):
                    raise ValueError(f"Line {i+1}: 'messages' must be a list")
                if len(data["messages"]) < 1:
                    raise ValueError(f"Line {i+1}: 'messages' cannot be empty")
                
                # Validate message format
                for j, message in enumerate(data["messages"]):
                    if not isinstance(message, dict):
                        raise ValueError(f"Line {i+1}, message {j+1}: Must be an object")
                    if "role" not in message or "content" not in message:
                        raise ValueError(f"Line {i+1}, message {j+1}: Must have 'role' and 'content'")
                    
            except json.JSONDecodeError:
                raise ValueError(f"Line {i+1}: Invalid JSON")
    
    async def _monitor_training(self, job: TrainingJob, db: AsyncSession):
        """Monitor training progress"""
        max_wait = settings.default_training_timeout
        check_interval = 30  # seconds
        elapsed = 0
        
        while elapsed < max_wait:
            await asyncio.sleep(check_interval)
            elapsed += check_interval
            
            await self.sync_status(job, db)
            
            # Refresh job from database
            await db.refresh(job)
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                break
        
        if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            logger.warning(f"Training timeout for job {job.id}")
            job.status = JobStatus.FAILED
            job.error_message = f"Training timeout after {max_wait} seconds"
            job.completed_at = datetime.utcnow()
            await db.commit()
    
    def _calculate_cost(self, fine_tune_job) -> Optional[float]:
        """Calculate training cost based on OpenAI pricing"""
        if not fine_tune_job.trained_tokens:
            return None
        
        # OpenAI fine-tuning pricing (as of 2024)
        # These rates change, so should be configurable
        base_model_rates = {
            "gpt-3.5-turbo": 0.008,  # per 1K tokens
            "gpt-4": 0.03,           # per 1K tokens (estimated)
            "davinci-002": 0.006,    # per 1K tokens
            "babbage-002": 0.0016,   # per 1K tokens
        }
        
        model_name = fine_tune_job.model
        rate = base_model_rates.get(model_name, 0.008)  # default rate
        
        cost = (fine_tune_job.trained_tokens / 1000) * rate
        return round(cost, 4)
