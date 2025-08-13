import re
import logging
from typing import List, Set

logger = logging.getLogger(__name__)

# Profanity filter - basic list for MVP (in production, use external service)
PROFANITY_WORDS = {
    'damn', 'hell', 'crap', 'stupid', 'idiot', 'dumb', 'moron', 'jerk',
    'shit', 'fuck', 'bitch', 'ass', 'piss', 'bastard',
    # Add more as needed - keep this list minimal for MVP
}

# PII patterns to detect
PII_PATTERNS = [
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
    r'\b\d{3}-\d{3}-\d{4}\b',  # Phone pattern
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email pattern
    r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b',  # Credit card pattern
]

# Common first names and surnames that shouldn't be used as aliases
COMMON_NAMES = {
    'john', 'jane', 'mike', 'michael', 'sarah', 'david', 'chris', 'jennifer',
    'robert', 'mary', 'james', 'patricia', 'william', 'linda', 'richard',
    'elizabeth', 'joseph', 'barbara', 'thomas', 'susan', 'charles', 'jessica',
    'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller',
    'davis', 'rodriguez', 'martinez', 'hernandez', 'lopez', 'gonzalez',
    # Add more common names as needed
}

class AliasValidationError(Exception):
    """Raised when alias validation fails"""
    pass

def validate_alias(alias: str) -> bool:
    """
    Validate alias for safety - no profanity, PII, or real names.
    
    Args:
        alias: The proposed alias string
        
    Returns:
        bool: True if alias is safe to use
        
    Raises:
        AliasValidationError: If alias is unsafe with specific reason
    """
    if not alias or len(alias.strip()) == 0:
        raise AliasValidationError("Alias cannot be empty")
    
    alias_clean = alias.strip().lower()
    
    # Length check
    if len(alias_clean) < 2:
        raise AliasValidationError("Alias must be at least 2 characters")
    
    if len(alias_clean) > 100:
        raise AliasValidationError("Alias cannot exceed 100 characters")
    
    # Check for profanity
    if _contains_profanity(alias_clean):
        logger.warning(f"Profanity detected in alias attempt - rejected")
        raise AliasValidationError("Alias contains inappropriate language")
    
    # Check for PII patterns
    if _contains_pii(alias):
        logger.warning(f"PII pattern detected in alias attempt - rejected")
        raise AliasValidationError("Alias appears to contain personal information")
    
    # Check for common names (potential real names)
    if _contains_common_names(alias_clean):
        logger.warning(f"Common name detected in alias attempt - rejected")
        raise AliasValidationError("Alias appears to be a real name - please use a nickname or creative alias")
    
    # Check for multiple consecutive spaces or special characters
    if re.search(r'\s{2,}', alias) or re.search(r'[^\w\s\-_]', alias):
        raise AliasValidationError("Alias can only contain letters, numbers, spaces, hyphens, and underscores")
    
    return True

def _contains_profanity(alias: str) -> bool:
    """Check if alias contains profanity"""
    # Split on common separators to catch variations (including underscores and hyphens)
    words = re.split(r'[_\-\s]+', alias.lower())
    return any(word in PROFANITY_WORDS for word in words if word)

def _contains_pii(alias: str) -> bool:
    """Check if alias contains PII patterns"""
    for pattern in PII_PATTERNS:
        if re.search(pattern, alias):
            return True
    return False

def _contains_common_names(alias: str) -> bool:
    """Check if alias contains common first names or surnames"""
    # Split on common separators to catch variations (including underscores and hyphens)
    words = re.split(r'[_\-\s]+', alias.lower())
    return any(word in COMMON_NAMES for word in words if word)

def redact_alias_from_logs(message: str, alias: str) -> str:
    """
    Redact alias from log messages to prevent exposure.
    
    Args:
        message: The log message
        alias: The alias to redact
        
    Returns:
        str: Message with alias redacted
    """
    if not alias:
        return message
    
    # Case-insensitive replacement
    pattern = re.escape(alias)
    return re.sub(pattern, "[ALIAS_REDACTED]", message, flags=re.IGNORECASE)

def generate_safe_log_context(learner_id: str, alias: str = None) -> str:
    """
    Generate a safe context string for logging that doesn't expose the alias.
    
    Args:
        learner_id: The learner's UUID
        alias: The learner's alias (will be redacted)
        
    Returns:
        str: Safe context string for logs
    """
    if alias:
        return f"learner_id={learner_id}, alias=[REDACTED]"
    else:
        return f"learner_id={learner_id}"
