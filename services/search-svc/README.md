# AIVO Search Service Documentation

## S1-13 Implementation - OpenSearch with Role-Based Access Control

## S4-16 Implementation - Search Relevance & Multilingual Synonyms

## Overview

The AIVO Search Service provides powerful full-text search and intelligent suggestions across educational documents with comprehensive role-based access control (RBAC) and advanced multilingual capabilities. Built on OpenSearch, it enables secure, multi-tenant search capabilities for IEPs, assessments, student records, curriculum, and educational resources across 14 supported languages.

## 🌍 S4-16: Multilingual Search Features

### Supported Languages (14 Total)

| Language                 | Locale    | Analyzer Features                | Educational Synonyms |
| ------------------------ | --------- | -------------------------------- | -------------------- |
| **English**              | `en`      | Stemming, stopwords, synonyms    | ✅ 200+ terms        |
| **Spanish**              | `es`      | Spanish stemming, accent folding | ✅ 200+ terms        |
| **French**               | `fr`      | Elision filters, French stemming | ✅ 200+ terms        |
| **Arabic**               | `ar`      | RTL support, normalization       | ✅ 200+ terms        |
| **Chinese (Simplified)** | `zh-Hans` | IK tokenization, segmentation    | ✅ 200+ terms        |
| **Hindi**                | `hi`      | Devanagari, ICU normalization    | ✅ 200+ terms        |
| **Portuguese**           | `pt`      | Portuguese stemming, accents     | ✅ 200+ terms        |
| **Igbo**                 | `ig`      | Tone preservation, compounds     | ✅ 200+ terms        |
| **Yoruba**               | `yo`      | Tonal diacritics, harmony        | ✅ 200+ terms        |
| **Hausa**                | `ha`      | Arabic loanwords, roots          | ✅ 200+ terms        |
| **Efik**                 | `efi`     | Cross River linguistics          | ✅ 200+ terms        |
| **Swahili**              | `sw`      | Bantu morphology, Arabic         | ✅ 200+ terms        |
| **Xhosa**                | `xh`      | Click consonants, noun classes   | ✅ 200+ terms        |
| **Kikuyu**               | `ki`      | Bantu tones, agglutination       | ✅ 200+ terms        |

### Advanced Search Capabilities

- **Educational Synonyms**: Subject-specific mappings (Math, ELA, Science, Social Studies)
- **Fuzzy Matching**: Typo tolerance and approximate matching
- **Autocomplete**: Edge n-gram based suggestions (2-20 characters)
- **Relevance Boosting**: Recent content, tenant-specific, popularity scoring
- **Query-time Optimization**: Multi-field search with weighted scoring

## S1-13: Core Search Features

### Core Search Capabilities

- **Full-text Search**: Advanced multi-field search across document title, content, goals, accommodations, and metadata
- **Smart Suggestions**: Real-time auto-complete with "fra" → "fractions" intelligent matching
- **Document Types**: IEP, assessment, student, curriculum, resource, and user documents
- **Fuzzy Matching**: Tolerant search with automatic typo correction and synonym expansion
- **Syntax Highlighting**: Search term highlighting in results for better user experience

### Role-Based Access Control (RBAC)

- **Multi-level Security**: System, tenant, school, and individual-level access controls
- **Cross-school Visibility**: Blocks unauthorized access to other schools' data
- **Granular Permissions**: Fine-grained control over document type access
- **Dynamic Filtering**: Real-time result filtering based on user context and permissions
- **Audit Trail**: Complete logging of search operations for compliance

### Multi-tenant Architecture

- **Tenant Isolation**: Complete data separation between organizations
- **School-level Segmentation**: Granular access control within tenants
- **Scalable Design**: Efficient handling of multiple organizations and schools
- **Performance Optimization**: Optimized queries with strategic indexing

## Quick Start

### Prerequisites

- Python 3.11+
- OpenSearch 2.11+
- JWT authentication infrastructure

### Installation

1. **Setup the service:**

```bash
cd services/search-svc
pip install -r requirements.txt
```

2. **Configure OpenSearch:**

```bash
# Start OpenSearch (Docker)
docker run -d \
  --name opensearch \
  -p 9200:9200 -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=admin123" \
  opensearchproject/opensearch:2.11.1
```

3. **Configure environment variables:**

