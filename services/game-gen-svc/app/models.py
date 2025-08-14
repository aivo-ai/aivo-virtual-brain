# AIVO Game Generation Service - Data Models
# S2-13 Implementation - Dynamic reset game generation

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON, ForeignKey, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

Base = declarative_base()


class GradeBand(str, Enum):
    """Educational grade bands for game adaptation."""
    EARLY_ELEMENTARY = "early_elementary"      # K-2
    LATE_ELEMENTARY = "late_elementary"        # 3-5
    MIDDLE_SCHOOL = "middle_school"            # 6-8
    HIGH_SCHOOL = "high_school"                # 9-12
    ADULT = "adult"                            # Adult learners


class GameType(str, Enum):
    """Types of reset games available."""
    PUZZLE = "puzzle"                          # Logic and problem-solving
    MEMORY = "memory"                          # Memory and recall games
    PATTERN = "pattern"                        # Pattern recognition
    WORD = "word"                              # Word games and vocabulary
    MATH = "math"                              # Mathematical games
    CREATIVE = "creative"                      # Creative expression
    MINDFULNESS = "mindfulness"                # Relaxation and breathing
    MOVEMENT = "movement"                      # Physical activity games
    STRATEGY = "strategy"                      # Strategic thinking
    TRIVIA = "trivia"                          # Knowledge-based games


