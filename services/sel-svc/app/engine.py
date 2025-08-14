# AIVO SEL Service - Business Logic Engine
# S2-12 Implementation - SEL strategy generation and alert processing

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import asyncio
import httpx
import json
import uuid

from .models import (
    SELCheckIn, SELStrategy, SELAlert, ConsentRecord, StrategyUsage, SELReport,
    EmotionType, SELDomain, AlertLevel, StrategyType, GradeBand, ConsentStatus, AlertStatus
)
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

logger = logging.getLogger(__name__)


class SELEngine:
    """
    Core SEL engine for processing check-ins, generating strategies, and managing alerts.
    Integrates with inference gateway for AI-powered personalization.
    """
    
    def __init__(self):
        self.inference_gateway_url = "http://inference-gateway-svc:8000"
        
        # SEL domain thresholds for alert generation
        self.alert_thresholds = {
            SELDomain.SELF_AWARENESS: {"low": 3, "medium": 2, "high": 1},
            SELDomain.SELF_MANAGEMENT: {"low": 3, "medium": 2, "high": 1},
            SELDomain.SOCIAL_AWARENESS: {"low": 3, "medium": 2, "high": 1},
            SELDomain.RELATIONSHIP_SKILLS: {"low": 3, "medium": 2, "high": 1},
            SELDomain.RESPONSIBLE_DECISION_MAKING: {"low": 3, "medium": 2, "high": 1}
        }
        
        # Grade band strategy mappings
        self.grade_strategies = {
            GradeBand.EARLY_ELEMENTARY: {
                "preferred_duration": 5,  # 5-10 minutes
                "complexity_level": 1,
                "interactive_elements": True,
                "visual_supports": True
            },
            GradeBand.LATE_ELEMENTARY: {
                "preferred_duration": 10,  # 10-15 minutes
                "complexity_level": 2,
                "interactive_elements": True,
                "visual_supports": True
            },
            GradeBand.MIDDLE_SCHOOL: {
                "preferred_duration": 15,  # 15-20 minutes
                "complexity_level": 3,
                "interactive_elements": False,
                "visual_supports": False
            },
            GradeBand.HIGH_SCHOOL: {
                "preferred_duration": 20,  # 20-30 minutes
                "complexity_level": 4,
                "interactive_elements": False,
                "visual_supports": False
            },
            GradeBand.ADULT: {
                "preferred_duration": 25,  # 25-45 minutes
                "complexity_level": 5,
                "interactive_elements": False,
                "visual_supports": False
            }
        }
        
        # HTTP client will be initialized in initialize() method
        self.http_client = None
    
    async def initialize(self):
        """Initialize engine resources."""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("SEL Engine resources initialized")
        
    async def cleanup(self):
        """Cleanup engine resources."""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("SEL Engine resources cleaned up")
    
    async def process_checkin(self, checkin: SELCheckIn, db: Session) -> Dict[str, Any]:
        """
        Process SEL check-in data and generate insights, strategies, and alerts.
        
        Args:
            checkin: The check-in instance to process
            db: Database session
            
        Returns:
            Dict containing processing results and recommendations
        """
        try:
            logger.info(f"Processing check-in {checkin.id} for student {checkin.student_id}")
            
            # Analyze check-in data for patterns and insights
            analysis = await self._analyze_checkin_data(checkin, db)
            
            # Check for alert conditions
            alerts_generated = await self._check_alert_conditions(checkin, analysis, db)
            
            # Generate personalized strategy recommendation
            suggested_strategy = await self._generate_strategy_recommendation(checkin, analysis, db)
            
            # Update student's SEL profile trends
            profile_update = await self._update_student_profile(checkin, db)
            
            results = {
                "analysis": analysis,
                "alerts_generated": alerts_generated,
                "suggested_strategy": suggested_strategy,
                "profile_trends": profile_update,
                "processing_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Check-in {checkin.id} processing completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error processing check-in {checkin.id}: {str(e)}")
            raise
    
    async def _analyze_checkin_data(self, checkin: SELCheckIn, db: Session) -> Dict[str, Any]:
        """Analyze check-in data using AI inference."""
        try:
            # Get recent check-ins for context
            recent_checkins = db.query(SELCheckIn).filter(
                and_(
                    SELCheckIn.student_id == checkin.student_id,
                    SELCheckIn.checkin_date >= datetime.now(timezone.utc) - timedelta(days=30)
                )
            ).order_by(SELCheckIn.checkin_date.desc()).limit(10).all()
            
            # Prepare context for AI analysis
            context_data = {
                "current_checkin": {
                    "primary_emotion": checkin.primary_emotion.value,
                    "intensity": checkin.emotion_intensity,
                    "secondary_emotions": [e.value for e in checkin.secondary_emotions] if checkin.secondary_emotions else [],
                    "triggers": checkin.triggers or [],
                    "situation": checkin.current_situation,
                    "location": checkin.location_context,
                    "social_context": checkin.social_context,
                    "domain_ratings": {
                        "self_awareness": checkin.self_awareness_rating,
                        "self_management": checkin.self_management_rating,
                        "social_awareness": checkin.social_awareness_rating,
                        "relationship_skills": checkin.relationship_skills_rating,
                        "decision_making": checkin.decision_making_rating
                    },
                    "wellness_indicators": {
                        "energy": checkin.energy_level,
                        "stress": checkin.stress_level,
                        "confidence": checkin.confidence_level
                    },
                    "support_needed": checkin.support_needed
                },
                "recent_history": [
                    {
                        "date": ci.checkin_date.isoformat(),
                        "emotion": ci.primary_emotion.value,
                        "intensity": ci.emotion_intensity,
                        "support_needed": ci.support_needed
                    }
                    for ci in recent_checkins
                ],
                "grade_band": checkin.grade_band.value,
                "student_age_group": checkin.grade_band.value
            }
            
            # Call inference gateway for analysis (if available)
            if self.http_client:
                try:
                    response = await self.http_client.post(
                        f"{self.inference_gateway_url}/api/v1/inference/completion",
                        json={
                            "provider": "openai",
                            "model": "gpt-4",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are an expert in social-emotional learning assessment. Analyze the student's check-in data and provide insights about their emotional state, patterns, and needs. Focus on identifying trends, risk factors, and growth opportunities."
                                },
                                {
                                    "role": "user", 
                                    "content": f"Analyze this student's SEL check-in data: {json.dumps(context_data)}"
                                }
                            ],
                            "max_tokens": 1000,
                            "temperature": 0.3
                        }
                    )
                    
                    if response.status_code == 200:
                        ai_response = response.json()
                        analysis = {
                            "ai_insights": ai_response.get("choices", [{}])[0].get("message", {}).get("content", ""),
                            "emotional_patterns": self._identify_emotional_patterns(recent_checkins),
                            "risk_indicators": self._assess_risk_factors(checkin, recent_checkins),
                            "growth_areas": self._identify_growth_opportunities(checkin, recent_checkins),
                            "support_recommendations": self._generate_support_recommendations(checkin)
                        }
                    else:
                        # Fallback to rule-based analysis
                        analysis = self._fallback_analysis(checkin, recent_checkins)
                
                except Exception as e:
                    logger.warning(f"AI analysis failed, using fallback: {str(e)}")
                    analysis = self._fallback_analysis(checkin, recent_checkins)
            else:
                analysis = self._fallback_analysis(checkin, recent_checkins)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in check-in analysis: {str(e)}")
            return {"error": "Analysis failed", "message": str(e)}
    
    def _fallback_analysis(self, checkin: SELCheckIn, recent_checkins: List[SELCheckIn]) -> Dict[str, Any]:
        """Rule-based analysis when AI is unavailable."""
        return {
            "emotional_patterns": self._identify_emotional_patterns(recent_checkins),
            "risk_indicators": self._assess_risk_factors(checkin, recent_checkins),
            "growth_areas": self._identify_growth_opportunities(checkin, recent_checkins),
            "support_recommendations": self._generate_support_recommendations(checkin),
            "trend_analysis": self._analyze_trends(recent_checkins)
        }
    
    def _identify_emotional_patterns(self, recent_checkins: List[SELCheckIn]) -> Dict[str, Any]:
        """Identify patterns in recent emotional check-ins."""
        if not recent_checkins:
            return {"pattern": "insufficient_data"}
        
        # Analyze emotion frequency
        emotion_counts = {}
        intensity_sum = 0
        support_requests = 0
        
        for checkin in recent_checkins:
            emotion = checkin.primary_emotion.value
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            intensity_sum += checkin.emotion_intensity
            if checkin.support_needed:
                support_requests += 1
        
        most_common_emotion = max(emotion_counts, key=emotion_counts.get)
        avg_intensity = intensity_sum / len(recent_checkins)
        support_frequency = support_requests / len(recent_checkins)
        
        return {
            "most_common_emotion": most_common_emotion,
            "average_intensity": round(avg_intensity, 2),
            "support_request_frequency": round(support_frequency, 2),
            "emotional_diversity": len(emotion_counts),
            "pattern_stability": "stable" if len(emotion_counts) <= 3 else "variable"
        }
    
    def _assess_risk_factors(self, checkin: SELCheckIn, recent_checkins: List[SELCheckIn]) -> List[str]:
        """Assess risk factors from check-in data."""
        risk_factors = []
        
        # High stress level
        if checkin.stress_level and checkin.stress_level >= 8:
            risk_factors.append("high_stress_level")
        
        # Low confidence
        if checkin.confidence_level and checkin.confidence_level <= 3:
            risk_factors.append("low_confidence")
        
        # High emotion intensity with negative emotions
        negative_emotions = [EmotionType.SAD, EmotionType.ANGRY, EmotionType.ANXIOUS, EmotionType.FRUSTRATED, EmotionType.OVERWHELMED]
        if checkin.primary_emotion in negative_emotions and checkin.emotion_intensity >= 8:
            risk_factors.append("high_negative_emotion_intensity")
        
        # Persistent support requests
        recent_support_requests = sum(1 for ci in recent_checkins[:5] if ci.support_needed)
        if recent_support_requests >= 3:
            risk_factors.append("persistent_support_requests")
        
        # Low SEL domain ratings
        domain_ratings = [
            checkin.self_awareness_rating,
            checkin.self_management_rating,
            checkin.social_awareness_rating,
            checkin.relationship_skills_rating,
            checkin.decision_making_rating
        ]
        low_ratings = sum(1 for rating in domain_ratings if rating and rating <= 3)
        if low_ratings >= 2:
            risk_factors.append("multiple_low_sel_domains")
        
        return risk_factors
    
    def _identify_growth_opportunities(self, checkin: SELCheckIn, recent_checkins: List[SELCheckIn]) -> List[str]:
        """Identify areas of growth and strength."""
        opportunities = []
        
        # Strong domain ratings
        domain_ratings = {
            "self_awareness": checkin.self_awareness_rating,
            "self_management": checkin.self_management_rating,
            "social_awareness": checkin.social_awareness_rating,
            "relationship_skills": checkin.relationship_skills_rating,
            "decision_making": checkin.decision_making_rating
        }
        
        for domain, rating in domain_ratings.items():
            if rating and rating >= 7:
                opportunities.append(f"strength_in_{domain}")
        
        # Positive emotional state
        positive_emotions = [EmotionType.HAPPY, EmotionType.EXCITED, EmotionType.CALM, EmotionType.PROUD, EmotionType.CONTENT]
        if checkin.primary_emotion in positive_emotions:
            opportunities.append("positive_emotional_state")
        
        # High energy and confidence
        if checkin.energy_level and checkin.energy_level >= 7 and checkin.confidence_level and checkin.confidence_level >= 7:
            opportunities.append("high_energy_confidence_combination")
        
        return opportunities
    
    def _generate_support_recommendations(self, checkin: SELCheckIn) -> List[str]:
        """Generate recommendations for support based on check-in data."""
        recommendations = []
        
        if checkin.support_needed:
            recommendations.append("immediate_support_requested")
        
        if checkin.stress_level and checkin.stress_level >= 7:
            recommendations.append("stress_management_techniques")
        
        if checkin.primary_emotion in [EmotionType.ANXIOUS, EmotionType.OVERWHELMED]:
            recommendations.append("anxiety_coping_strategies")
        
        if checkin.primary_emotion == EmotionType.SAD:
            recommendations.append("mood_boosting_activities")
        
        if checkin.primary_emotion in [EmotionType.ANGRY, EmotionType.FRUSTRATED]:
            recommendations.append("emotional_regulation_techniques")
        
        # Low confidence support
        if checkin.confidence_level and checkin.confidence_level <= 4:
            recommendations.append("confidence_building_activities")
        
        return recommendations
    
    def _analyze_trends(self, recent_checkins: List[SELCheckIn]) -> Dict[str, str]:
        """Analyze trends in recent check-ins."""
        if len(recent_checkins) < 3:
            return {"trend": "insufficient_data"}
        
        # Analyze intensity trend
        recent_intensities = [ci.emotion_intensity for ci in recent_checkins[:5]]
        if len(recent_intensities) >= 3:
            if recent_intensities[0] > recent_intensities[-1]:
                intensity_trend = "improving"
            elif recent_intensities[0] < recent_intensities[-1]:
                intensity_trend = "worsening"
            else:
                intensity_trend = "stable"
        else:
            intensity_trend = "unknown"
        
        return {
            "intensity_trend": intensity_trend,
            "checkin_frequency": "regular" if len(recent_checkins) >= 5 else "irregular"
        }
    
    async def _check_alert_conditions(self, checkin: SELCheckIn, analysis: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """Check if check-in data triggers any alert conditions."""
        alerts = []
        
        try:
            # Check consent for alerting
            consent = db.query(ConsentRecord).filter(
                and_(
                    ConsentRecord.student_id == checkin.student_id,
                    ConsentRecord.tenant_id == checkin.tenant_id,
                    ConsentRecord.status == ConsentStatus.GRANTED,
                    ConsentRecord.alert_notifications_allowed == True
                )
            ).first()
            
            if not consent:
                logger.info(f"No alert consent found for student {checkin.student_id}")
                return alerts
            
            # Check domain-specific thresholds
            domain_alerts = self._check_domain_thresholds(checkin, consent)
            alerts.extend(domain_alerts)
            
            # Check risk factor alerts
            risk_alerts = self._check_risk_factor_alerts(checkin, analysis, consent)
            alerts.extend(risk_alerts)
            
            # Check pattern-based alerts
            pattern_alerts = await self._check_pattern_alerts(checkin, analysis, db, consent)
            alerts.extend(pattern_alerts)
            
            # Create alert records in database
            for alert_data in alerts:
                alert = SELAlert(
                    tenant_id=checkin.tenant_id,
                    student_id=checkin.student_id,
                    checkin_id=checkin.id,
                    consent_record_id=consent.id,
                    alert_type=alert_data["type"],
                    alert_level=AlertLevel(alert_data["level"]),
                    title=alert_data["title"],
                    description=alert_data["description"],
                    trigger_domain=SELDomain(alert_data["trigger_domain"]),
                    trigger_value=alert_data["trigger_value"],
                    threshold_value=alert_data["threshold_value"],
                    risk_score=alert_data["risk_score"],
                    risk_factors=alert_data["risk_factors"],
                    protective_factors=alert_data.get("protective_factors", []),
                    consent_verified=True,
                    privacy_level="confidential"
                )
                db.add(alert)
                db.flush()
                alert_data["alert_id"] = alert.id
            
            logger.info(f"Generated {len(alerts)} alerts for student {checkin.student_id}")
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking alert conditions: {str(e)}")
            return []
    
    def _check_domain_thresholds(self, checkin: SELCheckIn, consent: ConsentRecord) -> List[Dict[str, Any]]:
        """Check SEL domain ratings against thresholds."""
        alerts = []
        
        domain_ratings = {
            SELDomain.SELF_AWARENESS: checkin.self_awareness_rating,
            SELDomain.SELF_MANAGEMENT: checkin.self_management_rating,
            SELDomain.SOCIAL_AWARENESS: checkin.social_awareness_rating,
            SELDomain.RELATIONSHIP_SKILLS: checkin.relationship_skills_rating,
            SELDomain.RESPONSIBLE_DECISION_MAKING: checkin.decision_making_rating
        }
        
        # Use custom thresholds if available, otherwise default
        custom_thresholds = consent.alert_thresholds or {}
        
        for domain, rating in domain_ratings.items():
            if rating is None:
                continue
            
            domain_key = domain.value
            thresholds = custom_thresholds.get(domain_key, self.alert_thresholds[domain])
            
            alert_level = None
            threshold_value = None
            
            if rating <= thresholds["high"]:
                alert_level = "critical"
                threshold_value = thresholds["high"]
            elif rating <= thresholds["medium"]:
                alert_level = "high"
                threshold_value = thresholds["medium"]
            elif rating <= thresholds["low"]:
                alert_level = "medium"
                threshold_value = thresholds["low"]
            
            if alert_level:
                alerts.append({
                    "type": "domain_threshold_exceeded",
                    "level": alert_level,
                    "title": f"Low {domain.value.replace('_', ' ').title()} Rating",
                    "description": f"Student rated themselves {rating}/10 in {domain.value.replace('_', ' ')}, which is below the threshold of {threshold_value}.",
                    "trigger_domain": domain.value,
                    "trigger_value": float(rating),
                    "threshold_value": float(threshold_value),
                    "risk_score": min(100, (threshold_value - rating + 1) * 20),
                    "risk_factors": [f"low_{domain.value}_rating"]
                })
        
        return alerts
    
    def _check_risk_factor_alerts(self, checkin: SELCheckIn, analysis: Dict[str, Any], consent: ConsentRecord) -> List[Dict[str, Any]]:
        """Check for risk factor-based alerts."""
        alerts = []
        risk_factors = analysis.get("risk_indicators", [])
        
        if not risk_factors:
            return alerts
        
        # High priority risk factors
        high_priority_risks = ["high_negative_emotion_intensity", "persistent_support_requests", "multiple_low_sel_domains"]
        critical_risks = [risk for risk in risk_factors if risk in high_priority_risks]
        
        if critical_risks:
            risk_score = min(100, len(critical_risks) * 30 + checkin.emotion_intensity * 5)
            alert_level = "critical" if risk_score >= 80 else "high"
            
            alerts.append({
                "type": "risk_factors_detected",
                "level": alert_level,
                "title": "Multiple Risk Factors Identified",
                "description": f"Student shows {len(critical_risks)} high-priority risk indicators requiring attention.",
                "trigger_domain": "self_management",  # Default domain for risk alerts
                "trigger_value": float(len(critical_risks)),
                "threshold_value": 1.0,
                "risk_score": risk_score,
                "risk_factors": critical_risks
            })
        
        # Support request alert
        if checkin.support_needed:
            alerts.append({
                "type": "support_requested",
                "level": "medium",
                "title": "Student Requested Support",
                "description": "Student has indicated they need support during this check-in.",
                "trigger_domain": "self_management",
                "trigger_value": 1.0,
                "threshold_value": 0.0,
                "risk_score": 40.0,
                "risk_factors": ["support_requested"]
            })
        
        return alerts
    
    async def _check_pattern_alerts(self, checkin: SELCheckIn, analysis: Dict[str, Any], db: Session, consent: ConsentRecord) -> List[Dict[str, Any]]:
        """Check for pattern-based alerts across multiple check-ins."""
        alerts = []
        
        # Check for concerning trends
        patterns = analysis.get("emotional_patterns", {})
        
        # High support request frequency
        support_frequency = patterns.get("support_request_frequency", 0)
        if support_frequency >= 0.6:  # 60% or more check-ins request support
            alerts.append({
                "type": "pattern_high_support_frequency",
                "level": "high",
                "title": "Frequent Support Requests Pattern",
                "description": f"Student has requested support in {support_frequency*100:.0f}% of recent check-ins.",
                "trigger_domain": "self_management",
                "trigger_value": support_frequency,
                "threshold_value": 0.6,
                "risk_score": min(100, support_frequency * 100),
                "risk_factors": ["frequent_support_requests"]
            })
        
        # Consistently high negative emotion intensity
        avg_intensity = patterns.get("average_intensity", 0)
        most_common = patterns.get("most_common_emotion", "")
        
        negative_emotions = ["sad", "angry", "anxious", "frustrated", "overwhelmed"]
        if most_common in negative_emotions and avg_intensity >= 7:
            alerts.append({
                "type": "pattern_persistent_negative_emotions",
                "level": "high",
                "title": "Persistent High-Intensity Negative Emotions",
                "description": f"Student consistently reports {most_common} emotions with high intensity (avg: {avg_intensity:.1f}/10).",
                "trigger_domain": "self_awareness",
                "trigger_value": avg_intensity,
                "threshold_value": 7.0,
                "risk_score": min(100, avg_intensity * 10),
                "risk_factors": [f"persistent_{most_common}_emotions"]
            })
        
        return alerts
    
    async def generate_personalized_strategy(self, request_data: Dict[str, Any], db: Session) -> SELStrategy:
        """
        Generate a personalized SEL strategy for a student.
        
        Args:
            request_data: Strategy request parameters
            db: Database session
            
        Returns:
            Generated SEL strategy instance
        """
        try:
            student_id = request_data["student_id"]
            tenant_id = request_data["tenant_id"]
            
            # Get student context from recent check-ins
            recent_checkin = db.query(SELCheckIn).filter(
                and_(
                    SELCheckIn.student_id == student_id,
                    SELCheckIn.tenant_id == tenant_id
                )
            ).order_by(SELCheckIn.checkin_date.desc()).first()
            
            if not recent_checkin:
                # Create a basic strategy without personalization
                return await self._create_generic_strategy(request_data, db)
            
            # Determine strategy parameters
            strategy_params = await self._determine_strategy_parameters(recent_checkin, request_data)
            
            # Generate strategy content using AI
            strategy_content = await self._generate_strategy_content(strategy_params, recent_checkin)
            
            # Create strategy instance
            strategy = SELStrategy(
                tenant_id=tenant_id,
                student_id=student_id,
                checkin_id=recent_checkin.id,
                strategy_type=StrategyType(strategy_params["strategy_type"]),
                strategy_title=strategy_content["title"],
                strategy_description=strategy_content["description"],
                instructions=strategy_content["instructions"],
                grade_band=recent_checkin.grade_band,
                target_emotion=strategy_params["target_emotion"],
                target_domain=strategy_params["target_domain"],
                difficulty_level=strategy_params["difficulty_level"],
                estimated_duration=strategy_params["estimated_duration"],
                materials_needed=strategy_content.get("materials", []),
                step_by_step=strategy_content["steps"],
                success_indicators=strategy_content.get("success_indicators", []),
                video_url=strategy_content.get("video_url"),
                audio_url=strategy_content.get("audio_url"),
                image_urls=strategy_content.get("image_urls", []),
                interactive_elements=strategy_content.get("interactive_elements")
            )
            
            db.add(strategy)
            db.flush()
            
            logger.info(f"Generated personalized strategy {strategy.id} for student {student_id}")
            return strategy
            
        except Exception as e:
            logger.error(f"Error generating strategy: {str(e)}")
            raise
    
    async def _create_generic_strategy(self, request_data: Dict[str, Any], db: Session) -> SELStrategy:
        """Create a generic strategy when no check-in context is available."""
        grade_band = GradeBand(request_data.get("grade_band", "middle_school"))
        
        # Default strategy for mindfulness
        strategy = SELStrategy(
            tenant_id=request_data["tenant_id"],
            student_id=request_data["student_id"],
            strategy_type=StrategyType.MINDFULNESS,
            strategy_title="Basic Mindfulness Breathing",
            strategy_description="A simple breathing exercise to help manage emotions and reduce stress.",
            instructions="Find a comfortable position and focus on your breathing. This exercise will help you feel more centered and calm.",
            grade_band=grade_band,
            target_emotion=EmotionType.ANXIOUS,  # Default
            target_domain=SELDomain.SELF_MANAGEMENT,  # Default
            difficulty_level=1,
            estimated_duration=5,
            materials_needed=[],
            step_by_step=[
                "Sit comfortably with your feet flat on the floor",
                "Close your eyes or look down at your hands",
                "Take a slow, deep breath in through your nose for 4 counts",
                "Hold your breath for 2 counts",
                "Slowly breathe out through your mouth for 6 counts",
                "Repeat this breathing pattern 5 times"
            ],
            success_indicators=["Feeling more relaxed", "Breathing feels natural", "Mind feels calmer"]
        )
        
        return strategy
    
    async def _determine_strategy_parameters(self, checkin: SELCheckIn, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine appropriate strategy parameters based on check-in data."""
        grade_config = self.grade_strategies[checkin.grade_band]
        
        # Determine target emotion
        target_emotion = request_data.get("target_emotion")
        if not target_emotion:
            target_emotion = checkin.primary_emotion
        
        # Determine target domain based on lowest rating
        domain_ratings = {
            SELDomain.SELF_AWARENESS: checkin.self_awareness_rating,
            SELDomain.SELF_MANAGEMENT: checkin.self_management_rating,
            SELDomain.SOCIAL_AWARENESS: checkin.social_awareness_rating,
            SELDomain.RELATIONSHIP_SKILLS: checkin.relationship_skills_rating,
            SELDomain.RESPONSIBLE_DECISION_MAKING: checkin.decision_making_rating
        }
        
        # Filter out None ratings and find lowest
        valid_ratings = {domain: rating for domain, rating in domain_ratings.items() if rating is not None}
        if valid_ratings:
            target_domain = min(valid_ratings, key=valid_ratings.get)
        else:
            target_domain = SELDomain.SELF_MANAGEMENT  # Default
        
        # Determine strategy type based on emotion and domain
        strategy_type = self._select_strategy_type(target_emotion, target_domain, checkin)
        
        # Adjust difficulty based on grade and request
        difficulty_pref = request_data.get("difficulty_preference", "adaptive")
        if difficulty_pref == "easy":
            difficulty_level = max(1, grade_config["complexity_level"] - 1)
        elif difficulty_pref == "challenging":
            difficulty_level = min(5, grade_config["complexity_level"] + 1)
        else:  # adaptive
            difficulty_level = grade_config["complexity_level"]
        
        # Adjust duration based on available time
        max_duration = request_data.get("max_duration", grade_config["preferred_duration"])
        estimated_duration = min(max_duration, grade_config["preferred_duration"])
        
        return {
            "strategy_type": strategy_type.value,
            "target_emotion": target_emotion,
            "target_domain": target_domain,
            "difficulty_level": difficulty_level,
            "estimated_duration": estimated_duration,
            "grade_band": checkin.grade_band,
            "visual_supports": grade_config["visual_supports"],
            "interactive_elements": grade_config["interactive_elements"]
        }
    
    def _select_strategy_type(self, target_emotion: EmotionType, target_domain: SELDomain, checkin: SELCheckIn) -> StrategyType:
        """Select appropriate strategy type based on emotion and domain."""
        
        # Emotion-based strategy selection
        emotion_strategies = {
            EmotionType.ANXIOUS: StrategyType.BREATHING,
            EmotionType.OVERWHELMED: StrategyType.MINDFULNESS,
            EmotionType.ANGRY: StrategyType.EMOTIONAL_REGULATION,
            EmotionType.FRUSTRATED: StrategyType.PROBLEM_SOLVING,
            EmotionType.SAD: StrategyType.COPING_SKILLS,
            EmotionType.WORRIED: StrategyType.COGNITIVE_REFRAMING
        }
        
        # Domain-based strategy selection
        domain_strategies = {
            SELDomain.SELF_AWARENESS: StrategyType.MINDFULNESS,
            SELDomain.SELF_MANAGEMENT: StrategyType.EMOTIONAL_REGULATION,
            SELDomain.SOCIAL_AWARENESS: StrategyType.SOCIAL_SKILLS,
            SELDomain.RELATIONSHIP_SKILLS: StrategyType.COMMUNICATION,
            SELDomain.RESPONSIBLE_DECISION_MAKING: StrategyType.PROBLEM_SOLVING
        }
        
        # Prioritize emotion-based if available
        if target_emotion in emotion_strategies:
            return emotion_strategies[target_emotion]
        
        # Fall back to domain-based
        return domain_strategies.get(target_domain, StrategyType.BREATHING)
    
    async def _generate_strategy_content(self, strategy_params: Dict[str, Any], checkin: SELCheckIn) -> Dict[str, Any]:
        """Generate personalized strategy content using AI."""
        
        context = {
            "strategy_type": strategy_params["strategy_type"],
            "target_emotion": strategy_params["target_emotion"].value if hasattr(strategy_params["target_emotion"], 'value') else str(strategy_params["target_emotion"]),
            "target_domain": strategy_params["target_domain"].value,
            "grade_band": strategy_params["grade_band"].value,
            "difficulty_level": strategy_params["difficulty_level"],
            "duration": strategy_params["estimated_duration"],
            "student_context": {
                "current_emotion": checkin.primary_emotion.value,
                "intensity": checkin.emotion_intensity,
                "stress_level": checkin.stress_level,
                "confidence_level": checkin.confidence_level,
                "support_needed": checkin.support_needed
            }
        }
        
        try:
            if self.http_client:
                response = await self.http_client.post(
                    f"{self.inference_gateway_url}/api/v1/inference/completion",
                    json={
                        "provider": "openai",
                        "model": "gpt-4",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert SEL curriculum designer. Create engaging, age-appropriate social-emotional learning strategies. Return JSON with: title, description, instructions, steps (array), materials (array), success_indicators (array)."
                            },
                            {
                                "role": "user",
                                "content": f"Create a {strategy_params['strategy_type']} strategy for: {json.dumps(context)}"
                            }
                        ],
                        "max_tokens": 1500,
                        "temperature": 0.5
                    }
                )
                
                if response.status_code == 200:
                    ai_response = response.json()
                    content_text = ai_response.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    try:
                        # Try to parse as JSON
                        content = json.loads(content_text)
                        return content
                    except json.JSONDecodeError:
                        # Fall back to parsing text response
                        return self._parse_text_strategy_response(content_text, strategy_params)
        
        except Exception as e:
            logger.warning(f"AI strategy generation failed: {str(e)}")
        
        # Fallback to template-based strategy
        return self._generate_template_strategy(strategy_params, checkin)
    
    def _generate_template_strategy(self, strategy_params: Dict[str, Any], checkin: SELCheckIn) -> Dict[str, Any]:
        """Generate strategy using predefined templates."""
        strategy_type = strategy_params["strategy_type"]
        
        templates = {
            "breathing": {
                "title": "Deep Breathing Exercise",
                "description": "A calming breathing technique to help manage emotions and reduce stress.",
                "instructions": "Follow the breathing pattern to help your body and mind relax.",
                "steps": [
                    "Find a comfortable seated position",
                    "Place one hand on your chest, one on your stomach", 
                    "Breathe in slowly through your nose for 4 counts",
                    "Hold your breath for 4 counts",
                    "Breathe out slowly through your mouth for 6 counts",
                    "Repeat 5-8 times"
                ],
                "materials": [],
                "success_indicators": ["Feeling more relaxed", "Slower heart rate", "Calmer thoughts"]
            },
            "mindfulness": {
                "title": "Mindful Moment Check-In",
                "description": "A brief mindfulness practice to increase self-awareness and emotional regulation.",
                "instructions": "Take a few minutes to connect with the present moment and your inner experience.",
                "steps": [
                    "Sit comfortably and close your eyes or soften your gaze",
                    "Notice 3 things you can hear around you",
                    "Notice 2 physical sensations in your body",
                    "Notice 1 emotion you're feeling right now",
                    "Take 3 deep breaths and open your eyes"
                ],
                "materials": [],
                "success_indicators": ["Increased awareness", "Feeling more grounded", "Better emotional clarity"]
            },
            "emotional_regulation": {
                "title": "Emotion Thermometer Check",
                "description": "Learn to identify and regulate emotional intensity using visualization.",
                "instructions": "Use this technique to better understand and manage your emotional temperature.",
                "steps": [
                    "Imagine your emotion as a thermometer reading",
                    "What number is it at right now? (1-10)",
                    "Take deep breaths to help lower the temperature",
                    "Visualize the number slowly going down",
                    "What strategies can help keep it at a comfortable level?"
                ],
                "materials": ["Paper and pencil (optional)"],
                "success_indicators": ["Better emotion awareness", "Feeling more in control", "Lower intensity rating"]
            }
        }
        
        template = templates.get(strategy_type, templates["breathing"])
        
        # Personalize based on grade band
        if strategy_params["grade_band"] == GradeBand.EARLY_ELEMENTARY:
            template["instructions"] = "Let's try this fun activity together!"
            template["steps"] = [step.replace("counts", "seconds") for step in template["steps"]]
        
        return template
    
    async def record_strategy_usage(self, usage_data: Dict[str, Any], db: Session) -> StrategyUsage:
        """Record strategy usage and effectiveness data."""
        try:
            usage = StrategyUsage(
                tenant_id=usage_data["tenant_id"],
                student_id=usage_data["student_id"],
                strategy_id=usage_data["strategy_id"],
                duration_used=usage_data.get("duration_used"),
                completion_status=usage_data["completion_status"],
                pre_emotion_rating=usage_data["pre_emotion_rating"],
                post_emotion_rating=usage_data["post_emotion_rating"],
                helpfulness_rating=usage_data["helpfulness_rating"],
                difficulty_rating=usage_data.get("difficulty_rating"),
                liked_aspects=usage_data.get("liked_aspects"),
                disliked_aspects=usage_data.get("disliked_aspects"),
                suggestions=usage_data.get("suggestions"),
                would_use_again=usage_data.get("would_use_again"),
                usage_context=usage_data.get("usage_context"),
                support_received=usage_data.get("support_received")
            )
            
            db.add(usage)
            db.flush()
            
            # Update strategy effectiveness metrics
            await self._update_strategy_metrics(usage_data["strategy_id"], db)
            
            logger.info(f"Recorded strategy usage {usage.id}")
            return usage
            
        except Exception as e:
            logger.error(f"Error recording strategy usage: {str(e)}")
            raise
    
    async def _update_strategy_metrics(self, strategy_id: uuid.UUID, db: Session):
        """Update aggregate metrics for a strategy based on usage data."""
        try:
            strategy = db.query(SELStrategy).filter(SELStrategy.id == strategy_id).first()
            if not strategy:
                return
            
            # Get all usage records for this strategy
            usage_records = db.query(StrategyUsage).filter(
                StrategyUsage.strategy_id == strategy_id
            ).all()
            
            if not usage_records:
                return
            
            # Calculate metrics
            total_uses = len(usage_records)
            completed_uses = len([u for u in usage_records if u.completion_status == "completed"])
            avg_helpfulness = sum(u.helpfulness_rating for u in usage_records) / total_uses
            effectiveness_scores = [u.post_emotion_rating - u.pre_emotion_rating for u in usage_records]
            avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores)
            
            # Update strategy
            strategy.times_used = total_uses
            strategy.average_rating = avg_helpfulness
            strategy.success_rate = completed_uses / total_uses
            strategy.last_used_at = max(u.used_at for u in usage_records)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating strategy metrics: {str(e)}")
    
    async def generate_report(self, request_data: Dict[str, Any], db: Session) -> SELReport:
        """Generate comprehensive SEL report for a student."""
        try:
            student_id = request_data["student_id"]
            tenant_id = request_data["tenant_id"]
            start_date = request_data["start_date"]
            end_date = request_data["end_date"]
            
            # Get data for the report period
            checkins = db.query(SELCheckIn).filter(
                and_(
                    SELCheckIn.student_id == student_id,
                    SELCheckIn.tenant_id == tenant_id,
                    SELCheckIn.checkin_date >= start_date,
                    SELCheckIn.checkin_date <= end_date
                )
            ).order_by(SELCheckIn.checkin_date).all()
            
            if not checkins:
                # Return empty report
                return self._create_empty_report(request_data, db)
            
            # Generate report content
            report_data = await self._compile_report_data(checkins, db)
            insights = await self._generate_report_insights(report_data, checkins)
            recommendations = self._generate_report_recommendations(report_data, insights)
            
            # Create report instance
            report = SELReport(
                tenant_id=tenant_id,
                student_id=student_id,
                report_type=request_data["report_type"],
                report_period_start=start_date,
                report_period_end=end_date,
                generated_for=request_data["report_audience"],
                total_checkins=len(checkins),
                average_emotion_intensity=report_data["avg_emotion_intensity"],
                most_common_emotion=EmotionType(report_data["most_common_emotion"]) if report_data["most_common_emotion"] else None,
                trend_direction=report_data["trend_direction"],
                domain_scores=report_data["domain_scores"],
                domain_trends=report_data["domain_trends"],
                growth_indicators=report_data["growth_indicators"],
                areas_for_support=report_data["areas_for_support"],
                strategies_used=report_data["strategies_used"],
                strategy_success_rate=report_data["strategy_success_rate"],
                preferred_strategies=report_data["preferred_strategies"],
                total_alerts=report_data["total_alerts"],
                alert_trends=report_data["alert_trends"],
                key_insights=insights,
                recommendations=recommendations,
                celebration_points=report_data["celebration_points"],
                report_data=report_data,
                narrative_summary=self._generate_narrative_summary(report_data, insights),
                privacy_level=request_data["privacy_level"],
                consent_verified=True  # Assume consent checked before report generation
            )
            
            db.add(report)
            db.flush()
            
            logger.info(f"Generated SEL report {report.id} for student {student_id}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating SEL report: {str(e)}")
            raise
    
    def _create_empty_report(self, request_data: Dict[str, Any], db: Session) -> SELReport:
        """Create an empty report when no data is available."""
        return SELReport(
            tenant_id=request_data["tenant_id"],
            student_id=request_data["student_id"],
            report_type=request_data["report_type"],
            report_period_start=request_data["start_date"],
            report_period_end=request_data["end_date"],
            generated_for=request_data["report_audience"],
            total_checkins=0,
            domain_scores={},
            strategies_used=0,
            total_alerts=0,
            key_insights=["Insufficient data for analysis"],
            recommendations=["Encourage regular check-ins to build meaningful insights"],
            report_data={"status": "insufficient_data"},
            privacy_level=request_data["privacy_level"],
            consent_verified=True
        )
    
    async def _compile_report_data(self, checkins: List[SELCheckIn], db: Session) -> Dict[str, Any]:
        """Compile statistical data for the report."""
        if not checkins:
            return {}
        
        # Basic statistics
        total_checkins = len(checkins)
        emotions = [ci.primary_emotion for ci in checkins]
        intensities = [ci.emotion_intensity for ci in checkins]
        
        # Emotion analysis
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion.value] = emotion_counts.get(emotion.value, 0) + 1
        
        most_common_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else None
        avg_emotion_intensity = sum(intensities) / len(intensities)
        
        # Domain analysis
        domain_scores = {}
        domain_data = {
            "self_awareness": [ci.self_awareness_rating for ci in checkins if ci.self_awareness_rating],
            "self_management": [ci.self_management_rating for ci in checkins if ci.self_management_rating],
            "social_awareness": [ci.social_awareness_rating for ci in checkins if ci.social_awareness_rating],
            "relationship_skills": [ci.relationship_skills_rating for ci in checkins if ci.relationship_skills_rating],
            "decision_making": [ci.decision_making_rating for ci in checkins if ci.decision_making_rating]
        }
        
        for domain, ratings in domain_data.items():
            if ratings:
                domain_scores[domain] = sum(ratings) / len(ratings)
        
        # Trend analysis
        if len(intensities) >= 3:
            recent_avg = sum(intensities[:len(intensities)//2]) / (len(intensities)//2)
            earlier_avg = sum(intensities[len(intensities)//2:]) / (len(intensities) - len(intensities)//2)
            
            if recent_avg < earlier_avg - 0.5:
                trend_direction = "improving"
            elif recent_avg > earlier_avg + 0.5:
                trend_direction = "declining"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "insufficient_data"
        
        # Support requests
        support_requests = sum(1 for ci in checkins if ci.support_needed)
        
        # Growth and support areas
        growth_indicators = []
        areas_for_support = []
        
        for domain, avg_score in domain_scores.items():
            if avg_score >= 7:
                growth_indicators.append(f"strength_in_{domain}")
            elif avg_score <= 4:
                areas_for_support.append(f"support_needed_in_{domain}")
        
        # Strategy data (would need to join with strategy usage)
        strategies_used = 0  # Placeholder
        strategy_success_rate = None  # Placeholder
        preferred_strategies = []  # Placeholder
        
        # Alert data (would need to join with alerts)
        total_alerts = 0  # Placeholder
        alert_trends = {}  # Placeholder
        
        # Celebration points
        celebration_points = []
        if avg_emotion_intensity <= 6:
            celebration_points.append("Maintaining emotional balance")
        if support_requests / total_checkins <= 0.3:
            celebration_points.append("Developing independence in emotional management")
        
        return {
            "total_checkins": total_checkins,
            "avg_emotion_intensity": round(avg_emotion_intensity, 2),
            "most_common_emotion": most_common_emotion,
            "trend_direction": trend_direction,
            "domain_scores": domain_scores,
            "domain_trends": {},  # Would need more complex analysis
            "growth_indicators": growth_indicators,
            "areas_for_support": areas_for_support,
            "strategies_used": strategies_used,
            "strategy_success_rate": strategy_success_rate,
            "preferred_strategies": preferred_strategies,
            "total_alerts": total_alerts,
            "alert_trends": alert_trends,
            "support_request_rate": support_requests / total_checkins,
            "celebration_points": celebration_points,
            "emotion_distribution": emotion_counts
        }
    
    async def _generate_report_insights(self, report_data: Dict[str, Any], checkins: List[SELCheckIn]) -> List[str]:
        """Generate AI-powered insights for the report."""
        insights = []
        
        # Rule-based insights for now
        avg_intensity = report_data.get("avg_emotion_intensity", 0)
        trend = report_data.get("trend_direction", "unknown")
        
        if trend == "improving":
            insights.append("Student shows positive emotional development over the reporting period")
        elif trend == "declining":
            insights.append("Student may benefit from additional SEL support and intervention")
        
        if avg_intensity <= 5:
            insights.append("Student demonstrates good emotional regulation skills")
        elif avg_intensity >= 8:
            insights.append("Student experiences high emotional intensity and may benefit from coping strategies")
        
        support_rate = report_data.get("support_request_rate", 0)
        if support_rate <= 0.2:
            insights.append("Student shows strong independence in managing emotions")
        elif support_rate >= 0.5:
            insights.append("Student frequently requests support, indicating need for additional resources")
        
        return insights
    
    def _generate_report_recommendations(self, report_data: Dict[str, Any], insights: List[str]) -> List[str]:
        """Generate actionable recommendations based on report data."""
        recommendations = []
        
        # Domain-specific recommendations
        areas_for_support = report_data.get("areas_for_support", [])
        for area in areas_for_support:
            if "self_management" in area:
                recommendations.append("Focus on self-regulation strategies like deep breathing and mindfulness")
            elif "social_awareness" in area:
                recommendations.append("Practice perspective-taking and empathy-building activities")
            elif "relationship_skills" in area:
                recommendations.append("Work on communication and conflict resolution skills")
        
        # Trend-based recommendations
        if report_data.get("trend_direction") == "declining":
            recommendations.append("Consider scheduling additional check-ins and support sessions")
        
        # Intensity-based recommendations
        if report_data.get("avg_emotion_intensity", 0) >= 7:
            recommendations.append("Introduce daily emotion regulation practices")
        
        # General recommendations
        if report_data.get("total_checkins", 0) < 5:
            recommendations.append("Encourage more frequent SEL check-ins for better tracking")
        
        return recommendations
    
    def _generate_narrative_summary(self, report_data: Dict[str, Any], insights: List[str]) -> str:
        """Generate a human-readable narrative summary of the report."""
        total_checkins = report_data.get("total_checkins", 0)
        avg_intensity = report_data.get("avg_emotion_intensity", 0)
        most_common = report_data.get("most_common_emotion", "varied")
        trend = report_data.get("trend_direction", "stable")
        
        summary = f"During this reporting period, the student completed {total_checkins} check-ins with an average emotional intensity of {avg_intensity}/10. "
        summary += f"The most commonly reported emotion was {most_common.replace('_', ' ') if most_common != 'varied' else 'varied across different emotions'}. "
        summary += f"Overall, the student's emotional trend appears to be {trend}. "
        
        if insights:
            summary += "Key insights include: " + "; ".join(insights[:2]) + "."
        
        return summary
