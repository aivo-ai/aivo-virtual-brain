"""
Analytics Service - ETL Jobs (S2-15)
Extract, Transform, Load jobs for converting raw events to anonymized aggregates
"""
import hashlib
import logging
import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
from decimal import Decimal
from collections import defaultdict, Counter

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text

from ..models import (
    SessionAggregate, MasteryAggregate, WeeklyActiveAggregate, 
    IEPProgressAggregate, ETLJobRun, AggregationLevel, 
    PrivacyLevel, MetricType
)

logger = logging.getLogger(__name__)


class DifferentialPrivacyEngine:
    """Differential Privacy noise generation and application."""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5, sensitivity: float = 1.0):
        """
        Initialize DP engine.
        
        Args:
            epsilon: Privacy budget (lower = more private)
            delta: Probability of privacy loss
            sensitivity: L1 sensitivity of queries
        """
        self.epsilon = epsilon
        self.delta = delta
        self.sensitivity = sensitivity
    
    def add_laplace_noise(self, value: float, sensitivity: float = None) -> float:
        """Add Laplace noise for epsilon-differential privacy."""
        if sensitivity is None:
            sensitivity = self.sensitivity
        
        # Laplace noise scale
        scale = sensitivity / self.epsilon
        noise = np.random.laplace(0, scale)
        
        return max(0, value + noise)  # Ensure non-negative for counts
    
    def add_gaussian_noise(self, value: float, sensitivity: float = None) -> float:
        """Add Gaussian noise for (epsilon, delta)-differential privacy."""
        if sensitivity is None:
            sensitivity = self.sensitivity
        
        # Gaussian noise for (ε,δ)-DP
        sigma = sensitivity * np.sqrt(2 * np.log(1.25 / self.delta)) / self.epsilon
        noise = np.random.normal(0, sigma)
        
        return max(0, value + noise)
    
    def add_noise_to_count(self, count: int, method: str = "laplace") -> int:
        """Add noise to count queries."""
        if method == "laplace":
            noisy_count = self.add_laplace_noise(float(count), sensitivity=1.0)
        else:
            noisy_count = self.add_gaussian_noise(float(count), sensitivity=1.0)
        
        return max(0, int(round(noisy_count)))
    
    def add_noise_to_average(self, total: float, count: int, range_size: float) -> float:
        """Add noise to average queries."""
        # For averages, sensitivity is range_size / count
        sensitivity = range_size / max(1, count)
        return self.add_laplace_noise(total / max(1, count), sensitivity)


class PrivacyAnonimizer:
    """Data anonymization utilities."""
    
    @staticmethod
    def hash_learner_id(learner_id: UUID, salt: str = "aivo_analytics_2025") -> str:
        """Create consistent hash of learner ID for privacy."""
        combined = f"{learner_id}{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    @staticmethod
    def generalize_age(age: int) -> str:
        """Generalize age to broader categories."""
        if age < 13:
            return "under_13"
        elif age < 18:
            return "13_17"
        elif age < 25:
            return "18_24"
        elif age < 35:
            return "25_34"
        elif age < 50:
            return "35_49"
        else:
            return "50_plus"
    
    @staticmethod
    def suppress_small_counts(data: Dict[str, int], threshold: int = 5) -> Dict[str, int]:
        """Suppress categories with counts below threshold."""
        filtered = {}
        suppressed_total = 0
        
        for key, count in data.items():
            if count >= threshold:
                filtered[key] = count
            else:
                suppressed_total += count
        
        if suppressed_total > 0:
            filtered["other_suppressed"] = suppressed_total
        
        return filtered
    
    @staticmethod
    def ensure_k_anonymity(groups: List[Dict], k: int = 5) -> List[Dict]:
        """Ensure k-anonymity by suppressing small groups."""
        return [group for group in groups if group.get("count", 0) >= k]


