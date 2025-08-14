"""
API routes for Model Trainer Service
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import JobStatus
from .schemas import (
    EvaluationCreate,
    EvaluationList,
    EvaluationResponse,
    PromotionRequest,
    PromotionResponse,
    ServiceStats,
    TrainingJobCreate,
    TrainingJobList,
    TrainingJobResponse,
    TrainingJobUpdate,
)
from .service import TrainerService

router = APIRouter()


@router.post("/jobs", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_training_job(
    job_data: TrainingJobCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new fine-tuning job
    
    - **provider**: Training provider (currently supports OpenAI)
    - **base_model**: Base model identifier (e.g., "gpt-3.5-turbo")
    - **dataset_uri**: URI to training dataset
    - **config**: Training configuration parameters
    - **policy**: Training policy and thresholds
    - **datasheet**: Dataset documentation requirements
    
    Returns the created job with a unique job_id.
    """
    try:
        service = TrainerService(db)
        job = await service.create_training_job(job_data)
        logger.info(f"Created training job {job.id} for provider {job_data.provider}")
        return job
    except ValueError as e:
        logger.error(f"Validation error creating training job: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating training job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create training job")


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get training job status and details
    
    Returns current status, progress, and results (if completed).
    On completion, automatically creates version and binding in registry.
    """
    try:
        service = TrainerService(db)
        job = await service.get_training_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting training job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get training job")


@router.get("/jobs", response_model=TrainingJobList)
async def list_training_jobs(
    status_filter: Optional[JobStatus] = Query(None, description="Filter by job status"),
    provider_filter: Optional[str] = Query(None, description="Filter by provider"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    db: AsyncSession = Depends(get_db)
):
    """
    List training jobs with filtering and pagination
    
    - **status**: Filter by job status
    - **provider**: Filter by training provider
    - **offset**: Pagination offset
    - **limit**: Maximum number of results
    """
    try:
        service = TrainerService(db)
        jobs, total = await service.list_training_jobs(
            status_filter=status_filter,
            provider_filter=provider_filter,
            offset=offset,
            limit=limit
        )
        return TrainingJobList(
            jobs=jobs,
            total=total,
            offset=offset,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error listing training jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list training jobs")


@router.put("/jobs/{job_id}", response_model=TrainingJobResponse)
async def update_training_job(
    job_id: UUID,
    job_update: TrainingJobUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update training job details"""
    try:
        service = TrainerService(db)
        job = await service.update_training_job(job_id, job_update)
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating training job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update training job")


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_training_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a training job"""
    try:
        service = TrainerService(db)
        success = await service.cancel_training_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Training job not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling training job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel training job")


@router.post("/jobs/{job_id}/evaluate", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    job_id: UUID,
    evaluation_data: EvaluationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Run evaluation harness on trained model
    
    Evaluates the trained model using pedagogy and safety test suites.
    Only models that pass all thresholds are eligible for promotion.
    """
    try:
        service = TrainerService(db)
        evaluation = await service.create_evaluation(job_id, evaluation_data)
        logger.info(f"Created evaluation {evaluation.id} for job {job_id}")
        return evaluation
    except ValueError as e:
        logger.error(f"Validation error creating evaluation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating evaluation for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create evaluation")


@router.get("/jobs/{job_id}/evaluation", response_model=EvaluationResponse)
async def get_evaluation(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get evaluation results for a training job"""
    try:
        service = TrainerService(db)
        evaluation = await service.get_job_evaluation(job_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        return evaluation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evaluation for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get evaluation")


@router.post("/jobs/{job_id}/promote", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
async def promote_model(
    job_id: UUID,
    promotion_request: PromotionRequest = PromotionRequest(),
    db: AsyncSession = Depends(get_db)
):
    """
    Promote trained model to registry
    
    Creates model version and binding in the Model Registry Service.
    Only successful evaluations are promoted unless force=true.
    """
    try:
        service = TrainerService(db)
        promotion = await service.promote_model(job_id, promotion_request)
        logger.info(f"Promoted model from job {job_id} to registry")
        return promotion
    except ValueError as e:
        logger.error(f"Validation error promoting model: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error promoting model from job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to promote model")


@router.get("/evaluations", response_model=EvaluationList)
async def list_evaluations(
    job_id: Optional[UUID] = Query(None, description="Filter by job ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    db: AsyncSession = Depends(get_db)
):
    """List evaluations with filtering and pagination"""
    try:
        service = TrainerService(db)
        evaluations, total = await service.list_evaluations(
            job_id_filter=job_id,
            status_filter=status_filter,
            offset=offset,
            limit=limit
        )
        return EvaluationList(
            evaluations=evaluations,
            total=total,
            offset=offset,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error listing evaluations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list evaluations")


@router.get("/stats", response_model=ServiceStats)
async def get_service_statistics(db: AsyncSession = Depends(get_db)):
    """Get training service statistics"""
    try:
        service = TrainerService(db)
        stats = await service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting service statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


# Export router
trainer_router = router