class GameDifficulty(str, Enum):
    """Game difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADAPTIVE = "adaptive"                      # Adjusts based on performance


class GameStatus(str, Enum):
    """Game generation and completion status."""
    GENERATING = "generating"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class SubjectArea(str, Enum):
    """Subject areas for educational games."""
    MATH = "math"
    ENGLISH = "english"
    SCIENCE = "science"
    SOCIAL_STUDIES = "social_studies"
    ART = "art"
    MUSIC = "music"
    PE = "physical_education"
    GENERAL = "general"                        # Non-specific subject


class LearnerProfile(Base):
    """Learner profile for personalized game generation."""
    
    __tablename__ = "learner_profiles"
    
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    learner_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False, unique=True)
    
    # Basic demographics
    grade_band = Column(String(50), nullable=False, default=GradeBand.MIDDLE_SCHOOL)
    age_group = Column(String(50), nullable=True)
    
    # Game preferences
    preferred_game_types = Column(JSON, nullable=True)  # List[GameType]
    disliked_game_types = Column(JSON, nullable=True)   # List[GameType]
    preferred_difficulty = Column(String(20), nullable=False, default=GameDifficulty.ADAPTIVE)
    favorite_subjects = Column(JSON, nullable=True)     # List[SubjectArea]
    
    # Learning traits and characteristics
    learning_traits = Column(JSON, nullable=True)       # Dict[str, Any]
    attention_span_minutes = Column(Integer, nullable=True)
    preferred_interaction_style = Column(String(50), nullable=True)  # visual, auditory, kinesthetic
    accessibility_needs = Column(JSON, nullable=True)   # List[str]
    
    # Performance and adaptation data
    skill_levels = Column(JSON, nullable=True)          # Dict[subject, level]
    performance_history = Column(JSON, nullable=True)   # Recent game performance
    adaptation_parameters = Column(JSON, nullable=True) # AI adaptation settings
    
    # Behavioral preferences
    competitive_preference = Column(Boolean, nullable=True)
    social_play_preference = Column(Boolean, nullable=True)
    reward_preferences = Column(JSON, nullable=True)    # Types of rewards preferred
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_game_request = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    games = relationship("GameManifest", back_populates="learner_profile")


class GameManifest(Base):
    """Generated game manifest with complete game definition."""
    
    __tablename__ = "game_manifests"
    
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    learner_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    learner_profile_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey('learner_profiles.id'), nullable=True)
    
    # Game identification
    game_title = Column(String(200), nullable=False)
    game_type = Column(String(50), nullable=False)
    game_description = Column(Text, nullable=True)
    game_version = Column(String(20), nullable=False, default="1.0.0")
    
    # Generation parameters
    subject_area = Column(String(50), nullable=False, default=SubjectArea.GENERAL)
    target_duration_minutes = Column(Integer, nullable=False)
    difficulty_level = Column(String(20), nullable=False, default=GameDifficulty.MEDIUM)
    grade_band = Column(String(50), nullable=False)
    
    # Request context
    request_traits = Column(JSON, nullable=True)        # Traits from generation request
    generation_context = Column(JSON, nullable=True)    # Context and parameters used
    
    # Game definition
    game_scenes = Column(JSON, nullable=False)          # List[GameScene]
    game_assets = Column(JSON, nullable=False)          # List[GameAsset]
    game_rules = Column(JSON, nullable=False)           # GameRules object
    game_config = Column(JSON, nullable=True)           # Additional configuration
    
    # Interactive elements
    user_interface = Column(JSON, nullable=True)        # UI configuration
    scoring_system = Column(JSON, nullable=True)        # Scoring and rewards
    hint_system = Column(JSON, nullable=True)           # Help and hints
    accessibility_features = Column(JSON, nullable=True) # Accessibility options
    
    # Timing and constraints
    estimated_duration_minutes = Column(Float, nullable=False)
    min_duration_minutes = Column(Float, nullable=True)
    max_duration_minutes = Column(Float, nullable=True)
    timeout_behavior = Column(String(50), nullable=False, default="graceful_end")
    
    # Status and lifecycle
    status = Column(String(20), nullable=False, default=GameStatus.GENERATING)
    generation_started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    generation_completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Performance tracking
    expected_learning_outcomes = Column(JSON, nullable=True)  # List[str]
    success_metrics = Column(JSON, nullable=True)            # Dict[metric, target]
    adaptation_triggers = Column(JSON, nullable=True)        # Conditions for difficulty adjustment
    
    # Generation metadata
    generation_engine_version = Column(String(50), nullable=False, default="1.0.0")
    ai_model_used = Column(String(100), nullable=True)
    generation_parameters = Column(JSON, nullable=True)
    quality_score = Column(Float, nullable=True)             # Generated quality assessment
    
    # Error handling
    generation_errors = Column(JSON, nullable=True)          # Any errors during generation
    fallback_used = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    learner_profile = relationship("LearnerProfile", back_populates="games")
    sessions = relationship("GameSession", back_populates="game_manifest")


class GameSession(Base):
    """Game session tracking actual gameplay."""
    
    __tablename__ = "game_sessions"
    
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    learner_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    game_manifest_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey('game_manifests.id'), nullable=False)
    
    # Session tracking
    session_started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    session_ended_at = Column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes = Column(Float, nullable=True)
    session_status = Column(String(20), nullable=False, default="active")
    
    # Gameplay data
    current_scene = Column(String(100), nullable=True)
    progress_percentage = Column(Float, nullable=False, default=0.0)
    score = Column(Integer, nullable=False, default=0)
    achievements = Column(JSON, nullable=True)              # List[str]
    
    # Performance metrics
    correct_answers = Column(Integer, nullable=False, default=0)
    incorrect_answers = Column(Integer, nullable=False, default=0)
    hints_used = Column(Integer, nullable=False, default=0)
    time_spent_per_scene = Column(JSON, nullable=True)      # Dict[scene_id, seconds]
    
    # Engagement metrics
    interaction_count = Column(Integer, nullable=False, default=0)
    pause_count = Column(Integer, nullable=False, default=0)
    restart_count = Column(Integer, nullable=False, default=0)
    engagement_score = Column(Float, nullable=True)         # 0-100
    
    # Learning analytics
    learning_objectives_met = Column(JSON, nullable=True)   # List[str]
    difficulty_adjustments = Column(JSON, nullable=True)    # List[adjustment_events]
    behavioral_observations = Column(JSON, nullable=True)   # AI observations
    
    # Completion data
    completion_reason = Column(String(50), nullable=True)   # "finished", "timeout", "quit"
    final_feedback = Column(Text, nullable=True)
    learner_satisfaction = Column(Integer, nullable=True)   # 1-5 rating
    would_play_again = Column(Boolean, nullable=True)
    
    # Technical data
    client_info = Column(JSON, nullable=True)              # Device, browser, etc.
    performance_issues = Column(JSON, nullable=True)       # Technical problems
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    game_manifest = relationship("GameManifest", back_populates="sessions")


class GameTemplate(Base):
    """Reusable game templates for rapid generation."""
    
    __tablename__ = "game_templates"
    
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    
    # Template identification
    template_name = Column(String(200), nullable=False)
    template_type = Column(String(50), nullable=False)     # GameType
    template_description = Column(Text, nullable=True)
    template_version = Column(String(20), nullable=False, default="1.0.0")
    
    # Applicability
    supported_grade_bands = Column(JSON, nullable=False)   # List[GradeBand]
    supported_subjects = Column(JSON, nullable=False)      # List[SubjectArea]
    supported_durations = Column(JSON, nullable=False)     # {"min": 5, "max": 30}
    
    # Template structure
    template_scenes = Column(JSON, nullable=False)         # Scene templates
    template_assets = Column(JSON, nullable=False)         # Asset templates
    template_rules = Column(JSON, nullable=False)          # Rule templates
    customization_points = Column(JSON, nullable=False)    # Areas for customization
    
    # Generation parameters
    difficulty_variations = Column(JSON, nullable=True)    # Per difficulty level
    subject_adaptations = Column(JSON, nullable=True)      # Per subject customizations
    age_adaptations = Column(JSON, nullable=True)          # Per age group modifications
    
    # Quality metrics
    usage_count = Column(Integer, nullable=False, default=0)
    average_rating = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Template metadata
    created_by = Column(String(100), nullable=True)        # Creator identifier
    is_active = Column(Boolean, nullable=False, default=True)
    requires_review = Column(Boolean, nullable=False, default=False)
    tags = Column(JSON, nullable=True)                     # List[str] for categorization
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class GameAnalytics(Base):
    """Analytics and insights from game sessions."""
    
    __tablename__ = "game_analytics"
    
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    learner_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    
    # Analysis period
    analysis_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Aggregate metrics
    total_games_played = Column(Integer, nullable=False, default=0)
    total_time_minutes = Column(Float, nullable=False, default=0.0)
    average_session_duration = Column(Float, nullable=True)
    completion_rate = Column(Float, nullable=True)
    
    # Performance insights
    favorite_game_types = Column(JSON, nullable=True)      # List[GameType] by frequency
    preferred_difficulty = Column(String(20), nullable=True)
    strongest_subjects = Column(JSON, nullable=True)       # List[SubjectArea] by performance
    improvement_areas = Column(JSON, nullable=True)        # List[SubjectArea] needing work
    
    # Engagement patterns
    peak_engagement_times = Column(JSON, nullable=True)    # Time patterns
    attention_span_analysis = Column(JSON, nullable=True)  # Duration analysis
    interaction_patterns = Column(JSON, nullable=True)     # Behavioral patterns
    
    # Learning outcomes
    learning_objectives_achieved = Column(JSON, nullable=True)  # List[str]
    skill_progression = Column(JSON, nullable=True)            # Dict[skill, progress]
    knowledge_gaps = Column(JSON, nullable=True)               # List[str]
    
    # Recommendations
    recommended_game_types = Column(JSON, nullable=True)    # AI recommendations
    suggested_difficulty_adjustments = Column(JSON, nullable=True)
    personalization_suggestions = Column(JSON, nullable=True)
    
    # Quality metrics
    confidence_score = Column(Float, nullable=True)        # Analysis confidence 0-1
    data_completeness = Column(Float, nullable=True)       # Data quality 0-1
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# Helper classes for structured data within JSON fields

class GameScene:
    """Structure for individual game scenes."""
    
    def __init__(self, 
                 scene_id: str,
                 scene_name: str,
                 scene_type: str,
                 duration_minutes: float,
                 content: Dict[str, Any],
                 interactions: List[Dict[str, Any]] = None,
                 transitions: List[str] = None):
        self.scene_id = scene_id
        self.scene_name = scene_name
        self.scene_type = scene_type
        self.duration_minutes = duration_minutes
        self.content = content
        self.interactions = interactions or []
        self.transitions = transitions or []
    
    def to_dict(self):
        return {
            "scene_id": self.scene_id,
            "scene_name": self.scene_name,
            "scene_type": self.scene_type,
            "duration_minutes": self.duration_minutes,
            "content": self.content,
            "interactions": self.interactions,
            "transitions": self.transitions
        }


class GameAsset:
    """Structure for game assets (images, sounds, etc.)."""
    
    def __init__(self,
                 asset_id: str,
                 asset_type: str,
                 asset_url: Optional[str] = None,
                 asset_data: Optional[Dict[str, Any]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.asset_id = asset_id
        self.asset_type = asset_type  # "image", "sound", "video", "text", "data"
        self.asset_url = asset_url
        self.asset_data = asset_data
        self.metadata = metadata or {}
    
    def to_dict(self):
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "asset_url": self.asset_url,
            "asset_data": self.asset_data,
            "metadata": self.metadata
        }


class GameRules:
    """Structure for game rules and mechanics."""
    
    def __init__(self,
                 scoring_rules: Dict[str, Any],
                 win_conditions: List[str],
                 lose_conditions: List[str] = None,
                 time_limits: Optional[Dict[str, float]] = None,
                 difficulty_scaling: Optional[Dict[str, Any]] = None,
                 player_actions: Optional[List[str]] = None):
        self.scoring_rules = scoring_rules
        self.win_conditions = win_conditions
        self.lose_conditions = lose_conditions or []
        self.time_limits = time_limits or {}
        self.difficulty_scaling = difficulty_scaling or {}
        self.player_actions = player_actions or []
    
    def to_dict(self):
        return {
            "scoring_rules": self.scoring_rules,
            "win_conditions": self.win_conditions,
            "lose_conditions": self.lose_conditions,
            "time_limits": self.time_limits,
            "difficulty_scaling": self.difficulty_scaling,
            "player_actions": self.player_actions
        }