class SessionDurationETL:
    """ETL job for session duration aggregates."""
    
    def __init__(self, db: Session, privacy_level: PrivacyLevel = PrivacyLevel.ANONYMIZED):
        self.db = db
        self.privacy_level = privacy_level
        self.dp_engine = DifferentialPrivacyEngine(epsilon=1.0) if privacy_level.name.startswith("DP") else None
        self.anonymizer = PrivacyAnonimizer()
    
    def extract_raw_sessions(self, start_date: date, end_date: date, tenant_id: UUID) -> List[Dict]:
        """
        Extract raw session data from event store.
        In production, this would query Kafka/event store.
        """
        # Simulated raw session events
        logger.info(f"Extracting session events from {start_date} to {end_date} for tenant {tenant_id}")
        
        # Mock data generation for demo
        sessions = []
        for day in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=day)
            
            # Generate 50-200 sessions per day
            num_sessions = random.randint(50, 200)
            for _ in range(num_sessions):
                learner_id = uuid4()
                sessions.append({
                    "learner_id": learner_id,
                    "tenant_id": tenant_id,
                    "session_start": datetime.combine(current_date, datetime.min.time()) + timedelta(
                        hours=random.randint(8, 20),
                        minutes=random.randint(0, 59)
                    ),
                    "duration_minutes": max(1, int(np.random.lognormal(3.0, 0.8)))  # Log-normal distribution
                })
        
        return sessions
    
    def transform_to_aggregates(self, raw_sessions: List[Dict], aggregation_level: AggregationLevel) -> List[Dict]:
        """Transform raw sessions into privacy-aware aggregates."""
        aggregates = []
        
        if aggregation_level == AggregationLevel.INDIVIDUAL:
            # Per-learner daily aggregates
            learner_daily = defaultdict(lambda: defaultdict(list))
            
            for session in raw_sessions:
                learner_id = session["learner_id"]
                session_date = session["session_start"].date()
                duration = session["duration_minutes"]
                
                learner_daily[learner_id][session_date].append(duration)
            
            for learner_id, daily_sessions in learner_daily.items():
                for session_date, durations in daily_sessions.items():
                    if len(durations) == 0:
                        continue
                    
                    # Calculate basic statistics
                    total_sessions = len(durations)
                    avg_duration = sum(durations) / len(durations)
                    median_duration = np.median(durations)
                    max_duration = max(durations)
                    total_duration = sum(durations)
                    
                    # Apply differential privacy noise if enabled
                    if self.dp_engine and self.privacy_level != PrivacyLevel.ANONYMIZED:
                        total_sessions = self.dp_engine.add_noise_to_count(total_sessions)
                        avg_duration = self.dp_engine.add_noise_to_average(total_duration, total_sessions, 480)  # 8-hour max
                        total_duration = self.dp_engine.add_laplace_noise(total_duration, sensitivity=480)
                    
                    aggregates.append({
                        "tenant_id": raw_sessions[0]["tenant_id"],
                        "learner_id_hash": self.anonymizer.hash_learner_id(learner_id),
                        "date_bucket": session_date,
                        "total_sessions": max(0, total_sessions),
                        "avg_duration_minutes": max(0, avg_duration),
                        "median_duration_minutes": max(0, median_duration),
                        "max_duration_minutes": max_duration,
                        "total_duration_minutes": max(0, total_duration),
                        "aggregation_level": aggregation_level,
                        "privacy_level": self.privacy_level,
                        "noise_epsilon": self.dp_engine.epsilon if self.dp_engine else None,
                        "cohort_size": 1
                    })
        
        elif aggregation_level == AggregationLevel.TENANT:
            # Tenant-wide daily aggregates
            daily_sessions = defaultdict(list)
            
            for session in raw_sessions:
                session_date = session["session_start"].date()
                duration = session["duration_minutes"]
                daily_sessions[session_date].append(duration)
            
            for session_date, durations in daily_sessions.items():
                if len(durations) == 0:
                    continue
                
                total_sessions = len(durations)
                avg_duration = sum(durations) / len(durations)
                median_duration = np.median(durations)
                max_duration = max(durations)
                total_duration = sum(durations)
                
                # Apply DP noise for tenant-level data
                if self.dp_engine and self.privacy_level != PrivacyLevel.ANONYMIZED:
                    total_sessions = self.dp_engine.add_noise_to_count(total_sessions)
                    avg_duration = self.dp_engine.add_noise_to_average(total_duration, total_sessions, 480)
                    total_duration = self.dp_engine.add_laplace_noise(total_duration)
                
                aggregates.append({
                    "tenant_id": raw_sessions[0]["tenant_id"],
                    "learner_id_hash": None,  # Tenant-wide aggregate
                    "date_bucket": session_date,
                    "total_sessions": max(0, total_sessions),
                    "avg_duration_minutes": max(0, avg_duration),
                    "median_duration_minutes": max(0, median_duration),
                    "max_duration_minutes": max_duration,
                    "total_duration_minutes": max(0, total_duration),
                    "aggregation_level": aggregation_level,
                    "privacy_level": self.privacy_level,
                    "noise_epsilon": self.dp_engine.epsilon if self.dp_engine else None,
                    "cohort_size": len(set(s["learner_id"] for s in raw_sessions))
                })
        
        return aggregates
    
    def load_aggregates(self, aggregates: List[Dict]) -> int:
        """Load aggregates into database with upsert logic."""
        loaded_count = 0
        
        for agg_data in aggregates:
            try:
                # Check if aggregate already exists
                existing = self.db.query(SessionAggregate).filter(
                    and_(
                        SessionAggregate.tenant_id == agg_data["tenant_id"],
                        SessionAggregate.learner_id_hash == agg_data["learner_id_hash"],
                        SessionAggregate.date_bucket == agg_data["date_bucket"],
                        SessionAggregate.aggregation_level == agg_data["aggregation_level"]
                    )
                ).first()
                
                if existing:
                    # Update existing record
                    for key, value in agg_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new record
                    aggregate = SessionAggregate(**agg_data)
                    self.db.add(aggregate)
                
                loaded_count += 1
                
            except Exception as e:
                logger.error(f"Failed to load session aggregate: {e}")
                continue
        
        self.db.commit()
        return loaded_count
    
    def run_etl(self, start_date: date, end_date: date, tenant_id: UUID) -> ETLJobRun:
        """Execute complete ETL pipeline for session duration."""
        job_run = ETLJobRun(
            job_name=f"session_duration_etl_{tenant_id}",
            job_type=MetricType.SESSION_DURATION,
            started_at=datetime.utcnow(),
            status="running",
            privacy_level_used=self.privacy_level,
            epsilon_budget_used=self.dp_engine.epsilon if self.dp_engine else None,
            data_start_date=start_date,
            data_end_date=end_date
        )
        self.db.add(job_run)
        self.db.commit()
        
        try:
            # Extract
            raw_sessions = self.extract_raw_sessions(start_date, end_date, tenant_id)
            job_run.records_processed = len(raw_sessions)
            
            # Transform
            individual_aggregates = self.transform_to_aggregates(raw_sessions, AggregationLevel.INDIVIDUAL)
            tenant_aggregates = self.transform_to_aggregates(raw_sessions, AggregationLevel.TENANT)
            
            all_aggregates = individual_aggregates + tenant_aggregates
            
            # Load
            loaded_count = self.load_aggregates(all_aggregates)
            
            # Update job status
            job_run.records_created = loaded_count
            job_run.status = "completed"
            job_run.completed_at = datetime.utcnow()
            job_run.processing_time_seconds = (job_run.completed_at - job_run.started_at).total_seconds()
            
        except Exception as e:
            job_run.status = "failed"
            job_run.error_message = str(e)
            job_run.completed_at = datetime.utcnow()
            logger.error(f"Session duration ETL failed: {e}")
        
        self.db.commit()
        return job_run