```bash
# OpenSearch Configuration
SEARCH_OPENSEARCH_HOST=localhost
SEARCH_OPENSEARCH_PORT=9200
SEARCH_OPENSEARCH_USERNAME=admin
SEARCH_OPENSEARCH_PASSWORD=admin123
SEARCH_OPENSEARCH_USE_SSL=false
SEARCH_OPENSEARCH_VERIFY_CERTS=false

# Index Configuration
SEARCH_DEFAULT_INDEX_PREFIX=aivo
SEARCH_MAX_SEARCH_RESULTS=100
SEARCH_SUGGESTION_SIZE=10

# JWT Configuration (must match auth service)
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
```

4. **Start the service:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

5. **Access the API:**
   - REST API: http://localhost:8004/api/v1
   - API Documentation: http://localhost:8004/docs
   - Health Check: http://localhost:8004/health

## API Documentation

### Authentication

All endpoints require JWT authentication:

```bash
curl -H "Authorization: Bearer <jwt-token>" \
     "http://localhost:8004/api/v1/search?q=reading"
```

**Required JWT Claims:**

```json
{
  "sub": "user_123",
  "tenant_id": "district_456",
  "roles": ["teacher", "case_manager"],
  "school_ids": ["school_789"],
  "student_ids": ["student_101", "student_102"]
}
```

### Search Endpoint

**Basic Search:**

```bash
GET /api/v1/search?q=reading comprehension
```

**Advanced Search:**

```bash
GET /api/v1/search?q=autism&doc_types=iep,assessment&size=10&sort=updated_at:desc
```

**Response Example:**

```json
{
  "results": [
    {
      "id": "iep_12345",
      "title": "IEP for Jane Doe - Grade 5",
      "content": "Individual Education Program focusing on reading comprehension...",
      "document_type": "iep",
      "tenant_id": "district_123",
      "school_id": "elementary_456",
      "score": 0.95,
      "highlight": {
        "title": ["IEP for <em>Jane Doe</em> - Grade 5"],
        "content": ["focusing on <em>reading comprehension</em>"]
      },
      "metadata": {
        "student_id": "student_789",
        "grade_level": "5",
        "disability_categories": ["specific_learning_disability"]
      }
    }
  ],
  "total": 1,
  "query": "reading comprehension",
  "took": 15
}
```

### Suggestion Endpoint

**Auto-complete Suggestions:**

```bash
GET /api/v1/suggest?q=fra&size=5
```

**Response Example:**

```json
{
  "suggestions": [
    {
      "text": "fractions",
      "score": 0.9,
      "category": "curriculum"
    },
    {
      "text": "framework",
      "score": 0.8,
      "category": "curriculum"
    },
    {
      "text": "fragmented attention",
      "score": 0.7,
      "category": "assessment"
    }
  ],
  "query": "fra",
  "total": 3
}
```

## Role-Based Access Control

### User Roles and Permissions

#### System Administrator

- **Access**: All data across all tenants
- **Search Scope**: Unrestricted global search
- **Document Types**: All types including user management
- **Cross-school**: Full visibility across all schools

#### Tenant Administrator

- **Access**: All data within their tenant
- **Search Scope**: Tenant-wide search capabilities
- **Document Types**: IEP, assessment, student, curriculum, resource
- **Cross-school**: Full visibility within tenant schools

#### School Administrator

- **Access**: Data within assigned schools
- **Search Scope**: School-level search
- **Document Types**: IEP, assessment, student, curriculum, resource
- **Cross-school**: Limited to assigned schools

#### Teacher

- **Access**: Student data within assigned schools
- **Search Scope**: School and classroom-level search
- **Document Types**: IEP, assessment, student, curriculum, resource
- **Cross-school**: Limited to assigned schools

#### Case Manager

- **Access**: IEPs and assessments for assigned students
- **Search Scope**: Caseload-specific search
- **Document Types**: IEP, assessment, student, curriculum
- **Cross-school**: Limited to assigned schools

#### Parent

- **Access**: Only their children's educational records
- **Search Scope**: Child-specific search
- **Document Types**: IEP, assessment (their children only)
- **Cross-school**: No cross-school visibility

#### Student

- **Access**: Only their own educational records
- **Search Scope**: Self-data search only
- **Document Types**: IEP (own record only)
- **Cross-school**: No cross-school visibility

