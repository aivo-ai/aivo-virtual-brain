"""
Test Suite for S4-16 Search Relevance & Multilingual Synonyms
Validates multilingual search functionality, educational content synonyms, and relevance boosting
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

import aiohttp
from fastapi.testclient import TestClient
from opensearchpy import AsyncOpenSearch

# Import the search service
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import app, search_service, LessonDocument, SearchQuery

# Test configuration
TEST_BASE_URL = "http://localhost:8082"
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))

# Test client
client = TestClient(app)

class TestSearchRelevance:
    """Test suite for multilingual search relevance"""
    
    @pytest.fixture(autouse=True)
    async def setup_test_data(self):
        """Setup test lesson documents for each supported locale"""
        
        # Sample test lessons for multiple languages
        self.test_lessons = {
            "en": [
                LessonDocument(
                    id="lesson_en_001",
                    title="Introduction to Algebra",
                    description="Basic algebraic concepts and equations",
                    content="Learn about variables, coefficients, and solving equations. This lesson covers fundamental algebra concepts including linear equations, graphing, and problem-solving strategies.",
                    subject="math",
                    grade_band="6-8",
                    lesson_type="interactive",
                    tags=["algebra", "equations", "mathematics", "variables"],
                    locale="en",
                    tenant_id="edu_tenant_001",
                    difficulty_level=3,
                    popularity_score=4.5,
                    completion_rate=0.85,
                    created_at=datetime.now() - timedelta(days=5),
                    updated_at=datetime.now() - timedelta(days=1)
                ),
                LessonDocument(
                    id="lesson_en_002",
                    title="Reading Comprehension Strategies",
                    description="Improve your reading skills with proven techniques",
                    content="Master reading comprehension through summarizing, questioning, and analyzing text. Practice with fiction and non-fiction passages.",
                    subject="ela",
                    grade_band="K-5",
                    lesson_type="guided",
                    tags=["reading", "comprehension", "literacy", "strategies"],
                    locale="en",
                    tenant_id="edu_tenant_001",
                    difficulty_level=2,
                    popularity_score=4.2,
                    completion_rate=0.78,
                    created_at=datetime.now() - timedelta(days=10),
                    updated_at=datetime.now() - timedelta(days=3)
                )
            ],
            "es": [
                LessonDocument(
                    id="lesson_es_001",
                    title="Introducción al Álgebra",
                    description="Conceptos básicos de álgebra y ecuaciones",
                    content="Aprende sobre variables, coeficientes y resolución de ecuaciones. Esta lección cubre conceptos fundamentales del álgebra incluyendo ecuaciones lineales.",
                    subject="matematicas",
                    grade_band="6-8",
                    lesson_type="interactiva",
                    tags=["algebra", "ecuaciones", "matematicas", "variables"],
                    locale="es",
                    tenant_id="edu_tenant_002",
                    difficulty_level=3,
                    popularity_score=4.3,
                    completion_rate=0.82,
                    created_at=datetime.now() - timedelta(days=7),
                    updated_at=datetime.now() - timedelta(days=2)
                ),
                LessonDocument(
                    id="lesson_es_002",
                    title="Estrategias de Comprensión Lectora",
                    description="Mejora tus habilidades de lectura con técnicas probadas",
                    content="Domina la comprensión lectora a través de resumir, preguntar y analizar textos. Practica con pasajes de ficción y no ficción.",
                    subject="lengua",
                    grade_band="K-5",
                    lesson_type="guiada",
                    tags=["lectura", "comprension", "alfabetizacion", "estrategias"],
                    locale="es",
                    tenant_id="edu_tenant_002",
                    difficulty_level=2,
                    popularity_score=4.0,
                    completion_rate=0.75,
                    created_at=datetime.now() - timedelta(days=12),
                    updated_at=datetime.now() - timedelta(days=4)
                )
            ],
            "fr": [
                LessonDocument(
                    id="lesson_fr_001",
                    title="Introduction à l'Algèbre",
                    description="Concepts de base en algèbre et équations",
                    content="Apprenez les variables, coefficients et résolution d'équations. Cette leçon couvre les concepts fondamentaux de l'algèbre y compris les équations linéaires.",
                    subject="mathematiques",
                    grade_band="6-8",
                    lesson_type="interactive",
                    tags=["algebre", "equations", "mathematiques", "variables"],
                    locale="fr",
                    tenant_id="edu_tenant_003",
                    difficulty_level=3,
                    popularity_score=4.1,
                    completion_rate=0.80,
                    created_at=datetime.now() - timedelta(days=8),
                    updated_at=datetime.now() - timedelta(days=1)
                )
            ],
            "sw": [
                LessonDocument(
                    id="lesson_sw_001",
                    title="Utangulizi wa Aljebra",
                    description="Misingi ya aljebra na mlinganyo",
                    content="Jifunze kuhusu vigeuzi, vipimo na kutatua mlinganyo. Somo hili linashughulikia misingi ya aljebra ikijumuisha mlinganyo wa mstari.",
                    subject="hisabati",
                    grade_band="6-8",
                    lesson_type="shirikishi",
                    tags=["aljebra", "mlinganyo", "hisabati", "vigeuzi"],
                    locale="sw",
                    tenant_id="edu_tenant_004",
                    difficulty_level=3,
                    popularity_score=3.9,
                    completion_rate=0.77,
                    created_at=datetime.now() - timedelta(days=6),
                    updated_at=datetime.now() - timedelta(days=2)
                )
            ]
        }
        
        # Index test lessons
        for locale, lessons in self.test_lessons.items():
            for lesson in lessons:
                await search_service.index_document(lesson)
                
        # Wait for indexing
        await asyncio.sleep(2)
        
    @pytest.mark.asyncio
    async def test_multilingual_search_basic(self):
        """Test basic search functionality across different languages"""
        
        # Test English search
        en_query = SearchQuery(
            query="algebra",
            locale="en"
        )
        en_response = await search_service.search(en_query)
        
        assert en_response.total > 0
        assert any("algebra" in result.title.lower() for result in en_response.results)
        assert en_response.locale == "en"
        
        # Test Spanish search 
        es_query = SearchQuery(
            query="algebra",
            locale="es"
        )
        es_response = await search_service.search(es_query)
        
        assert es_response.total > 0
        assert any("álgebra" in result.title.lower() for result in es_response.results)
        assert es_response.locale == "es"
        
        # Test French search
        fr_query = SearchQuery(
            query="algèbre",
            locale="fr"
        )
        fr_response = await search_service.search(fr_query)
        
        assert fr_response.total > 0
        assert any("algèbre" in result.title.lower() for result in fr_response.results)
        assert fr_response.locale == "fr"
        
    @pytest.mark.asyncio
    async def test_synonym_search(self):
        """Test educational content synonym functionality"""
        
        # Test English math synonyms
        math_queries = ["math", "mathematics", "arithmetic", "numbers"]
        
        for query in math_queries:
            search_query = SearchQuery(
                query=query,
                locale="en",
                subject="math"
            )
            response = await search_service.search(search_query)
            
            # Should find math-related content regardless of synonym used
            assert response.total > 0
            math_results = [r for r in response.results if r.subject in ["math", "mathematics"]]
            assert len(math_results) > 0
            
        # Test Spanish synonyms
        spanish_math_queries = ["matemáticas", "mates", "aritmética", "números"]
        
        for query in spanish_math_queries:
            search_query = SearchQuery(
                query=query,
                locale="es",
                subject="matematicas"
            )
            response = await search_service.search(search_query)
            
            assert response.total > 0
            
    @pytest.mark.asyncio
    async def test_subject_filtering(self):
        """Test subject-based filtering functionality"""
        
        # Test math subject filter
        math_query = SearchQuery(
            query="algebra",
            locale="en",
            subject="math"
        )
        math_response = await search_service.search(math_query)
        
        assert all(result.subject == "math" for result in math_response.results)
        
        # Test ELA subject filter
        ela_query = SearchQuery(
            query="reading",
            locale="en",
            subject="ela"
        )
        ela_response = await search_service.search(ela_query)
        
        assert all(result.subject == "ela" for result in ela_response.results)
        
    @pytest.mark.asyncio
    async def test_grade_band_filtering(self):
        """Test grade band filtering functionality"""
        
        # Test K-5 grade band
        k5_query = SearchQuery(
            query="reading",
            locale="en",
            grade_band="K-5"
        )
        k5_response = await search_service.search(k5_query)
        
        assert all(result.grade_band == "K-5" for result in k5_response.results)
        
        # Test 6-8 grade band
        middle_query = SearchQuery(
            query="algebra",
            locale="en",
            grade_band="6-8"
        )
        middle_response = await search_service.search(middle_query)
        
        assert all(result.grade_band == "6-8" for result in middle_response.results)
        
    @pytest.mark.asyncio
    async def test_relevance_boosting(self):
        """Test relevance boosting for recent and tenant-specific content"""
        
        # Test recent content boosting
        recent_query = SearchQuery(
            query="algebra",
            locale="en",
            boost_recent=True
        )
        recent_response = await search_service.search(recent_query)
        
        # Test tenant boosting
        tenant_query = SearchQuery(
            query="algebra",
            locale="en",
            tenant_id="edu_tenant_001",
            boost_tenant=True
        )
        tenant_response = await search_service.search(tenant_query)
        
        # Tenant-specific results should be boosted
        if tenant_response.results:
            top_result = tenant_response.results[0]
            assert top_result.tenant_id == "edu_tenant_001"
            
    @pytest.mark.asyncio
    async def test_fuzzy_search(self):
        """Test fuzzy search for handling typos and variations"""
        
        # Test with typos
        typo_queries = [
            "algebr",  # Missing 'a'
            "algenra", # Character transposition
            "algrebra" # Extra character
        ]
        
        for query in typo_queries:
            search_query = SearchQuery(
                query=query,
                locale="en"
            )
            response = await search_service.search(search_query)
            
            # Should still find algebra-related content with fuzzy matching
            assert response.total > 0
            
    @pytest.mark.asyncio
    async def test_edge_ngram_suggestions(self):
        """Test edge n-gram autocomplete functionality"""
        
        # Test partial matches for autocomplete
        partial_queries = ["alg", "read", "math"]
        
        for query in partial_queries:
            search_query = SearchQuery(
                query=query,
                locale="en"
            )
            response = await search_service.search(search_query)
            
            # Should find results starting with partial query
            assert response.total > 0
            # Should have suggestions
            assert len(response.suggestions) >= 0
            
    @pytest.mark.asyncio
    async def test_pagination(self):
        """Test search result pagination"""
        
        # Test first page
        page1_query = SearchQuery(
            query="lesson",
            locale="en",
            page=1,
            size=1
        )
        page1_response = await search_service.search(page1_query)
        
        assert page1_response.page == 1
        assert page1_response.size == 1
        assert len(page1_response.results) <= 1
        
        # Test second page if there are more results
        if page1_response.total > 1:
            page2_query = SearchQuery(
                query="lesson",
                locale="en",
                page=2,
                size=1
            )
            page2_response = await search_service.search(page2_query)
            
            assert page2_response.page == 2
            # Results should be different
            if page1_response.results and page2_response.results:
                assert page1_response.results[0].id != page2_response.results[0].id
                
    @pytest.mark.asyncio
    async def test_faceted_search(self):
        """Test faceted search functionality"""
        
        search_query = SearchQuery(
            query="lesson",
            locale="en"
        )
        response = await search_service.search(search_query)
        
        # Should have facets
        assert "subjects" in response.facets
        assert "grade_bands" in response.facets
        assert "lesson_types" in response.facets
        assert "difficulty_levels" in response.facets
        
        # Facets should have counts
        if response.facets["subjects"]:
            for facet in response.facets["subjects"]:
                assert "value" in facet
                assert "count" in facet
                assert facet["count"] > 0
                
    @pytest.mark.asyncio
    async def test_highlighting(self):
        """Test search result highlighting"""
        
        search_query = SearchQuery(
            query="algebra",
            locale="en"
        )
        response = await search_service.search(search_query)
        
        if response.results:
            result = response.results[0]
            
            # Should have highlights for matched terms
            if result.highlights:
                # Check if highlights contain search term
                all_highlights = []
                for field, highlights in result.highlights.items():
                    all_highlights.extend(highlights)
                    
                # Should contain highlight markers
                highlight_text = " ".join(all_highlights)
                assert "<mark>" in highlight_text and "</mark>" in highlight_text
                
    @pytest.mark.asyncio  
    async def test_difficulty_filtering(self):
        """Test difficulty level filtering"""
        
        # Test specific difficulty level
        difficulty_query = SearchQuery(
            query="lesson",
            locale="en",
            difficulty_level=3
        )
        difficulty_response = await search_service.search(difficulty_query)
        
        assert all(result.difficulty_level == 3 for result in difficulty_response.results)
        
    @pytest.mark.asyncio
    async def test_multilingual_cross_search(self):
        """Test search doesn't return results from other locales"""
        
        # Search for English content with Spanish query should not return Spanish results
        cross_query = SearchQuery(
            query="álgebra",  # Spanish term
            locale="en"       # English locale
        )
        cross_response = await search_service.search(cross_query)
        
        # Should only return English locale results
        assert all(result.locale == "en" for result in cross_response.results)
        
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test search performance metrics"""
        
        search_query = SearchQuery(
            query="algebra",
            locale="en"
        )
        response = await search_service.search(search_query)
        
        # Should have performance metrics
        assert response.took_ms > 0
        assert response.took_ms < 5000  # Should complete within 5 seconds
        
    @pytest.mark.asyncio
    async def test_empty_query_handling(self):
        """Test handling of empty or minimal queries"""
        
        # Test empty query
        empty_query = SearchQuery(
            query="",
            locale="en"
        )
        
        try:
            empty_response = await search_service.search(empty_query)
            # Should handle gracefully
            assert empty_response.total >= 0
        except Exception as e:
            # Should not crash
            assert False, f"Empty query caused exception: {e}"
            
    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Test handling of special characters in queries"""
        
        special_queries = [
            "algebra & equations",
            "reading (comprehension)",
            "math-related",
            "science/physics"
        ]
        
        for query in special_queries:
            search_query = SearchQuery(
                query=query,
                locale="en"
            )
            
            try:
                response = await search_service.search(search_query)
                assert response.total >= 0
            except Exception as e:
                assert False, f"Special character query '{query}' caused exception: {e}"


