"""
SCIM 2.0 Pagination Implementation

Complete pagination support with startIndex, count, and totalResults
following SCIM 2.0 specification requirements.
"""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Query
from ..schemas import SCIMListResponse


class SCIMPagination:
    """SCIM 2.0 Pagination Handler."""
    
    # SCIM pagination defaults and limits
    DEFAULT_COUNT = 20
    MAX_COUNT = 200
    MIN_START_INDEX = 1
    
    def __init__(self, start_index: Optional[int] = None, count: Optional[int] = None):
        """Initialize pagination parameters."""
        self.start_index = max(start_index or self.MIN_START_INDEX, self.MIN_START_INDEX)
        self.count = min(count or self.DEFAULT_COUNT, self.MAX_COUNT)
        
        # Convert to 0-based offset for SQL
        self.offset = max(self.start_index - 1, 0)
        self.limit = self.count
    
    def apply_to_query(self, query: Query) -> Query:
        """Apply pagination to SQLAlchemy query."""
        return query.offset(self.offset).limit(self.limit)
    
    def get_total_results(self, query: Query) -> int:
        """Get total count without pagination."""
        return query.count()
    
    def create_list_response(
        self, 
        resources: List[Dict[str, Any]], 
        total_results: int
    ) -> SCIMListResponse:
        """Create SCIM ListResponse with pagination metadata."""
        return SCIMListResponse(
            totalResults=total_results,
            startIndex=self.start_index,
            itemsPerPage=len(resources),
            Resources=resources
        )
    
    def get_pagination_info(self, total_results: int) -> Dict[str, Any]:
        """Get pagination information for logging/debugging."""
        return {
            'startIndex': self.start_index,
            'count': self.count,
            'offset': self.offset,
            'limit': self.limit,
            'totalResults': total_results,
            'hasMore': self.start_index + self.count - 1 < total_results,
            'currentPage': (self.start_index - 1) // self.count + 1,
            'totalPages': (total_results + self.count - 1) // self.count
        }


class SCIMSorting:
    """SCIM 2.0 Sorting Implementation."""
    
    SUPPORTED_SORT_ATTRIBUTES = {
        'User': {
            'id', 'userName', 'displayName', 'familyName', 'givenName',
            'title', 'userType', 'active', 'meta.created', 'meta.lastModified'
        },
        'Group': {
            'id', 'displayName', 'meta.created', 'meta.lastModified'
        }
    }
    
    def __init__(self, sort_by: Optional[str] = None, sort_order: Optional[str] = None):
        """Initialize sorting parameters."""
        self.sort_by = sort_by
        self.sort_order = (sort_order or 'ascending').lower()
        
        if self.sort_order not in ('ascending', 'descending'):
            raise ValueError(f"Invalid sort order: {sort_order}")
    
    def apply_to_query(self, query: Query, model_class) -> Query:
        """Apply sorting to SQLAlchemy query."""
        if not self.sort_by:
            return query
        
        # Map SCIM attributes to model columns
        column = self._get_sort_column(model_class)
        
        if self.sort_order == 'descending':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
        
        return query
    
    def _get_sort_column(self, model_class):
        """Get SQLAlchemy column for sorting."""
        from ..models import User, Group
        
        if model_class == User:
            column_map = {
                'id': User.id,
                'userName': User.user_name,
                'displayName': User.display_name,
                'familyName': User.family_name,
                'givenName': User.given_name,
                'title': User.title,
                'userType': User.user_type,
                'active': User.active,
                'meta.created': User.created_at,
                'meta.lastModified': User.updated_at
            }
        elif model_class == Group:
            column_map = {
                'id': Group.id,
                'displayName': Group.display_name,
                'meta.created': Group.created_at,
                'meta.lastModified': Group.updated_at
            }
        else:
            raise ValueError(f"Unsupported model class: {model_class}")
        
        column = column_map.get(self.sort_by)
        if not column:
            raise ValueError(f"Unsupported sort attribute: {self.sort_by}")
        
        return column
    
    def validate(self, resource_type: str) -> bool:
        """Validate sort parameters for resource type."""
        if not self.sort_by:
            return True
        
        supported = self.SUPPORTED_SORT_ATTRIBUTES.get(resource_type, set())
        return self.sort_by in supported