### RBAC Implementation Examples

#### Cross-School Visibility Test

```python
def test_cross_school_visibility():
    # Teacher from School A cannot see School B data
    teacher_context = UserContext(
        user_id="teacher_123",
        tenant_id="district_456",
        school_ids=["school_a"],
        roles=[Role.TEACHER]
    )

    # Search results automatically filtered by school
    assert not rbac_manager.get_cross_school_visibility(teacher_context)
```

#### Parent Access Restrictions

```python
def test_parent_access():
    # Parent can only access their children's data
    parent_context = UserContext(
        user_id="parent_123",
        student_ids=["student_456", "student_789"],
        roles=[Role.PARENT]
    )

    # Search filters include student_id restrictions
    filters = rbac_manager.build_search_filters(parent_context)
    assert "metadata.student_id" in filters
```

## OpenSearch Index Templates

### IEP Document Template

**Specialized Analysis:**

- Synonyms: "IEP" ↔ "Individual Education Program"
- Educational terms: "FAPE", "LRE", "ESY", "RTI"
- Therapy abbreviations: "OT", "PT", "SLP"

**Index Fields:**

```json
{
  "title": { "type": "text", "analyzer": "aivo_iep_analyzer" },
  "goals": { "type": "text", "analyzer": "aivo_iep_analyzer" },
  "accommodations": { "type": "text", "analyzer": "aivo_iep_analyzer" },
  "student_id": { "type": "keyword" },
  "grade_level": { "type": "keyword" },
  "disability_categories": { "type": "keyword" }
}
```

### Assessment Document Template

**Specialized Analysis:**

- Test abbreviations: "WISC" ↔ "Wechsler Intelligence Scale"
- Psychometric terms: "percentile", "standard score", "grade equivalent"
- Assessment tools: "BASC", "CBCL", "CARS", "ADOS"

**Index Fields:**

```json
{
  "test_name": { "type": "text", "analyzer": "aivo_assessment_analyzer" },
  "score": { "type": "float" },
  "percentile": { "type": "float" },
  "standard_score": { "type": "float" },
  "subject": { "type": "keyword" }
}
```

### Curriculum Document Template

**Specialized Analysis:**

- Standards: "CCSS" ↔ "Common Core State Standards"
- Math concepts: "fractions" ↔ "rational numbers"
- Reading skills: "phonics" ↔ "phonemic awareness"

**Index Fields:**

```json
{
  "standard": { "type": "text", "analyzer": "aivo_curriculum_analyzer" },
  "learning_objective": {
    "type": "text",
    "analyzer": "aivo_curriculum_analyzer"
  },
  "subject": { "type": "keyword" },
  "grade_level": { "type": "keyword" }
}
```

## Testing

### Comprehensive Test Suite

**Run All Tests:**

```bash
pytest tests/ -v --cov=app --cov-report=html
```

**Specific Test Categories:**

```bash
# RBAC and ACL tests
pytest tests/test_search_acl.py -v

# Cross-school visibility tests
pytest tests/test_search_acl.py::TestRBACSearchFiltering::test_cross_school_visibility_blocked -v

# Suggestion filtering tests
pytest tests/test_search_acl.py::TestRBACSearchFiltering::test_suggestions_fra_to_fractions -v
```

### Key Test Scenarios

#### 1. "Fra" → "Fractions" Suggestion Test

```python
@patch('app.client.get_search_client')
def test_suggestions_fra_to_fractions(self, mock_get_client, test_client):
    """Test 'fra' -> 'fractions' suggestion with ACL"""

    mock_suggestions = [
        SuggestionResult(text="fractions", score=0.9, category="curriculum"),
        SuggestionResult(text="framework", score=0.7, category="curriculum")
    ]
    mock_client.suggest.return_value = mock_suggestions

    token = self.create_jwt_token(user_id="teacher_456", roles=["teacher"])

    response = test_client.get(
        "/api/v1/suggest?q=fra&size=5",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"][0]["text"] == "fractions"
    assert data["suggestions"][0]["score"] == 0.9
```

#### 2. ACL Cross-School Blocking Test

