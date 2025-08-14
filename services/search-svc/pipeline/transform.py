"""
Data Transformation and RBAC Filtering for Search Pipeline

Transforms raw database events into search-optimized documents
with role-based access control filtering and field masking.
"""
import re
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class RBACRule:
    """Role-based access control rule definition."""
    entity_type: str
    field_name: str
    allowed_roles: Set[str]
    mask_strategy: str = "remove"  # remove, hash, redact
    condition: Optional[str] = None


class DataTransformer:
    """
    Transforms raw database records into search-optimized documents.
    
    Handles data normalization, enrichment, and preparation for indexing
    with subject-specific processing.
    """
    
    def __init__(self):
        self.text_processors = {
            "mathematics": self._process_math_content,
            "math": self._process_math_content,
            "english": self._process_ela_content,
            "ela": self._process_ela_content,
            "science": self._process_science_content,
            "social_studies": self._process_social_studies_content
        }
    
    def transform(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform entity data for search indexing."""
        try:
            # Apply entity-specific transformations
            if entity_type == "learner":
                return self._transform_learner(data)
            elif entity_type == "lesson":
                return self._transform_lesson(data)
            elif entity_type == "assessment":
                return self._transform_assessment(data)
            elif entity_type == "user":
                return self._transform_user(data)
            else:
                return self._transform_generic(data)
                
        except Exception as e:
            logger.error(f"Transformation failed for {entity_type}: {e}")
            return data  # Return original data as fallback
    
    def _transform_learner(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform learner data for search."""
        transformed = {
            "id": data.get("id"),
            "name": self._normalize_name(data.get("name", "")),
            "email": data.get("email", "").lower(),
            "grade_level": str(data.get("grade_level", "")),
            "status": data.get("status", "active"),
            "created_at": self._format_datetime(data.get("created_at")),
            "updated_at": self._format_datetime(data.get("updated_at")),
            "tenant_id": data.get("tenant_id"),
            "school_id": data.get("school_id")
        }
        
        # Extract subjects from enrollment data
        subjects = []
        if "enrollments" in data:
            for enrollment in data.get("enrollments", []):
                if enrollment.get("subject"):
                    subjects.append(enrollment["subject"].lower())
        transformed["subjects"] = list(set(subjects))
        
        # Add search-friendly fields
        transformed["search_text"] = self._build_search_text([
            transformed.get("name", ""),
            transformed.get("email", ""),
            " ".join(transformed.get("subjects", []))
        ])
        
        # Add suggest field for autocomplete
        transformed["name_suggest"] = {
            "input": [
                transformed.get("name", ""),
                transformed.get("email", "").split("@")[0]  # Email prefix
            ],
            "weight": 10 if transformed.get("status") == "active" else 5
        }
        
        return self._clean_empty_fields(transformed)
    
    def _transform_lesson(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform lesson data for search."""
        transformed = {
            "id": data.get("id"),
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "subject": data.get("subject", "").lower(),
            "grade_level": str(data.get("grade_level", "")),
            "difficulty": data.get("difficulty_level", "intermediate"),
            "duration_minutes": data.get("duration_minutes", 0),
            "status": data.get("status", "draft"),
            "created_by": data.get("created_by"),
            "tenant_id": data.get("tenant_id"),
            "created_at": self._format_datetime(data.get("created_at")),
            "updated_at": self._format_datetime(data.get("updated_at"))
        }
        
        # Process topics/tags
        topics = []
        if "topic" in data:
            topics.append(data["topic"])
        if "tags" in data:
            topics.extend(data.get("tags", []))
        transformed["topics"] = [t.lower() for t in topics if t]
        
        # Extract and process content based on subject
        content = data.get("content", "")
        if content:
            subject = transformed.get("subject", "")
            if subject in self.text_processors:
                content = self.text_processors[subject](content)
            transformed["content"] = content
        
        # Build comprehensive search text
        transformed["search_text"] = self._build_search_text([
            transformed.get("title", ""),
            transformed.get("description", ""),
            transformed.get("content", ""),
            " ".join(transformed.get("topics", []))
        ])
        
        # Add suggest field with weighted inputs
        transformed["title_suggest"] = {
            "input": [
                transformed.get("title", ""),
                *transformed.get("topics", [])
            ],
            "weight": 10 if transformed.get("status") == "published" else 3
        }
        
        return self._clean_empty_fields(transformed)
    
    def _transform_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform assessment data for search."""
        transformed = {
            "id": data.get("id"),
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "subject": data.get("subject", "").lower(),
            "status": data.get("status", "draft"),
            "tenant_id": data.get("tenant_id"),
            "created_at": self._format_datetime(data.get("created_at")),
            "updated_at": self._format_datetime(data.get("updated_at"))
        }
        
        # Process grade levels
        if "grade_levels" in data:
            transformed["grade_levels"] = [str(g) for g in data["grade_levels"]]
        elif "grade_level" in data:
            transformed["grade_levels"] = [str(data["grade_level"])]
        
        # Process curriculum standards
        transformed["standards"] = data.get("curriculum_standards", [])
        
        # Extract and process questions
        questions = []
        question_texts = []
        
        if "questions" in data:
            for q in data["questions"]:
                question_data = {
                    "id": q.get("id"),
                    "text": q.get("text", ""),
                    "type": q.get("type", "multiple_choice"),
                    "difficulty": q.get("difficulty", "medium")
                }
                questions.append(question_data)
                question_texts.append(q.get("text", ""))
        
        transformed["questions"] = questions
        
        # Build search text including questions
        transformed["search_text"] = self._build_search_text([
            transformed.get("title", ""),
            transformed.get("description", ""),
            " ".join(question_texts),
            " ".join(transformed.get("standards", []))
        ])
        
        # Add suggest field
        transformed["title_suggest"] = {
            "input": [
                transformed.get("title", ""),
                *transformed.get("standards", [])
            ],
            "weight": 8 if transformed.get("status") == "published" else 2
        }
        
        return self._clean_empty_fields(transformed)
    
    def _transform_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user data (similar to learner but for staff)."""
        transformed = {
            "id": data.get("id"),
            "name": self._normalize_name(data.get("name", "")),
            "email": data.get("email", "").lower(),
            "role": data.get("role", "").lower(),
            "status": data.get("status", "active"),
            "created_at": self._format_datetime(data.get("created_at")),
            "updated_at": self._format_datetime(data.get("updated_at")),
            "tenant_id": data.get("tenant_id"),
            "school_id": data.get("school_id")
        }
        
        # Extract subjects for teachers
        if transformed.get("role") in ["teacher", "instructor"]:
            subjects = data.get("subjects", [])
            transformed["subjects"] = [s.lower() for s in subjects]
        
        # Build search text
        transformed["search_text"] = self._build_search_text([
            transformed.get("name", ""),
            transformed.get("email", ""),
            transformed.get("role", "")
        ])
        
        return self._clean_empty_fields(transformed)
    
    def _transform_generic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic transformation for unknown entity types."""
        transformed = dict(data)  # Copy original data
        
        # Add timestamp formatting
        for field in ["created_at", "updated_at"]:
            if field in transformed:
                transformed[field] = self._format_datetime(transformed[field])
        
        return transformed
    
    def _process_math_content(self, content: str) -> str:
        """Process mathematical content for search optimization."""
        # Extract mathematical expressions and formulas
        content = self._extract_math_terms(content)
        
        # Normalize mathematical notation
        content = re.sub(r'\b(\d+)/(\d+)\b', r'\1 divided by \2', content)  # Fractions
        content = re.sub(r'\^(\d+)', r' to the power of \1', content)  # Exponents
        content = re.sub(r'√(\d+)', r'square root of \1', content)  # Square roots
        
        return content
    
    def _process_ela_content(self, content: str) -> str:
        """Process English Language Arts content for search optimization."""
        # Extract key literary terms and concepts
        content = self._extract_ela_terms(content)
        
        # Normalize reading level indicators
        content = re.sub(r'grade\s+(\d+)', r'grade level \1', content, flags=re.IGNORECASE)
        
        return content
    
    def _process_science_content(self, content: str) -> str:
        """Process science content for search optimization."""
        # Extract scientific terms and concepts
        content = self._extract_science_terms(content)
        return content
    
    def _process_social_studies_content(self, content: str) -> str:
        """Process social studies content for search optimization."""
        # Extract historical dates and events
        content = re.sub(r'\b(\d{4})\s*-\s*(\d{4})\b', r'\1 to \2', content)  # Date ranges
        return content
    
    def _extract_math_terms(self, content: str) -> str:
        """Extract and normalize mathematical terms."""
        # Mathematical operations
        math_terms = {
            '+': 'plus addition',
            '-': 'minus subtraction', 
            '*': 'times multiplication multiply',
            '/': 'divided division',
            '=': 'equals equal',
            '>': 'greater than',
            '<': 'less than',
            '≥': 'greater than or equal',
            '≤': 'less than or equal'
        }
        
        for symbol, words in math_terms.items():
            if symbol in content:
                content = content.replace(symbol, f' {words} ')
        
        return content
    
    def _extract_ela_terms(self, content: str) -> str:
        """Extract and normalize ELA terms."""
        # Common ELA concepts for better searchability
        ela_expansions = {
            'metaphor': 'metaphor figurative language comparison',
            'simile': 'simile figurative language like as comparison',
            'alliteration': 'alliteration repetition sound',
            'theme': 'theme main idea message',
            'plot': 'plot story structure narrative'
        }
        
        for term, expansion in ela_expansions.items():
            if term in content.lower():
                content = content + f' {expansion}'
        
        return content
    
    def _extract_science_terms(self, content: str) -> str:
        """Extract and normalize science terms."""
        # Scientific notation and units
        content = re.sub(r'(\d+)\s*x\s*10\^([+-]?\d+)', r'\1 times ten to the \2', content)
        return content
    
    def _normalize_name(self, name: str) -> str:
        """Normalize person names for consistent search."""
        if not name:
            return ""
        
        # Basic cleaning and standardization
        name = re.sub(r'\s+', ' ', name.strip())  # Normalize whitespace
        name = re.sub(r'[^\w\s-]', '', name)     # Remove special chars except hyphens
        
        return name
    
    def _build_search_text(self, text_parts: List[str]) -> str:
        """Build comprehensive search text from multiple fields."""
        text = " ".join([part for part in text_parts if part])
        
        # Clean and normalize
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()
        
        return text
    
    def _format_datetime(self, dt: Any) -> Optional[str]:
        """Format datetime for OpenSearch indexing."""
        if not dt:
            return None
        
        if isinstance(dt, str):
            return dt
        elif isinstance(dt, datetime):
            return dt.isoformat()
        else:
            return str(dt)
    
    def _clean_empty_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove empty or None fields from document."""
        return {k: v for k, v in data.items() if v is not None and v != ""}


class RBACFilter:
    """
    Role-Based Access Control filter for search documents.
    
    Applies data masking, field removal, and access controls based on
    user roles and data sensitivity levels.
    """
    
    def __init__(self):
        self.rbac_rules = self._load_rbac_rules()
        self.sensitive_patterns = self._load_sensitive_patterns()
    
    def _load_rbac_rules(self) -> List[RBACRule]:
        """Load RBAC rules configuration."""
        return [
            # Learner data rules
            RBACRule(
                entity_type="learner",
                field_name="email",
                allowed_roles={"admin", "teacher", "counselor"},
                mask_strategy="redact"
            ),
            RBACRule(
                entity_type="learner", 
                field_name="phone",
                allowed_roles={"admin", "teacher", "parent"},
                mask_strategy="hash"
            ),
            RBACRule(
                entity_type="learner",
                field_name="address", 
                allowed_roles={"admin", "counselor"},
                mask_strategy="remove"
            ),
            RBACRule(
                entity_type="learner",
                field_name="ssn",
                allowed_roles={"admin"},
                mask_strategy="remove"
            ),
            
            # Assessment data rules
            RBACRule(
                entity_type="assessment",
                field_name="answers",
                allowed_roles={"admin", "teacher"},
                mask_strategy="remove"
            ),
            RBACRule(
                entity_type="assessment",
                field_name="scores",
                allowed_roles={"admin", "teacher", "counselor"},
                mask_strategy="redact"
            ),
            
            # User data rules
            RBACRule(
                entity_type="user",
                field_name="salary",
                allowed_roles={"admin", "hr"},
                mask_strategy="remove"
            ),
            RBACRule(
                entity_type="user",
                field_name="personal_phone",
                allowed_roles={"admin", "self"},
                mask_strategy="hash"
            )
        ]
    
    def _load_sensitive_patterns(self) -> Dict[str, str]:
        """Load patterns for detecting sensitive data."""
        return {
            "ssn": r'\b\d{3}-?\d{2}-?\d{4}\b',
            "phone": r'\b\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "credit_card": r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'
        }
    
    async def filter_document(
        self, 
        entity_type: str, 
        document: Dict[str, Any],
        user_roles: Optional[Set[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Filter document based on RBAC rules and user roles.
        
        Returns None if document should not be indexed for the given roles,
        otherwise returns filtered document.
        """
        if not user_roles:
            user_roles = {"public"}  # Default to most restrictive
        
        try:
            filtered_doc = dict(document)
            
            # Apply field-level RBAC rules
            for rule in self.rbac_rules:
                if rule.entity_type != entity_type:
                    continue
                
                if rule.field_name in filtered_doc:
                    if not user_roles.intersection(rule.allowed_roles):
                        # User doesn't have permission for this field
                        filtered_doc = self._apply_mask_strategy(
                            filtered_doc,
                            rule.field_name,
                            rule.mask_strategy
                        )
            
            # Scan for sensitive data patterns
            filtered_doc = await self._scan_sensitive_data(filtered_doc)
            
            # Add RBAC metadata to document
            filtered_doc["visible_to_roles"] = list(user_roles)
            filtered_doc["data_sensitivity"] = self._calculate_sensitivity_level(document)
            
            # Apply tenant-level filtering
            if "tenant_id" in filtered_doc:
                filtered_doc["restricted_fields"] = self._get_restricted_fields(
                    entity_type,
                    user_roles
                )
            
            return filtered_doc
            
        except Exception as e:
            logger.error(f"RBAC filtering failed: {e}")
            return None
    
    def _apply_mask_strategy(
        self, 
        document: Dict[str, Any], 
        field_name: str, 
        strategy: str
    ) -> Dict[str, Any]:
        """Apply masking strategy to sensitive field."""
        if field_name not in document:
            return document
        
        value = document[field_name]
        
        if strategy == "remove":
            del document[field_name]
        elif strategy == "redact":
            if isinstance(value, str) and len(value) > 3:
                document[field_name] = value[:2] + "*" * (len(value) - 2)
            else:
                document[field_name] = "***"
        elif strategy == "hash":
            document[field_name] = hashlib.sha256(str(value).encode()).hexdigest()[:8]
        
        return document
    
    async def _scan_sensitive_data(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Scan document for sensitive data patterns and mask them."""
        for field_name, value in document.items():
            if not isinstance(value, str):
                continue
            
            for pattern_name, pattern in self.sensitive_patterns.items():
                if re.search(pattern, value):
                    # Found sensitive data, apply redaction
                    document[field_name] = re.sub(pattern, "[REDACTED]", value)
                    logger.info(f"Redacted {pattern_name} pattern in field {field_name}")
        
        return document
    
    def _calculate_sensitivity_level(self, document: Dict[str, Any]) -> str:
        """Calculate data sensitivity level for the document."""
        sensitive_fields = {
            "high": ["ssn", "credit_card", "salary", "medical_info"],
            "medium": ["email", "phone", "address", "birth_date"],
            "low": ["name", "grade", "subject"]
        }
        
        for level, fields in sensitive_fields.items():
            for field in fields:
                if field in document:
                    return level
        
        return "public"
    
    def _get_restricted_fields(self, entity_type: str, user_roles: Set[str]) -> List[str]:
        """Get list of fields restricted for given user roles."""
        restricted = []
        
        for rule in self.rbac_rules:
            if (rule.entity_type == entity_type and 
                not user_roles.intersection(rule.allowed_roles)):
                restricted.append(rule.field_name)
        
        return restricted