class MasteryProgressETL:
    """ETL job for subject mastery aggregates."""
    
    def __init__(self, db: Session, privacy_level: PrivacyLevel = PrivacyLevel.ANONYMIZED):
        self.db = db
        self.privacy_level = privacy_level
        self.dp_engine = DifferentialPrivacyEngine(epsilon=0.5) if privacy_level.name.startswith("DP") else None
        self.anonymizer = PrivacyAnonimizer()
    
    def extract_assessment_events(self, start_date: date, end_date: date, tenant_id: UUID) -> List[Dict]:
        """Extract assessment completion events."""
        logger.info(f"Extracting assessment events from {start_date} to {end_date}")
        
        # Mock assessment data
        assessments = []
        subjects = [
            {"id": uuid4(), "name": "Mathematics", "category": "STEM"},
            {"id": uuid4(), "name": "Reading", "category": "Language Arts"},
            {"id": uuid4(), "name": "Science", "category": "STEM"},
            {"id": uuid4(), "name": "Writing", "category": "Language Arts"},
        ]
        
        for day in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=day)
            
            # 20-50 assessments per day
            num_assessments = random.randint(20, 50)
            for _ in range(num_assessments):
                learner_id = uuid4()
                subject = random.choice(subjects)
                
                # Simulate learning progression
                base_score = random.uniform(0.3, 0.9)
                assessments.append({
                    "learner_id": learner_id,
                    "tenant_id": tenant_id,
                    "subject_id": subject["id"],
                    "subject_category": subject["category"],
                    "assessment_date": current_date,
                    "mastery_score": min(1.0, base_score + random.uniform(-0.1, 0.2)),
                    "difficulty_level": random.randint(1, 5),
                    "time_spent_minutes": random.randint(10, 90)
                })
        
        return assessments
    
    def transform_mastery_aggregates(self, assessments: List[Dict]) -> List[Dict]:
        """Transform assessments into mastery aggregates."""
        aggregates = []
        
        # Group by learner and subject
        learner_subject_data = defaultdict(lambda: defaultdict(list))
        
        for assessment in assessments:
            learner_id = assessment["learner_id"]
            subject_id = assessment["subject_id"]
            
            learner_subject_data[learner_id][subject_id].append(assessment)
        
        for learner_id, subjects in learner_subject_data.items():
            for subject_id, subject_assessments in subjects.items():
                if not subject_assessments:
                    continue
                
                # Sort by date to track progression
                subject_assessments.sort(key=lambda x: x["assessment_date"])
                
                current_mastery = subject_assessments[-1]["mastery_score"]
                avg_mastery = sum(a["mastery_score"] for a in subject_assessments) / len(subject_assessments)
                
                # Calculate improvement (last vs first)
                if len(subject_assessments) > 1:
                    mastery_improvement = current_mastery - subject_assessments[0]["mastery_score"]
                else:
                    mastery_improvement = 0.0
                
                assessments_completed = len(subject_assessments)
                total_time = sum(a["time_spent_minutes"] for a in subject_assessments)
                
                # Apply DP noise
                if self.dp_engine and self.privacy_level != PrivacyLevel.ANONYMIZED:
                    current_mastery = max(0, min(1, self.dp_engine.add_laplace_noise(current_mastery, 0.1)))
                    avg_mastery = max(0, min(1, self.dp_engine.add_laplace_noise(avg_mastery, 0.1)))
                    assessments_completed = self.dp_engine.add_noise_to_count(assessments_completed)
                
                aggregates.append({
                    "tenant_id": subject_assessments[0]["tenant_id"],
                    "learner_id_hash": self.anonymizer.hash_learner_id(learner_id),
                    "subject_id": subject_id,
                    "date_bucket": subject_assessments[-1]["assessment_date"],
                    "current_mastery_score": Decimal(str(round(current_mastery, 4))),
                    "avg_mastery_score": Decimal(str(round(avg_mastery, 4))),
                    "mastery_improvement": Decimal(str(round(mastery_improvement, 4))),
                    "assessments_completed": max(0, assessments_completed),
                    "time_to_mastery_hours": round(total_time / 60.0, 2) if total_time > 0 else None,
                    "subject_category": subject_assessments[0]["subject_category"],
                    "difficulty_level": int(np.mean([a["difficulty_level"] for a in subject_assessments])),
                    "aggregation_level": AggregationLevel.INDIVIDUAL,
                    "privacy_level": self.privacy_level,
                    "noise_epsilon": self.dp_engine.epsilon if self.dp_engine else None,
                    "cohort_size": 1
                })
        
        return aggregates
    
    def run_etl(self, start_date: date, end_date: date, tenant_id: UUID) -> ETLJobRun:
        """Execute mastery progress ETL."""
        job_run = ETLJobRun(
            job_name=f"mastery_progress_etl_{tenant_id}",
            job_type=MetricType.MASTERY_SCORE,
            started_at=datetime.utcnow(),
            status="running",
            privacy_level_used=self.privacy_level,
            epsilon_budget_used=self.dp_engine.epsilon if self.dp_engine else None,
            data_start_date=start_date,
            data_end_date=end_date
        )
        self.db.add(job_run)
        self.db.commit()
        
        try:
            # Extract and transform
            assessments = self.extract_assessment_events(start_date, end_date, tenant_id)
            aggregates = self.transform_mastery_aggregates(assessments)
            
            # Load
            loaded_count = 0
            for agg_data in aggregates:
                try:
                    existing = self.db.query(MasteryAggregate).filter(
                        and_(
                            MasteryAggregate.tenant_id == agg_data["tenant_id"],
                            MasteryAggregate.learner_id_hash == agg_data["learner_id_hash"],
                            MasteryAggregate.subject_id == agg_data["subject_id"],
                            MasteryAggregate.date_bucket == agg_data["date_bucket"]
                        )
                    ).first()
                    
                    if existing:
                        for key, value in agg_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                    else:
                        mastery_agg = MasteryAggregate(**agg_data)
                        self.db.add(mastery_agg)
                    
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to load mastery aggregate: {e}")
                    continue
            
            job_run.records_processed = len(assessments)
            job_run.records_created = loaded_count
            job_run.status = "completed"
            job_run.completed_at = datetime.utcnow()
            job_run.processing_time_seconds = (job_run.completed_at - job_run.started_at).total_seconds()
            
        except Exception as e:
            job_run.status = "failed"
            job_run.error_message = str(e)
            job_run.completed_at = datetime.utcnow()
            logger.error(f"Mastery progress ETL failed: {e}")
        
        self.db.commit()
        return job_run