```python
def test_cross_school_visibility_blocked(self, rbac_manager):
    """Test that non-admin users cannot see cross-school data"""

    teacher_context = UserContext(
        user_id="teacher_123",
        school_ids=["school_a"],
        roles=[Role.TEACHER]
    )

    # Should not have cross-school visibility
    assert not rbac_manager.get_cross_school_visibility(teacher_context)

    # Admin should have cross-school visibility
    admin_context = UserContext(
        user_id="admin_123",
        roles=[Role.TENANT_ADMIN]
    )

    assert rbac_manager.get_cross_school_visibility(admin_context)
```

#### 3. Parent Access Restriction Test

```python
def test_parent_student_access(self, rbac_manager):
    """Test parent access limited to their children's data"""

    parent_context = UserContext(
        user_id="parent_123",
        roles=[Role.PARENT],
        student_ids=["student_456", "student_789"]
    )

    filters = rbac_manager.build_search_filters(parent_context)

    # Should include student ID filter
    student_filter_found = False
    for filter_clause in filters["bool"]["must"]:
        if "terms" in filter_clause and "metadata.student_id" in filter_clause["terms"]:
            student_filter_found = True
            assert set(filter_clause["terms"]["metadata.student_id"]) == {"student_456", "student_789"}

    assert student_filter_found, "Student filter not found"
```

## Integration with Other Services

### IEP Service Integration

**Index IEP on Creation:**

```python
# In IEP service after creating/updating IEP
async def index_iep_document(iep: IEPDocument):
    search_data = {
        "id": iep.id,
        "title": f"IEP for {iep.student_name} - Grade {iep.grade_level}",
        "content": f"{iep.goals} {iep.accommodations} {iep.services}",
        "document_type": "iep",
        "tenant_id": iep.tenant_id,
        "school_id": iep.school_id,
        "metadata": {
            "student_id": iep.student_id,
            "grade_level": iep.grade_level,
            "case_manager": iep.case_manager_id,
            "disability_categories": iep.disability_categories
        }
    }

    async with httpx.AsyncClient() as client:
        await client.post(
            "http://search-svc:8004/api/v1/index",
            json=search_data,
            headers={"Authorization": f"Bearer {system_token}"}
        )
```

### Assessment Service Integration

**Index Assessment Results:**

```python
# In Assessment service after scoring
async def index_assessment_document(assessment: AssessmentResult):
    search_data = {
        "id": assessment.id,
        "title": f"{assessment.test_name} - {assessment.student_name}",
        "content": f"Assessment results: {assessment.interpretation}",
        "document_type": "assessment",
        "tenant_id": assessment.tenant_id,
        "school_id": assessment.school_id,
        "metadata": {
            "student_id": assessment.student_id,
            "test_name": assessment.test_name,
            "standard_score": assessment.standard_score,
            "percentile": assessment.percentile,
            "examiner": assessment.examiner_id
        }
    }

    async with httpx.AsyncClient() as client:
        await client.post(
            "http://search-svc:8004/api/v1/index",
            json=search_data
        )
```

## Performance Optimization

### Index Strategy

- **Sharding**: Single shard per index for optimal performance
- **Replicas**: No replicas for development, 1 replica for production
- **Refresh**: Real-time refresh for immediate search availability
- **Mapping**: Optimized field mappings for search and suggestions

### Query Optimization

- **Multi-match**: Best fields strategy for relevance ranking
- **Filters**: Term and terms filters for efficient RBAC enforcement
- **Highlighting**: Fragment-based highlighting for result previews
- **Pagination**: Efficient offset-based pagination with limits

### Caching Strategy

- **Query Caching**: OpenSearch query result caching
- **Filter Caching**: RBAC filter result caching
- **Suggestion Caching**: Frequent suggestion pattern caching
- **JWT Caching**: Token validation result caching

## Monitoring & Observability

### Health Monitoring

```bash
# Service health check
curl http://localhost:8004/health

# OpenSearch cluster health
curl http://localhost:9200/_cluster/health
```

### Metrics Collection

- **Search Latency**: Query execution time tracking
- **Index Performance**: Document indexing rate and failures
- **RBAC Efficiency**: Permission check performance
- **User Activity**: Search pattern analysis

### Logging

