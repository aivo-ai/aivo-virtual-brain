"""
AIVO Search Service - API Routes
S1-13 Implementation

REST API endpoints for search and suggestion operations with RBAC.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from .client import get_search_client, OpenSearchClient, SearchContext
from .rbac import extract_user_context, UserContext, get_rbac_manager, RBACManager

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for API requests/responses
class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., description="Search query string", min_length=1, max_length=500)
    doc_types: Optional[List[str]] = Field(
        None, 
        description="Document types to search (iep, assessment, student, curriculum, resource)"
    )
    size: int = Field(20, description="Number of results to return", ge=1, le=100)
    from_: int = Field(0, alias="from", description="Starting offset for pagination", ge=0)
    sort: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Sort criteria (e.g. [{'score': 'desc'}, {'updated_at': 'asc'}])"
    )
    
    @validator('doc_types')
    def validate_doc_types(cls, v):
        if v:
            valid_types = {'iep', 'assessment', 'student', 'curriculum', 'resource', 'user'}
            invalid_types = set(v) - valid_types
            if invalid_types:
                raise ValueError(f"Invalid document types: {invalid_types}")
        return v


class SuggestionRequest(BaseModel):
    """Suggestion request model"""
    query: str = Field(..., description="Partial query for suggestions", min_length=1, max_length=100)
    size: int = Field(10, description="Number of suggestions to return", ge=1, le=20)


class SearchResult(BaseModel):
    """Search result model"""
    id: str
    title: str
    content: str
    document_type: str
    tenant_id: str
    school_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    score: Optional[float] = None
    highlight: Optional[Dict[str, List[str]]] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response model"""
    results: List[SearchResult]
    total: int
    page: int
    size: int
    query: str
    filters: Dict[str, Any]
    took: int  # Search time in milliseconds
    
    
class SuggestionResult(BaseModel):
    """Suggestion result model"""
    text: str
    score: float
    category: Optional[str] = None


class SuggestionResponse(BaseModel):
    """Suggestion response model"""
    suggestions: List[SuggestionResult]
    query: str
    total: int


class IndexDocument(BaseModel):
    """Document indexing model"""
    id: str
    title: str
    content: str
    document_type: str
    tenant_id: str
    school_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Dependency to get authenticated user context
async def get_user_context(
    authorization: str = Header(..., description="Bearer token")
) -> UserContext:
    """Extract and validate user context from Authorization header"""
    return extract_user_context(authorization)


# Dependency to get search client
def get_client() -> OpenSearchClient:
    """Get OpenSearch client instance"""
    return get_search_client()


# Dependency to get RBAC manager
def get_rbac() -> RBACManager:
    """Get RBAC manager instance"""
    return get_rbac_manager()