class WeeklyActiveLearnersETL:
    """ETL job for weekly active learner metrics."""
    
    def __init__(self, db: Session, privacy_level: PrivacyLevel = PrivacyLevel.ANONYMIZED):
        self.db = db
        self.privacy_level = privacy_level
        self.dp_engine = DifferentialPrivacyEngine(epsilon=2.0) if privacy_level.name.startswith("DP") else None
        self.anonymizer = PrivacyAnonimizer()
    
    def run_etl(self, week_start: date, tenant_id: UUID) -> ETLJobRun:
        """Execute weekly active learners ETL."""
        job_run = ETLJobRun(
            job_name=f"weekly_active_etl_{tenant_id}",
            job_type=MetricType.WEEKLY_ACTIVE,
            started_at=datetime.utcnow(),
            status="running",
            privacy_level_used=self.privacy_level,
            epsilon_budget_used=self.dp_engine.epsilon if self.dp_engine else None,
            data_start_date=week_start,
            data_end_date=week_start + timedelta(days=6)
        )
        self.db.add(job_run)
        self.db.commit()
        
        try:
            # Mock weekly activity data
            total_active = random.randint(150, 300)
            new_learners = random.randint(10, 30)
            returning_learners = total_active - new_learners
            churned_learners = random.randint(5, 20)
            
            # Apply DP noise
            if self.dp_engine and self.privacy_level != PrivacyLevel.ANONYMIZED:
                total_active = self.dp_engine.add_noise_to_count(total_active)
                new_learners = self.dp_engine.add_noise_to_count(new_learners)
                returning_learners = self.dp_engine.add_noise_to_count(returning_learners)
                churned_learners = self.dp_engine.add_noise_to_count(churned_learners)
            
            # Demographics (suppressed for privacy)
            age_dist = {
                "13_17": random.randint(20, 50),
                "18_24": random.randint(80, 120),
                "25_34": random.randint(40, 80),
                "35_plus": random.randint(10, 30)
            }
            age_dist = self.anonymizer.suppress_small_counts(age_dist, threshold=10)
            
            aggregate_data = {
                "tenant_id": tenant_id,
                "week_start_date": week_start,
                "total_active_learners": max(0, total_active),
                "new_learners": max(0, new_learners),
                "returning_learners": max(0, returning_learners),
                "churned_learners": max(0, churned_learners),
                "avg_sessions_per_learner": random.uniform(2.5, 5.5),
                "avg_time_per_learner_minutes": random.uniform(45, 120),
                "engagement_rate": Decimal(str(round(random.uniform(0.6, 0.9), 4))),
                "age_distribution": age_dist,
                "grade_distribution": {"k_5": 40, "6_8": 35, "9_12": 25},
                "special_needs_percentage": round(random.uniform(0.15, 0.25), 3),
                "aggregation_level": AggregationLevel.TENANT,
                "privacy_level": self.privacy_level,
                "noise_epsilon": self.dp_engine.epsilon if self.dp_engine else None,
                "total_population": total_active
            }
            
            # Upsert logic
            existing = self.db.query(WeeklyActiveAggregate).filter(
                and_(
                    WeeklyActiveAggregate.tenant_id == tenant_id,
                    WeeklyActiveAggregate.week_start_date == week_start
                )
            ).first()
            
            if existing:
                for key, value in aggregate_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
            else:
                weekly_agg = WeeklyActiveAggregate(**aggregate_data)
                self.db.add(weekly_agg)
            
            job_run.records_processed = 1
            job_run.records_created = 1
            job_run.status = "completed"
            job_run.completed_at = datetime.utcnow()
            job_run.processing_time_seconds = (job_run.completed_at - job_run.started_at).total_seconds()
            
        except Exception as e:
            job_run.status = "failed"
            job_run.error_message = str(e)
            job_run.completed_at = datetime.utcnow()
            logger.error(f"Weekly active learners ETL failed: {e}")
        
        self.db.commit()
        return job_run