def parse_pagination_params(
    start_index: Optional[str] = None,
    count: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None
) -> Tuple[SCIMPagination, SCIMSorting]:
    """Parse pagination and sorting parameters from query string."""
    
    # Parse pagination
    try:
        start_idx = int(start_index) if start_index else None
    except (ValueError, TypeError):
        start_idx = None
    
    try:
        cnt = int(count) if count else None
    except (ValueError, TypeError):
        cnt = None
    
    pagination = SCIMPagination(start_idx, cnt)
    sorting = SCIMSorting(sort_by, sort_order)
    
    return pagination, sorting


def apply_pagination_and_sorting(
    query: Query,
    model_class,
    start_index: Optional[str] = None,
    count: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None
) -> Tuple[Query, SCIMPagination, int]:
    """Apply pagination and sorting to query and return metadata."""
    
    pagination, sorting = parse_pagination_params(start_index, count, sort_by, sort_order)
    
    # Get total count before pagination
    total_results = pagination.get_total_results(query)
    
    # Apply sorting
    query = sorting.apply_to_query(query, model_class)
    
    # Apply pagination
    query = pagination.apply_to_query(query)
    
    return query, pagination, total_results


class SCIMQueryBuilder:
    """Builder for SCIM queries with filtering, sorting, and pagination."""
    
    def __init__(self, model_class):
        """Initialize query builder for model class."""
        self.model_class = model_class
        self.query = None
        self.pagination = None
        self.sorting = None
        self.total_results = 0
    
    def filter(self, filter_string: Optional[str] = None):
        """Add SCIM filter to query."""
        if filter_string:
            from .filters import apply_scim_filter
            self.query = apply_scim_filter(self.query, filter_string, self.model_class)
        return self
    
    def sort(self, sort_by: Optional[str] = None, sort_order: Optional[str] = None):
        """Add sorting to query."""
        self.sorting = SCIMSorting(sort_by, sort_order)
        if self.sorting.sort_by:
            self.query = self.sorting.apply_to_query(self.query, self.model_class)
        return self
    
    def paginate(self, start_index: Optional[int] = None, count: Optional[int] = None):
        """Add pagination to query."""
        self.pagination = SCIMPagination(start_index, count)
        self.total_results = self.pagination.get_total_results(self.query)
        self.query = self.pagination.apply_to_query(self.query)
        return self
    
    def execute(self, session) -> Tuple[List, Dict[str, Any]]:
        """Execute query and return results with metadata."""
        results = session.execute(self.query).scalars().all()
        
        metadata = {
            'totalResults': self.total_results,
            'startIndex': self.pagination.start_index if self.pagination else 1,
            'itemsPerPage': len(results),
        }
        
        if self.pagination:
            metadata.update(self.pagination.get_pagination_info(self.total_results))
        
        return results, metadata
    
    @classmethod
    def from_params(
        cls,
        session,
        model_class,
        filter_string: Optional[str] = None,
        start_index: Optional[str] = None,
        count: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """Create query builder from request parameters."""
        builder = cls(model_class)
        
        # Start with base query
        builder.query = session.query(model_class)
        
        # Add tenant filter if specified
        if tenant_id and hasattr(model_class, 'tenant_id'):
            builder.query = builder.query.filter(model_class.tenant_id == tenant_id)
        
        # Apply filter, sort, and pagination
        builder.filter(filter_string)
        
        # Parse pagination parameters
        try:
            start_idx = int(start_index) if start_index else None
        except (ValueError, TypeError):
            start_idx = None
        
        try:
            cnt = int(count) if count else None
        except (ValueError, TypeError):
            cnt = None
        
        builder.sort(sort_by, sort_order)
        builder.paginate(start_idx, cnt)
        
        return builder
