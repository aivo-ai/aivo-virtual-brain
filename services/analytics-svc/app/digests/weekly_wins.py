"""
Analytics Service - Weekly Wins Digest Generator (S5-07)
Generates personalized weekly progress digests for learners and guardians
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID
from decimal import Decimal
import pytz
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from ..models import (
    SessionAggregate, MasteryAggregate, GoalProgress, 
    SLPStreaks, SELProgress, AggregationLevel
)
from ..database import get_db_session

logger = logging.getLogger(__name__)

class WeeklyWinsGenerator:
    """Generates Weekly Wins digest data for learners."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def generate_weekly_wins(
        self, 
        learner_id: UUID, 
        tenant_id: UUID,
        user_timezone: str = "UTC",
        locale: str = "en",
        grade_band: str = "elementary"
    ) -> Dict[str, Any]:
        """
        Generate weekly wins digest for a specific learner.
        
        Args:
            learner_id: The learner's unique identifier
            tenant_id: The tenant/organization ID
            user_timezone: User's timezone for local scheduling
            locale: User's locale for translations
            grade_band: User's grade band for age-appropriate messaging
        
        Returns:
            Dict containing weekly wins data
        """
        try:
            # Calculate week range (Sunday to Saturday)
            user_tz = pytz.timezone(user_timezone)
            now = datetime.now(user_tz)
            
            # Find the most recent Sunday
            days_since_sunday = now.weekday() + 1 if now.weekday() != 6 else 0
            week_start = (now - timedelta(days=days_since_sunday)).date()
            week_end = week_start + timedelta(days=6)
            
            logger.info(f"Generating weekly wins for learner {learner_id} from {week_start} to {week_end}")
            
            # Get learner's hashed ID for privacy-compliant queries
            learner_id_hash = self._hash_learner_id(str(learner_id))
            
            # Gather all metrics
            wins_data = {
                "learner_id": str(learner_id),
                "tenant_id": str(tenant_id),
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "timezone": user_timezone,
                "locale": locale,
                "grade_band": grade_band,
                "generated_at": datetime.utcnow().isoformat(),
            }
            
            # 1. Minutes learned this week
            wins_data["minutes_learned"] = await self._get_minutes_learned(
                learner_id_hash, tenant_id, week_start, week_end
            )
            
            # 2. Subjects advanced
            wins_data["subjects_advanced"] = await self._get_subjects_advanced(
                learner_id_hash, tenant_id, week_start, week_end
            )
            
            # 3. Completed goals
            wins_data["completed_goals"] = await self._get_completed_goals(
                learner_id_hash, tenant_id, week_start, week_end
            )
            
            # 4. SLP streaks
            wins_data["slp_streaks"] = await self._get_slp_streaks(
                learner_id_hash, tenant_id, week_start, week_end
            )
            
            # 5. SEL progress
            wins_data["sel_progress"] = await self._get_sel_progress(
                learner_id_hash, tenant_id, week_start, week_end
            )
            
            # 6. One thing to celebrate (auto-selected highlight)
            wins_data["celebration_highlight"] = await self._get_celebration_highlight(
                wins_data, locale, grade_band
            )
            
            # 7. Week-over-week comparison
            wins_data["week_comparison"] = await self._get_week_comparison(
                learner_id_hash, tenant_id, week_start
            )
            
            # 8. Personalized encouragement message
            wins_data["encouragement_message"] = self._generate_encouragement_message(
                wins_data, locale, grade_band
            )
            
            return wins_data
            
        except Exception as e:
            logger.error(f"Error generating weekly wins for learner {learner_id}: {str(e)}")
            raise
    
    async def _get_minutes_learned(
        self, learner_id_hash: str, tenant_id: UUID, week_start: date, week_end: date
    ) -> Dict[str, Any]:
        """Get total minutes learned this week."""
        try:
            result = self.db.query(
                func.sum(SessionAggregate.total_duration_minutes).label("total_minutes"),
                func.count(SessionAggregate.total_sessions).label("session_count"),
                func.avg(SessionAggregate.avg_duration_minutes).label("avg_session_minutes")
            ).filter(
                and_(
                    SessionAggregate.learner_id_hash == learner_id_hash,
                    SessionAggregate.tenant_id == tenant_id,
                    SessionAggregate.date_bucket >= week_start,
                    SessionAggregate.date_bucket <= week_end,
                    SessionAggregate.aggregation_level == AggregationLevel.INDIVIDUAL
                )
            ).first()
            
            return {
                "total_minutes": float(result.total_minutes or 0),
                "session_count": int(result.session_count or 0),
                "avg_session_minutes": float(result.avg_session_minutes or 0),
                "hours_learned": round(float(result.total_minutes or 0) / 60, 1)
            }
            
        except Exception as e:
            logger.warning(f"Error getting minutes learned: {str(e)}")
            return {"total_minutes": 0, "session_count": 0, "avg_session_minutes": 0, "hours_learned": 0}
    
    async def _get_subjects_advanced(
        self, learner_id_hash: str, tenant_id: UUID, week_start: date, week_end: date
    ) -> Dict[str, Any]:
        """Get subjects where mastery increased this week."""
        try:
            # Get mastery improvements by subject
            improvements = self.db.query(
                MasteryAggregate.subject_id,
                func.max(MasteryAggregate.current_mastery_score).label("max_score"),
                func.min(MasteryAggregate.current_mastery_score).label("min_score")
            ).filter(
                and_(
                    MasteryAggregate.learner_id_hash == learner_id_hash,
                    MasteryAggregate.tenant_id == tenant_id,
                    MasteryAggregate.date_bucket >= week_start,
                    MasteryAggregate.date_bucket <= week_end,
                    MasteryAggregate.aggregation_level == AggregationLevel.INDIVIDUAL
                )
            ).group_by(MasteryAggregate.subject_id).all()
            
            advanced_subjects = []
            total_improvement = 0
            
            for improvement in improvements:
                score_gain = float(improvement.max_score - improvement.min_score)
                if score_gain > 0.05:  # Meaningful improvement threshold
                    advanced_subjects.append({
                        "subject_id": str(improvement.subject_id),
                        "score_improvement": round(score_gain, 3),
                        "percentage_improvement": round(score_gain * 100, 1)
                    })
                    total_improvement += score_gain
            
            return {
                "subjects_count": len(advanced_subjects),
                "subjects": advanced_subjects,
                "total_improvement": round(total_improvement, 3),
                "avg_improvement": round(total_improvement / len(advanced_subjects), 3) if advanced_subjects else 0
            }
            
        except Exception as e:
            logger.warning(f"Error getting subjects advanced: {str(e)}")
            return {"subjects_count": 0, "subjects": [], "total_improvement": 0, "avg_improvement": 0}
    
    async def _get_completed_goals(
        self, learner_id_hash: str, tenant_id: UUID, week_start: date, week_end: date
    ) -> Dict[str, Any]:
        """Get goals completed this week."""
        try:
            completed_goals = self.db.query(GoalProgress).filter(
                and_(
                    GoalProgress.learner_id_hash == learner_id_hash,
                    GoalProgress.tenant_id == tenant_id,
                    GoalProgress.completed_at >= week_start,
                    GoalProgress.completed_at <= week_end,
                    GoalProgress.is_completed == True
                )
            ).all()
            
            goals_data = []
            for goal in completed_goals:
                goals_data.append({
                    "goal_id": str(goal.goal_id),
                    "goal_title": goal.goal_title,
                    "goal_type": goal.goal_type,
                    "completed_at": goal.completed_at.isoformat(),
                    "achievement_score": float(goal.achievement_score or 1.0)
                })
            
            return {
                "goals_count": len(goals_data),
                "goals": goals_data,
                "total_achievement_score": sum(g["achievement_score"] for g in goals_data)
            }
            
        except Exception as e:
            logger.warning(f"Error getting completed goals: {str(e)}")
            return {"goals_count": 0, "goals": [], "total_achievement_score": 0}
    
    async def _get_slp_streaks(
        self, learner_id_hash: str, tenant_id: UUID, week_start: date, week_end: date
    ) -> Dict[str, Any]:
        """Get SLP (Speech Language Pathology) streaks this week."""
        try:
            current_streak = self.db.query(SLPStreaks).filter(
                and_(
                    SLPStreaks.learner_id_hash == learner_id_hash,
                    SLPStreaks.tenant_id == tenant_id,
                    SLPStreaks.is_active == True
                )
            ).first()
            
            weekly_activities = self.db.query(
                func.count(SLPStreaks.activity_date).label("activity_count")
            ).filter(
                and_(
                    SLPStreaks.learner_id_hash == learner_id_hash,
                    SLPStreaks.tenant_id == tenant_id,
                    SLPStreaks.activity_date >= week_start,
                    SLPStreaks.activity_date <= week_end
                )
            ).first()
            
            return {
                "current_streak_days": current_streak.streak_days if current_streak else 0,
                "weekly_activity_count": int(weekly_activities.activity_count or 0),
                "streak_active": bool(current_streak and current_streak.is_active),
                "longest_streak": current_streak.longest_streak if current_streak else 0
            }
            
        except Exception as e:
            logger.warning(f"Error getting SLP streaks: {str(e)}")
            return {"current_streak_days": 0, "weekly_activity_count": 0, "streak_active": False, "longest_streak": 0}
    
    async def _get_sel_progress(
        self, learner_id_hash: str, tenant_id: UUID, week_start: date, week_end: date
    ) -> Dict[str, Any]:
        """Get SEL (Social Emotional Learning) progress this week."""
        try:
            sel_progress = self.db.query(SELProgress).filter(
                and_(
                    SELProgress.learner_id_hash == learner_id_hash,
                    SELProgress.tenant_id == tenant_id,
                    SELProgress.assessment_date >= week_start,
                    SELProgress.assessment_date <= week_end
                )
            ).order_by(desc(SELProgress.assessment_date)).all()
            
            if not sel_progress:
                return {"activities_count": 0, "skills_improved": [], "overall_improvement": 0}
            
            skills_improved = []
            total_improvement = 0
            
            # Group by skill and calculate improvement
            skill_groups = {}
            for progress in sel_progress:
                skill = progress.sel_skill
                if skill not in skill_groups:
                    skill_groups[skill] = []
                skill_groups[skill].append(progress.skill_score)
            
            for skill, scores in skill_groups.items():
                if len(scores) > 1:
                    improvement = max(scores) - min(scores)
                    if improvement > 0.1:  # Meaningful improvement
                        skills_improved.append({
                            "skill": skill,
                            "improvement": round(improvement, 2),
                            "current_score": max(scores)
                        })
                        total_improvement += improvement
            
            return {
                "activities_count": len(sel_progress),
                "skills_improved": skills_improved,
                "skills_count": len(skills_improved),
                "overall_improvement": round(total_improvement, 2)
            }
            
        except Exception as e:
            logger.warning(f"Error getting SEL progress: {str(e)}")
            return {"activities_count": 0, "skills_improved": [], "skills_count": 0, "overall_improvement": 0}
    
    async def _get_celebration_highlight(
        self, wins_data: Dict[str, Any], locale: str, grade_band: str
    ) -> Dict[str, Any]:
        """Select the most impressive achievement to highlight."""
        highlights = []
        
        # Check for standout achievements
        if wins_data["minutes_learned"]["total_minutes"] > 120:  # 2+ hours
            highlights.append({
                "type": "time_dedication",
                "value": wins_data["minutes_learned"]["hours_learned"],
                "message_key": "celebration.time_dedication"
            })
        
        if wins_data["subjects_advanced"]["subjects_count"] >= 3:
            highlights.append({
                "type": "multi_subject_mastery",
                "value": wins_data["subjects_advanced"]["subjects_count"],
                "message_key": "celebration.multi_subject_mastery"
            })
        
        if wins_data["completed_goals"]["goals_count"] >= 2:
            highlights.append({
                "type": "goal_achiever",
                "value": wins_data["completed_goals"]["goals_count"],
                "message_key": "celebration.goal_achiever"
            })
        
        if wins_data["slp_streaks"]["current_streak_days"] >= 5:
            highlights.append({
                "type": "consistent_practice",
                "value": wins_data["slp_streaks"]["current_streak_days"],
                "message_key": "celebration.consistent_practice"
            })
        
        if wins_data["sel_progress"]["skills_count"] >= 2:
            highlights.append({
                "type": "emotional_growth",
                "value": wins_data["sel_progress"]["skills_count"],
                "message_key": "celebration.emotional_growth"
            })
        
        # Select the best highlight or default
        if highlights:
            best_highlight = max(highlights, key=lambda x: x["value"])
            return best_highlight
        else:
            return {
                "type": "participation",
                "value": wins_data["minutes_learned"]["session_count"],
                "message_key": "celebration.participation"
            }
    
    async def _get_week_comparison(
        self, learner_id_hash: str, tenant_id: UUID, week_start: date
    ) -> Dict[str, Any]:
        """Compare this week's performance to last week."""
        try:
            last_week_start = week_start - timedelta(days=7)
            last_week_end = week_start - timedelta(days=1)
            
            # Get last week's minutes
            last_week_minutes = self.db.query(
                func.sum(SessionAggregate.total_duration_minutes).label("total_minutes")
            ).filter(
                and_(
                    SessionAggregate.learner_id_hash == learner_id_hash,
                    SessionAggregate.tenant_id == tenant_id,
                    SessionAggregate.date_bucket >= last_week_start,
                    SessionAggregate.date_bucket <= last_week_end,
                    SessionAggregate.aggregation_level == AggregationLevel.INDIVIDUAL
                )
            ).first()
            
            return {
                "last_week_minutes": float(last_week_minutes.total_minutes or 0),
                "has_comparison": bool(last_week_minutes.total_minutes)
            }
            
        except Exception as e:
            logger.warning(f"Error getting week comparison: {str(e)}")
            return {"last_week_minutes": 0, "has_comparison": False}
    
    def _generate_encouragement_message(
        self, wins_data: Dict[str, Any], locale: str, grade_band: str
    ) -> Dict[str, Any]:
        """Generate personalized encouragement message."""
        message_data = {
            "locale": locale,
            "grade_band": grade_band,
            "tone": "encouraging"
        }
        
        # Customize based on performance
        total_minutes = wins_data["minutes_learned"]["total_minutes"]
        goals_completed = wins_data["completed_goals"]["goals_count"]
        
        if total_minutes > 180 and goals_completed > 2:
            message_data["message_key"] = "encouragement.exceptional_week"
            message_data["tone"] = "celebratory"
        elif total_minutes > 60 or goals_completed > 0:
            message_data["message_key"] = "encouragement.great_progress"
            message_data["tone"] = "encouraging"
        else:
            message_data["message_key"] = "encouragement.keep_going"
            message_data["tone"] = "supportive"
        
        return message_data
    
    def _hash_learner_id(self, learner_id: str) -> str:
        """Generate privacy-compliant hash of learner ID."""
        import hashlib
        return hashlib.sha256(learner_id.encode()).hexdigest()[:32]

# Factory function for dependency injection
def create_weekly_wins_generator(db_session: Session = None) -> WeeklyWinsGenerator:
    """Create a WeeklyWinsGenerator instance with database session."""
    if db_session is None:
        db_session = next(get_db_session())
    return WeeklyWinsGenerator(db_session)
