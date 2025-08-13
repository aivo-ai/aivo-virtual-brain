# AIVO Assessment Service - Baseline Logic
# S1-10 Implementation - IRT-Ready Assessment Logic

import math
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

from app.models import (
    AssessmentSession, QuestionBank, AssessmentResponse, 
    AssessmentResult, AssessmentStatus, SubjectLevel
)
from app.schemas import SubjectLevelSchema

logger = logging.getLogger(__name__)

class IRTEngine:
    """Item Response Theory calculation engine."""
    
    @staticmethod
    def probability_correct(theta: float, difficulty: float, discrimination: float, guessing: float = 0.0) -> float:
        """
        Calculate probability of correct response using 3PL IRT model.
        P(θ) = c + (1-c) * [1 / (1 + exp(-a(θ-b)))]
        
        Args:
            theta: Ability parameter
            difficulty: Item difficulty (b parameter)
            discrimination: Item discrimination (a parameter)  
            guessing: Guessing parameter (c parameter)
        """
        try:
            exp_term = math.exp(-discrimination * (theta - difficulty))
            probability = guessing + (1 - guessing) / (1 + exp_term)
            return max(0.0, min(1.0, probability))  # Clamp to [0,1]
        except OverflowError:
            # Handle extreme values
            if theta > difficulty:
                return 1.0 - guessing * 0.1  # Very high probability
            else:
                return guessing + 0.1  # Low probability
    
    @staticmethod
    def information_function(theta: float, difficulty: float, discrimination: float, guessing: float = 0.0) -> float:
        """
        Calculate Fisher information for item at given ability level.
        I(θ) = a² * P(θ) * (1-P(θ)) * [(1-c)/(1-c*P(θ))]²
        """
        try:
            prob = IRTEngine.probability_correct(theta, difficulty, discrimination, guessing)
            if prob <= 0 or prob >= 1:
                return 0.0
                
            base_info = discrimination ** 2 * prob * (1 - prob)
            if guessing > 0:
                correction = ((1 - guessing) / (1 - guessing * prob)) ** 2
                return base_info * correction
            return base_info
        except (OverflowError, ZeroDivisionError):
            return 0.0
    
    @staticmethod
    def update_theta_eap(theta: float, responses: List[Tuple[float, float, float, bool]]) -> Tuple[float, float]:
        """
        Update ability estimate using Expected A Posteriori (EAP) method.
        Returns (new_theta, standard_error).
        """
        if not responses:
            return theta, 1.0
            
        # Quadrature points and weights for EAP integration
        quad_points = np.linspace(-4.0, 4.0, 41)  # -4 to +4 standard deviations
        quad_weights = np.ones(len(quad_points)) / len(quad_points)
        
        # Prior distribution (standard normal)
        prior = np.exp(-0.5 * quad_points ** 2) / math.sqrt(2 * math.pi)
        
        # Likelihood calculation
        likelihood = np.ones(len(quad_points))
        for difficulty, discrimination, guessing, is_correct in responses:
            for i, t in enumerate(quad_points):
                prob = IRTEngine.probability_correct(t, difficulty, discrimination, guessing)
                if is_correct:
                    likelihood[i] *= prob
                else:
                    likelihood[i] *= (1 - prob)
        
        # Posterior distribution
        posterior = prior * likelihood
        posterior_sum = np.sum(posterior * quad_weights)
        
        if posterior_sum == 0:
            return theta, 1.0
            
        # Normalize posterior
        posterior = posterior / posterior_sum
        
        # Calculate EAP estimate
        new_theta = np.sum(quad_points * posterior * quad_weights) / np.sum(posterior * quad_weights)
        
        # Calculate posterior standard deviation
        variance = np.sum((quad_points - new_theta) ** 2 * posterior * quad_weights) / np.sum(posterior * quad_weights)
        standard_error = math.sqrt(variance)
        
        return float(new_theta), float(standard_error)

