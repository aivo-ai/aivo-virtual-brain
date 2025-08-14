"""
AIVO Inference Gateway - PII Scrubbing Module
S2-01 Implementation: Detects and masks PII in requests/responses
"""

import re
import hashlib
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class PIIType(Enum):
    """PII type classifications"""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    NAME = "name"  # First/last names
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    LICENSE_PLATE = "license_plate"


@dataclass
class PIIMatch:
    """Represents a detected PII match"""
    pii_type: PIIType
    start: int
    end: int
    original_text: str
    confidence: float
    replacement: str


class PIIDetector:
    """PII detection engine with pattern matching and ML heuristics"""
    
    # Regex patterns for common PII types
    PATTERNS = {
        PIIType.EMAIL: re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        PIIType.PHONE: re.compile(
            r'(?:\+?1[-.\s]?)?(?:\([0-9]{3}\)|[0-9]{3})[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        ),
        PIIType.SSN: re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b'
        ),
        PIIType.CREDIT_CARD: re.compile(
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'
        ),
        PIIType.IP_ADDRESS: re.compile(
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ),
        PIIType.DATE_OF_BIRTH: re.compile(
            r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b'
        ),
        PIIType.LICENSE_PLATE: re.compile(
            r'\b[A-Z]{2,3}[-\s]?\d{3,4}\b|\b\d{3}[-\s]?[A-Z]{3}\b',
            re.IGNORECASE
        )
    }
    
    # Common first/last names for heuristic detection
    COMMON_FIRST_NAMES = {
        "james", "robert", "john", "michael", "david", "william", "richard", "charles",
        "joseph", "thomas", "christopher", "daniel", "paul", "mark", "donald", "george",
        "mary", "patricia", "jennifer", "linda", "elizabeth", "barbara", "susan",
        "jessica", "sarah", "karen", "nancy", "lisa", "betty", "helen", "sandra"
    }
    
    COMMON_LAST_NAMES = {
        "smith", "johnson", "williams", "brown", "jones", "garcia", "miller", "davis",
        "rodriguez", "martinez", "hernandez", "lopez", "gonzalez", "wilson", "anderson",
        "thomas", "taylor", "moore", "jackson", "martin", "lee", "perez", "thompson"
    }
    
    def __init__(self):
        self.confidence_threshold = 0.7
    
    def detect_pii(self, text: str) -> List[PIIMatch]:
        """Detect all PII in the given text"""
        with tracer.start_as_current_span("detect_pii") as span:
            matches = []
            
            # Pattern-based detection
            for pii_type, pattern in self.PATTERNS.items():
                for match in pattern.finditer(text):
                    confidence = self._calculate_pattern_confidence(pii_type, match.group())
                    if confidence >= self.confidence_threshold:
                        matches.append(PIIMatch(
                            pii_type=pii_type,
                            start=match.start(),
                            end=match.end(),
                            original_text=match.group(),
                            confidence=confidence,
                            replacement=self._generate_replacement(pii_type, match.group())
                        ))
            
            # Name detection using heuristics
            name_matches = self._detect_names(text)
            matches.extend(name_matches)
            
            # Address detection using heuristics
            address_matches = self._detect_addresses(text)
            matches.extend(address_matches)
            
            # Remove overlapping matches (keep higher confidence)
            matches = self._remove_overlaps(matches)
            
            span.set_attribute("pii_matches_found", len(matches))
            span.set_attribute("pii_types", [m.pii_type.value for m in matches])
            
            return matches
    
    def _calculate_pattern_confidence(self, pii_type: PIIType, text: str) -> float:
        """Calculate confidence score for pattern matches"""
        base_confidence = 0.8
        
        # Additional validation for specific types
        if pii_type == PIIType.CREDIT_CARD:
            # Luhn algorithm check
            if self._luhn_check(text.replace(' ', '').replace('-', '')):
                return 0.95
            else:
                return 0.3
        
        elif pii_type == PIIType.SSN:
            # Basic SSN validation
            digits = text.replace('-', '')
            if len(digits) == 9 and not digits.startswith('000'):
                return 0.9
            else:
                return 0.4
        
        elif pii_type == PIIType.PHONE:
            # Basic phone validation
            digits = re.sub(r'[^\d]', '', text)
            if len(digits) == 10 or len(digits) == 11:
                return 0.85
            else:
                return 0.5
        
        return base_confidence
    
    def _luhn_check(self, card_number: str) -> bool:
        """Validate credit card using Luhn algorithm"""
        def digits_of(number):
            return [int(d) for d in str(number)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        
        return checksum % 10 == 0
    
    def _detect_names(self, text: str) -> List[PIIMatch]:
        """Detect potential names using heuristics"""
        matches = []
        
        # Look for capitalized words that could be names
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        
        for i, word in enumerate(words):
            if word.lower() in self.COMMON_FIRST_NAMES:
                # Look for a last name following
                start_pos = text.find(word)
                next_word_match = re.search(r'\s+([A-Z][a-z]+)\b', text[start_pos + len(word):])
                
                if next_word_match and next_word_match.group(1).lower() in self.COMMON_LAST_NAMES:
                    full_name = f"{word} {next_word_match.group(1)}"
                    matches.append(PIIMatch(
                        pii_type=PIIType.NAME,
                        start=start_pos,
                        end=start_pos + len(full_name),
                        original_text=full_name,
                        confidence=0.75,
                        replacement=self._generate_replacement(PIIType.NAME, full_name)
                    ))
        
        return matches
    
    def _detect_addresses(self, text: str) -> List[PIIMatch]:
        """Detect potential addresses using pattern matching"""
        matches = []
        
        # Simple address pattern: number + street name + (optional apt/suite)
        address_pattern = re.compile(
            r'\b\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct)\b(?:\s+(?:Apt|Suite|Unit)\s*\d+)?',
            re.IGNORECASE
        )
        
        for match in address_pattern.finditer(text):
            matches.append(PIIMatch(
                pii_type=PIIType.ADDRESS,
                start=match.start(),
                end=match.end(),
                original_text=match.group(),
                confidence=0.7,
                replacement=self._generate_replacement(PIIType.ADDRESS, match.group())
            ))
        
        return matches
    
    def _remove_overlaps(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove overlapping matches, keeping higher confidence ones"""
        if not matches:
            return matches
        
        # Sort by start position
        matches.sort(key=lambda x: x.start)
        
        result = [matches[0]]
        
        for match in matches[1:]:
            last_match = result[-1]
            
            # Check for overlap
            if match.start < last_match.end:
                # Keep the higher confidence match
                if match.confidence > last_match.confidence:
                    result[-1] = match
            else:
                result.append(match)
        
        return result
    
    def _generate_replacement(self, pii_type: PIIType, original: str) -> str:
        """Generate appropriate replacement for PII"""
        # Create consistent hash-based replacements
        hash_suffix = hashlib.md5(original.encode()).hexdigest()[:6]
        
        replacements = {
            PIIType.EMAIL: f"[EMAIL_{hash_suffix}]",
            PIIType.PHONE: f"[PHONE_{hash_suffix}]",
            PIIType.SSN: f"[SSN_{hash_suffix}]",
            PIIType.CREDIT_CARD: f"[CARD_{hash_suffix}]",
            PIIType.IP_ADDRESS: f"[IP_{hash_suffix}]",
            PIIType.NAME: f"[NAME_{hash_suffix}]",
            PIIType.ADDRESS: f"[ADDRESS_{hash_suffix}]",
            PIIType.DATE_OF_BIRTH: f"[DOB_{hash_suffix}]",
            PIIType.PASSPORT: f"[PASSPORT_{hash_suffix}]",
            PIIType.LICENSE_PLATE: f"[PLATE_{hash_suffix}]",
        }
        
        return replacements.get(pii_type, f"[PII_{hash_suffix}]")


class PIIScrubber:
    """Main PII scrubbing service"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.detector = PIIDetector()
        self.enabled_types = set(PIIType)  # Enable all types by default
        self.scrub_mode = self.config.get("scrub_mode", "mask")  # mask, hash, remove
        
        # Configure enabled PII types
        if "enabled_types" in self.config:
            self.enabled_types = {PIIType(t) for t in self.config["enabled_types"]}
    
    def scrub_text(self, text: str) -> Tuple[str, List[PIIMatch]]:
        """Scrub PII from text and return cleaned text with matches"""
        with tracer.start_as_current_span("scrub_text") as span:
            matches = self.detector.detect_pii(text)
            
            # Filter matches by enabled types
            matches = [m for m in matches if m.pii_type in self.enabled_types]
            
            if not matches:
                span.set_attribute("pii_scrubbed", False)
                return text, matches
            
            # Apply scrubbing (reverse order to maintain positions)
            cleaned_text = text
            for match in reversed(matches):
                replacement = self._get_replacement(match)
                cleaned_text = (
                    cleaned_text[:match.start] + 
                    replacement + 
                    cleaned_text[match.end:]
                )
            
            span.set_attribute("pii_scrubbed", True)
            span.set_attribute("pii_matches_count", len(matches))
            
            return cleaned_text, matches
    
    def scrub_request(self, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[PIIMatch]]:
        """Scrub PII from request data"""
        with tracer.start_as_current_span("scrub_request") as span:
            all_matches = []
            scrubbed_data = {}
            
            for key, value in request_data.items():
                if isinstance(value, str):
                    scrubbed_value, matches = self.scrub_text(value)
                    scrubbed_data[key] = scrubbed_value
                    all_matches.extend(matches)
                elif isinstance(value, list):
                    scrubbed_list = []
                    for item in value:
                        if isinstance(item, str):
                            scrubbed_item, matches = self.scrub_text(item)
                            scrubbed_list.append(scrubbed_item)
                            all_matches.extend(matches)
                        else:
                            scrubbed_list.append(item)
                    scrubbed_data[key] = scrubbed_list
                elif isinstance(value, dict):
                    # Recursively scrub nested dictionaries
                    scrubbed_nested, matches = self.scrub_request(value)
                    scrubbed_data[key] = scrubbed_nested
                    all_matches.extend(matches)
                else:
                    scrubbed_data[key] = value
            
            span.set_attribute("total_pii_matches", len(all_matches))
            
            return scrubbed_data, all_matches
    
    def _get_replacement(self, match: PIIMatch) -> str:
        """Get replacement text based on scrub mode"""
        if self.scrub_mode == "remove":
            return ""
        elif self.scrub_mode == "hash":
            return hashlib.md5(match.original_text.encode()).hexdigest()[:8]
        else:  # mask mode (default)
            return match.replacement
    
    def is_pii_present(self, text: str) -> bool:
        """Quick check if text contains PII"""
        matches = self.detector.detect_pii(text)
        return len([m for m in matches if m.pii_type in self.enabled_types]) > 0
    
    def get_pii_summary(self, matches: List[PIIMatch]) -> Dict[str, int]:
        """Get summary of PII types found"""
        summary = {}
        for match in matches:
            pii_type = match.pii_type.value
            summary[pii_type] = summary.get(pii_type, 0) + 1
        return summary


# Configuration presets
DEFAULT_CONFIG = {
    "scrub_mode": "mask",
    "enabled_types": [t.value for t in PIIType]
}

STRICT_CONFIG = {
    "scrub_mode": "remove",
    "enabled_types": [t.value for t in PIIType]
}

LENIENT_CONFIG = {
    "scrub_mode": "mask", 
    "enabled_types": [
        PIIType.EMAIL.value,
        PIIType.PHONE.value,
        PIIType.SSN.value,
        PIIType.CREDIT_CARD.value
    ]
}
