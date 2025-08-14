"""
Core service layer for Model Trainer Service
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Evaluation,
    EvaluationStatus,
    JobStatus,
    ModelPromotion,
    TrainingJob,
)
from .schemas import (
    EvaluationCreate,
    EvaluationResponse,
    PromotionRequest,
    PromotionResponse,
    ServiceStats,
    TrainingJobCreate,
    TrainingJobResponse,
    TrainingJobUpdate,
)


class TrainerService:
    """Core training service logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_training_job(self, job_data: TrainingJobCreate) -> TrainingJobResponse:
        """Create a new training job"""
        # Validate dataset URI and datasheet
        await self._validate_dataset(job_data.dataset_uri, job_data.datasheet)
        
        # Create job record
        job = TrainingJob(
            name=job_data.name,
            description=job_data.description,
            provider=job_data.provider,
            base_model=job_data.base_model,
            dataset_uri=job_data.dataset_uri,
            config=job_data.config.dict(),
            policy=job_data.policy.dict(),
            datasheet=job_data.datasheet.dict(),
            status=JobStatus.PENDING,
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        # Start async training process
        asyncio.create_task(self._start_training(job.id))
        
        return TrainingJobResponse.from_orm(job)
    
    async def get_training_job(self, job_id: UUID) -> Optional[TrainingJobResponse]:
        """Get training job by ID"""
        result = await self.db.execute(
            select(TrainingJob).where(TrainingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if job:
            # Update status from provider if needed
            await self._sync_job_status(job)
            return TrainingJobResponse.from_orm(job)
        return None
    
    async def list_training_jobs(
        self,
        status_filter: Optional[JobStatus] = None,
        provider_filter: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[TrainingJobResponse], int]:
        """List training jobs with filtering"""
        query = select(TrainingJob)
        count_query = select(func.count(TrainingJob.id))
        
        if status_filter:
            query = query.where(TrainingJob.status == status_filter)
            count_query = count_query.where(TrainingJob.status == status_filter)
        
        if provider_filter:
            query = query.where(TrainingJob.provider == provider_filter)
            count_query = count_query.where(TrainingJob.provider == provider_filter)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get jobs with pagination
        jobs_result = await self.db.execute(
            query.order_by(TrainingJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        jobs = jobs_result.scalars().all()
        
        return [TrainingJobResponse.from_orm(job) for job in jobs], total
    
    async def update_training_job(
        self,
        job_id: UUID,
        job_update: TrainingJobUpdate
    ) -> Optional[TrainingJobResponse]:
        """Update training job"""
        result = await self.db.execute(
            select(TrainingJob).where(TrainingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        # Update fields
        if job_update.name is not None:
            job.name = job_update.name
        if job_update.description is not None:
            job.description = job_update.description
        if job_update.status is not None:
            job.status = job_update.status
        
        job.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(job)
        
        return TrainingJobResponse.from_orm(job)
    
    async def cancel_training_job(self, job_id: UUID) -> bool:
        """Cancel a training job"""
        result = await self.db.execute(
            select(TrainingJob).where(TrainingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return False
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False
        
        # Cancel with provider if needed
        if job.provider_job_id:
            await self._cancel_provider_job(job)
        
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.utcnow()
        job.completed_at = datetime.utcnow()
        
        await self.db.commit()
        return True
    
    async def create_evaluation(
        self,
        job_id: UUID,
        evaluation_data: EvaluationCreate
    ) -> EvaluationResponse:
        """Create evaluation for a training job"""
        # Verify job exists and is completed
        result = await self.db.execute(
            select(TrainingJob).where(TrainingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise ValueError("Training job not found")
        
        if job.status != JobStatus.COMPLETED:
            raise ValueError("Training job must be completed before evaluation")
        
        # Create evaluation record
        evaluation = Evaluation(
            job_id=job_id,
            name=evaluation_data.name,
            description=evaluation_data.description,
            harness_config=evaluation_data.harness_config.dict(),
            thresholds=evaluation_data.thresholds.dict(),
            status=EvaluationStatus.PENDING,
        )
        
        self.db.add(evaluation)
        await self.db.commit()
        await self.db.refresh(evaluation)
        
        # Start async evaluation process
        asyncio.create_task(self._start_evaluation(evaluation.id))
        
        return EvaluationResponse.from_orm(evaluation)
    
    async def get_job_evaluation(self, job_id: UUID) -> Optional[EvaluationResponse]:
        """Get evaluation for a training job"""
        result = await self.db.execute(
            select(Evaluation).where(Evaluation.job_id == job_id)
        )
        evaluation = result.scalar_one_or_none()
        
        if evaluation:
            return EvaluationResponse.from_orm(evaluation)
        return None
    
    async def list_evaluations(
        self,
        job_id_filter: Optional[UUID] = None,
        status_filter: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[EvaluationResponse], int]:
        """List evaluations with filtering"""
        query = select(Evaluation)
        count_query = select(func.count(Evaluation.id))
        
        if job_id_filter:
            query = query.where(Evaluation.job_id == job_id_filter)
            count_query = count_query.where(Evaluation.job_id == job_id_filter)
        
        if status_filter:
            query = query.where(Evaluation.status == status_filter)
            count_query = count_query.where(Evaluation.status == status_filter)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get evaluations with pagination
        evals_result = await self.db.execute(
            query.order_by(Evaluation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        evaluations = evals_result.scalars().all()
        
        return [EvaluationResponse.from_orm(eval) for eval in evaluations], total
    
    async def promote_model(
        self,
        job_id: UUID,
        promotion_request: PromotionRequest
    ) -> PromotionResponse:
        """Promote model to registry"""
        # Get job and evaluation
        result = await self.db.execute(
            select(TrainingJob).where(TrainingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise ValueError("Training job not found")
        
        if job.status != JobStatus.COMPLETED:
            raise ValueError("Training job must be completed before promotion")
        
        # Check if evaluation passed (unless forced)
        evaluation = None
        eval_result = await self.db.execute(
            select(Evaluation).where(Evaluation.job_id == job_id)
        )
        evaluation = eval_result.scalar_one_or_none()
        
        if not promotion_request.force and evaluation and not evaluation.passed:
            raise ValueError("Model evaluation failed - cannot promote")
        
        # Create promotion record
        promotion = ModelPromotion(
            job_id=job_id,
            evaluation_id=evaluation.id if evaluation else None,
            promoted=False,
            promotion_reason="Automatic promotion after successful training and evaluation",
        )
        
        try:
            # Promote to registry
            registry_ids = await self._promote_to_registry(job, evaluation)
            
            promotion.registry_model_id = registry_ids.get("model_id")
            promotion.registry_version_id = registry_ids.get("version_id")
            promotion.registry_binding_id = registry_ids.get("binding_id")
            promotion.promoted = True
            promotion.promotion_metadata = promotion_request.metadata
            
        except Exception as e:
            promotion.promoted = False
            promotion.error_message = str(e)
            logger.error(f"Failed to promote model from job {job_id}: {e}")
        
        self.db.add(promotion)
        await self.db.commit()
        await self.db.refresh(promotion)
        
        return PromotionResponse.from_orm(promotion)
    
    async def get_statistics(self) -> ServiceStats:
        """Get service statistics"""
        # Training job stats
        jobs_result = await self.db.execute(
            select(
                func.count(TrainingJob.id).label("total"),
                func.count(TrainingJob.id).filter(
                    TrainingJob.status.in_([JobStatus.TRAINING, JobStatus.EVALUATING])
                ).label("active"),
                func.count(TrainingJob.id).filter(
                    TrainingJob.status == JobStatus.COMPLETED
                ).label("completed"),
                func.count(TrainingJob.id).filter(
                    TrainingJob.status == JobStatus.FAILED
                ).label("failed"),
                func.avg(TrainingJob.training_duration).label("avg_duration"),
                func.sum(TrainingJob.training_cost).label("total_cost"),
            )
        )
        job_stats = jobs_result.first()
        
        # Evaluation stats
        eval_result = await self.db.execute(
            select(
                func.count(Evaluation.id).label("total"),
                func.count(Evaluation.id).filter(
                    Evaluation.passed == True
                ).label("passed"),
                func.count(Evaluation.id).filter(
                    Evaluation.passed == False
                ).label("failed"),
            )
        )
        eval_stats = eval_result.first()
        
        # Promotion stats
        promo_result = await self.db.execute(
            select(
                func.count(ModelPromotion.id).label("total"),
                func.count(ModelPromotion.id).filter(
                    ModelPromotion.promoted == True
                ).label("successful"),
            )
        )
        promo_stats = promo_result.first()
        
        return ServiceStats(
            total_jobs=job_stats.total or 0,
            active_jobs=job_stats.active or 0,
            completed_jobs=job_stats.completed or 0,
            failed_jobs=job_stats.failed or 0,
            total_evaluations=eval_stats.total or 0,
            passed_evaluations=eval_stats.passed or 0,
            failed_evaluations=eval_stats.failed or 0,
            total_promotions=promo_stats.total or 0,
            successful_promotions=promo_stats.successful or 0,
            average_training_time=job_stats.avg_duration,
            total_training_cost=job_stats.total_cost,
        )
    
    # Private helper methods
    
    async def _validate_dataset(self, dataset_uri: str, datasheet: dict):
        """Validate dataset and datasheet requirements"""
        # TODO: Implement dataset validation
        # - Check URI accessibility
        # - Validate datasheet completeness
        # - Check data format and quality
        pass
    
    async def _start_training(self, job_id: UUID):
        """Start async training process"""
        try:
            result = await self.db.execute(
                select(TrainingJob).where(TrainingJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return
            
            # Import provider-specific trainer
            from .trainers.openai_trainer import OpenAITrainer
            
            trainer = OpenAITrainer()
            await trainer.train(job, self.db)
            
        except Exception as e:
            logger.error(f"Training failed for job {job_id}: {e}")
            # Update job status to failed
            await self._update_job_status(job_id, JobStatus.FAILED, str(e))
    
    async def _start_evaluation(self, evaluation_id: UUID):
        """Start async evaluation process"""
        try:
            result = await self.db.execute(
                select(Evaluation).where(Evaluation.id == evaluation_id)
            )
            evaluation = result.scalar_one_or_none()
            
            if not evaluation:
                return
            
            # Import evaluation harness
            from .evals.harness import EvaluationHarness
            
            harness = EvaluationHarness()
            await harness.evaluate(evaluation, self.db)
            
        except Exception as e:
            logger.error(f"Evaluation failed for evaluation {evaluation_id}: {e}")
            # Update evaluation status to error
            await self._update_evaluation_status(evaluation_id, EvaluationStatus.ERROR, str(e))
    
    async def _sync_job_status(self, job: TrainingJob):
        """Sync job status with provider"""
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return
        
        if job.provider_job_id:
            # Import provider-specific trainer
            from .trainers.openai_trainer import OpenAITrainer
            
            trainer = OpenAITrainer()
            await trainer.sync_status(job, self.db)
    
    async def _cancel_provider_job(self, job: TrainingJob):
        """Cancel job with provider"""
        # Import provider-specific trainer
        from .trainers.openai_trainer import OpenAITrainer
        
        trainer = OpenAITrainer()
        await trainer.cancel(job, self.db)
    
    async def _promote_to_registry(self, job: TrainingJob, evaluation: Optional[Evaluation]) -> dict:
        """Promote model to registry"""
        # TODO: Implement registry client
        # Create model, version, and binding in Model Registry
        return {
            "model_id": "mock-model-id",
            "version_id": "mock-version-id",
            "binding_id": "mock-binding-id"
        }
    
    async def _update_job_status(self, job_id: UUID, status: JobStatus, error_message: str = None):
        """Update job status"""
        result = await self.db.execute(
            select(TrainingJob).where(TrainingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if job:
            job.status = status
            job.error_message = error_message
            job.updated_at = datetime.utcnow()
            if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                job.completed_at = datetime.utcnow()
            
            await self.db.commit()
    
    async def _update_evaluation_status(self, eval_id: UUID, status: EvaluationStatus, error_message: str = None):
        """Update evaluation status"""
        result = await self.db.execute(
            select(Evaluation).where(Evaluation.id == eval_id)
        )
        evaluation = result.scalar_one_or_none()
        
        if evaluation:
            evaluation.status = status
            evaluation.error_message = error_message
            evaluation.updated_at = datetime.utcnow()
            if status in [EvaluationStatus.PASSED, EvaluationStatus.FAILED, EvaluationStatus.ERROR]:
                evaluation.completed_at = datetime.utcnow()
            
            await self.db.commit()