class IEPProgressETL:
    """ETL job for IEP progress tracking."""
    
    def __init__(self, db: Session, privacy_level: PrivacyLevel = PrivacyLevel.ANONYMIZED):
        self.db = db
        self.privacy_level = privacy_level
        self.dp_engine = DifferentialPrivacyEngine(epsilon=0.3) if privacy_level.name.startswith("DP") else None
        self.anonymizer = PrivacyAnonimizer()
    
    def run_etl(self, start_date: date, end_date: date, tenant_id: UUID) -> ETLJobRun:
        """Execute IEP progress ETL."""
        job_run = ETLJobRun(
            job_name=f"iep_progress_etl_{tenant_id}",
            job_type=MetricType.IEP_PROGRESS,
            started_at=datetime.utcnow(),
            status="running",
            privacy_level_used=self.privacy_level,
            epsilon_budget_used=self.dp_engine.epsilon if self.dp_engine else None,
            data_start_date=start_date,
            data_end_date=end_date
        )
        self.db.add(job_run)
        self.db.commit()
        
        try:
            # Mock IEP data for learners with special needs
            iep_categories = [
                "reading_comprehension",
                "mathematical_reasoning", 
                "social_skills",
                "communication",
                "behavioral_goals"
            ]
            
            aggregates = []
            for _ in range(random.randint(15, 40)):  # 15-40 IEP learners
                learner_id = uuid4()
                category = random.choice(iep_categories)
                
                baseline = random.uniform(20, 60)
                target = baseline + random.uniform(20, 40)
                current = baseline + random.uniform(5, 35)
                progress_delta = current - baseline
                progress_pct = min(1.0, progress_delta / (target - baseline))
                
                # Apply DP noise to scores
                if self.dp_engine and self.privacy_level != PrivacyLevel.ANONYMIZED:
                    current = self.dp_engine.add_laplace_noise(current, sensitivity=5.0)
                    progress_delta = self.dp_engine.add_laplace_noise(progress_delta, sensitivity=5.0)
                
                is_on_track = progress_pct >= 0.5  # 50% progress threshold
                
                aggregates.append({
                    "tenant_id": tenant_id,
                    "learner_id_hash": self.anonymizer.hash_learner_id(learner_id),
                    "iep_goal_category": category,
                    "date_bucket": end_date,
                    "baseline_score": Decimal(str(round(baseline, 2))),
                    "current_score": Decimal(str(round(max(0, current), 2))),
                    "target_score": Decimal(str(round(target, 2))),
                    "progress_delta": Decimal(str(round(progress_delta, 2))),
                    "progress_percentage": Decimal(str(round(max(0, progress_pct), 4))),
                    "days_since_baseline": random.randint(30, 180),
                    "projected_days_to_goal": random.randint(60, 300) if is_on_track else None,
                    "is_on_track": is_on_track,
                    "accommodations_used": random.sample(["audio", "extended_time", "breaks", "visual_aids"], k=random.randint(1, 3)),
                    "intervention_count": random.randint(0, 5),
                    "support_level": random.choice(["minimal", "moderate", "intensive"]),
                    "aggregation_level": AggregationLevel.INDIVIDUAL,
                    "privacy_level": self.privacy_level,
                    "noise_epsilon": self.dp_engine.epsilon if self.dp_engine else None,
                    "cohort_size": 1
                })
            
            # Load aggregates
            loaded_count = 0
            for agg_data in aggregates:
                try:
                    existing = self.db.query(IEPProgressAggregate).filter(
                        and_(
                            IEPProgressAggregate.tenant_id == agg_data["tenant_id"],
                            IEPProgressAggregate.learner_id_hash == agg_data["learner_id_hash"],
                            IEPProgressAggregate.iep_goal_category == agg_data["iep_goal_category"],
                            IEPProgressAggregate.date_bucket == agg_data["date_bucket"]
                        )
                    ).first()
                    
                    if existing:
                        for key, value in agg_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                    else:
                        iep_agg = IEPProgressAggregate(**agg_data)
                        self.db.add(iep_agg)
                    
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to load IEP aggregate: {e}")
                    continue
            
            job_run.records_processed = len(aggregates)
            job_run.records_created = loaded_count
            job_run.status = "completed"
            job_run.completed_at = datetime.utcnow()
            job_run.processing_time_seconds = (job_run.completed_at - job_run.started_at).total_seconds()
            
        except Exception as e:
            job_run.status = "failed"
            job_run.error_message = str(e)
            job_run.completed_at = datetime.utcnow()
            logger.error(f"IEP progress ETL failed: {e}")
        
        self.db.commit()
        return job_run


