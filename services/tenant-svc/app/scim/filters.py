"""
SCIM 2.0 Filtering Implementation

Complete SCIM filter parsing and SQL query generation with support
for all SCIM filter operations and complex expressions.
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy import and_, or_, not_, func
from sqlalchemy.orm import Query
from ..models import User, Group


class SCIMFilterParser:
    """
    SCIM 2.0 Filter Expression Parser
    
    Supports the complete SCIM filter grammar including:
    - Attribute operators: eq, ne, co, sw, ew, pr, gt, ge, lt, le
    - Logical operators: and, or, not
    - Grouping with parentheses
    - Complex attribute paths
    """
    
    # SCIM filter tokens
    OPERATORS = {
        'eq': '==',
        'ne': '!=', 
        'co': 'contains',
        'sw': 'startswith',
        'ew': 'endswith',
        'pr': 'present',
        'gt': '>',
        'ge': '>=',
        'lt': '<',
        'le': '<='
    }
    
    LOGICAL_OPS = {'and', 'or', 'not'}
    
    def __init__(self, model_class):
        """Initialize parser for specific model class."""
        self.model_class = model_class
        self.attribute_map = self._build_attribute_map()
    
    def _build_attribute_map(self) -> Dict[str, str]:
        """Build mapping from SCIM attributes to SQLAlchemy columns."""
        if self.model_class == User:
            return {
                'id': 'id',
                'externalId': 'external_id',
                'userName': 'user_name',
                'displayName': 'display_name',
                'nickName': 'nick_name',
                'profileUrl': 'profile_url',
                'title': 'title',
                'userType': 'user_type',
                'locale': 'locale',
                'timezone': 'timezone',
                'active': 'active',
                'name.formatted': 'formatted_name',
                'name.familyName': 'family_name',
                'name.givenName': 'given_name',
                'name.middleName': 'middle_name',
                'name.honorificPrefix': 'honorific_prefix',
                'name.honorificSuffix': 'honorific_suffix',
                'emails[primary eq true].value': 'primary_email',
                'emails.value': 'primary_email',
                'phoneNumbers[type eq "work"].value': 'work_phone',
                'phoneNumbers[type eq "mobile"].value': 'mobile_phone',
                'addresses[type eq "work"].formatted': 'work_address',
                'employeeNumber': 'employee_number',
                'costCenter': 'cost_center',
                'organization': 'organization',
                'division': 'division',
                'department': 'department',
                'manager.value': 'manager_id',
                'meta.created': 'created_at',
                'meta.lastModified': 'updated_at'
            }
        elif self.model_class == Group:
            return {
                'id': 'id',
                'externalId': 'external_id',
                'displayName': 'display_name',
                'meta.created': 'created_at',
                'meta.lastModified': 'updated_at'
            }
        return {}
    
    def parse(self, filter_string: str) -> Any:
        """Parse SCIM filter string into SQLAlchemy conditions."""
        if not filter_string:
            return None
        
        try:
            tokens = self._tokenize(filter_string)
            return self._parse_expression(tokens)
        except Exception as e:
            raise ValueError(f"Invalid SCIM filter: {e}")
    
    def _tokenize(self, filter_string: str) -> List[str]:
        """Tokenize filter string into components."""
        # Regex pattern for SCIM filter tokens
        pattern = r'''
            (?P<STRING>"[^"]*")|                    # Quoted strings
            (?P<DATETIME>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z)|  # ISO dates
            (?P<NUMBER>\d+(?:\.\d+)?)|              # Numbers
            (?P<BOOLEAN>true|false)|                # Booleans
            (?P<OPERATOR>eq|ne|co|sw|ew|pr|gt|ge|lt|le)|  # Comparison operators
            (?P<LOGICAL>and|or|not)|                # Logical operators
            (?P<PAREN>[()])|                        # Parentheses
            (?P<ATTR>[a-zA-Z][a-zA-Z0-9_.[\]"]*)|  # Attribute paths
            (?P<WHITESPACE>\s+)|                    # Whitespace
            (?P<OTHER>.)                            # Other characters
        '''
        
        tokens = []
        for match in re.finditer(pattern, filter_string, re.VERBOSE):
            kind = match.lastgroup
            value = match.group()
            
            if kind == 'WHITESPACE':
                continue
            elif kind == 'STRING':
                tokens.append(value[1:-1])  # Remove quotes
            elif kind == 'NUMBER':
                tokens.append(float(value) if '.' in value else int(value))
            elif kind == 'BOOLEAN':
                tokens.append(value == 'true')
            else:
                tokens.append(value)
        
        return tokens
    
    def _parse_expression(self, tokens: List[str]) -> Any:
        """Parse expression with operator precedence."""
        return self._parse_or_expression(tokens)
    
    def _parse_or_expression(self, tokens: List[str]) -> Any:
        """Parse OR expressions (lowest precedence)."""
        left = self._parse_and_expression(tokens)
        
        while tokens and tokens[0] == 'or':
            tokens.pop(0)  # consume 'or'
            right = self._parse_and_expression(tokens)
            left = or_(left, right)
        
        return left
    
    def _parse_and_expression(self, tokens: List[str]) -> Any:
        """Parse AND expressions (middle precedence)."""
        left = self._parse_not_expression(tokens)
        
        while tokens and tokens[0] == 'and':
            tokens.pop(0)  # consume 'and'
            right = self._parse_not_expression(tokens)
            left = and_(left, right)
        
        return left
    
    def _parse_not_expression(self, tokens: List[str]) -> Any:
        """Parse NOT expressions (high precedence)."""
        if tokens and tokens[0] == 'not':
            tokens.pop(0)  # consume 'not'
            expr = self._parse_primary_expression(tokens)
            return not_(expr)
        
        return self._parse_primary_expression(tokens)
    
    def _parse_primary_expression(self, tokens: List[str]) -> Any:
        """Parse primary expressions (highest precedence)."""
        if not tokens:
            raise ValueError("Unexpected end of filter expression")
        
        # Handle parentheses
        if tokens[0] == '(':
            tokens.pop(0)  # consume '('
            expr = self._parse_expression(tokens)
            if not tokens or tokens[0] != ')':
                raise ValueError("Missing closing parenthesis")
            tokens.pop(0)  # consume ')'
            return expr
        
        # Handle attribute expressions
        return self._parse_attribute_expression(tokens)
    
    def _parse_attribute_expression(self, tokens: List[str]) -> Any:
        """Parse attribute comparison expressions."""
        if len(tokens) < 2:
            raise ValueError("Invalid attribute expression")
        
        attr_path = tokens.pop(0)
        operator = tokens.pop(0)
        
        if operator not in self.OPERATORS:
            raise ValueError(f"Unknown operator: {operator}")
        
        # Handle 'pr' (present) operator
        if operator == 'pr':
            return self._build_present_condition(attr_path)
        
        # Other operators require a value
        if not tokens:
            raise ValueError(f"Missing value for operator {operator}")
        
        value = tokens.pop(0)
        return self._build_comparison_condition(attr_path, operator, value)
    
    def _build_present_condition(self, attr_path: str) -> Any:
        """Build condition for 'pr' (present) operator."""
        column = self._get_column(attr_path)
        return column.isnot(None)
    
    def _build_comparison_condition(self, attr_path: str, operator: str, value: Any) -> Any:
        """Build comparison condition."""
        column = self._get_column(attr_path)
        
        if operator == 'eq':
            return column == value
        elif operator == 'ne':
            return column != value
        elif operator == 'co':
            return column.contains(str(value))
        elif operator == 'sw':
            return column.startswith(str(value))
        elif operator == 'ew':
            return column.endswith(str(value))
        elif operator == 'gt':
            return column > value
        elif operator == 'ge':
            return column >= value
        elif operator == 'lt':
            return column < value
        elif operator == 'le':
            return column <= value
        else:
            raise ValueError(f"Unsupported operator: {operator}")
    
    def _get_column(self, attr_path: str) -> Any:
        """Get SQLAlchemy column for SCIM attribute path."""
        # Handle complex attribute paths
        if '[' in attr_path:
            # Extract base attribute (e.g., "emails" from "emails[type eq 'work'].value")
            base_attr = attr_path.split('[')[0]
            if base_attr in self.attribute_map:
                column_name = self.attribute_map[base_attr]
            else:
                # Try full path mapping
                column_name = self.attribute_map.get(attr_path)
        else:
            column_name = self.attribute_map.get(attr_path)
        
        if not column_name:
            raise ValueError(f"Unknown attribute: {attr_path}")
        
        return getattr(self.model_class, column_name)


class SCIMFilterValidator:
    """Validate SCIM filter expressions."""
    
    SUPPORTED_ATTRIBUTES = {
        'User': {
            'id', 'externalId', 'userName', 'displayName', 'nickName',
            'profileUrl', 'title', 'userType', 'locale', 'timezone', 'active',
            'name.formatted', 'name.familyName', 'name.givenName', 'name.middleName',
            'name.honorificPrefix', 'name.honorificSuffix',
            'emails.value', 'emails.type', 'emails.primary',
            'phoneNumbers.value', 'phoneNumbers.type',
            'addresses.formatted', 'addresses.type',
            'employeeNumber', 'costCenter', 'organization', 'division', 'department',
            'manager.value', 'meta.created', 'meta.lastModified'
        },
        'Group': {
            'id', 'externalId', 'displayName', 'meta.created', 'meta.lastModified'
        }
    }
    
    @classmethod
    def validate(cls, filter_string: str, resource_type: str) -> bool:
        """Validate SCIM filter for resource type."""
        if not filter_string:
            return True
        
        try:
            # Extract all attribute references from filter
            attributes = cls._extract_attributes(filter_string)
            supported = cls.SUPPORTED_ATTRIBUTES.get(resource_type, set())
            
            # Check if all attributes are supported
            unsupported = attributes - supported
            if unsupported:
                raise ValueError(f"Unsupported attributes: {', '.join(unsupported)}")
            
            return True
        except Exception:
            return False
    
    @classmethod
    def _extract_attributes(cls, filter_string: str) -> set:
        """Extract all attribute references from filter string."""
        # Simplified attribute extraction
        pattern = r'[a-zA-Z][a-zA-Z0-9_.[\]"]*(?=\s+(?:eq|ne|co|sw|ew|pr|gt|ge|lt|le))'
        matches = re.findall(pattern, filter_string)
        return {match.strip('"') for match in matches}


def apply_scim_filter(query: Query, filter_string: str, model_class) -> Query:
    """Apply SCIM filter to SQLAlchemy query."""
    if not filter_string:
        return query
    
    parser = SCIMFilterParser(model_class)
    condition = parser.parse(filter_string)
    
    if condition is not None:
        query = query.filter(condition)
    
    return query
