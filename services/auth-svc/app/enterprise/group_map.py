"""
Group to Role Mapping for Enterprise SSO

Handles mapping of IdP groups/roles to application roles based on 
tenant-specific configuration.
"""

import re
from typing import Dict, Any, List, Optional


class GroupMapper:
    """Maps IdP groups to application roles."""
    
    def __init__(self):
        """Initialize group mapper."""
        self.default_staff_role = "staff"
        self.admin_keywords = ["admin", "administrator", "manager", "lead"]
        self.support_keywords = ["support", "help", "assist"]
    
    
    def map_groups_to_roles(
        self, 
        idp_groups: List[str], 
        mapping_config: Dict[str, Any]
    ) -> List[str]:
        """
        Map IdP groups to application roles.
        
        Args:
            idp_groups: List of groups from IdP
            mapping_config: Tenant-specific mapping configuration
            
        Returns:
            List of mapped application roles
        """
        if not idp_groups:
            return [self.default_staff_role]
        
        mapped_roles = set()
        
        # Apply explicit mappings first
        explicit_mappings = mapping_config.get("explicit_mappings", {})
        for group in idp_groups:
            if group in explicit_mappings:
                role = explicit_mappings[group]
                if isinstance(role, list):
                    mapped_roles.update(role)
                else:
                    mapped_roles.add(role)
        
        # Apply pattern-based mappings
        pattern_mappings = mapping_config.get("pattern_mappings", [])
        for group in idp_groups:
            for pattern_config in pattern_mappings:
                pattern = pattern_config.get("pattern")
                roles = pattern_config.get("roles", [])
                
                if pattern and self._match_pattern(group, pattern):
                    if isinstance(roles, list):
                        mapped_roles.update(roles)
                    else:
                        mapped_roles.add(roles)
        
        # Apply default role mappings if no explicit mappings found
        if not mapped_roles:
            mapped_roles.update(self._apply_default_mappings(idp_groups, mapping_config))
        
        # Ensure staff role is always included for SSO users
        if mapping_config.get("require_staff_role", True):
            mapped_roles.add(self.default_staff_role)
        
        # Apply role hierarchy and restrictions
        final_roles = self._apply_role_hierarchy(list(mapped_roles), mapping_config)
        
        return final_roles
    
    
    def _match_pattern(self, group: str, pattern: str) -> bool:
        """Check if group matches pattern."""
        try:
            # Support both glob-style and regex patterns
            if pattern.startswith("regex:"):
                # Regex pattern
                regex_pattern = pattern[6:]
                return bool(re.search(regex_pattern, group, re.IGNORECASE))
            else:
                # Glob-style pattern (simple implementation)
                # Convert glob to regex
                regex_pattern = pattern.replace("*", ".*").replace("?", ".")
                return bool(re.search(f"^{regex_pattern}$", group, re.IGNORECASE))
        except Exception:
            return False
    
    
    def _apply_default_mappings(
        self, 
        idp_groups: List[str], 
        mapping_config: Dict[str, Any]
    ) -> List[str]:
        """Apply default role mappings based on group names."""
        roles = set()
        
        # Check for admin groups
        admin_patterns = mapping_config.get("default_admin_patterns", self.admin_keywords)
        for group in idp_groups:
            if any(keyword.lower() in group.lower() for keyword in admin_patterns):
                roles.add("admin")
                break
        
        # Check for support groups
        support_patterns = mapping_config.get("default_support_patterns", self.support_keywords)
        for group in idp_groups:
            if any(keyword.lower() in group.lower() for keyword in support_patterns):
                roles.add("support")
                break
        
        # Default to staff role if no specific role found
        if not roles:
            roles.add(self.default_staff_role)
        
        return list(roles)
    
    
    def _apply_role_hierarchy(
        self, 
        roles: List[str], 
        mapping_config: Dict[str, Any]
    ) -> List[str]:
        """Apply role hierarchy and restrictions."""
        
        # Role hierarchy (higher roles include lower roles)
        hierarchy = mapping_config.get("role_hierarchy", {
            "admin": ["staff", "support"],
            "support": ["staff"]
        })
        
        # Expand roles based on hierarchy
        expanded_roles = set(roles)
        for role in roles:
            if role in hierarchy:
                expanded_roles.update(hierarchy[role])
        
        # Apply role restrictions
        restrictions = mapping_config.get("role_restrictions", {})
        
        # Maximum roles per user
        max_roles = restrictions.get("max_roles_per_user")
        if max_roles and len(expanded_roles) > max_roles:
            # Keep highest priority roles
            priority_order = restrictions.get("role_priority", ["admin", "support", "staff"])
            prioritized_roles = []
            for priority_role in priority_order:
                if priority_role in expanded_roles:
                    prioritized_roles.append(priority_role)
                    if len(prioritized_roles) >= max_roles:
                        break
            expanded_roles = set(prioritized_roles)
        
        # Forbidden role combinations
        forbidden_combinations = restrictions.get("forbidden_combinations", [])
        for combination in forbidden_combinations:
            if all(role in expanded_roles for role in combination):
                # Remove all but the first role in forbidden combination
                for role in combination[1:]:
                    expanded_roles.discard(role)
        
        # Required roles
        required_roles = restrictions.get("required_roles", [])
        expanded_roles.update(required_roles)
        
        return sorted(list(expanded_roles))
    
    
    def validate_mapping_config(self, mapping_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate group mapping configuration.
        
        Returns:
            Validation result with errors if any
        """
        errors = []
        warnings = []
        
        try:
            # Validate explicit mappings
            explicit_mappings = mapping_config.get("explicit_mappings", {})
            if not isinstance(explicit_mappings, dict):
                errors.append("explicit_mappings must be a dictionary")
            else:
                for group, roles in explicit_mappings.items():
                    if not isinstance(group, str):
                        errors.append(f"Group name must be string: {group}")
                    if not isinstance(roles, (str, list)):
                        errors.append(f"Roles must be string or list: {roles}")
            
            # Validate pattern mappings
            pattern_mappings = mapping_config.get("pattern_mappings", [])
            if not isinstance(pattern_mappings, list):
                errors.append("pattern_mappings must be a list")
            else:
                for i, pattern_config in enumerate(pattern_mappings):
                    if not isinstance(pattern_config, dict):
                        errors.append(f"Pattern mapping {i} must be a dictionary")
                        continue
                    
                    pattern = pattern_config.get("pattern")
                    if not pattern or not isinstance(pattern, str):
                        errors.append(f"Pattern mapping {i} missing valid pattern")
                    
                    roles = pattern_config.get("roles")
                    if not roles or not isinstance(roles, (str, list)):
                        errors.append(f"Pattern mapping {i} missing valid roles")
                    
                    # Test pattern validity
                    try:
                        self._match_pattern("test", pattern)
                    except Exception as e:
                        errors.append(f"Invalid pattern in mapping {i}: {e}")
            
            # Validate role hierarchy
            role_hierarchy = mapping_config.get("role_hierarchy", {})
            if not isinstance(role_hierarchy, dict):
                errors.append("role_hierarchy must be a dictionary")
            
            # Validate restrictions
            restrictions = mapping_config.get("role_restrictions", {})
            if not isinstance(restrictions, dict):
                warnings.append("role_restrictions should be a dictionary")
            else:
                max_roles = restrictions.get("max_roles_per_user")
                if max_roles is not None and (not isinstance(max_roles, int) or max_roles < 1):
                    errors.append("max_roles_per_user must be a positive integer")
                
                forbidden_combinations = restrictions.get("forbidden_combinations", [])
                if not isinstance(forbidden_combinations, list):
                    warnings.append("forbidden_combinations should be a list")
        
        except Exception as e:
            errors.append(f"Configuration validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    
    def get_default_mapping_config(self) -> Dict[str, Any]:
        """Get default mapping configuration template."""
        return {
            "explicit_mappings": {
                "Domain Admins": ["admin"],
                "IT Support": ["support"],
                "Help Desk": ["support"],
                "Staff": ["staff"]
            },
            "pattern_mappings": [
                {
                    "pattern": "*admin*",
                    "roles": ["admin"]
                },
                {
                    "pattern": "*support*",
                    "roles": ["support"]
                },
                {
                    "pattern": "regex:^(help|assist).*",
                    "roles": ["support"]
                }
            ],
            "role_hierarchy": {
                "admin": ["staff", "support"],
                "support": ["staff"]
            },
            "role_restrictions": {
                "max_roles_per_user": 3,
                "role_priority": ["admin", "support", "staff"],
                "forbidden_combinations": [],
                "required_roles": ["staff"]
            },
            "require_staff_role": True,
            "default_admin_patterns": ["admin", "administrator", "manager"],
            "default_support_patterns": ["support", "help", "assist"]
        }
    
    
    def preview_group_mapping(
        self, 
        test_groups: List[str], 
        mapping_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Preview group mapping results for testing.
        
        Args:
            test_groups: List of test group names
            mapping_config: Mapping configuration to test
            
        Returns:
            Preview results with mapped roles for each group combination
        """
        results = []
        
        # Test individual groups
        for group in test_groups:
            mapped_roles = self.map_groups_to_roles([group], mapping_config)
            results.append({
                "input_groups": [group],
                "mapped_roles": mapped_roles,
                "mapping_source": self._get_mapping_source([group], mapping_config)
            })
        
        # Test all groups together
        if len(test_groups) > 1:
            mapped_roles = self.map_groups_to_roles(test_groups, mapping_config)
            results.append({
                "input_groups": test_groups,
                "mapped_roles": mapped_roles,
                "mapping_source": self._get_mapping_source(test_groups, mapping_config)
            })
        
        return {
            "results": results,
            "config_validation": self.validate_mapping_config(mapping_config)
        }
    
    
    def _get_mapping_source(
        self, 
        groups: List[str], 
        mapping_config: Dict[str, Any]
    ) -> Dict[str, str]:
        """Get the source of each role mapping for debugging."""
        sources = {}
        
        # Check explicit mappings
        explicit_mappings = mapping_config.get("explicit_mappings", {})
        for group in groups:
            if group in explicit_mappings:
                role = explicit_mappings[group]
                if isinstance(role, list):
                    for r in role:
                        sources[r] = f"explicit_mapping:{group}"
                else:
                    sources[role] = f"explicit_mapping:{group}"
        
        # Check pattern mappings
        pattern_mappings = mapping_config.get("pattern_mappings", [])
        for group in groups:
            for i, pattern_config in enumerate(pattern_mappings):
                pattern = pattern_config.get("pattern")
                roles = pattern_config.get("roles", [])
                
                if pattern and self._match_pattern(group, pattern):
                    if isinstance(roles, list):
                        for role in roles:
                            if role not in sources:  # Don't override explicit mappings
                                sources[role] = f"pattern_mapping:{pattern}"
                    else:
                        if roles not in sources:
                            sources[roles] = f"pattern_mapping:{pattern}"
        
        # Add default mappings
        if self.default_staff_role not in sources:
            sources[self.default_staff_role] = "default_staff_role"
        
        return sources
