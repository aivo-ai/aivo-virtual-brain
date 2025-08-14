"""
AIVO Assessment Service - IRT (Item Response Theory) Logic
S2-08 Implementation - 3-Parameter Logistic Model for Adaptive Assessment

This module implements the Three Parameter Logistic (3PL) IRT model for:
- Ability estimation (theta) using Maximum Likelihood Estimation
- Information functions for optimal item selection
- Standard error calculation for stopping criteria
- Item calibration utilities for question banks
"""

import math
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from scipy.optimize import minimize_scalar, fsolve
from scipy.stats import norm
import logging

logger = logging.getLogger(__name__)

class IRTParameters:
    """Container for IRT item parameters."""
    
    def __init__(self, difficulty: float, discrimination: float, guessing: float = 0.0):
        """
        Initialize IRT parameters for 3PL model.
        
        Args:
            difficulty (float): Item difficulty parameter (b)
            discrimination (float): Item discrimination parameter (a)
            guessing (float): Guessing parameter (c), default 0.0
        """
        self.difficulty = difficulty  # b parameter
        self.discrimination = discrimination  # a parameter
        self.guessing = guessing  # c parameter
    
    def __repr__(self):
        return f"IRT(a={self.discrimination:.3f}, b={self.difficulty:.3f}, c={self.guessing:.3f})"

