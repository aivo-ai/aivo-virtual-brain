"""
AIVO Search Service - OpenSearch Client
S1-13 Implementation

Provides OpenSearch integration with multi-tenant search capabilities,
role-based access control, and intelligent suggestions.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass

from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import NotFoundError, RequestError
import httpx
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class SearchConfig(BaseSettings):
    """Search service configuration"""
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False
    opensearch_ca_certs: Optional[str] = None
    
    # Index configuration
    default_index_prefix: str = "aivo"
    max_search_results: int = 100
    suggestion_size: int = 10
    
    class Config:
        env_prefix = "SEARCH_"


@dataclass
class SearchContext:
    """User search context for RBAC filtering"""
    user_id: str
    tenant_id: str
    school_ids: List[str]
    roles: List[str]
    permissions: List[str]
    is_admin: bool = False
    is_system: bool = False


@dataclass
class SearchResult:
    """Search result with metadata"""
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


@dataclass
class SuggestionResult:
    """Search suggestion result"""
    text: str
    score: float
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OpenSearchClient:
    """OpenSearch client with RBAC-aware search capabilities"""
    
    def __init__(self, config: SearchConfig):
        self.config = config
        
        # Initialize OpenSearch client
        self.client = OpenSearch(
            hosts=[{
                'host': config.opensearch_host,
                'port': config.opensearch_port
            }],
            http_auth=(config.opensearch_username, config.opensearch_password),
            use_ssl=config.opensearch_use_ssl,
            verify_certs=config.opensearch_verify_certs,
            ca_certs=config.opensearch_ca_certs,
            connection_class=RequestsHttpConnection
        )
        
        # Index mappings by document type
        self.index_mappings = {
            "iep": f"{config.default_index_prefix}_iep",
            "assessment": f"{config.default_index_prefix}_assessment",
            "student": f"{config.default_index_prefix}_student",
            "curriculum": f"{config.default_index_prefix}_curriculum",
            "resource": f"{config.default_index_prefix}_resource",
            "user": f"{config.default_index_prefix}_user"
        }
        
    async def ensure_indices(self):
        """Ensure all required indices exist with proper mappings"""
        for doc_type, index_name in self.index_mappings.items():
            if not self.client.indices.exists(index=index_name):
                await self.create_index(doc_type, index_name)
                
    async def create_index(self, doc_type: str, index_name: str):
        """Create index with appropriate mapping for document type"""
        mapping = self._get_index_mapping(doc_type)
        
        try:
            self.client.indices.create(
                index=index_name,
                body={
                    "mappings": mapping,
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "analysis": {
                            "analyzer": {
                                "aivo_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "standard",
                                    "filter": [
                                        "lowercase",
                                        "asciifolding",
                                        "stop",
                                        "snowball"
                                    ]
                                },
                                "suggestion_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "keyword",
                                    "filter": [
                                        "lowercase",
                                        "asciifolding"
                                    ]
                                }
                            }
                        }
                    }
                }
            )
            logger.info(f"Created index: {index_name}")
        except RequestError as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            raise
            
    def _get_index_mapping(self, doc_type: str) -> Dict[str, Any]:
        """Get index mapping for specific document type"""
        base_mapping = {
            "properties": {
                "id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "analyzer": "aivo_analyzer",
                    "fields": {
                        "suggest": {
                            "type": "completion",
                            "analyzer": "suggestion_analyzer"
                        },
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                "content": {
                    "type": "text",
                    "analyzer": "aivo_analyzer"
                },
                "document_type": {"type": "keyword"},
                "tenant_id": {"type": "keyword"},
                "school_id": {"type": "keyword"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "status": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "metadata": {
                    "type": "object",
                    "enabled": False
                }
            }
        }
        
        # Document-specific mappings
        if doc_type == "iep":
            base_mapping["properties"].update({
                "student_id": {"type": "keyword"},
                "goals": {"type": "text", "analyzer": "aivo_analyzer"},
                "accommodations": {"type": "text", "analyzer": "aivo_analyzer"},
                "services": {"type": "text", "analyzer": "aivo_analyzer"},
                "grade_level": {"type": "keyword"},
                "disability_categories": {"type": "keyword"}
            })
        elif doc_type == "assessment":
            base_mapping["properties"].update({
                "student_id": {"type": "keyword"},
                "assessment_type": {"type": "keyword"},
                "subject": {"type": "keyword"},
                "score": {"type": "float"},
                "percentile": {"type": "float"},
                "grade_equivalent": {"type": "keyword"}
            })
        elif doc_type == "student":
            base_mapping["properties"].update({
                "first_name": {"type": "text", "analyzer": "aivo_analyzer"},
                "last_name": {"type": "text", "analyzer": "aivo_analyzer"},
                "student_number": {"type": "keyword"},
                "grade_level": {"type": "keyword"},
                "birth_date": {"type": "date"},
                "enrollment_status": {"type": "keyword"}
            })
        elif doc_type == "curriculum":
            base_mapping["properties"].update({
                "subject": {"type": "keyword"},
                "grade_level": {"type": "keyword"},
                "standard": {"type": "text", "analyzer": "aivo_analyzer"},
                "learning_objective": {"type": "text", "analyzer": "aivo_analyzer"},
                "difficulty_level": {"type": "keyword"}
            })
        elif doc_type == "resource":
            base_mapping["properties"].update({
                "resource_type": {"type": "keyword"},
                "subject": {"type": "keyword"},
                "grade_level": {"type": "keyword"},
                "format": {"type": "keyword"},
                "url": {"type": "keyword"},
                "file_size": {"type": "long"},
                "mime_type": {"type": "keyword"}
            })
            
        return base_mapping
        
    async def index_document(
        self,
        doc_id: str,
        document: Dict[str, Any],
        doc_type: str,
        refresh: bool = False
    ):
        """Index a document with proper type mapping"""
        index_name = self.index_mappings.get(doc_type)
        if not index_name:
            raise ValueError(f"Unknown document type: {doc_type}")
            
        # Ensure document has required fields
        document.update({
            "id": doc_id,
            "document_type": doc_type,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Add suggestion field for title
        if "title" in document:
            document["title_suggest"] = {
                "input": [document["title"]],
                "weight": 10
            }
            
        try:
            response = self.client.index(
                index=index_name,
                id=doc_id,
                body=document,
                refresh=refresh
            )
            logger.debug(f"Indexed document {doc_id} in {index_name}")
            return response
        except RequestError as e:
            logger.error(f"Failed to index document {doc_id}: {e}")
            raise
            
    async def search(
        self,
        query: str,
        context: SearchContext,
        doc_types: Optional[List[str]] = None,
        size: int = 20,
        from_: int = 0,
        sort: Optional[List[Dict[str, Any]]] = None
    ) -> List[SearchResult]:
        """Search with RBAC filtering"""
        
        # Build search query with RBAC filters
        search_body = self._build_search_query(
            query=query,
            context=context,
            doc_types=doc_types,
            size=size,
            from_=from_,
            sort=sort
        )
        
        # Determine indices to search
        indices = self._get_search_indices(doc_types)
        
        try:
            response = self.client.search(
                index=",".join(indices),
                body=search_body
            )
            
            return self._parse_search_results(response)
            
        except NotFoundError:
            logger.warning(f"Search indices not found: {indices}")
            return []
        except RequestError as e:
            logger.error(f"Search query failed: {e}")
            raise
            
    async def suggest(
        self,
        query: str,
        context: SearchContext,
        size: int = 10
    ) -> List[SuggestionResult]:
        """Get search suggestions with RBAC filtering"""
        
        suggest_body = {
            "suggest": {
                "title_suggest": {
                    "prefix": query.lower(),
                    "completion": {
                        "field": "title.suggest",
                        "size": size * 2,  # Get more to filter
                        "contexts": {
                            "tenant_id": [context.tenant_id]
                        }
                    }
                }
            },
            "query": self._build_rbac_filter(context),
            "size": 0  # Don't return documents, just suggestions
        }
        
        indices = self._get_search_indices()
        
        try:
            response = self.client.search(
                index=",".join(indices),
                body=suggest_body
            )
            
            return self._parse_suggestion_results(response, size)
            
        except NotFoundError:
            logger.warning("Suggestion indices not found")
            return []
        except RequestError as e:
            logger.error(f"Suggestion query failed: {e}")
            return []
            
    def _build_search_query(
        self,
        query: str,
        context: SearchContext,
        doc_types: Optional[List[str]] = None,
        size: int = 20,
        from_: int = 0,
        sort: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Build OpenSearch query with RBAC filters"""
        
        # Main query
        if query.strip():
            main_query = {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",
                        "content^2", 
                        "goals",
                        "accommodations",
                        "services",
                        "standard",
                        "learning_objective"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        else:
            main_query = {"match_all": {}}
            
        # RBAC filter
        rbac_filter = self._build_rbac_filter(context)
        
        # Document type filter
        filters = [rbac_filter]
        if doc_types:
            filters.append({
                "terms": {
                    "document_type": doc_types
                }
            })
            
        search_body = {
            "query": {
                "bool": {
                    "must": [main_query],
                    "filter": filters
                }
            },
            "size": min(size, self.config.max_search_results),
            "from": from_,
            "highlight": {
                "fields": {
                    "title": {},
                    "content": {"fragment_size": 150},
                    "goals": {},
                    "accommodations": {}
                }
            },
            "_source": {
                "excludes": ["metadata.large_data"]
            }
        }
        
        if sort:
            search_body["sort"] = sort
        else:
            search_body["sort"] = [
                "_score",
                {"updated_at": {"order": "desc"}}
            ]
            
        return search_body
        
    def _build_rbac_filter(self, context: SearchContext) -> Dict[str, Any]:
        """Build RBAC filter based on user context"""
        
        # System users can see everything
        if context.is_system:
            return {"match_all": {}}
            
        # Tenant admins can see all within tenant
        if context.is_admin:
            return {
                "term": {
                    "tenant_id": context.tenant_id
                }
            }
            
        # Regular users - school-based access
        school_filters = []
        if context.school_ids:
            school_filters.append({
                "terms": {
                    "school_id": context.school_ids
                }
            })
            
        # Role-based document access
        if "teacher" in context.roles:
            # Teachers can see IEPs and assessments for their students
            school_filters.extend([
                {
                    "bool": {
                        "must": [
                            {"term": {"document_type": "iep"}},
                            {"terms": {"school_id": context.school_ids}}
                        ]
                    }
                },
                {
                    "bool": {
                        "must": [
                            {"term": {"document_type": "assessment"}},
                            {"terms": {"school_id": context.school_ids}}
                        ]
                    }
                }
            ])
        elif "parent" in context.roles:
            # Parents can only see their own children's data
            school_filters.append({
                "bool": {
                    "must": [
                        {"terms": {"document_type": ["iep", "assessment"]}},
                        {"term": {"metadata.parent_id": context.user_id}}
                    ]
                }
            })
        elif "student" in context.roles:
            # Students can see their own data
            school_filters.append({
                "term": {"metadata.student_id": context.user_id}
            })
            
        return {
            "bool": {
                "must": [
                    {"term": {"tenant_id": context.tenant_id}}
                ],
                "should": school_filters,
                "minimum_should_match": 1
            }
        }
        
    def _get_search_indices(
        self, 
        doc_types: Optional[List[str]] = None
    ) -> List[str]:
        """Get list of indices to search"""
        if doc_types:
            return [
                self.index_mappings[doc_type] 
                for doc_type in doc_types 
                if doc_type in self.index_mappings
            ]
        else:
            return list(self.index_mappings.values())
            
    def _parse_search_results(
        self, 
        response: Dict[str, Any]
    ) -> List[SearchResult]:
        """Parse OpenSearch response to SearchResult objects"""
        results = []
        
        for hit in response.get("hits", {}).get("hits", []):
            source = hit["_source"]
            
            result = SearchResult(
                id=source.get("id", hit["_id"]),
                title=source.get("title", ""),
                content=source.get("content", ""),
                document_type=source.get("document_type", "unknown"),
                tenant_id=source.get("tenant_id", ""),
                school_id=source.get("school_id"),
                created_at=self._parse_date(source.get("created_at")),
                updated_at=self._parse_date(source.get("updated_at")),
                score=hit.get("_score"),
                highlight=hit.get("highlight"),
                metadata=source.get("metadata", {})
            )
            
            results.append(result)
            
        return results
        
    def _parse_suggestion_results(
        self,
        response: Dict[str, Any],
        limit: int
    ) -> List[SuggestionResult]:
        """Parse suggestion response"""
        suggestions = []
        
        suggest_data = response.get("suggest", {}).get("title_suggest", [])
        
        for suggestion_group in suggest_data:
            for option in suggestion_group.get("options", []):
                suggestion = SuggestionResult(
                    text=option["text"],
                    score=option["_score"],
                    metadata=option.get("_source", {})
                )
                suggestions.append(suggestion)
                
        # Sort by score and limit results
        suggestions.sort(key=lambda x: x.score, reverse=True)
        return suggestions[:limit]
        
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
            
    async def delete_document(self, doc_id: str, doc_type: str):
        """Delete a document from the index"""
        index_name = self.index_mappings.get(doc_type)
        if not index_name:
            raise ValueError(f"Unknown document type: {doc_type}")
            
        try:
            response = self.client.delete(
                index=index_name,
                id=doc_id
            )
            logger.debug(f"Deleted document {doc_id} from {index_name}")
            return response
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found for deletion")
        except RequestError as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            raise
            
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenSearch cluster health"""
        try:
            cluster_health = self.client.cluster.health()
            indices_stats = self.client.indices.stats()
            
            return {
                "status": "healthy",
                "cluster_status": cluster_health.get("status"),
                "total_indices": len(self.index_mappings),
                "total_documents": indices_stats.get("_all", {}).get("total", {}).get("docs", {}).get("count", 0),
                "cluster_info": {
                    "cluster_name": cluster_health.get("cluster_name"),
                    "number_of_nodes": cluster_health.get("number_of_nodes"),
                    "active_shards": cluster_health.get("active_shards")
                }
            }
        except Exception as e:
            logger.error(f"OpenSearch health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global client instance
search_client: Optional[OpenSearchClient] = None


def get_search_client() -> OpenSearchClient:
    """Get or create search client instance"""
    global search_client
    if search_client is None:
        config = SearchConfig()
        search_client = OpenSearchClient(config)
    return search_client