class LevelMapper:
    """Maps IRT theta scores to proficiency levels L0-L4."""
    
    # Theta thresholds for level mapping (can be configured per subject)
    DEFAULT_THRESHOLDS = {
        "L0": -2.0,  # Below -2.0 = L0 (Beginner)
        "L1": -1.0,  # -2.0 to -1.0 = L1 (Elementary)  
        "L2": 0.0,   # -1.0 to 0.0 = L2 (Intermediate)
        "L3": 1.0,   # 0.0 to 1.0 = L3 (Advanced)
        "L4": 2.0    # Above 1.0 = L4 (Expert)
    }
    
    @classmethod
    def theta_to_level(cls, theta: float, standard_error: float, subject: str = None) -> Tuple[str, float]:
        """
        Map theta score to proficiency level with confidence.
        
        Args:
            theta: Final ability estimate
            standard_error: Standard error of measurement
            subject: Subject name (for subject-specific thresholds)
            
        Returns:
            (level, confidence) tuple
        """
        # Use subject-specific thresholds if available, otherwise default
        thresholds = cls.DEFAULT_THRESHOLDS  # Could extend for subject-specific mapping
        
        # Determine most likely level
        if theta < thresholds["L1"]:
            level = "L0"
            boundary = thresholds["L1"]
        elif theta < thresholds["L2"]:
            level = "L1" 
            boundary = thresholds["L2"]
        elif theta < thresholds["L3"]:
            level = "L2"
            boundary = thresholds["L3"]
        elif theta < thresholds["L4"]:
            level = "L3"
            boundary = thresholds["L4"]
        else:
            level = "L4"
            boundary = float('inf')
        
        # Calculate confidence based on distance from boundary
        if boundary == float('inf'):
            # For L4, calculate confidence based on distance from L3 boundary
            distance = theta - thresholds["L3"]
        else:
            # Calculate distance to nearest boundary
            if level == "L0":
                distance = boundary - theta
            else:
                prev_boundary = list(thresholds.values())[list(thresholds.keys()).index(level) - 1]
                distance = min(abs(theta - prev_boundary), abs(boundary - theta))
        
        # Convert distance to confidence (higher distance = higher confidence)
        # Confidence decreases as we approach boundaries
        confidence = 1.0 / (1.0 + math.exp(-2 * distance / standard_error))
        confidence = max(0.5, min(0.99, confidence))  # Clamp between 50% and 99%
        
        return level, confidence

