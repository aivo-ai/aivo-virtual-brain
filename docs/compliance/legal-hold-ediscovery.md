# Legal Hold & eDiscovery System

## Overview

The Legal Hold and eDiscovery system provides comprehensive compliance capabilities for data preservation, litigation holds, and regulatory requirements. This system ensures that data subject to legal proceedings or investigations is preserved according to legal requirements and can be exported in various formats for discovery purposes.

## Architecture

### Core Components

1. **Legal Hold Service** (`services/legal-hold-svc/`)
   - FastAPI-based microservice
   - PostgreSQL database with comprehensive compliance models
   - RESTful APIs for hold management and eDiscovery exports
   - Background task processing for data preservation

2. **Database Models**
   - `LegalHold`: Core hold definitions and scope parameters
   - `HoldCustodian`: Data custodians responsible for preservation
   - `HoldAffectedEntity`: Specific entities under legal hold
   - `eDiscoveryExport`: Export requests and tracking
   - `ExportItem`: Individual items within exports
   - `HoldAuditLog`: Comprehensive audit trail
   - `ExportAccessLog`: Access tracking for compliance
   - `DataRetentionOverride`: Retention policy suspension

3. **Frontend Interface** (`apps/web/src/pages/compliance/LegalHolds.tsx`)
   - React-based compliance dashboard
   - Legal hold creation and management
   - eDiscovery export tracking
   - Audit log visualization

## Features

### Legal Hold Management

1. **Hold Creation**
   - Flexible scope definitions (tenant, learner, teacher, classroom, time range, custom)
   - Multiple legal bases (litigation, investigation, regulatory, compliance)
   - Automatic custodian notification
   - Immediate data preservation activation

2. **Hold Types and Scopes**

   ```json
   {
     "scope_type": "tenant|learner|teacher|classroom|timerange|custom",
     "scope_parameters": {
       "tenant_id": "uuid",
       "learner_ids": ["uuid"],
       "teacher_ids": ["uuid"],
       "classroom_ids": ["uuid"],
       "start_date": "2025-01-01T00:00:00Z",
       "end_date": "2025-12-31T23:59:59Z",
       "custom_filters": {}
     }
   }
   ```

3. **Data Preservation**
   - Automatic suspension of deletion and retention policies
   - Integration with privacy and audit services
   - Preservation of metadata and system logs
   - Protection of deleted data marked for legal hold

### eDiscovery Exports

1. **Export Formats**
   - **Structured JSON**: Complete data with metadata
   - **PST Archive**: Email-compatible format for legal tools
   - **PDF Reports**: Human-readable summary documents
   - **Native Format**: Original file formats preserved

2. **Export Content Types**
   - Chat messages and conversations
   - Audit logs and system events
   - User-generated files and content
   - System metadata and configuration
   - Deleted data (when legally required)

3. **Chain of Custody**
   - Digital signatures for export integrity
   - Complete access logging
   - Immutable export archives
   - Attorney-verified requests

### Audit and Compliance

1. **Comprehensive Audit Trail**
   - All hold creation, modification, and release events
   - Data access and export activities
   - Retention policy override tracking
   - User notification and acknowledgment logs

2. **Risk Assessment**
   - Automatic risk level calculation
   - Compliance status monitoring
   - Policy violation detection
   - Notification triggers

## API Reference

### Legal Hold Endpoints

```http
# Create legal hold
POST /api/v1/legal-holds
Content-Type: application/json
{
  "title": "Student Records Investigation",
  "description": "Investigation into data handling practices",
  "case_number": "CASE-2025-001",
  "legal_basis": "investigation",
  "scope_type": "tenant",
  "scope_parameters": {"tenant_id": "uuid"},
  "custodian_user_ids": ["uuid1", "uuid2"],
  "notify_custodians": true
}

# List legal holds
GET /api/v1/legal-holds?status=active&page=1&size=50

# Get hold details
GET /api/v1/legal-holds/{hold_id}

# Update hold status
PUT /api/v1/legal-holds/{hold_id}
{
  "status": "released"
}

# Check retention override
GET /api/v1/legal-holds/retention-override?entity_type=chat&entity_id=uuid
```