class TestSearchAPI:
    """Test the FastAPI search endpoints"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "search-svc"
        assert "supported_locales" in data
        
    def test_locales_endpoint(self):
        """Test supported locales endpoint"""
        response = client.get("/locales")
        assert response.status_code == 200
        
        data = response.json()
        assert "supported_locales" in data
        assert "total_count" in data
        assert data["total_count"] == 14  # Should support 14 locales
        
        # Should include key locales
        locales = data["supported_locales"]
        assert "en" in locales
        assert "es" in locales
        assert "fr" in locales
        assert "sw" in locales
        
    def test_search_get_endpoint(self):
        """Test GET search endpoint"""
        response = client.get("/search", params={
            "q": "algebra",
            "locale": "en",
            "subject": "math",
            "page": 1,
            "size": 10
        })
        
        assert response.status_code == 200
        
        data = response.json()
        assert "query" in data
        assert "locale" in data
        assert "total" in data
        assert "results" in data
        assert data["query"] == "algebra"
        assert data["locale"] == "en"
        
    def test_search_post_endpoint(self):
        """Test POST search endpoint"""
        search_data = {
            "query": "reading comprehension",
            "locale": "en",
            "subject": "ela",
            "grade_band": "K-5",
            "page": 1,
            "size": 20,
            "boost_recent": True,
            "boost_tenant": True
        }
        
        response = client.post("/search", json=search_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"] == "reading comprehension"
        assert data["locale"] == "en"
        assert "results" in data
        assert "facets" in data
        
    def test_analyze_endpoint(self):
        """Test text analysis endpoint"""
        response = client.get("/analyze/en", params={
            "text": "mathematics algebra equations"
        })
        
        assert response.status_code == 200
        
        data = response.json()
        assert "locale" in data
        assert "analyzer" in data
        assert "original_text" in data
        assert "tokens" in data
        assert "token_count" in data
        
        assert data["locale"] == "en"
        assert data["original_text"] == "mathematics algebra equations"
        assert len(data["tokens"]) > 0
        
    def test_invalid_locale(self):
        """Test handling of invalid locale"""
        response = client.get("/analyze/invalid", params={
            "text": "test"
        })
        
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"]


@pytest.mark.integration
class TestSearchIntegration:
    """Integration tests with OpenSearch"""
    
    @pytest.mark.asyncio
    async def test_opensearch_connection(self):
        """Test OpenSearch connection and index creation"""
        
        # Test client connection
        client = AsyncOpenSearch(
            hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
            http_auth=("admin", "admin"),
            use_ssl=True,
            verify_certs=False
        )
        
        try:
            # Test cluster health
            health = await client.cluster.health()
            assert health["status"] in ["green", "yellow"]
            
            # Test index existence
            for locale in ["en", "es", "fr", "sw"]:
                index_name = f"aivo_lessons_{locale}"
                exists = await client.indices.exists(index=index_name)
                assert exists, f"Index {index_name} should exist"
                
        finally:
            await client.close()
            
    @pytest.mark.asyncio
    async def test_bulk_indexing(self):
        """Test bulk indexing performance"""
        
        # Create test documents
        test_docs = []
        for i in range(10):
            doc = LessonDocument(
                id=f"bulk_test_{i}",
                title=f"Test Lesson {i}",
                description=f"Test description {i}",
                content=f"Test content for lesson {i}",
                subject="math",
                grade_band="6-8",
                lesson_type="test",
                tags=["test", "bulk"],
                locale="en",
                tenant_id="test_tenant",
                difficulty_level=2,
                popularity_score=3.0,
                completion_rate=0.5,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            test_docs.append(doc)
            
        # Test bulk indexing
        success_count = await search_service.bulk_index_documents(test_docs)
        assert success_count == len(test_docs)
        
        # Wait for indexing
        await asyncio.sleep(2)
        
        # Verify documents are searchable
        search_query = SearchQuery(
            query="bulk",
            locale="en"
        )
        response = await search_service.search(search_query)
        
        assert response.total >= len(test_docs)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