class IRTEngine:
    """
    IRT Engine implementing 3-Parameter Logistic Model for adaptive assessment.
    
    The 3PL model: P(theta) = c + (1-c) * (1 / (1 + exp(-a*(theta - b))))
    
    Where:
    - theta: ability level
    - a: discrimination parameter (slope)
    - b: difficulty parameter (location)
    - c: guessing parameter (lower asymptote)
    """
    
    def __init__(self):
        """Initialize IRT Engine."""
        self.logger = logger
        
        # IRT Model parameters
        self.min_theta = -4.0  # Minimum ability level
        self.max_theta = 4.0   # Maximum ability level
        self.default_se = 1.0  # Default standard error
        
        # Adaptive testing parameters
        self.target_se = 0.25  # Target standard error for stopping
        self.max_questions = 10  # Maximum questions per session
        self.min_questions = 3   # Minimum questions before stopping
    
    def probability(self, theta: float, item_params: IRTParameters) -> float:
        """
        Calculate probability of correct response using 3PL model.
        
        P(theta) = c + (1-c) * (1 / (1 + exp(-a*(theta - b))))
        
        Args:
            theta: Ability level
            item_params: IRT parameters for the item
            
        Returns:
            Probability of correct response (0-1)
        """
        a, b, c = item_params.discrimination, item_params.difficulty, item_params.guessing
        
        # Prevent overflow in exponential
        exponent = -a * (theta - b)
        exponent = max(min(exponent, 500), -500)
        
        try:
            prob = c + (1 - c) * (1 / (1 + math.exp(exponent)))
            return max(0.01, min(0.99, prob))  # Clamp to avoid numerical issues
        except (OverflowError, ZeroDivisionError):
            return 0.5  # Fallback to neutral probability
    
    def information(self, theta: float, item_params: IRTParameters) -> float:
        """
        Calculate Fisher information for an item at given ability level.
        
        I(theta) = a² * P(theta) * Q(theta) * (1-c)² / P(theta)²
        
        Where Q(theta) = 1 - P(theta)
        
        Args:
            theta: Ability level
            item_params: IRT parameters for the item
            
        Returns:
            Information value
        """
        a, c = item_params.discrimination, item_params.guessing
        p = self.probability(theta, item_params)
        q = 1 - p
        
        # Handle edge cases
        if p <= 0.01 or p >= 0.99:
            return 0.0
            
        try:
            # Information formula for 3PL model
            numerator = (a ** 2) * p * q * ((1 - c) ** 2)
            denominator = (p ** 2)
            info = numerator / denominator
            
            return max(0.0, info)
        except (ZeroDivisionError, ValueError):
            return 0.0
    
    def likelihood(self, theta: float, responses: List[Tuple[bool, IRTParameters]]) -> float:
        """
        Calculate likelihood of observed responses given ability level.
        
        L(theta) = ∏ P(theta)^u * (1-P(theta))^(1-u)
        
        Args:
            theta: Ability level
            responses: List of (is_correct, item_params) tuples
            
        Returns:
            Log-likelihood value
        """
        log_likelihood = 0.0
        
        for is_correct, item_params in responses:
            p = self.probability(theta, item_params)
            
            if is_correct:
                log_likelihood += math.log(max(0.001, p))
            else:
                log_likelihood += math.log(max(0.001, 1 - p))
        
        return log_likelihood
    
    def estimate_ability(self, responses: List[Tuple[bool, IRTParameters]], 
                        initial_theta: float = 0.0) -> Tuple[float, float]:
        """
        Estimate ability level using Maximum Likelihood Estimation.
        
        Args:
            responses: List of (is_correct, item_params) tuples
            initial_theta: Starting point for optimization
            
        Returns:
            Tuple of (theta_estimate, standard_error)
        """
        if not responses:
            return initial_theta, self.default_se
        
        try:
            # Define negative log-likelihood function for minimization
            def neg_log_likelihood(theta):
                return -self.likelihood(theta, responses)
            
            # Find MLE using bounded optimization
            result = minimize_scalar(
                neg_log_likelihood,
                bounds=(self.min_theta, self.max_theta),
                method='bounded'
            )
            
            theta_est = result.x
            
            # Calculate standard error using Fisher Information
            se = self.calculate_standard_error(theta_est, responses)
            
            self.logger.info(f"Ability estimated: theta={theta_est:.3f}, SE={se:.3f}")
            return theta_est, se
            
        except Exception as e:
            self.logger.warning(f"Ability estimation failed: {e}")
            # Fallback: simple proportion correct with adjustment
            correct = sum(1 for is_correct, _ in responses if is_correct)
            proportion = correct / len(responses)
            
            # Convert proportion to theta using normal inverse
            if proportion >= 0.95:
                theta_fallback = 2.0
            elif proportion <= 0.05:
                theta_fallback = -2.0
            else:
                theta_fallback = norm.ppf(proportion)
            
            return theta_fallback, self.default_se / math.sqrt(len(responses))
    
    def calculate_standard_error(self, theta: float, responses: List[Tuple[bool, IRTParameters]]) -> float:
        """
        Calculate standard error of ability estimate.
        
        SE(theta) = 1 / sqrt(sum(I(theta)))
        
        Args:
            theta: Current ability estimate
            responses: List of (is_correct, item_params) tuples
            
        Returns:
            Standard error
        """
        total_info = sum(self.information(theta, item_params) 
                        for _, item_params in responses)
        
        if total_info <= 0:
            return self.default_se
        
        return 1.0 / math.sqrt(total_info)
    
    def select_next_item(self, theta: float, item_pool: List[Dict[str, Any]], 
                        used_items: List[str]) -> Optional[Dict[str, Any]]:
        """
        Select next optimal item using Maximum Information criterion.
        
        Args:
            theta: Current ability estimate
            item_pool: Available items with IRT parameters
            used_items: List of already used item IDs
            
        Returns:
            Next optimal item or None if pool exhausted
        """
        available_items = [
            item for item in item_pool 
            if item['id'] not in used_items
        ]
        
        if not available_items:
            return None
        
        # Calculate information for each available item
        best_item = None
        max_info = -1.0
        
        for item in available_items:
            item_params = IRTParameters(
                difficulty=item['difficulty'],
                discrimination=item['discrimination'],
                guessing=item.get('guessing', 0.0)
            )
            
            info = self.information(theta, item_params)
            
            if info > max_info:
                max_info = info
                best_item = item
        
        if best_item:
            self.logger.info(f"Selected item {best_item['id']} with info={max_info:.3f}")
        
        return best_item
    
    def should_stop_assessment(self, current_se: float, num_questions: int) -> bool:
        """
        Determine if assessment should stop based on stopping criteria.
        
        Args:
            current_se: Current standard error
            num_questions: Number of questions answered
            
        Returns:
            True if assessment should stop
        """
        # Stop if target precision achieved and minimum questions met
        if current_se <= self.target_se and num_questions >= self.min_questions:
            return True
        
        # Stop if maximum questions reached
        if num_questions >= self.max_questions:
            return True
        
        return False
    
    def map_theta_to_level(self, theta: float, se: float) -> Tuple[str, float]:
        """
        Map theta estimate to proficiency level (L0-L4) with confidence.
        
        Level mapping based on theta ranges:
        - L0 (Beginner): theta < -1.5
        - L1 (Elementary): -1.5 <= theta < -0.5  
        - L2 (Intermediate): -0.5 <= theta < 0.5
        - L3 (Advanced): 0.5 <= theta < 1.5
        - L4 (Expert): theta >= 1.5
        
        Args:
            theta: Ability estimate
            se: Standard error
            
        Returns:
            Tuple of (level, confidence)
        """
        # Define level boundaries
        boundaries = {
            'L0': (-float('inf'), -1.5),
            'L1': (-1.5, -0.5),
            'L2': (-0.5, 0.5), 
            'L3': (0.5, 1.5),
            'L4': (1.5, float('inf'))
        }
        
        # Find current level
        current_level = None
        for level, (lower, upper) in boundaries.items():
            if lower <= theta < upper:
                current_level = level
                break
        
        if current_level is None:
            current_level = 'L2'  # Default fallback
        
        # Calculate confidence using normal distribution
        # Confidence = probability that true theta is in current level range
        lower, upper = boundaries[current_level]
        
        if lower == -float('inf'):
            confidence = norm.cdf((upper - theta) / se)
        elif upper == float('inf'):
            confidence = 1 - norm.cdf((lower - theta) / se)
        else:
            confidence = (norm.cdf((upper - theta) / se) - 
                         norm.cdf((lower - theta) / se))
        
        confidence = max(0.5, min(0.99, confidence))  # Reasonable bounds
        
        self.logger.info(f"Level mapping: theta={theta:.3f} -> {current_level} (conf={confidence:.2f})")
        
        return current_level, confidence

