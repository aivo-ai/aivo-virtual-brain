# AIVO SEL Service - Data Models
# S2-12 Implementation - Social-Emotional Learning data structures

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
import enum

Base = declarative_base()


# Enums for SEL domain classification
class EmotionType(enum.Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    FRUSTRATED = "frustrated"
    EXCITED = "excited"
    CALM = "calm"
    CONFUSED = "confused"
    PROUD = "proud"
    WORRIED = "worried"
    CONTENT = "content"
    OVERWHELMED = "overwhelmed"


class SELDomain(enum.Enum):
    SELF_AWARENESS = "self_awareness"
    SELF_MANAGEMENT = "self_management"
    SOCIAL_AWARENESS = "social_awareness"
    RELATIONSHIP_SKILLS = "relationship_skills"
    RESPONSIBLE_DECISION_MAKING = "responsible_decision_making"


class AlertLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StrategyType(enum.Enum):
    BREATHING = "breathing"
    MINDFULNESS = "mindfulness"
    COGNITIVE_REFRAMING = "cognitive_reframing"
    SOCIAL_SKILLS = "social_skills"
    PROBLEM_SOLVING = "problem_solving"
    EMOTIONAL_REGULATION = "emotional_regulation"
    COPING_SKILLS = "coping_skills"
    COMMUNICATION = "communication"


class GradeBand(enum.Enum):
    EARLY_ELEMENTARY = "early_elementary"  # K-2
    LATE_ELEMENTARY = "late_elementary"    # 3-5
    MIDDLE_SCHOOL = "middle_school"        # 6-8
    HIGH_SCHOOL = "high_school"            # 9-12
    ADULT = "adult"                        # 18+


class ConsentStatus(enum.Enum):
    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"
    REVOKED = "revoked"


class CheckInStatus(enum.Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    ABANDONED = "abandoned"


class AlertStatus(enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class SELCheckIn(Base):
    """
    Student check-in sessions for emotional state assessment.
    Records emotional ratings, triggers, and contextual information.
    """
    __tablename__ = "sel_checkins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(String(100), nullable=False, index=True)
    student_name = Column(String(200), nullable=False)
    grade_band = Column(SQLEnum(GradeBand), nullable=False)
    
    # Check-in metadata
    checkin_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(SQLEnum(CheckInStatus), nullable=False, default=CheckInStatus.IN_PROGRESS)
    session_duration = Column(Integer, nullable=True)  # Duration in seconds
    
    # Emotional assessment data
    primary_emotion = Column(SQLEnum(EmotionType), nullable=False)
    emotion_intensity = Column(Integer, nullable=False)  # 1-10 scale
    secondary_emotions = Column(JSON, nullable=True)  # List of additional emotions
    
    # Contextual information
    triggers = Column(JSON, nullable=True)  # List of identified triggers
    current_situation = Column(Text, nullable=True)  # Free text description
    location_context = Column(String(100), nullable=True)  # classroom, home, cafeteria, etc.
    social_context = Column(String(100), nullable=True)  # alone, with_friends, with_teacher, etc.
    
    # SEL domain ratings (1-10 scale)
    self_awareness_rating = Column(Integer, nullable=True)
    self_management_rating = Column(Integer, nullable=True)
    social_awareness_rating = Column(Integer, nullable=True)
    relationship_skills_rating = Column(Integer, nullable=True)
    decision_making_rating = Column(Integer, nullable=True)
    
    # Overall wellness indicators
    energy_level = Column(Integer, nullable=True)  # 1-10 scale
    stress_level = Column(Integer, nullable=True)  # 1-10 scale
    confidence_level = Column(Integer, nullable=True)  # 1-10 scale
    support_needed = Column(Boolean, nullable=False, default=False)
    
    # Additional context
    checkin_notes = Column(Text, nullable=True)
    previous_strategies_used = Column(JSON, nullable=True)  # List of strategies tried
    strategy_effectiveness = Column(JSON, nullable=True)  # Ratings for previous strategies
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    strategies = relationship("SELStrategy", back_populates="checkin")
    alerts = relationship("SELAlert", back_populates="checkin")

    def __repr__(self):
        return f"<SELCheckIn(student_id='{self.student_id}', emotion='{self.primary_emotion}', intensity={self.emotion_intensity})>"


class SELStrategy(Base):
    """
    Personalized SEL strategies generated based on check-in data.
    Tailored to student's grade band, emotional state, and needs.
    """
    __tablename__ = "sel_strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(String(100), nullable=False, index=True)
    checkin_id = Column(UUID(as_uuid=True), ForeignKey('sel_checkins.id'), nullable=False)
    
    # Strategy content
    strategy_type = Column(SQLEnum(StrategyType), nullable=False)
    strategy_title = Column(String(200), nullable=False)
    strategy_description = Column(Text, nullable=False)
    instructions = Column(Text, nullable=False)
    
    # Personalization
    grade_band = Column(SQLEnum(GradeBand), nullable=False)
    target_emotion = Column(SQLEnum(EmotionType), nullable=False)
    target_domain = Column(SQLEnum(SELDomain), nullable=False)
    difficulty_level = Column(Integer, nullable=False, default=1)  # 1-5 scale
    
    # Implementation details
    estimated_duration = Column(Integer, nullable=False)  # Minutes
    materials_needed = Column(JSON, nullable=True)  # List of materials
    step_by_step = Column(JSON, nullable=False)  # Ordered list of steps
    success_indicators = Column(JSON, nullable=True)  # How to measure success
    
    # Multimedia content
    video_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=True)
    image_urls = Column(JSON, nullable=True)  # List of image URLs
    interactive_elements = Column(JSON, nullable=True)  # Interactive components
    
    # Effectiveness tracking
    times_used = Column(Integer, default=0)
    average_rating = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True)
    
    # Adaptation data
    adaptations = Column(JSON, nullable=True)  # Previous adaptations made
    personalization_notes = Column(Text, nullable=True)
    
    # Metadata
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    checkin = relationship("SELCheckIn", back_populates="strategies")
    usage_logs = relationship("StrategyUsage", back_populates="strategy")

    def __repr__(self):
        return f"<SELStrategy(type='{self.strategy_type}', title='{self.strategy_title}')>"


class StrategyUsage(Base):
    """
    Tracking usage and effectiveness of SEL strategies.
    Records student feedback and outcome data.
    """
    __tablename__ = "strategy_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(String(100), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey('sel_strategies.id'), nullable=False)
    
    # Usage details
    used_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    duration_used = Column(Integer, nullable=True)  # Minutes actually spent
    completion_status = Column(String(50), nullable=False)  # completed, partial, abandoned
    
    # Effectiveness measures
    pre_emotion_rating = Column(Integer, nullable=False)  # 1-10 before strategy
    post_emotion_rating = Column(Integer, nullable=False)  # 1-10 after strategy
    helpfulness_rating = Column(Integer, nullable=False)  # 1-10 how helpful
    difficulty_rating = Column(Integer, nullable=True)  # 1-10 how difficult
    
    # Student feedback
    liked_aspects = Column(JSON, nullable=True)  # What they liked
    disliked_aspects = Column(JSON, nullable=True)  # What they didn't like
    suggestions = Column(Text, nullable=True)  # Student suggestions
    would_use_again = Column(Boolean, nullable=True)
    
    # Context
    usage_context = Column(String(100), nullable=True)  # where/when used
    support_received = Column(String(100), nullable=True)  # teacher, peer, independent
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    strategy = relationship("SELStrategy", back_populates="usage_logs")

    def __repr__(self):
        return f"<StrategyUsage(strategy_id='{self.strategy_id}', effectiveness={self.post_emotion_rating - self.pre_emotion_rating})>"


class ConsentRecord(Base):
    """
    Student/guardian consent for SEL data sharing and alert notifications.
    Critical for FERPA compliance and privacy protection.
    """
    __tablename__ = "consent_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(String(100), nullable=False, index=True)
    
    # Consent details
    consent_type = Column(String(100), nullable=False)  # data_sharing, alerts, research, etc.
    status = Column(SQLEnum(ConsentStatus), nullable=False)
    granted_by = Column(String(200), nullable=False)  # student, guardian, both
    granted_by_role = Column(String(50), nullable=False)  # student, parent, guardian, etc.
    
    # Scope of consent
    data_sharing_allowed = Column(Boolean, nullable=False, default=False)
    alert_notifications_allowed = Column(Boolean, nullable=False, default=False)
    counselor_sharing_allowed = Column(Boolean, nullable=False, default=False)
    parent_notification_allowed = Column(Boolean, nullable=False, default=False)
    research_participation_allowed = Column(Boolean, nullable=False, default=False)
    
    # Alert preferences
    alert_thresholds = Column(JSON, nullable=True)  # Custom thresholds per domain
    notification_methods = Column(JSON, nullable=True)  # email, phone, in_person, etc.
    emergency_contacts = Column(JSON, nullable=True)  # List of emergency contacts
    
    # Consent history
    granted_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(Text, nullable=True)
    
    # Legal compliance
    consent_document_url = Column(String(500), nullable=True)
    ip_address = Column(String(50), nullable=True)
    digital_signature = Column(String(500), nullable=True)
    witness_signature = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    alerts = relationship("SELAlert", back_populates="consent_record")

    def __repr__(self):
        return f"<ConsentRecord(student_id='{self.student_id}', status='{self.status}')>"


class SELAlert(Base):
    """
    Automated alerts triggered by concerning check-in patterns.
    Respects consent preferences for notification and escalation.
    """
    __tablename__ = "sel_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(String(100), nullable=False, index=True)
    checkin_id = Column(UUID(as_uuid=True), ForeignKey('sel_checkins.id'), nullable=False)
    consent_record_id = Column(UUID(as_uuid=True), ForeignKey('consent_records.id'), nullable=True)
    
    # Alert details
    alert_type = Column(String(100), nullable=False)  # threshold_exceeded, pattern_detected, etc.
    alert_level = Column(SQLEnum(AlertLevel), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Triggering conditions
    trigger_domain = Column(SQLEnum(SELDomain), nullable=False)
    trigger_value = Column(Float, nullable=False)  # The value that triggered alert
    threshold_value = Column(Float, nullable=False)  # The threshold that was exceeded
    pattern_data = Column(JSON, nullable=True)  # Supporting pattern analysis
    
    # Risk assessment
    risk_score = Column(Float, nullable=False)  # 0-100 risk score
    risk_factors = Column(JSON, nullable=False)  # List of contributing factors
    protective_factors = Column(JSON, nullable=True)  # Mitigating factors
    
    # Notification details
    notifications_sent = Column(JSON, nullable=True)  # List of notifications sent
    recipients = Column(JSON, nullable=True)  # Who was notified
    notification_methods = Column(JSON, nullable=True)  # How they were notified
    
    # Response tracking
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE)
    acknowledged_by = Column(String(200), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, nullable=False, default=True)
    
    # Consent compliance
    consent_verified = Column(Boolean, nullable=False, default=False)
    consent_override_reason = Column(Text, nullable=True)  # If alert sent without consent
    privacy_level = Column(String(50), nullable=False, default="confidential")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    checkin = relationship("SELCheckIn", back_populates="alerts")
    consent_record = relationship("ConsentRecord", back_populates="alerts")

    def __repr__(self):
        return f"<SELAlert(student_id='{self.student_id}', level='{self.alert_level}', status='{self.status}')>"


class SELReport(Base):
    """
    Comprehensive SEL reports for students, teachers, and administrators.
    Aggregates data across time periods with privacy controls.
    """
    __tablename__ = "sel_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(String(100), nullable=False, index=True)
    
    # Report metadata
    report_type = Column(String(100), nullable=False)  # weekly, monthly, semester, annual
    report_period_start = Column(DateTime(timezone=True), nullable=False)
    report_period_end = Column(DateTime(timezone=True), nullable=False)
    generated_for = Column(String(100), nullable=False)  # student, teacher, parent, counselor
    
    # Summary statistics
    total_checkins = Column(Integer, nullable=False, default=0)
    average_emotion_intensity = Column(Float, nullable=True)
    most_common_emotion = Column(SQLEnum(EmotionType), nullable=True)
    trend_direction = Column(String(50), nullable=True)  # improving, stable, declining
    
    # SEL domain progress
    domain_scores = Column(JSON, nullable=False)  # Average scores per domain
    domain_trends = Column(JSON, nullable=True)  # Trend analysis per domain
    growth_indicators = Column(JSON, nullable=True)  # Areas of growth
    areas_for_support = Column(JSON, nullable=True)  # Areas needing attention
    
    # Strategy effectiveness
    strategies_used = Column(Integer, nullable=False, default=0)
    strategy_success_rate = Column(Float, nullable=True)
    preferred_strategies = Column(JSON, nullable=True)  # Most effective strategies
    
    # Alert summary
    total_alerts = Column(Integer, nullable=False, default=0)
    alert_trends = Column(JSON, nullable=True)  # Alert frequency over time
    resolution_rate = Column(Float, nullable=True)
    
    # Insights and recommendations
    key_insights = Column(JSON, nullable=True)  # AI-generated insights
    recommendations = Column(JSON, nullable=True)  # Suggested actions
    celebration_points = Column(JSON, nullable=True)  # Positive achievements
    
    # Report content
    report_data = Column(JSON, nullable=False)  # Full report data
    visualizations = Column(JSON, nullable=True)  # Chart/graph configurations
    narrative_summary = Column(Text, nullable=True)  # Human-readable summary
    
    # Privacy and sharing
    privacy_level = Column(String(50), nullable=False, default="confidential")
    shared_with = Column(JSON, nullable=True)  # Who has access
    consent_verified = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SELReport(student_id='{self.student_id}', type='{self.report_type}', period='{self.report_period_start}' to '{self.report_period_end}')>"


# Indexes for performance optimization
from sqlalchemy import Index

# Composite indexes for common queries
Index('idx_checkin_student_date', SELCheckIn.student_id, SELCheckIn.checkin_date)
Index('idx_strategy_student_type', SELStrategy.student_id, SELStrategy.strategy_type)
Index('idx_alert_student_status', SELAlert.student_id, SELAlert.status)
Index('idx_consent_student_type', ConsentRecord.student_id, ConsentRecord.consent_type)
Index('idx_report_student_period', SELReport.student_id, SELReport.report_period_start, SELReport.report_period_end)