class ETLOrchestrator:
    """Orchestrates all ETL jobs for analytics processing."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def run_daily_etl(self, target_date: date, tenant_id: UUID, privacy_level: PrivacyLevel = PrivacyLevel.ANONYMIZED) -> List[ETLJobRun]:
        """Run all daily ETL jobs for a tenant."""
        logger.info(f"Starting daily ETL for {target_date}, tenant {tenant_id}, privacy level {privacy_level}")
        
        job_runs = []
        
        # Session Duration ETL
        try:
            session_etl = SessionDurationETL(self.db, privacy_level)
            session_job = session_etl.run_etl(target_date, target_date, tenant_id)
            job_runs.append(session_job)
        except Exception as e:
            logger.error(f"Session duration ETL failed: {e}")
        
        # Mastery Progress ETL  
        try:
            mastery_etl = MasteryProgressETL(self.db, privacy_level)
            mastery_job = mastery_etl.run_etl(target_date, target_date, tenant_id)
            job_runs.append(mastery_job)
        except Exception as e:
            logger.error(f"Mastery progress ETL failed: {e}")
        
        # IEP Progress ETL
        try:
            iep_etl = IEPProgressETL(self.db, privacy_level)
            iep_job = iep_etl.run_etl(target_date, target_date, tenant_id)
            job_runs.append(iep_job)
        except Exception as e:
            logger.error(f"IEP progress ETL failed: {e}")
        
        return job_runs
    
    def run_weekly_etl(self, week_start: date, tenant_id: UUID, privacy_level: PrivacyLevel = PrivacyLevel.ANONYMIZED) -> ETLJobRun:
        """Run weekly ETL job."""
        logger.info(f"Starting weekly ETL for week {week_start}, tenant {tenant_id}")
        
        weekly_etl = WeeklyActiveLearnersETL(self.db, privacy_level)
        return weekly_etl.run_etl(week_start, tenant_id)
