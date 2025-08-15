"""
Simple Search Service
A simplified version of the search service for development
"""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn

app = FastAPI(
    title="Search Service", 
    description="Content search and discovery service",
    version="1.0.0"
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "search-svc", "version": "1.0.0"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Search Service is running", "service": "search-svc"}

# Search models
class SearchQuery(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = {}
    limit: Optional[int] = 10
    offset: Optional[int] = 0

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float
    type: str
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_count: int
    query_time_ms: int

class SuggestionResponse(BaseModel):
    suggestions: List[str]

# Mock search data
mock_content = [
    {
        "id": "content_1",
        "title": "Introduction to Machine Learning",
        "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms...",
        "type": "lesson",
        "metadata": {"subject": "AI", "difficulty": "beginner", "duration": 30}
    },
    {
        "id": "content_2", 
        "title": "Advanced Neural Networks",
        "content": "Deep learning with neural networks involves multiple layers of interconnected nodes...",
        "type": "lesson",
        "metadata": {"subject": "AI", "difficulty": "advanced", "duration": 60}
    },
    {
        "id": "content_3",
        "title": "Python Programming Basics",
        "content": "Python is a versatile programming language used in data science and AI development...",
        "type": "tutorial",
        "metadata": {"subject": "Programming", "difficulty": "beginner", "duration": 45}
    }
]

# Search endpoints
@app.post("/search", response_model=SearchResponse)
async def search_content(query: SearchQuery):
    """Search for content based on query"""
    # Simple mock search implementation
    results = []
    
    for item in mock_content:
        score = 0.0
        if query.query.lower() in item["title"].lower():
            score += 1.0
        if query.query.lower() in item["content"].lower():
            score += 0.5
            
        if score > 0:
            results.append(SearchResult(
                id=item["id"],
                title=item["title"],
                content=item["content"][:200] + "..." if len(item["content"]) > 200 else item["content"],
                score=score,
                type=item["type"],
                metadata=item["metadata"]
            ))
    
    # Sort by score
    results.sort(key=lambda x: x.score, reverse=True)
    
    # Apply pagination
    start = query.offset or 0
    end = start + (query.limit or 10)
    paginated_results = results[start:end]
    
    return SearchResponse(
        results=paginated_results,
        total_count=len(results),
        query_time_ms=12  # Mock query time
    )

@app.get("/search", response_model=SearchResponse)
async def search_content_get(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Number of results to return"),
    offset: int = Query(0, description="Offset for pagination"),
    type: Optional[str] = Query(None, description="Content type filter")
):
    """Search for content via GET request"""
    query = SearchQuery(
        query=q,
        limit=limit,
        offset=offset,
        filters={"type": type} if type else {}
    )
    return await search_content(query)

@app.get("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(
    q: str = Query(..., description="Partial query for suggestions"),
    limit: int = Query(5, description="Number of suggestions")
):
    """Get search suggestions based on partial query"""
    suggestions = []
    
    # Simple suggestion logic based on content titles
    for item in mock_content:
        if q.lower() in item["title"].lower() and item["title"] not in suggestions:
            suggestions.append(item["title"])
        
        # Add some common search terms
        common_terms = ["machine learning", "neural networks", "python", "AI", "programming"]
        for term in common_terms:
            if q.lower() in term.lower() and term not in suggestions:
                suggestions.append(term)
    
    return SuggestionResponse(suggestions=suggestions[:limit])

@app.get("/content/{content_id}")
async def get_content(content_id: str):
    """Get specific content by ID"""
    for item in mock_content:
        if item["id"] == content_id:
            return item
    
    raise HTTPException(status_code=404, detail="Content not found")

@app.get("/content/types")
async def get_content_types():
    """Get available content types"""
    types = set(item["type"] for item in mock_content)
    return {"types": list(types)}

@app.get("/analytics/popular")
async def get_popular_searches():
    """Get popular search terms (mock data)"""
    return {
        "popular_searches": [
            {"term": "machine learning", "count": 150},
            {"term": "python", "count": 120},
            {"term": "neural networks", "count": 95},
            {"term": "AI basics", "count": 80}
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3007)
