"""
Celery tasks for async training operations
"""

import asyncio
from celery import current_task
from loguru import logger
from sqlalchemy import select
from uuid import UUID

from .celery import celery
from .database import SessionLocal
from .models import TrainingJob, JobStatus
from .trainers.openai_trainer import OpenAITrainer


@celery.task(bind=True)
def train_model(self, job_id: str):
    """Async task to train a model"""
    try:
        logger.info(f"Starting training task for job {job_id}")
        
        # Convert string to UUID
        job_uuid = UUID(job_id)
        
        # Get database session
        db = SessionLocal()
        
        try:
            # Get job
            result = db.execute(select(TrainingJob).where(TrainingJob.id == job_uuid))
            job = result.scalar_one_or_none()
            
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Update task ID
            job.provider_metadata = job.provider_metadata or {}
            job.provider_metadata["celery_task_id"] = self.request.id
            db.commit()
            
            # Initialize trainer
            trainer = OpenAITrainer()
            
            # Start training (this will be sync in Celery context)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(trainer.train(job, db))
            finally:
                loop.close()
            
            logger.info(f"Training task completed for job {job_id}")
            return {"status": "completed", "job_id": job_id}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Training task failed for job {job_id}: {e}")
        
        # Update job status to failed
        db = SessionLocal()
        try:
            result = db.execute(select(TrainingJob).where(TrainingJob.id == UUID(job_id)))
            job = result.scalar_one_or_none()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                db.commit()
        finally:
            db.close()
        
        raise


@celery.task(bind=True)
def evaluate_model(self, job_id: str, evaluation_id: str):
    """Async task to evaluate a trained model"""
    try:
        logger.info(f"Starting evaluation task for job {job_id}, evaluation {evaluation_id}")
        
        from .evals.harness import EvaluationHarness
        from .models import Evaluation
        
        # Get database session
        db = SessionLocal()
        
        try:
            # Get evaluation
            evaluation_uuid = UUID(evaluation_id)
            result = db.execute(select(Evaluation).where(Evaluation.id == evaluation_uuid))
            evaluation = result.scalar_one_or_none()
            
            if not evaluation:
                raise ValueError(f"Evaluation {evaluation_id} not found")
            
            # Run evaluation
            harness = EvaluationHarness()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(harness.evaluate(evaluation, db))
            finally:
                loop.close()
            
            logger.info(f"Evaluation task completed for evaluation {evaluation_id}")
            return {"status": "completed", "evaluation_id": evaluation_id}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Evaluation task failed for evaluation {evaluation_id}: {e}")
        raise


@celery.task
def promote_model(job_id: str, promotion_data: dict):
    """Async task to promote a model to registry"""
    try:
        logger.info(f"Starting promotion task for job {job_id}")
        
        from .service import TrainerService
        from .schemas import PromotionRequest
        
        # Get database session
        db = SessionLocal()
        
        try:
            service = TrainerService(db)
            promotion_request = PromotionRequest(**promotion_data)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                promotion = loop.run_until_complete(
                    service.promote_model(UUID(job_id), promotion_request)
                )
            finally:
                loop.close()
            
            logger.info(f"Promotion task completed for job {job_id}")
            return {"status": "completed", "promotion_id": str(promotion.id)}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Promotion task failed for job {job_id}: {e}")
        raise


@celery.task
def sync_training_status():
    """Periodic task to sync training status with providers"""
    try:
        logger.debug("Starting training status sync")
        
        db = SessionLocal()
        
        try:
            # Get active training jobs
            result = db.execute(
                select(TrainingJob).where(
                    TrainingJob.status.in_([JobStatus.TRAINING, JobStatus.VALIDATING])
                )
            )
            active_jobs = result.scalars().all()
            
            logger.info(f"Found {len(active_jobs)} active training jobs to sync")
            
            for job in active_jobs:
                try:
                    trainer = OpenAITrainer()
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        loop.run_until_complete(trainer.sync_status(job, db))
                    finally:
                        loop.close()
                        
                except Exception as e:
                    logger.error(f"Failed to sync status for job {job.id}: {e}")
            
            logger.debug("Training status sync completed")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Training status sync failed: {e}")
        raise


@celery.task
def cleanup_old_jobs():
    """Periodic task to cleanup old completed/failed jobs"""
    try:
        from datetime import datetime, timedelta
        
        logger.debug("Starting old job cleanup")
        
        db = SessionLocal()
        
        try:
            # Delete jobs older than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            result = db.execute(
                select(TrainingJob).where(
                    TrainingJob.completed_at < cutoff_date,
                    TrainingJob.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED])
                )
            )
            old_jobs = result.scalars().all()
            
            for job in old_jobs:
                # Archive or delete job data
                logger.info(f"Archiving old job {job.id} ({job.name})")
                # Could move to archive table or delete
                db.delete(job)
            
            db.commit()
            logger.info(f"Cleaned up {len(old_jobs)} old training jobs")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Job cleanup failed: {e}")
        raise