### eDiscovery Export Endpoints

```http
# Create export
POST /api/v1/ediscovery/{hold_id}/exports
{
  "title": "Q1 2025 Discovery Export",
  "description": "Export for case CASE-2025-001",
  "export_format": "structured_json",
  "include_metadata": true,
  "include_system_logs": true,
  "include_deleted_data": false,
  "data_types": ["chat", "audit", "files"],
  "requesting_attorney": "John Smith, Esq."
}

# List exports for hold
GET /api/v1/ediscovery/{hold_id}/exports

# Get export status
GET /api/v1/ediscovery/exports/{export_id}

# Download export archive
GET /api/v1/ediscovery/exports/{export_id}/download
```

### Audit Endpoints

```http
# Get hold audit logs
GET /api/v1/audit/holds/{hold_id}/logs?risk_level=high&limit=100

# Get export access logs
GET /api/v1/audit/exports/{export_id}/access-logs
```

## Integration Points

### Service Integration

1. **Privacy Service** (`privacy-svc`)
   - Check retention overrides before data deletion
   - Apply legal hold markers to protected data
   - Coordinate with consent management

2. **Audit Service** (`audit-svc`)
   - Stream audit events to legal hold service
   - Include legal hold context in audit logs
   - Preserve audit data under legal hold

3. **Chat Service** (`chat-svc`)
   - Block message deletion for held data
   - Include chat data in eDiscovery exports
   - Maintain conversation metadata

4. **Analytics Service** (`analytics-svc`)
   - Apply data masking exceptions for legal holds
   - Include analytics data in exports
   - Preserve aggregated data patterns

### Database Integration

```sql
-- Check retention override before deletion
SELECT EXISTS(
  SELECT 1 FROM data_retention_overrides
  WHERE entity_type = ? AND entity_id = ?
  AND override_type = 'legal_hold' AND is_active = true
);

-- Mark data for legal hold preservation
INSERT INTO hold_affected_entities (
  hold_id, entity_type, entity_id, preservation_date
) VALUES (?, ?, ?, NOW());
```

## Configuration

### Environment Variables

```bash
# Database
LEGAL_HOLD_DB_URL=postgresql://user:pass@localhost/legal_hold_db
LEGAL_HOLD_DB_POOL_SIZE=20

# S3 Storage for exports
EDISCOVERY_S3_BUCKET=legal-exports-bucket
EDISCOVERY_S3_REGION=us-east-1
EDISCOVERY_STORAGE_CLASS=GLACIER

# Security
LEGAL_HOLD_ENCRYPTION_KEY=base64-encoded-key
EXPORT_SIGNING_KEY=base64-encoded-signing-key

# Integration
PRIVACY_SVC_URL=http://privacy-svc:8000
AUDIT_SVC_URL=http://audit-svc:8000
NOTIFICATION_SVC_URL=http://notification-svc:8000

# Compliance
RETENTION_CHECK_ENABLED=true
AUTO_EXPORT_ENCRYPTION=true
CHAIN_OF_CUSTODY_REQUIRED=true
```

### Docker Configuration

```yaml
# docker-compose.yml
services:
  legal-hold-svc:
    build: ./services/legal-hold-svc
    environment:
      - LEGAL_HOLD_DB_URL=postgresql://postgres:password@postgres:5432/legal_hold_db
      - EDISCOVERY_S3_BUCKET=legal-exports-bucket
      - LEGAL_HOLD_ENCRYPTION_KEY=${LEGAL_HOLD_ENCRYPTION_KEY}
    depends_on:
      - postgres
      - s3-minio
    networks:
      - backend
```

## Security Considerations

### Data Protection

1. **Encryption at Rest**
   - All legal hold data encrypted in database
   - Export archives encrypted with unique keys
   - Key rotation and management

2. **Access Control**
   - Role-based permissions (legal admin, attorney, compliance officer)
   - Multi-factor authentication for sensitive operations
   - Audit trail for all access

3. **Network Security**
   - TLS encryption for all API communications
   - VPN access for export downloads
   - IP allowlisting for compliance users

### Compliance Standards