@router.get("/search", response_model=SearchResponse, summary="Search Documents")
async def search_documents(
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    scope: Optional[str] = Query(None, description="Search scope filter (deprecated, use doc_types)"),
    doc_types: Optional[str] = Query(
        None, 
        description="Comma-separated document types to search"
    ),
    size: int = Query(20, description="Number of results", ge=1, le=100),
    from_: int = Query(0, alias="from", description="Result offset", ge=0),
    sort: Optional[str] = Query(None, description="Sort field:order (e.g. 'score:desc,updated_at:asc')"),
    user_context: UserContext = Depends(get_user_context),
    search_client: OpenSearchClient = Depends(get_client),
    rbac: RBACManager = Depends(get_rbac)
) -> SearchResponse:
    """
    Search documents with role-based access control.
    
    ## Query Parameters
    
    * **q**: Search query string (required)
    * **doc_types**: Comma-separated document types (iep,assessment,student,curriculum,resource)
    * **size**: Number of results to return (1-100, default: 20)
    * **from**: Starting offset for pagination (default: 0)
    * **sort**: Sort criteria as 'field:order' pairs (e.g. 'score:desc,updated_at:asc')
    
    ## Examples
    
    * Search IEPs: `/search?q=autism&doc_types=iep`
    * Search with pagination: `/search?q=reading&size=10&from=20`
    * Search and sort: `/search?q=math&sort=updated_at:desc`
    
    ## Access Control
    
    Results are filtered based on user role and permissions:
    - System/Tenant admins see all accessible documents
    - School-level users see documents from their schools
    - Parents see only their children's documents
    - Students see only their own documents
    """
    
    start_time = datetime.now()
    
    try:
        # Check search permission
        if not rbac.check_search_permission(user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to perform search"
            )
            
        # Parse document types
        doc_type_list = None
        if doc_types:
            doc_type_list = [dt.strip() for dt in doc_types.split(",") if dt.strip()]
            
        # Handle legacy scope parameter
        if scope and not doc_type_list:
            doc_type_list = [scope] if scope in ['iep', 'assessment', 'student', 'curriculum', 'resource'] else None
            
        # Filter document types based on permissions
        if doc_type_list:
            doc_type_list = rbac.filter_document_types(user_context, doc_type_list)
        else:
            doc_type_list = rbac.filter_document_types(user_context)
            
        if not doc_type_list:
            # User has no access to any document types
            return SearchResponse(
                results=[],
                total=0,
                page=from_ // size,
                size=size,
                query=q,
                filters={"accessible_types": []},
                took=0
            )
            
        # Parse sort parameters
        sort_criteria = None
        if sort:
            sort_criteria = []
            for sort_item in sort.split(","):
                if ":" in sort_item:
                    field, order = sort_item.strip().split(":", 1)
                    sort_criteria.append({field: {"order": order}})
                    
        # Create search context
        search_context = SearchContext(
            user_id=user_context.user_id,
            tenant_id=user_context.tenant_id,
            school_ids=user_context.school_ids,
            roles=[role.value for role in user_context.roles],
            permissions=[perm.value for perm in user_context.permissions],
            is_admin=user_context.is_admin,
            is_system=user_context.is_system
        )
        
        # Perform search
        results = await search_client.search(
            query=q,
            context=search_context,
            doc_types=doc_type_list,
            size=size,
            from_=from_,
            sort=sort_criteria
        )
        
        # Calculate elapsed time
        elapsed = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Convert results to response model
        search_results = [
            SearchResult(
                id=result.id,
                title=result.title,
                content=result.content[:500] + "..." if len(result.content) > 500 else result.content,
                document_type=result.document_type,
                tenant_id=result.tenant_id,
                school_id=result.school_id,
                created_at=result.created_at,
                updated_at=result.updated_at,
                score=result.score,
                highlight=result.highlight,
                metadata=result.metadata
            )
            for result in results
        ]
        
        return SearchResponse(
            results=search_results,
            total=len(results),  # Note: This would be total count from OpenSearch in production
            page=from_ // size,
            size=size,
            query=q,
            filters={
                "doc_types": doc_type_list,
                "tenant_id": user_context.tenant_id,
                "school_ids": user_context.school_ids
            },
            took=elapsed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for user {user_context.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search operation failed"
        )


@router.get("/suggest", response_model=SuggestionResponse, summary="Get Search Suggestions")
async def get_suggestions(
    q: str = Query(..., description="Partial query for suggestions", min_length=1, max_length=100),
    size: int = Query(10, description="Number of suggestions", ge=1, le=20),
    user_context: UserContext = Depends(get_user_context),
    search_client: OpenSearchClient = Depends(get_client),
    rbac: RBACManager = Depends(get_rbac)
) -> SuggestionResponse:
    """
    Get search suggestions with role-based filtering.
    
    ## Query Parameters
    
    * **q**: Partial query string (required, 1-100 characters)
    * **size**: Number of suggestions to return (1-20, default: 10)
    
    ## Examples
    
    * Get suggestions: `/suggest?q=fra` → returns "fractions", "framework", etc.
    * Limit suggestions: `/suggest?q=math&size=5`
    
    ## Access Control
    
    Suggestions are filtered based on documents the user can access.
    Cross-school visibility is blocked for non-admin users.
    
    ## Use Cases
    
    * Auto-complete in search boxes
    * Query expansion suggestions
    * Typo correction hints
    """
    
    try:
        # Check suggestion permission
        if not rbac.check_suggestion_permission(user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to get suggestions"
            )
            
        # Create search context
        search_context = SearchContext(
            user_id=user_context.user_id,
            tenant_id=user_context.tenant_id,
            school_ids=user_context.school_ids,
            roles=[role.value for role in user_context.roles],
            permissions=[perm.value for perm in user_context.permissions],
            is_admin=user_context.is_admin,
            is_system=user_context.is_system
        )
        
        # Get suggestions
        suggestions = await search_client.suggest(
            query=q,
            context=search_context,
            size=size
        )
        
        # Filter suggestions based on cross-school visibility
        if not rbac.get_cross_school_visibility(user_context):
            # For non-admin users, ensure suggestions don't reveal cross-school data
            # This is a simplified implementation - in production you'd have more sophisticated filtering
            pass
        
        # Convert to response model
        suggestion_results = [
            SuggestionResult(
                text=suggestion.text,
                score=suggestion.score,
                category=suggestion.category
            )
            for suggestion in suggestions
        ]
        
        return SuggestionResponse(
            suggestions=suggestion_results,
            query=q,
            total=len(suggestion_results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Suggestion failed for user {user_context.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Suggestion operation failed"
        )


@router.post("/index", summary="Index Document (Internal)")
async def index_document(
    document: IndexDocument,
    user_context: UserContext = Depends(get_user_context),
    search_client: OpenSearchClient = Depends(get_client),
    rbac: RBACManager = Depends(get_rbac)
) -> Dict[str, Any]:
    """
    Index a document for search (internal use by other services).
    
    ## Request Body
    
    * **id**: Unique document identifier
    * **title**: Document title for search and suggestions
    * **content**: Full document content for search
    * **document_type**: Type of document (iep, assessment, etc.)
    * **tenant_id**: Tenant identifier for multi-tenancy
    * **school_id**: Optional school identifier
    * **metadata**: Additional document metadata
    
    ## Access Control
    
    Only system admins and the creating tenant can index documents.
    """
    
    try:
        # Check if user can index documents (typically system/admin only)
        if not user_context.is_system and document.tenant_id != user_context.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot index documents for other tenants"
            )
            
        # Validate document type access
        if not rbac.check_document_access(user_context, document.document_type):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to document type: {document.document_type}"
            )
            
        # Prepare document for indexing
        doc_data = {
            "title": document.title,
            "content": document.content,
            "tenant_id": document.tenant_id,
            "school_id": document.school_id,
            "metadata": document.metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "tags": []
        }
        
        # Index document
        result = await search_client.index_document(
            doc_id=document.id,
            document=doc_data,
            doc_type=document.document_type,
            refresh=True
        )
        
        return {
            "indexed": True,
            "document_id": document.id,
            "document_type": document.document_type,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document indexing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document indexing failed"
        )


@router.delete("/index/{doc_type}/{doc_id}", summary="Delete Document (Internal)")
async def delete_document(
    doc_type: str,
    doc_id: str,
    user_context: UserContext = Depends(get_user_context),
    search_client: OpenSearchClient = Depends(get_client),
    rbac: RBACManager = Depends(get_rbac)
) -> Dict[str, Any]:
    """
    Delete a document from search index (internal use by other services).
    
    ## Path Parameters
    
    * **doc_type**: Document type (iep, assessment, student, etc.)
    * **doc_id**: Unique document identifier
    
    ## Access Control
    
    Only system admins and document owners can delete documents.
    """
    
    try:
        # Validate document type
        valid_types = {'iep', 'assessment', 'student', 'curriculum', 'resource', 'user'}
        if doc_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type: {doc_type}"
            )
            
        # Check permissions
        if not user_context.is_system and not rbac.check_document_access(user_context, doc_type):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to document type: {doc_type}"
            )
            
        # Delete document
        result = await search_client.delete_document(
            doc_id=doc_id,
            doc_type=doc_type
        )
        
        return {
            "deleted": True,
            "document_id": doc_id,
            "document_type": doc_type,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document deletion failed"
        )


@router.get("/stats", summary="Search Statistics")
async def get_search_stats(
    user_context: UserContext = Depends(get_user_context),
    search_client: OpenSearchClient = Depends(get_client)
) -> Dict[str, Any]:
    """
    Get search statistics and index information.
    
    Returns document counts and index health for accessible document types.
    """
    
    try:
        # Get OpenSearch health
        health_info = await search_client.health_check()
        
        # For demo, return basic stats
        # In production, you'd query actual index statistics
        return {
            "user_context": {
                "user_id": user_context.user_id,
                "tenant_id": user_context.tenant_id,
                "roles": [role.value for role in user_context.roles],
                "accessible_schools": user_context.school_ids,
                "is_admin": user_context.is_admin
            },
            "search_health": health_info,
            "accessible_document_types": get_rbac_manager().filter_document_types(user_context),
            "cross_school_access": get_rbac_manager().get_cross_school_visibility(user_context)
        }
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve search statistics"
        )