class ItemCalibration:
    """Utilities for calibrating item parameters using response data."""
    
    def __init__(self):
        """Initialize calibration utilities."""
        self.logger = logger
        
    def estimate_item_parameters(self, responses_data: List[Dict[str, Any]]) -> IRTParameters:
        """
        Estimate IRT parameters for an item using response data.
        
        Uses simple classical test theory approximations:
        - Difficulty (b): -logit(p) where p is proportion correct
        - Discrimination (a): Based on point-biserial correlation
        - Guessing (c): Set to 0 for simplicity, or estimated from low-ability responses
        
        Args:
            responses_data: List of response records with ability and correctness
            
        Returns:
            Estimated IRT parameters
        """
        if not responses_data:
            return IRTParameters(0.0, 1.0, 0.0)
        
        # Extract data
        abilities = [r['theta'] for r in responses_data]
        correct = [r['is_correct'] for r in responses_data]
        
        # Proportion correct (difficulty estimation)
        p_correct = sum(correct) / len(correct)
        p_correct = max(0.01, min(0.99, p_correct))  # Avoid extremes
        
        # Difficulty: -logit(p)
        difficulty = -math.log(p_correct / (1 - p_correct))
        
        # Discrimination: point-biserial correlation scaled
        if len(set(correct)) > 1 and len(set(abilities)) > 1:
            # Simple point-biserial approximation
            mean_ability_correct = np.mean([a for a, c in zip(abilities, correct) if c])
            mean_ability_incorrect = np.mean([a for a, c in zip(abilities, correct) if not c])
            
            if not math.isnan(mean_ability_correct) and not math.isnan(mean_ability_incorrect):
                discrimination = abs(mean_ability_correct - mean_ability_incorrect)
                discrimination = max(0.5, min(3.0, discrimination))  # Reasonable bounds
            else:
                discrimination = 1.0
        else:
            discrimination = 1.0
        
        # Guessing: estimate from low-ability responses (simplified)
        low_ability_responses = [c for a, c in zip(abilities, correct) if a < -1.5]
        if low_ability_responses:
            guessing = sum(low_ability_responses) / len(low_ability_responses)
            guessing = max(0.0, min(0.3, guessing))  # Reasonable bounds for MC
        else:
            guessing = 0.0
        
        params = IRTParameters(difficulty, discrimination, guessing)
        self.logger.info(f"Calibrated item parameters: {params}")
        
        return params
    
    def batch_calibrate_items(self, item_responses: Dict[str, List[Dict[str, Any]]]) -> Dict[str, IRTParameters]:
        """
        Calibrate multiple items from response data.
        
        Args:
            item_responses: Dict mapping item_id to list of response records
            
        Returns:
            Dict mapping item_id to calibrated IRT parameters
        """
        calibrated_params = {}
        
        for item_id, responses in item_responses.items():
            if len(responses) >= 10:  # Minimum responses for calibration
                params = self.estimate_item_parameters(responses)
                calibrated_params[item_id] = params
            else:
                # Default parameters for insufficient data
                calibrated_params[item_id] = IRTParameters(0.0, 1.0, 0.0)
                self.logger.warning(f"Insufficient data for item {item_id}, using defaults")
        
        return calibrated_params

# Convenience functions for common operations
def quick_ability_estimate(responses: List[Tuple[bool, float, float, float]], 
                          initial_theta: float = 0.0) -> Tuple[float, float]:
    """
    Quick ability estimation with simplified interface.
    
    Args:
        responses: List of (is_correct, difficulty, discrimination, guessing) tuples
        initial_theta: Starting ability estimate
        
    Returns:
        Tuple of (theta_estimate, standard_error)
    """
    engine = IRTEngine()
    irt_responses = [
        (is_correct, IRTParameters(b, a, c))
        for is_correct, b, a, c in responses
    ]
    return engine.estimate_ability(irt_responses, initial_theta)

def select_optimal_item(theta: float, item_pool: List[Dict[str, Any]], 
                       used_items: List[str] = None) -> Optional[Dict[str, Any]]:
    """
    Select optimal next item for adaptive testing.
    
    Args:
        theta: Current ability estimate
        item_pool: Available items with IRT parameters
        used_items: Previously used item IDs
        
    Returns:
        Optimal next item or None
    """
    engine = IRTEngine()
    return engine.select_next_item(theta, item_pool, used_items or [])

def theta_to_level_mapping(theta: float, se: float = 0.5) -> Tuple[str, float]:
    """
    Convert theta to proficiency level with confidence.
    
    Args:
        theta: Ability estimate
        se: Standard error
        
    Returns:
        Tuple of (level, confidence)
    """
    engine = IRTEngine()
    return engine.map_theta_to_level(theta, se)