```json
{
  "timestamp": "2025-01-15T14:30:00Z",
  "level": "INFO",
  "user_id": "teacher_123",
  "tenant_id": "district_456",
  "school_id": "elementary_789",
  "operation": "search",
  "query": "reading comprehension",
  "doc_types": ["iep", "assessment"],
  "results_count": 15,
  "took_ms": 23,
  "rbac_filters_applied": ["tenant", "school"]
}
```

## Security Considerations

### Authentication & Authorization

- **JWT Validation**: Secure token verification with signature validation
- **Role Verification**: Comprehensive role-based permission checking
- **Tenant Isolation**: Complete data separation between organizations
- **Audit Logging**: Complete search activity logging for compliance

### Data Protection

- **Result Filtering**: Dynamic result filtering based on permissions
- **Cross-tenant Prevention**: Strict enforcement of tenant boundaries
- **PII Handling**: Secure handling of personally identifiable information
- **Data Minimization**: Return only necessary data fields

### Rate Limiting & DoS Protection

- **Query Limits**: Maximum query complexity and size limits
- **Request Rate**: Per-user and per-tenant rate limiting
- **Resource Protection**: CPU and memory usage monitoring
- **Index Protection**: Prevent unauthorized index modification

## Deployment

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY opensearch/ ./opensearch/

EXPOSE 8004
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
```

### Production Environment

```yaml
# docker-compose.yml
version: "3.8"
services:
  search-svc:
    build: .
    ports:
      - "8004:8004"
    environment:
      - SEARCH_OPENSEARCH_HOST=opensearch
      - SEARCH_OPENSEARCH_PORT=9200
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - opensearch

  opensearch:
    image: opensearchproject/opensearch:2.11.1
    environment:
      - discovery.type=single-node
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=${OPENSEARCH_PASSWORD}
    ports:
      - "9200:9200"
    volumes:
      - opensearch_data:/usr/share/opensearch/data
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: search-svc
spec:
  replicas: 3
  selector:
    matchLabels:
      app: search-svc
  template:
    metadata:
      labels:
        app: search-svc
    spec:
      containers:
        - name: search-svc
          image: aivo/search-svc:latest
          ports:
            - containerPort: 8004
          env:
            - name: SEARCH_OPENSEARCH_HOST
              value: "opensearch-cluster"
            - name: JWT_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: jwt-secret
                  key: secret-key
```

## Troubleshooting

### Common Issues

#### OpenSearch Connection Failed

```bash
# Check OpenSearch status
curl -X GET "localhost:9200/_cluster/health?pretty"

# Check service logs
docker logs search-svc
```

#### JWT Authentication Errors

```bash
# Verify token claims
python -c "
import jwt
token = 'your-jwt-token'
decoded = jwt.decode(token, options={'verify_signature': False})
print(decoded)
"
```

#### Search Results Empty

```bash
# Check index existence
curl -X GET "localhost:9200/_cat/indices?v"

# Check document count
curl -X GET "localhost:9200/aivo_*/_count?pretty"
```

#### RBAC Permission Denied

- Verify user roles in JWT token
- Check school_ids assignment
- Confirm tenant_id matches
- Review permission hierarchy

### Performance Issues

#### Slow Search Queries

- Check index mapping optimization
- Review query complexity and filters
- Monitor OpenSearch cluster performance
- Consider search result caching

#### High Memory Usage

- Optimize OpenSearch heap size
- Review index shard configuration
- Monitor query cache usage
- Consider index lifecycle management

## Advanced Features

### Custom Analyzers

- **IEP Analyzer**: Specialized for educational terminology
- **Assessment Analyzer**: Optimized for psychometric terms
- **Curriculum Analyzer**: Enhanced for academic standards
- **Suggestion Analyzer**: Tuned for auto-complete performance

### Synonym Expansion

```json
{
  "synonyms": [
    "IEP,individualized education program,individual education plan",
    "fractions,rational numbers,parts of a whole",
    "WISC,wechsler intelligence scale for children"
  ]
}
```

### Multi-field Search

- **Title Boosting**: 3x weight for title matches
- **Content Analysis**: 2x weight for content matches
- **Metadata Matching**: Standard weight for metadata fields
- **Fuzzy Tolerance**: Automatic typo correction

This search service provides a robust, secure, and scalable foundation for educational document discovery in the AIVO Virtual Brains ecosystem, enabling efficient access to critical student information while maintaining strict privacy and security controls.