class BaselineAssessmentEngine:
    """Core baseline assessment logic with IRT support."""
    
    def __init__(self, db: Session):
        self.db = db
        self.irt_engine = IRTEngine()
        self.level_mapper = LevelMapper()
        
    def start_baseline_session(self, learner_id: str, tenant_id: str, subject: str, metadata: Dict = None) -> AssessmentSession:
        """Start a new baseline assessment session."""
        # Create new session
        session = AssessmentSession(
            learner_id=learner_id,
            tenant_id=tenant_id,
            assessment_type="baseline",
            subject=subject,
            status=AssessmentStatus.CREATED.value,
            current_theta=0.0,  # Start with neutral ability
            standard_error=1.0,
            theta_history=[0.0],
            session_data=metadata or {}
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"Started baseline session {session.id} for learner {learner_id} in subject {subject}")
        return session
    
    def get_next_question(self, session: AssessmentSession) -> Optional[QuestionBank]:
        """Select next optimal question using IRT item selection."""
        # Get questions not yet answered in this session
        answered_question_ids = [r.question_id for r in session.responses]
        
        available_questions = self.db.query(QuestionBank).filter(
            and_(
                QuestionBank.subject == session.subject,
                QuestionBank.is_active == True,
                ~QuestionBank.id.in_(answered_question_ids)
            )
        ).all()
        
        if not available_questions:
            return None
            
        # For first question, select medium difficulty
        if not session.responses:
            medium_difficulty_questions = [q for q in available_questions if abs(q.difficulty) < 0.5]
            if medium_difficulty_questions:
                return min(medium_difficulty_questions, key=lambda q: abs(q.difficulty))
            return available_questions[0]
        
        # Select question that maximizes information at current theta
        best_question = None
        max_information = 0.0
        
        for question in available_questions:
            information = self.irt_engine.information_function(
                session.current_theta,
                question.difficulty,
                question.discrimination,
                question.guessing
            )
            
            if information > max_information:
                max_information = information
                best_question = question
        
        return best_question or available_questions[0]
    
    def process_response(self, session: AssessmentSession, question: QuestionBank, 
                        user_answer: str, response_time_ms: int = None) -> AssessmentResponse:
        """Process a user response and update IRT estimates."""
        # Determine if answer is correct
        is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
        
        # Create response record
        response = AssessmentResponse(
            session_id=session.id,
            question_id=question.id,
            user_answer=user_answer,
            is_correct=is_correct,
            response_time_ms=response_time_ms,
            question_order=len(session.responses) + 1,
            theta_before=session.current_theta
        )
        
        # Update theta estimate using all responses
        all_responses = [(r.question.difficulty, r.question.discrimination, r.question.guessing, r.is_correct) 
                        for r in session.responses]
        all_responses.append((question.difficulty, question.discrimination, question.guessing, is_correct))
        
        new_theta, new_se = self.irt_engine.update_theta_eap(session.current_theta, all_responses)
        
        # Update session
        session.current_theta = new_theta
        session.standard_error = new_se
        session.theta_history.append(new_theta)
        session.questions_answered += 1
        if is_correct:
            session.correct_answers += 1
        
        # Update response with theta after
        response.theta_after = new_theta
        response.information_value = self.irt_engine.information_function(
            new_theta, question.difficulty, question.discrimination, question.guessing
        )
        
        self.db.add(response)
        self.db.commit()
        
        logger.info(f"Processed response for session {session.id}: correct={is_correct}, new_theta={new_theta:.3f}")
        return response
    
    def should_terminate_assessment(self, session: AssessmentSession) -> bool:
        """Determine if assessment should terminate based on IRT criteria."""
        # Minimum questions requirement
        if session.questions_answered < 5:
            return False
            
        # Maximum questions limit
        if session.questions_answered >= 30:
            return True
            
        # Terminate if standard error is small enough (precise estimate)
        if session.standard_error < 0.3:
            return True
            
        # Terminate if theta estimate has stabilized
        if len(session.theta_history) >= 3:
            recent_thetas = session.theta_history[-3:]
            theta_stability = max(recent_thetas) - min(recent_thetas)
            if theta_stability < 0.2:
                return True
        
        return False
    
    def complete_assessment(self, session: AssessmentSession) -> AssessmentResult:
        """Complete the assessment and generate final results."""
        # Map theta to proficiency level
        level, confidence = self.level_mapper.theta_to_level(
            session.current_theta, 
            session.standard_error,
            session.subject
        )
        
        # Calculate accuracy
        accuracy = (session.correct_answers / session.questions_answered) * 100 if session.questions_answered > 0 else 0
        
        # Generate strengths, weaknesses, and recommendations
        strengths, weaknesses, recommendations = self._analyze_performance(session)
        
        # Calculate reliability (simplified)
        reliability = max(0.0, 1.0 - session.standard_error ** 2)
        
        # Calculate average response time
        response_times = [r.response_time_ms for r in session.responses if r.response_time_ms]
        avg_response_time = sum(response_times) // len(response_times) if response_times else None
        
        # Create result record
        result = AssessmentResult(
            session_id=session.id,
            learner_id=session.learner_id,
            subject=session.subject,
            final_theta=session.current_theta,
            standard_error=session.standard_error,
            reliability=reliability,
            proficiency_level=level,
            level_confidence=confidence,
            total_questions=session.questions_answered,
            correct_answers=session.correct_answers,
            accuracy_percentage=accuracy,
            average_response_time_ms=avg_response_time,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )
        
        # Update session status
        session.status = AssessmentStatus.COMPLETED.value
        session.completed_at = func.now()
        
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        
        logger.info(f"Completed baseline assessment {session.id}: level={level}, theta={session.current_theta:.3f}")
        return result
    
    def _analyze_performance(self, session: AssessmentSession) -> Tuple[List[str], List[str], List[str]]:
        """Analyze performance to generate strengths, weaknesses, and recommendations."""
        strengths = []
        weaknesses = []  
        recommendations = []
        
        # Analyze by difficulty level
        easy_correct = sum(1 for r in session.responses if r.is_correct and r.question.difficulty < -0.5)
        medium_correct = sum(1 for r in session.responses if r.is_correct and -0.5 <= r.question.difficulty <= 0.5)
        hard_correct = sum(1 for r in session.responses if r.is_correct and r.question.difficulty > 0.5)
        
        easy_total = sum(1 for r in session.responses if r.question.difficulty < -0.5)
        medium_total = sum(1 for r in session.responses if -0.5 <= r.question.difficulty <= 0.5)
        hard_total = sum(1 for r in session.responses if r.question.difficulty > 0.5)
        
        # Generate insights
        if easy_total > 0 and (easy_correct / easy_total) > 0.8:
            strengths.append(f"Strong foundation in basic {session.subject} concepts")
        if medium_total > 0 and (medium_correct / medium_total) > 0.7:
            strengths.append(f"Good grasp of intermediate {session.subject} skills")
        if hard_total > 0 and (hard_correct / hard_total) > 0.5:
            strengths.append(f"Shows potential in advanced {session.subject} topics")
            
        if easy_total > 0 and (easy_correct / easy_total) < 0.6:
            weaknesses.append(f"Needs reinforcement of fundamental {session.subject} concepts")
            recommendations.append(f"Focus on mastering basic {session.subject} skills before advancing")
        if medium_total > 0 and (medium_correct / medium_total) < 0.5:
            weaknesses.append(f"Struggles with intermediate {session.subject} problems")
            recommendations.append(f"Practice more intermediate-level {session.subject} exercises")
            
        # Response time analysis
        response_times = [r.response_time_ms for r in session.responses if r.response_time_ms]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            if avg_time > 120000:  # > 2 minutes average
                recommendations.append("Consider working on speed and fluency in problem-solving")
            elif avg_time < 15000:  # < 15 seconds average
                recommendations.append("Take more time to carefully read and analyze problems")
        
        return strengths, weaknesses, recommendations
