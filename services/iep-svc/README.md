# IEP GraphQL Service Documentation

# S1-11 Implementation - Individual Education Program Management API

## Overview

The IEP (Individual Education Program) GraphQL Service provides a comprehensive API for managing Individual Education Programs with advanced collaborative editing capabilities and electronic signature workflows. This service is built using Strawberry GraphQL, FastAPI, and PostgreSQL with CRDT (Conflict-free Replicated Data Types) support for real-time collaboration.

## Features

### Core Functionality

- **IEP Document Management**: Create, read, update, and manage IEP documents
- **Real-time Collaboration**: CRDT-based collaborative editing with conflict resolution
- **Electronic Signatures**: Secure e-signature workflow with legal compliance
- **Evidence Management**: Attach and manage supporting documentation
- **Version Control**: Complete version history and audit trails
- **Status Workflows**: Draft → In Review → Active → Archived lifecycle

### Technical Architecture

- **GraphQL API**: Strawberry GraphQL with type-safe schema
- **Real-time Updates**: WebSocket subscriptions for live collaboration
- **CRDT Engine**: Operational Transform for conflict-free editing
- **PostgreSQL**: Robust data persistence with JSON fields for CRDT state
- **FastAPI**: High-performance async web framework
- **Docker Ready**: Containerized deployment with health checks

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+ (for CRDT state management)

### Installation

1. **Clone and setup the service:**

```bash
cd services/iep-svc
pip install -r requirements.txt
```

2. **Configure environment variables:**

```bash
cp .env.example .env
# Edit .env with your database and Redis connections
```

3. **Run database migrations:**

```bash
alembic upgrade head
```

4. **Start the service:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

5. **Access GraphQL Playground:**
   - Open http://localhost:8000/graphql
   - Explore the interactive API documentation

## API Documentation

### Core Types

#### IEP Document

```graphql
type IEP {
  id: ID!
  studentId: String!
  tenantId: String!
  title: String!
  status: IEPStatus!
  sections: [IEPSection!]!
  signatures: [ESignature!]!
  evidenceAttachments: [EvidenceAttachment!]!
  # ... additional fields
}
```

#### IEP Section with CRDT Support

```graphql
type IEPSection {
  id: ID!
  sectionType: IEPSectionType!
  title: String!
  content: String!
  operationCounter: Int! # CRDT conflict resolution
  isLocked: Boolean!
  # ... additional fields
}
```

### Key Operations

#### Create IEP

```graphql
mutation CreateIEP {
  createIep(
    input: {
      studentId: "student_123"
      tenantId: "district_456"
      title: "2024-2025 IEP for John Doe"
      academicYear: "2024-2025"
      gradeLevel: "3rd"
      signatureRequiredRoles: ["parent_guardian", "teacher", "case_manager"]
    }
  ) {
    success
    message
    iep {
      id
      status
      sections {
        id
        sectionType
        title
      }
    }
    errors
  }
}
```

#### Collaborative Section Editing

```graphql
mutation UpsertSection {
  upsertSection(input: {
    iepId: "iep_789"
    sectionType: ANNUAL_GOALS
    title: "Annual Goals and Objectives"
    content: "Student will improve reading comprehension by 25%..."
    crdtOperations: [{
      operationType: INSERT
      position: 45
      content: " through guided reading strategies"
      vectorClock: {"client1": 5, "client2": 3}
      clientId: "client1"
      timestamp: "2025-01-15T14:30:00Z"
    }]
  }) {
    success
    section {
      id
      content
      operationCounter
    }
    errors
  }
}
```

#### Real-time Subscriptions

```graphql
subscription IEPUpdates {
  iepUpdated(iepId: "iep_789") {
    eventType
    sectionId
    updatedBy
    timestamp
    metadata
  }
}
```

### Section Types

The service supports comprehensive IEP section types:

- `STUDENT_INFO`: Student demographics and contact information
- `PRESENT_LEVELS`: Current academic and functional performance
- `ANNUAL_GOALS`: Goals and short-term objectives
- `SERVICES`: Special education and related services
- `SUPPLEMENTARY_AIDS`: Additional supports and accommodations
- `PROGRAM_MODIFICATIONS`: Curriculum and instruction modifications
- `ASSESSMENT_ACCOMMODATIONS`: Testing accommodations
- `TRANSITION_SERVICES`: Post-secondary transition planning
- `BEHAVIOR_PLAN`: Behavior intervention strategies
- `ESY_SERVICES`: Extended school year services

### Status Workflow

```
DRAFT → IN_REVIEW → ACTIVE → ARCHIVED
           ↓
       DECLINED (can return to DRAFT)
```

## Collaborative Editing

The service implements a sophisticated CRDT (Conflict-free Replicated Data Types) engine for real-time collaborative editing:

### CRDT Operations

