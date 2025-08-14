#!/usr/bin/env python3
"""
Seed database with sample training data for development and testing
"""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.models import Base, TrainingJob, Evaluation, ModelPromotion, JobStatus, EvaluationStatus, Provider


async def seed_database():
    """Seed database with sample data"""
    
    # Create engine and session
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    )
    
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession)
    
    async with SessionLocal() as db:
        print("🌱 Seeding Model Trainer database...")
        
        # Sample training jobs
        jobs_data = [
            {
                "name": "gpt-3.5-curriculum-math",
                "description": "Fine-tune GPT-3.5 for mathematics curriculum",
                "provider": Provider.OPENAI,
                "base_model": "gpt-3.5-turbo",
                "dataset_uri": "s3://aivo-training/math-curriculum-v1.jsonl",
                "status": JobStatus.COMPLETED,
                "provider_job_id": "ft-job-abc123",
                "provider_model_id": "ft:gpt-3.5-turbo:aivo:math:abc123",
                "training_tokens": 25000,
                "training_cost": 0.20,
                "training_duration": 1800,
                "created_at": datetime.utcnow() - timedelta(days=7),
                "started_at": datetime.utcnow() - timedelta(days=7, hours=-1),
                "completed_at": datetime.utcnow() - timedelta(days=7, hours=-2),
                "config": {
                    "n_epochs": 3,
                    "batch_size": 1,
                    "learning_rate_multiplier": 0.1
                },
                "policy": {
                    "scope": "tenant_demo",
                    "thresholds": {"pedagogy_score": 0.8, "safety_score": 0.9}
                },
                "datasheet": {
                    "source": "curriculum_team",
                    "license": "proprietary",
                    "redaction": "pii_removed",
                    "description": "K-12 mathematics curriculum aligned content"
                }
            },
            {
                "name": "gpt-3.5-science-biology",
                "description": "Fine-tune GPT-3.5 for biology content",
                "provider": Provider.OPENAI,
                "base_model": "gpt-3.5-turbo",
                "dataset_uri": "s3://aivo-training/biology-content-v2.jsonl",
                "status": JobStatus.TRAINING,
                "provider_job_id": "ft-job-def456",
                "training_tokens": None,
                "training_cost": None,
                "training_duration": None,
                "created_at": datetime.utcnow() - timedelta(hours=2),
                "started_at": datetime.utcnow() - timedelta(hours=1),
                "completed_at": None,
                "config": {
                    "n_epochs": 4,
                    "batch_size": 2,
                    "learning_rate_multiplier": 0.05
                },
                "policy": {
                    "scope": "tenant_demo",
                    "thresholds": {"pedagogy_score": 0.85, "safety_score": 0.92}
                },
                "datasheet": {
                    "source": "textbook_publisher",
                    "license": "licensed",
                    "redaction": "anonymized",
                    "description": "High school biology textbook content"
                }
            },
            {
                "name": "gpt-4-advanced-physics",
                "description": "Fine-tune GPT-4 for advanced physics",
                "provider": Provider.OPENAI,
                "base_model": "gpt-4",
                "dataset_uri": "s3://aivo-training/physics-advanced-v1.jsonl",
                "status": JobStatus.FAILED,
                "provider_job_id": "ft-job-ghi789",
                "error_message": "Training data validation failed: insufficient examples",
                "training_tokens": None,
                "training_cost": None,
                "training_duration": None,
                "created_at": datetime.utcnow() - timedelta(days=2),
                "started_at": datetime.utcnow() - timedelta(days=2, hours=-1),
                "completed_at": datetime.utcnow() - timedelta(days=2, hours=-2),
                "config": {
                    "n_epochs": 3,
                    "batch_size": 1,
                    "learning_rate_multiplier": 0.02
                },
                "policy": {
                    "scope": "tenant_premium",
                    "thresholds": {"pedagogy_score": 0.9, "safety_score": 0.95}
                },
                "datasheet": {
                    "source": "university_content",
                    "license": "academic_use",
                    "redaction": "full_anonymization",
                    "description": "University-level physics problem sets"
                }
            }
        ]
        
        # Create training jobs
        created_jobs = []
        for job_data in jobs_data:
            job = TrainingJob(
                id=uuid4(),
                **job_data
            )
            db.add(job)
            created_jobs.append(job)
        
        await db.commit()
        print(f"✓ Created {len(created_jobs)} training jobs")
        
        # Create evaluations for completed jobs
        evaluations_data = []
        for job in created_jobs:
            if job.status == JobStatus.COMPLETED:
                evaluation = Evaluation(
                    id=uuid4(),
                    job_id=job.id,
                    name=f"evaluation-{job.name}",
                    description=f"Evaluation for {job.name}",
                    status=EvaluationStatus.PASSED,
                    harness_config={
                        "pedagogy_tests": ["curriculum_alignment", "learning_objectives", "content_accuracy"],
                        "safety_tests": ["harmful_content", "bias_detection", "age_appropriateness"],
                        "timeout": 600,
                        "parallel": True
                    },
                    thresholds=job.policy["thresholds"],
                    pedagogy_score=0.87,
                    safety_score=0.93,
                    overall_score=0.90,
                    passed=True,
                    results={
                        "pedagogy": {
                            "score": 0.87,
                            "tests": [
                                {"name": "curriculum_alignment", "score": 0.85, "passed": True},
                                {"name": "learning_objectives", "score": 0.88, "passed": True},
                                {"name": "content_accuracy", "score": 0.91, "passed": True}
                            ]
                        },
                        "safety": {
                            "score": 0.93,
                            "tests": [
                                {"name": "harmful_content", "score": 0.95, "passed": True},
                                {"name": "bias_detection", "score": 0.89, "passed": True},
                                {"name": "age_appropriateness", "score": 0.94, "passed": True}
                            ]
                        }
                    },
                    metrics={
                        "total_tests": 6,
                        "passed_tests": 6,
                        "failed_tests": 0,
                        "error_tests": 0,
                        "pass_rate": 1.0,
                        "execution_time": 245.5
                    },
                    created_at=job.completed_at + timedelta(minutes=10),
                    started_at=job.completed_at + timedelta(minutes=15),
                    completed_at=job.completed_at + timedelta(minutes=30)
                )
                db.add(evaluation)
                evaluations_data.append(evaluation)
        
        await db.commit()
        print(f"✓ Created {len(evaluations_data)} evaluations")
        
        # Create model promotions for passed evaluations
        promotions_data = []
        for evaluation in evaluations_data:
            if evaluation.passed:
                promotion = ModelPromotion(
                    id=uuid4(),
                    job_id=evaluation.job_id,
                    evaluation_id=evaluation.id,
                    registry_model_id=uuid4(),  # Mock registry IDs
                    registry_version_id=uuid4(),
                    registry_binding_id=uuid4(),
                    promoted=True,
                    promotion_reason="Automatic promotion after successful evaluation",
                    promotion_metadata={
                        "promotion_type": "automatic",
                        "evaluation_scores": {
                            "pedagogy": evaluation.pedagogy_score,
                            "safety": evaluation.safety_score,
                            "overall": evaluation.overall_score
                        }
                    },
                    created_at=evaluation.completed_at + timedelta(minutes=5)
                )
                db.add(promotion)
                promotions_data.append(promotion)
        
        await db.commit()
        print(f"✓ Created {len(promotions_data)} model promotions")
        
        print("🎉 Database seeding completed successfully!")
        print(f"   - Training Jobs: {len(created_jobs)}")
        print(f"   - Evaluations: {len(evaluations_data)}")  
        print(f"   - Promotions: {len(promotions_data)}")


if __name__ == "__main__":
    asyncio.run(seed_database())
