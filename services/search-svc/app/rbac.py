"""
AIVO Search Service - Role-Based Access Control
S1-13 Implementation

Provides RBAC filtering and permission management for search operations.
"""

import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

import jwt
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles in the AIVO system"""
    SYSTEM_ADMIN = "system_admin"
    TENANT_ADMIN = "tenant_admin" 
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    PARENT = "parent"
    STUDENT = "student"
    CASE_MANAGER = "case_manager"
    THERAPIST = "therapist"
    PSYCHOLOGIST = "psychologist"


class Permission(str, Enum):
    """Granular permissions for search operations"""
    SEARCH_ALL = "search:all"
    SEARCH_TENANT = "search:tenant"
    SEARCH_SCHOOL = "search:school"
    SEARCH_OWN = "search:own"
    
    VIEW_IEP = "iep:view"
    VIEW_ASSESSMENT = "assessment:view"
    VIEW_STUDENT = "student:view"
    VIEW_CURRICULUM = "curriculum:view"
    VIEW_RESOURCE = "resource:view"
    
    SUGGEST_ALL = "suggest:all"
    SUGGEST_TENANT = "suggest:tenant"
    SUGGEST_SCHOOL = "suggest:school"


@dataclass
class UserContext:
    """User context for RBAC operations"""
    user_id: str
    tenant_id: str
    school_ids: List[str]
    roles: List[Role]
    permissions: Set[Permission]
    student_ids: Optional[List[str]] = None  # For parents/students
    is_admin: bool = False
    is_system: bool = False
    
    def __post_init__(self):
        """Set admin flags based on roles"""
        self.is_system = Role.SYSTEM_ADMIN in self.roles
        self.is_admin = any(role in [Role.SYSTEM_ADMIN, Role.TENANT_ADMIN] for role in self.roles)


class RBACManager:
    """Role-Based Access Control manager for search operations"""
    
    # Role hierarchy - higher roles inherit permissions from lower roles
    ROLE_HIERARCHY = {
        Role.SYSTEM_ADMIN: [
            Role.TENANT_ADMIN, Role.SCHOOL_ADMIN, Role.TEACHER,
            Role.CASE_MANAGER, Role.THERAPIST, Role.PSYCHOLOGIST
        ],
        Role.TENANT_ADMIN: [
            Role.SCHOOL_ADMIN, Role.TEACHER, Role.CASE_MANAGER,
            Role.THERAPIST, Role.PSYCHOLOGIST
        ],
        Role.SCHOOL_ADMIN: [
            Role.TEACHER, Role.CASE_MANAGER, Role.THERAPIST, Role.PSYCHOLOGIST
        ],
        Role.CASE_MANAGER: [Role.TEACHER],
        Role.THERAPIST: [],
        Role.PSYCHOLOGIST: [],
        Role.TEACHER: [],
        Role.PARENT: [],
        Role.STUDENT: []
    }
    
    # Default permissions for each role
    ROLE_PERMISSIONS = {
        Role.SYSTEM_ADMIN: {
            Permission.SEARCH_ALL, Permission.VIEW_IEP, Permission.VIEW_ASSESSMENT,
            Permission.VIEW_STUDENT, Permission.VIEW_CURRICULUM, Permission.VIEW_RESOURCE,
            Permission.SUGGEST_ALL
        },
        Role.TENANT_ADMIN: {
            Permission.SEARCH_TENANT, Permission.VIEW_IEP, Permission.VIEW_ASSESSMENT,
            Permission.VIEW_STUDENT, Permission.VIEW_CURRICULUM, Permission.VIEW_RESOURCE,
            Permission.SUGGEST_TENANT
        },
        Role.SCHOOL_ADMIN: {
            Permission.SEARCH_SCHOOL, Permission.VIEW_IEP, Permission.VIEW_ASSESSMENT,
            Permission.VIEW_STUDENT, Permission.VIEW_CURRICULUM, Permission.VIEW_RESOURCE,
            Permission.SUGGEST_SCHOOL
        },
        Role.TEACHER: {
            Permission.SEARCH_SCHOOL, Permission.VIEW_IEP, Permission.VIEW_ASSESSMENT,
            Permission.VIEW_STUDENT, Permission.VIEW_CURRICULUM, Permission.VIEW_RESOURCE,
            Permission.SUGGEST_SCHOOL
        },
        Role.CASE_MANAGER: {
            Permission.SEARCH_SCHOOL, Permission.VIEW_IEP, Permission.VIEW_ASSESSMENT,
            Permission.VIEW_STUDENT, Permission.VIEW_CURRICULUM, Permission.SUGGEST_SCHOOL
        },
        Role.THERAPIST: {
            Permission.SEARCH_SCHOOL, Permission.VIEW_IEP, Permission.VIEW_ASSESSMENT,
            Permission.VIEW_STUDENT, Permission.SUGGEST_SCHOOL
        },
        Role.PSYCHOLOGIST: {
            Permission.SEARCH_SCHOOL, Permission.VIEW_IEP, Permission.VIEW_ASSESSMENT,
            Permission.VIEW_STUDENT, Permission.SUGGEST_SCHOOL
        },
        Role.PARENT: {
            Permission.SEARCH_OWN, Permission.VIEW_IEP, Permission.VIEW_ASSESSMENT
        },
        Role.STUDENT: {
            Permission.SEARCH_OWN, Permission.VIEW_IEP
        }
    }
    
    # Document type access by role
    DOCUMENT_ACCESS = {
        Role.SYSTEM_ADMIN: {"iep", "assessment", "student", "curriculum", "resource", "user"},
        Role.TENANT_ADMIN: {"iep", "assessment", "student", "curriculum", "resource", "user"},
        Role.SCHOOL_ADMIN: {"iep", "assessment", "student", "curriculum", "resource"},
        Role.TEACHER: {"iep", "assessment", "student", "curriculum", "resource"},
        Role.CASE_MANAGER: {"iep", "assessment", "student", "curriculum"},
        Role.THERAPIST: {"iep", "assessment", "student"},
        Role.PSYCHOLOGIST: {"iep", "assessment", "student"},
        Role.PARENT: {"iep", "assessment"},
        Role.STUDENT: {"iep"}
    }
    
    def __init__(self, jwt_secret: str = "your-jwt-secret", jwt_algorithm: str = "HS256"):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        
    def parse_token(self, token: str) -> UserContext:
        """Parse JWT token and extract user context"""
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
                
            tenant_id = payload.get("tenant_id")
            if not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing tenant ID"
                )
                
            # Parse roles
            role_strings = payload.get("roles", [])
            roles = []
            for role_str in role_strings:
                try:
                    roles.append(Role(role_str))
                except ValueError:
                    logger.warning(f"Unknown role in token: {role_str}")
                    
            if not roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User has no valid roles"
                )
                
            # Calculate effective permissions
            permissions = self.get_effective_permissions(roles)
            
            context = UserContext(
                user_id=user_id,
                tenant_id=tenant_id,
                school_ids=payload.get("school_ids", []),
                roles=roles,
                permissions=permissions,
                student_ids=payload.get("student_ids", [])
            )
            
            return context
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
    def get_effective_permissions(self, roles: List[Role]) -> Set[Permission]:
        """Calculate effective permissions based on role hierarchy"""
        permissions = set()
        
        for role in roles:
            # Add direct permissions for this role
            if role in self.ROLE_PERMISSIONS:
                permissions.update(self.ROLE_PERMISSIONS[role])
                
            # Add inherited permissions from role hierarchy
            if role in self.ROLE_HIERARCHY:
                for inherited_role in self.ROLE_HIERARCHY[role]:
                    if inherited_role in self.ROLE_PERMISSIONS:
                        permissions.update(self.ROLE_PERMISSIONS[inherited_role])
                        
        return permissions
        
    def check_search_permission(
        self,
        context: UserContext,
        doc_types: Optional[List[str]] = None
    ) -> bool:
        """Check if user can perform search operation"""
        
        # System admins can search everything
        if Permission.SEARCH_ALL in context.permissions:
            return True
            
        # Tenant-level search
        if Permission.SEARCH_TENANT in context.permissions:
            return True
            
        # School-level search  
        if Permission.SEARCH_SCHOOL in context.permissions and context.school_ids:
            return True
            
        # Own data search
        if Permission.SEARCH_OWN in context.permissions:
            return True
            
        return False
        
    def check_document_access(
        self,
        context: UserContext,
        doc_type: str
    ) -> bool:
        """Check if user can access specific document type"""
        
        for role in context.roles:
            if role in self.DOCUMENT_ACCESS:
                if doc_type in self.DOCUMENT_ACCESS[role]:
                    return True
                    
        return False
        
    def filter_document_types(
        self,
        context: UserContext,
        doc_types: Optional[List[str]] = None
    ) -> List[str]:
        """Filter document types based on user permissions"""
        
        if doc_types is None:
            # Get all accessible document types
            accessible_types = set()
            for role in context.roles:
                if role in self.DOCUMENT_ACCESS:
                    accessible_types.update(self.DOCUMENT_ACCESS[role])
            return list(accessible_types)
        else:
            # Filter requested types
            filtered_types = []
            for doc_type in doc_types:
                if self.check_document_access(context, doc_type):
                    filtered_types.append(doc_type)
            return filtered_types
            
    def build_search_filters(self, context: UserContext) -> Dict[str, Any]:
        """Build OpenSearch filters based on user context"""
        
        # System admin - no filters
        if context.is_system:
            return {"match_all": {}}
            
        # Tenant admin - tenant filter only
        if context.is_admin:
            return {
                "term": {
                    "tenant_id": context.tenant_id
                }
            }
            
        # Build filters based on role and scope
        filters = [
            {"term": {"tenant_id": context.tenant_id}}
        ]
        
        # School-based roles
        school_based_roles = [
            Role.SCHOOL_ADMIN, Role.TEACHER, Role.CASE_MANAGER,
            Role.THERAPIST, Role.PSYCHOLOGIST
        ]
        
        if any(role in school_based_roles for role in context.roles):
            if context.school_ids:
                filters.append({
                    "terms": {
                        "school_id": context.school_ids
                    }
                })
                
        # Parent role - children's data only
        elif Role.PARENT in context.roles:
            if context.student_ids:
                filters.append({
                    "terms": {
                        "metadata.student_id": context.student_ids
                    }
                })
            else:
                # No children assigned - no results
                filters.append({
                    "match_none": {}
                })
                
        # Student role - own data only
        elif Role.STUDENT in context.roles:
            filters.append({
                "term": {
                    "metadata.student_id": context.user_id
                }
            })
            
        return {
            "bool": {
                "must": filters
            }
        }
        
    def get_accessible_schools(self, context: UserContext) -> List[str]:
        """Get list of schools user can access data from"""
        
        if context.is_system:
            return ["*"]  # All schools
            
        if context.is_admin:
            return ["*"]  # All schools in tenant
            
        return context.school_ids
        
    def check_suggestion_permission(self, context: UserContext) -> bool:
        """Check if user can get search suggestions"""
        
        suggestion_permissions = [
            Permission.SUGGEST_ALL,
            Permission.SUGGEST_TENANT,
            Permission.SUGGEST_SCHOOL
        ]
        
        return any(perm in context.permissions for perm in suggestion_permissions)
        
    def get_cross_school_visibility(self, context: UserContext) -> bool:
        """Check if user can see data from other schools"""
        
        # System and tenant admins can see cross-school data
        if context.is_system or context.is_admin:
            return True
            
        # School-level roles are restricted to their schools
        return False


# Global RBAC manager instance
rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get or create RBAC manager instance"""
    global rbac_manager
    if rbac_manager is None:
        rbac_manager = RBACManager()
    return rbac_manager


def extract_user_context(authorization: str) -> UserContext:
    """Extract user context from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
        
    token = authorization.split(" ")[1]
    manager = get_rbac_manager()
    return manager.parse_token(token)