- **INSERT**: Add text at position
- **DELETE**: Remove text at position
- **UPDATE**: Modify existing text
- **RETAIN**: Keep existing text unchanged

### Conflict Resolution

- Vector clocks for operation ordering
- Operational Transform for conflict resolution
- Automatic state synchronization across clients
- Persistent operation logs for audit trails

### Usage Example

```python
# Multiple users can edit simultaneously
# Operations are automatically resolved and synchronized

# User A inserts text at position 10
operation_a = {
    "type": "INSERT",
    "position": 10,
    "content": "additional text",
    "vector_clock": {"client_a": 5},
    "client_id": "client_a"
}

# User B deletes text at position 15 (concurrent operation)
operation_b = {
    "type": "DELETE",
    "position": 15,
    "length": 8,
    "vector_clock": {"client_b": 3},
    "client_id": "client_b"
}

# CRDT engine automatically resolves conflicts and maintains consistency
```

## Electronic Signatures

### Signature Workflow

1. **Request Signatures**: Send signature requests to required parties
2. **Email Notifications**: Automated email invitations with secure tokens
3. **Signature Collection**: Secure signature capture with audit trails
4. **Legal Compliance**: Full audit logs, IP tracking, device fingerprinting
5. **Completion**: Automatic status updates and notifications

### Signature Request

```graphql
mutation RequestSignature {
  requestSignature(
    input: {
      iepId: "iep_789"
      signerEmails: ["parent@example.com", "teacher@school.edu"]
      customMessage: "Please review and sign the IEP for John Doe"
      expiresAt: "2025-02-15T23:59:59Z"
    }
  ) {
    success
    message
    signature {
      id
      status
      signerEmail
    }
    errors
  }
}
```

## Evidence Management

Attach supporting documentation to IEPs:

```graphql
mutation AttachEvidence {
  attachEvidence(
    input: {
      iepId: "iep_789"
      filename: "psychological_assessment.pdf"
      contentType: "application/pdf"
      fileSize: 2048000
      evidenceType: "assessment_report"
      description: "Comprehensive psychological assessment results"
      tags: ["assessment", "psychology", "baseline"]
      isConfidential: true
    }
  ) {
    success
    attachment {
      id
      filename
      evidenceType
    }
    uploadUrl # Pre-signed URL for file upload
    errors
  }
}
```

## Testing

### Run the Test Suite

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_graphql_iep.py -v  # GraphQL API tests
pytest tests/test_crdt_engine.py -v  # CRDT collaborative editing tests
pytest tests/test_signature_service.py -v  # E-signature workflow tests
```

### Test Coverage

- GraphQL Query/Mutation/Subscription operations
- CRDT collaborative editing scenarios
- Electronic signature workflows
- Error handling and validation
- Real-time subscription events
- Complete IEP lifecycle workflows

## Deployment

### Docker Deployment

```bash
# Build the container
docker build -t iep-service .

# Run with PostgreSQL and Redis
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/iep_db

# Redis (for CRDT state)
REDIS_URL=redis://localhost:6379

# JWT Configuration
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# E-signature Configuration
SIGNATURE_SECRET_KEY=your-signature-secret
SENDGRID_API_KEY=your-sendgrid-key

# File Storage
AWS_S3_BUCKET=iep-evidence-bucket
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

## Performance Considerations

- **Database Indexing**: Strategic indexes on foreign keys and query patterns
- **Connection Pooling**: SQLAlchemy connection pooling for scalability
- **Caching**: Redis caching for CRDT state and session data
- **Async Operations**: Full async/await support for high concurrency
- **GraphQL Optimization**: DataLoader pattern for efficient N+1 query resolution

## Security Features

- **Authentication**: JWT-based authentication with role-based access
- **Authorization**: Fine-grained permissions for IEP access
- **Data Encryption**: Encrypted sensitive fields in database
- **Audit Logging**: Comprehensive audit trails for all operations
- **Input Validation**: Strict input validation and sanitization
- **Rate Limiting**: API rate limiting to prevent abuse

## Monitoring & Observability

- **Health Checks**: Built-in health check endpoints
- **Metrics**: Prometheus metrics for monitoring
- **Logging**: Structured logging with request tracing
- **Error Tracking**: Comprehensive error handling and reporting

## API Schema

The complete GraphQL schema is available at:

- **Schema Definition**: `/docs/api/graphql/iep.graphql`
- **Interactive Playground**: `http://localhost:8000/graphql`
- **Schema Documentation**: Auto-generated from SDL

## Support & Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

### Code Style

- **Formatting**: Black code formatter
- **Linting**: Flake8 with custom rules
- **Type Hints**: MyPy type checking
- **Import Sorting**: isort for consistent imports

This service provides a production-ready, scalable solution for IEP management with advanced collaborative features and legal compliance capabilities.
