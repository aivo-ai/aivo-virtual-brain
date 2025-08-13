"""
AIVO Orchestrator Service - Orchestration Logic Engine
S1-14 Implementation

Core orchestration logic for processing educational events and generating
intelligent level suggestions and game break triggers.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .consumer import Event, EventType, OrchestrationAction, ActionType

logger = logging.getLogger(__name__)


class DifficultyLevel(str, Enum):
    """Learning difficulty levels"""
    BEGINNER = "beginner"
    EASY = "easy"
    MODERATE = "moderate"
    CHALLENGING = "challenging"
    ADVANCED = "advanced"


class EngagementLevel(str, Enum):
    """Learner engagement levels"""
    VERY_LOW = "very_low"
    LOW = "low" 
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class LearnerState:
    """Current state of a learner"""
    learner_id: str
    tenant_id: str
    current_level: DifficultyLevel = DifficultyLevel.MODERATE
    engagement_score: float = 0.5  # 0.0 - 1.0
    performance_score: float = 0.5  # 0.0 - 1.0
    consecutive_correct: int = 0
    consecutive_incorrect: int = 0
    session_duration_minutes: int = 0
    break_due_time: Optional[datetime] = None
    last_break_time: Optional[datetime] = None
    sel_alerts: List[Dict[str, Any]] = field(default_factory=list)
    baseline_established: bool = False
    slp_data: Optional[Dict[str, Any]] = None
    recent_assessments: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class OrchestrationRules:
    """Rule-based orchestration logic"""
    
    # Level suggestion thresholds
    LEVEL_UP_THRESHOLD = 0.85  # Performance score to level up
    LEVEL_DOWN_THRESHOLD = 0.35  # Performance score to level down
    CONSECUTIVE_CORRECT_THRESHOLD = 5  # Consecutive correct for level up
    CONSECUTIVE_INCORRECT_THRESHOLD = 3  # Consecutive incorrect for level down
    
    # Game break thresholds
    MAX_SESSION_DURATION = 25  # Minutes before suggesting break
    MIN_BREAK_INTERVAL = 15  # Minimum minutes between breaks
    LOW_ENGAGEMENT_THRESHOLD = 0.3  # Engagement score for immediate break
    
    # SEL intervention thresholds
    SEL_ALERT_THRESHOLD = 2  # Number of alerts in timeframe
    SEL_ALERT_TIMEFRAME_HOURS = 1  # Timeframe for alert counting
    
    # Performance analysis weights
    RECENT_PERFORMANCE_WEIGHT = 0.7  # Weight for recent performance
    BASELINE_PERFORMANCE_WEIGHT = 0.3  # Weight for baseline performance


class OrchestrationEngine:
    """Core orchestration engine with rule-based intelligence"""
    
    def __init__(self):
        self.learner_states: Dict[str, LearnerState] = {}
        self.rules = OrchestrationRules()
        self.is_initialized = False
        
        # Statistics tracking
        self.stats = {
            "level_suggestions_sent": 0,
            "game_breaks_scheduled": 0,
            "sel_interventions_triggered": 0,
            "learning_path_updates": 0,
            "total_events_processed": 0
        }
        
    async def initialize(self):
        """Initialize orchestration engine"""
        logger.info("Initializing orchestration engine...")
        
        # Load learner states from database (mock for now)
        await self._load_learner_states()
        
        self.is_initialized = True
        logger.info("Orchestration engine initialized")
        
    async def process_event(self, event: Event) -> List[OrchestrationAction]:
        """Process an event and generate orchestration actions"""
        if not self.is_initialized:
            await self.initialize()
            
        logger.info(f"Processing {event.type} event for learner {event.learner_id}")
        
        # Update learner state
        learner_state = self._get_or_create_learner_state(event.learner_id, event.tenant_id)
        await self._update_learner_state(learner_state, event)
        
        # Generate actions based on event type
        actions = []
        
        if event.type == EventType.BASELINE_COMPLETE:
            actions.extend(await self._handle_baseline_complete(learner_state, event))
        elif event.type == EventType.SLP_UPDATED:
            actions.extend(await self._handle_slp_updated(learner_state, event))
        elif event.type == EventType.SEL_ALERT:
            actions.extend(await self._handle_sel_alert(learner_state, event))
        elif event.type == EventType.COURSEWORK_ANALYZED:
            actions.extend(await self._handle_coursework_analyzed(learner_state, event))
        elif event.type == EventType.ASSESSMENT_COMPLETE:
            actions.extend(await self._handle_assessment_complete(learner_state, event))
        elif event.type == EventType.LEARNER_PROGRESS:
            actions.extend(await self._handle_learner_progress(learner_state, event))
        elif event.type == EventType.ENGAGEMENT_LOW:
            actions.extend(await self._handle_engagement_low(learner_state, event))
        
        # Check for universal actions (game breaks, general optimizations)
        actions.extend(await self._check_universal_actions(learner_state))
        
        # Update statistics
        self.stats["total_events_processed"] += 1
        for action in actions:
            if action.type == ActionType.LEVEL_SUGGESTED:
                self.stats["level_suggestions_sent"] += 1
            elif action.type == ActionType.GAME_BREAK:
                self.stats["game_breaks_scheduled"] += 1
            elif action.type == ActionType.SEL_INTERVENTION:
                self.stats["sel_interventions_triggered"] += 1
            elif action.type == ActionType.LEARNING_PATH_UPDATE:
                self.stats["learning_path_updates"] += 1
                
        logger.info(f"Generated {len(actions)} actions for learner {event.learner_id}")
        return actions
        
    async def _handle_baseline_complete(
        self, 
        learner_state: LearnerState, 
        event: Event
    ) -> List[OrchestrationAction]:
        """Handle baseline assessment completion"""
        actions = []
        
        baseline_data = event.data
        performance_score = baseline_data.get("overall_score", 0.5)
        strengths = baseline_data.get("strengths", [])
        challenges = baseline_data.get("challenges", [])
        
        # Update learner state
        learner_state.baseline_established = True
        learner_state.performance_score = performance_score
        
        # Suggest initial difficulty level based on baseline
        suggested_level = self._determine_initial_level(performance_score, baseline_data)
        
        if suggested_level != learner_state.current_level:
            action = OrchestrationAction(
                id=str(uuid.uuid4()),
                type=ActionType.LEVEL_SUGGESTED,
                target_service="learner-svc",
                learner_id=learner_state.learner_id,
                tenant_id=learner_state.tenant_id,
                action_data={
                    "level": suggested_level.value,
                    "reason": "Initial level assignment based on baseline assessment",
                    "confidence": 0.85,
                    "baseline_data": {
                        "performance_score": performance_score,
                        "strengths": strengths,
                        "challenges": challenges
                    }
                }
            )
            actions.append(action)
            learner_state.current_level = suggested_level
            
        # Create personalized learning path
        learning_path_action = OrchestrationAction(
            id=str(uuid.uuid4()),
            type=ActionType.LEARNING_PATH_UPDATE,
            target_service="learner-svc",
            learner_id=learner_state.learner_id,
            tenant_id=learner_state.tenant_id,
            action_data={
                "path_updates": {
                    "focus_areas": challenges,
                    "strength_areas": strengths,
                    "initial_level": suggested_level.value,
                    "adaptation_enabled": True
                },
                "reason": "Personalized path based on baseline assessment"
            }
        )
        actions.append(learning_path_action)
        
        return actions
        
    async def _handle_slp_updated(
        self, 
        learner_state: LearnerState, 
        event: Event
    ) -> List[OrchestrationAction]:
        """Handle Speech Language Pathology update"""
        actions = []
        
        slp_data = event.data
        learner_state.slp_data = slp_data
        
        # Check for communication support needs
        communication_score = slp_data.get("communication_score", 0.5)
        recommendations = slp_data.get("recommendations", [])
        
        # Adjust difficulty if communication issues detected
        if communication_score < 0.4:
            # Lower difficulty to reduce cognitive load
            if learner_state.current_level not in [DifficultyLevel.BEGINNER, DifficultyLevel.EASY]:
                new_level = DifficultyLevel.EASY if learner_state.current_level == DifficultyLevel.MODERATE else DifficultyLevel.BEGINNER
                
                action = OrchestrationAction(
                    id=str(uuid.uuid4()),
                    type=ActionType.LEVEL_SUGGESTED,
                    target_service="learner-svc",
                    learner_id=learner_state.learner_id,
                    tenant_id=learner_state.tenant_id,
                    action_data={
                        "level": new_level.value,
                        "reason": "Adjusted for speech-language needs",
                        "confidence": 0.75,
                        "slp_considerations": {
                            "communication_score": communication_score,
                            "recommendations": recommendations
                        }
                    }
                )
                actions.append(action)
                learner_state.current_level = new_level
                
        return actions
        
    async def _handle_sel_alert(
        self, 
        learner_state: LearnerState, 
        event: Event
    ) -> List[OrchestrationAction]:
        """Handle Social-Emotional Learning alert"""
        actions = []
        
        alert_data = event.data
        alert_type = alert_data.get("alert_type", "general")
        severity = alert_data.get("severity", "moderate")
        
        # Add alert to learner state
        learner_state.sel_alerts.append({
            "timestamp": event.timestamp,
            "alert_type": alert_type,
            "severity": severity,
            "data": alert_data
        })
        
        # Check if intervention threshold reached
        recent_alerts = self._get_recent_sel_alerts(learner_state)
        
        if len(recent_alerts) >= self.rules.SEL_ALERT_THRESHOLD or severity == "high":
            # Trigger SEL intervention
            intervention_action = OrchestrationAction(
                id=str(uuid.uuid4()),
                type=ActionType.SEL_INTERVENTION,
                target_service="notification-svc",
                learner_id=learner_state.learner_id,
                tenant_id=learner_state.tenant_id,
                action_data={
                    "intervention_type": alert_type,
                    "urgency": "high" if severity == "high" else "moderate",
                    "message": self._generate_sel_message(alert_type, recent_alerts),
                    "intervention_url": f"/sel/{alert_type}",
                    "recent_alerts_count": len(recent_alerts)
                }
            )
            actions.append(intervention_action)
            
            # Also suggest a break for emotional regulation
            break_action = OrchestrationAction(
                id=str(uuid.uuid4()),
                type=ActionType.GAME_BREAK,
                target_service="notification-svc",
                learner_id=learner_state.learner_id,
                tenant_id=learner_state.tenant_id,
                action_data={
                    "break_type": "mindfulness",
                    "duration": 5,
                    "message": "Let's take a moment to breathe and reset.",
                    "game_url": "/games/mindfulness"
                }
            )
            actions.append(break_action)
            
        return actions
        
    async def _handle_coursework_analyzed(
        self, 
        learner_state: LearnerState, 
        event: Event
    ) -> List[OrchestrationAction]:
        """Handle coursework analysis completion"""
        actions = []
        
        analysis_data = event.data
        performance_metrics = analysis_data.get("performance_metrics", {})
        accuracy = performance_metrics.get("accuracy", 0.5)
        engagement_score = performance_metrics.get("engagement", 0.5)
        time_efficiency = performance_metrics.get("time_efficiency", 0.5)
        
        # Update learner state
        learner_state.performance_score = accuracy
        learner_state.engagement_score = engagement_score
        learner_state.session_duration_minutes += analysis_data.get("session_duration", 0)
        
        # Track consecutive performance
        if accuracy >= 0.8:
            learner_state.consecutive_correct += 1
            learner_state.consecutive_incorrect = 0
        elif accuracy <= 0.4:
            learner_state.consecutive_incorrect += 1
            learner_state.consecutive_correct = 0
        else:
            learner_state.consecutive_correct = 0
            learner_state.consecutive_incorrect = 0
            
        # Check for level adjustment
        level_action = await self._check_level_adjustment(learner_state)
        if level_action:
            actions.append(level_action)
            
        # Check for learning path optimization
        if "learning_gaps" in analysis_data:
            path_action = OrchestrationAction(
                id=str(uuid.uuid4()),
                type=ActionType.LEARNING_PATH_UPDATE,
                target_service="learner-svc",
                learner_id=learner_state.learner_id,
                tenant_id=learner_state.tenant_id,
                action_data={
                    "path_updates": {
                        "remediation_topics": analysis_data["learning_gaps"],
                        "acceleration_topics": analysis_data.get("mastery_areas", []),
                        "engagement_adjustments": self._suggest_engagement_adjustments(engagement_score)
                    },
                    "reason": "Optimization based on coursework analysis"
                }
            )
            actions.append(path_action)
            
        return actions
        
    async def _handle_assessment_complete(
        self, 
        learner_state: LearnerState, 
        event: Event
    ) -> List[OrchestrationAction]:
        """Handle assessment completion"""
        actions = []
        
        assessment_data = event.data
        score = assessment_data.get("score", 0.5)
        percentile = assessment_data.get("percentile", 50)
        
        # Add to recent assessments
        learner_state.recent_assessments.append({
            "timestamp": event.timestamp,
            "score": score,
            "percentile": percentile,
            "assessment_type": assessment_data.get("assessment_type", "unknown")
        })
        
        # Keep only recent assessments
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        learner_state.recent_assessments = [
            a for a in learner_state.recent_assessments 
            if a["timestamp"] > cutoff_date
        ]
        
        # Update performance score based on trend
        recent_scores = [a["score"] for a in learner_state.recent_assessments[-3:]]
        learner_state.performance_score = sum(recent_scores) / len(recent_scores)
        
        # Check for level adjustment based on assessment performance
        level_action = await self._check_level_adjustment(learner_state)
        if level_action:
            actions.append(level_action)
            
        return actions
        
    async def _handle_learner_progress(
        self, 
        learner_state: LearnerState, 
        event: Event
    ) -> List[OrchestrationAction]:
        """Handle learner progress update"""
        actions = []
        
        progress_data = event.data
        learner_state.performance_score = progress_data.get("performance_score", learner_state.performance_score)
        learner_state.engagement_score = progress_data.get("engagement_score", learner_state.engagement_score)
        
        # Check for level adjustment
        level_action = await self._check_level_adjustment(learner_state)
        if level_action:
            actions.append(level_action)
            
        return actions
        
    async def _handle_engagement_low(
        self, 
        learner_state: LearnerState, 
        event: Event
    ) -> List[OrchestrationAction]:
        """Handle low engagement event"""
        actions = []
        
        # Immediate game break for low engagement
        break_action = OrchestrationAction(
            id=str(uuid.uuid4()),
            type=ActionType.GAME_BREAK,
            target_service="notification-svc",
            learner_id=learner_state.learner_id,
            tenant_id=learner_state.tenant_id,
            action_data={
                "break_type": "energizer",
                "duration": 3,
                "message": "Let's recharge with a quick brain energizer!",
                "game_url": "/games/energizer"
            }
        )
        actions.append(break_action)
        
        # Lower difficulty temporarily
        if learner_state.current_level not in [DifficultyLevel.BEGINNER, DifficultyLevel.EASY]:
            temp_level = DifficultyLevel.EASY
            level_action = OrchestrationAction(
                id=str(uuid.uuid4()),
                type=ActionType.LEVEL_SUGGESTED,
                target_service="learner-svc",
                learner_id=learner_state.learner_id,
                tenant_id=learner_state.tenant_id,
                action_data={
                    "level": temp_level.value,
                    "reason": "Temporary adjustment for low engagement",
                    "confidence": 0.6,
                    "temporary": True
                }
            )
            actions.append(level_action)
            
        return actions
        
    async def _check_universal_actions(self, learner_state: LearnerState) -> List[OrchestrationAction]:
        """Check for universal actions like scheduled breaks"""
        actions = []
        
        # Check for game break due to session duration
        if (learner_state.session_duration_minutes >= self.rules.MAX_SESSION_DURATION and
            self._is_break_due(learner_state)):
            
            break_action = OrchestrationAction(
                id=str(uuid.uuid4()),
                type=ActionType.GAME_BREAK,
                target_service="notification-svc",
                learner_id=learner_state.learner_id,
                tenant_id=learner_state.tenant_id,
                action_data={
                    "break_type": "movement",
                    "duration": 5,
                    "message": "Great work! Time for a movement break.",
                    "game_url": "/games/movement",
                    "reason": "Extended session duration"
                }
            )
            actions.append(break_action)
            learner_state.last_break_time = datetime.utcnow()
            learner_state.session_duration_minutes = 0
            
        # Check for immediate break due to low engagement
        elif (learner_state.engagement_score < self.rules.LOW_ENGAGEMENT_THRESHOLD and
              self._is_break_due(learner_state)):
            
            break_action = OrchestrationAction(
                id=str(uuid.uuid4()),
                type=ActionType.GAME_BREAK,
                target_service="notification-svc",
                learner_id=learner_state.learner_id,
                tenant_id=learner_state.tenant_id,
                action_data={
                    "break_type": "attention",
                    "duration": 3,
                    "message": "Let's refocus with a quick attention game!",
                    "game_url": "/games/attention",
                    "reason": "Low engagement detected"
                }
            )
            actions.append(break_action)
            learner_state.last_break_time = datetime.utcnow()
            
        return actions
        
    async def _check_level_adjustment(self, learner_state: LearnerState) -> Optional[OrchestrationAction]:
        """Check if level adjustment is needed"""
        
        current_level_index = list(DifficultyLevel).index(learner_state.current_level)
        suggested_level = learner_state.current_level
        reason = ""
        confidence = 0.5
        
        # Check for level up conditions
        if (learner_state.performance_score >= self.rules.LEVEL_UP_THRESHOLD or
            learner_state.consecutive_correct >= self.rules.CONSECUTIVE_CORRECT_THRESHOLD):
            
            if current_level_index < len(DifficultyLevel) - 1:
                suggested_level = list(DifficultyLevel)[current_level_index + 1]
                reason = f"Level up due to high performance (score: {learner_state.performance_score:.2f}, consecutive correct: {learner_state.consecutive_correct})"
                confidence = 0.8
                
        # Check for level down conditions
        elif (learner_state.performance_score <= self.rules.LEVEL_DOWN_THRESHOLD or
              learner_state.consecutive_incorrect >= self.rules.CONSECUTIVE_INCORRECT_THRESHOLD):
              
            if current_level_index > 0:
                suggested_level = list(DifficultyLevel)[current_level_index - 1]
                reason = f"Level down due to low performance (score: {learner_state.performance_score:.2f}, consecutive incorrect: {learner_state.consecutive_incorrect})"
                confidence = 0.8
                
        # Return action if level change suggested
        if suggested_level != learner_state.current_level:
            learner_state.current_level = suggested_level
            
            return OrchestrationAction(
                id=str(uuid.uuid4()),
                type=ActionType.LEVEL_SUGGESTED,
                target_service="learner-svc",
                learner_id=learner_state.learner_id,
                tenant_id=learner_state.tenant_id,
                action_data={
                    "level": suggested_level.value,
                    "reason": reason,
                    "confidence": confidence,
                    "performance_data": {
                        "current_score": learner_state.performance_score,
                        "consecutive_correct": learner_state.consecutive_correct,
                        "consecutive_incorrect": learner_state.consecutive_incorrect
                    }
                }
            )
            
        return None
        
    def _determine_initial_level(
        self, 
        performance_score: float, 
        baseline_data: Dict[str, Any]
    ) -> DifficultyLevel:
        """Determine initial difficulty level from baseline"""
        
        if performance_score >= 0.9:
            return DifficultyLevel.ADVANCED
        elif performance_score >= 0.75:
            return DifficultyLevel.CHALLENGING
        elif performance_score >= 0.5:
            return DifficultyLevel.MODERATE
        elif performance_score >= 0.25:
            return DifficultyLevel.EASY
        else:
            return DifficultyLevel.BEGINNER
            
    def _get_recent_sel_alerts(self, learner_state: LearnerState) -> List[Dict[str, Any]]:
        """Get SEL alerts within the recent timeframe"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.rules.SEL_ALERT_TIMEFRAME_HOURS)
        
        return [
            alert for alert in learner_state.sel_alerts
            if alert["timestamp"] > cutoff_time
        ]
        
    def _generate_sel_message(
        self, 
        alert_type: str, 
        recent_alerts: List[Dict[str, Any]]
    ) -> str:
        """Generate appropriate SEL intervention message"""
        
        if alert_type == "anxiety":
            return "We notice you might be feeling worried. Let's practice some calming techniques together."
        elif alert_type == "frustration":
            return "It's okay to feel frustrated sometimes. Let's take a break and try a different approach."
        elif alert_type == "confidence":
            return "Remember, everyone learns at their own pace. You're doing great - let's build on your strengths!"
        elif alert_type == "attention":
            return "Having trouble focusing? That's normal! Let's try some attention-building activities."
        else:
            return "We're here to support you. Let's work together to make learning more comfortable."
            
    def _suggest_engagement_adjustments(self, engagement_score: float) -> Dict[str, Any]:
        """Suggest engagement adjustments based on score"""
        
        if engagement_score < 0.3:
            return {
                "gamification_level": "high",
                "break_frequency": "increased",
                "content_variety": "high",
                "interaction_type": "active"
            }
        elif engagement_score < 0.6:
            return {
                "gamification_level": "moderate",
                "break_frequency": "normal",
                "content_variety": "moderate",
                "interaction_type": "mixed"
            }
        else:
            return {
                "gamification_level": "low",
                "break_frequency": "normal", 
                "content_variety": "focused",
                "interaction_type": "focused"
            }
            
    def _is_break_due(self, learner_state: LearnerState) -> bool:
        """Check if a break is due based on timing rules"""
        
        if learner_state.last_break_time is None:
            return True
            
        time_since_break = datetime.utcnow() - learner_state.last_break_time
        return time_since_break >= timedelta(minutes=self.rules.MIN_BREAK_INTERVAL)
        
    def _get_or_create_learner_state(self, learner_id: str, tenant_id: str) -> LearnerState:
        """Get existing learner state or create new one"""
        
        if learner_id not in self.learner_states:
            self.learner_states[learner_id] = LearnerState(
                learner_id=learner_id,
                tenant_id=tenant_id
            )
            
        return self.learner_states[learner_id]
        
    async def _update_learner_state(self, learner_state: LearnerState, event: Event):
        """Update learner state based on event"""
        learner_state.updated_at = datetime.utcnow()
        
        # Event-specific state updates would go here
        # For now, just update the timestamp
        
    async def _load_learner_states(self):
        """Load learner states from persistent storage"""
        # In production, this would load from database
        # For now, start with empty state
        logger.info("Loading learner states from storage...")
        pass
        
    async def get_stats(self) -> Dict[str, Any]:
        """Get orchestration engine statistics"""
        return {
            **self.stats,
            "active_learners": len(self.learner_states),
            "is_initialized": self.is_initialized
        }