1. **Legal Requirements**
   - FRCP (Federal Rules of Civil Procedure) compliance
   - International litigation support
   - Regulatory preservation requirements (GDPR, CCPA, FERPA)

2. **Industry Standards**
   - ISO 27001 information security
   - SOC 2 Type II controls
   - NIST Cybersecurity Framework

## Monitoring and Alerting

### Key Metrics

```yaml
# Prometheus metrics
legal_holds_active_total: Number of active legal holds
legal_holds_created_total: Counter of created holds
ediscovery_exports_pending: Number of pending exports
ediscovery_export_size_bytes: Size of export archives
retention_overrides_active: Number of active retention overrides
audit_events_legal_total: Legal hold related audit events
```

### Alerts

1. **Hold Management**
   - New legal hold created
   - Hold released or expired
   - Custodian notification failures

2. **Data Preservation**
   - Retention override conflicts
   - Data deletion attempts on held data
   - Preservation policy violations

3. **Export Process**
   - Export completion or failure
   - Large export size warnings
   - Export access by unauthorized users

## Best Practices

### Legal Hold Implementation

1. **Scope Definition**
   - Be specific but comprehensive in scope parameters
   - Include relevant time ranges and data types
   - Document legal basis clearly

2. **Custodian Management**
   - Notify all relevant custodians immediately
   - Provide clear preservation instructions
   - Track acknowledgment and compliance

3. **Data Preservation**
   - Implement holds before any data operations
   - Monitor for deletion attempts
   - Maintain complete audit trails

### eDiscovery Management

1. **Export Planning**
   - Define export scope carefully
   - Choose appropriate formats for intended use
   - Coordinate with legal counsel

2. **Chain of Custody**
   - Document all export access
   - Maintain export integrity
   - Provide detailed audit trails

3. **Data Security**
   - Encrypt all exports
   - Use secure transfer methods
   - Implement access controls

## Troubleshooting

### Common Issues

1. **Hold Creation Failures**

   ```bash
   # Check database connectivity
   curl http://legal-hold-svc:8000/health

   # Verify scope parameters
   grep "Invalid scope" /var/log/legal-hold-svc.log
   ```

2. **Export Generation Issues**

   ```bash
   # Check S3 connectivity
   aws s3 ls s3://legal-exports-bucket/

   # Monitor export progress
   curl -H "Authorization: Bearer $TOKEN" \
        http://legal-hold-svc:8000/api/v1/ediscovery/exports/$EXPORT_ID
   ```

3. **Retention Override Conflicts**
   ```sql
   -- Check for conflicting overrides
   SELECT * FROM data_retention_overrides
   WHERE entity_id = ? AND is_active = true;
   ```

### Logging

```bash
# View legal hold service logs
docker logs legal-hold-svc

# Check audit events
grep "legal_hold" /var/log/audit-svc.log

# Monitor export progress
tail -f /var/log/ediscovery-exports.log
```

## Testing

### Unit Tests

```bash
# Run legal hold service tests
cd services/legal-hold-svc
pytest tests/ -v --cov=app

# Run frontend tests
cd apps/web
npm test -- LegalHolds.test.tsx
```

### Integration Tests

```bash
# Test hold creation workflow
python tests/integration/test_legal_hold_workflow.py

# Test eDiscovery export process
python tests/integration/test_ediscovery_export.py

# Test retention override integration
python tests/integration/test_retention_integration.py
```

### Load Testing

```bash
# Test export performance
k6 run tests/performance/ediscovery-export-load.js

# Test concurrent hold operations
k6 run tests/performance/legal-hold-concurrency.js
```

## Future Enhancements

### Planned Features

1. **Advanced Analytics**
   - Hold impact analysis
   - Cost tracking and optimization
   - Compliance risk scoring

2. **Integration Expansion**
   - Third-party legal tools integration
   - Cloud storage provider support
   - Advanced search capabilities

3. **Automation**
   - Auto-hold triggers based on litigation alerts
   - Intelligent scope recommendations
   - Automated compliance reporting

### Roadmap

- **Q2 2025**: Advanced export formats and third-party integrations
- **Q3 2025**: AI-powered scope optimization and risk assessment
- **Q4 2025**: Full compliance automation and reporting suite
