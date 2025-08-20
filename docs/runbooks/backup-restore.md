# Backup and Restore Runbook

## Overview

This runbook covers the backup and restore procedures for the AIVO Virtual Brains platform. The system implements automated, encrypted backups with KMS integration and daily verification.

## Architecture

### Backup Components

- **PostgreSQL**: pgBackRest with incremental/full backups
- **MinIO**: Object storage sync to S3
- **OpenSearch**: Snapshot repositories to S3
- **Encryption**: AWS KMS with customer-managed keys
- **Storage**: S3 with Standard-IA storage class

### Backup Schedule

| Component    | Type         | Schedule                    | Retention      |
| ------------ | ------------ | --------------------------- | -------------- |
| PostgreSQL   | Incremental  | Daily 2:00 AM UTC           | 14 days        |
| PostgreSQL   | Full         | Weekly (Sunday 1:00 AM UTC) | 7 full backups |
| MinIO        | Full Sync    | Daily 3:00 AM UTC           | 30 days        |
| OpenSearch   | Snapshot     | Daily 4:00 AM UTC           | 30 days        |
| Verification | Restore Test | Daily 6:00 AM UTC           | N/A            |

## Service Level Objectives (SLOs)

- **Recovery Point Objective (RPO)**: ≤ 1 hour
- **Recovery Time Objective (RTO)**: ≤ 2 hours
- **Backup Success Rate**: ≥ 99.5%
- **Verification Success Rate**: ≥ 99%

## Prerequisites

### Required Tools

```bash
# Install required CLI tools
curl -LO https://github.com/pgbackrest/pgbackrest/releases/latest/download/pgbackrest
chmod +x pgbackrest && sudo mv pgbackrest /usr/local/bin/

# MinIO Client
curl -LO https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc && sudo mv mc /usr/local/bin/

# AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install
```

### Environment Setup

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# KMS Key ID for encryption
export KMS_KEY_ID="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

## Backup Procedures

### PostgreSQL Backup

#### Manual Full Backup

```bash
# Set environment variables
export PGBACKREST_STANZA="aivo-postgres"
export BACKUP_BUCKET="aivo-backup-postgres"
export ENCRYPTION_KEY_CMD="aws kms decrypt --ciphertext-blob fileb://key.enc --output text --query Plaintext | base64 -d"

# Execute backup script
cd /path/to/aivo-virtual-brains/infra/backup
chmod +x pgbackrest.sh
BACKUP_TYPE=full ./pgbackrest.sh
```

#### Manual Incremental Backup

```bash
# Execute incremental backup
BACKUP_TYPE=incr ./pgbackrest.sh
```

#### Verify Backup Status

```bash
# Check backup information
pgbackrest info --stanza=aivo-postgres --output=json | jq '.'

# List backups in S3
aws s3 ls s3://aivo-backup-postgres/backup/aivo-postgres/ --recursive
```

### MinIO Backup

#### Manual Backup

```bash
# Set environment variables
export MINIO_SOURCE_ENDPOINT="http://minio.aivo.svc.cluster.local:9000"
export MINIO_SOURCE_ACCESS_KEY="your-minio-access-key"
export MINIO_SOURCE_SECRET_KEY="your-minio-secret-key"
export BACKUP_TARGET_BUCKET="aivo-backup-minio"

# Execute backup
cd /path/to/aivo-virtual-brains/infra/backup
chmod +x minio-sync.sh
./minio-sync.sh
```

#### Verify MinIO Backup

```bash
# List backup contents
aws s3 ls s3://aivo-backup-minio/minio-data/ --recursive

# Check metadata
aws s3 ls s3://aivo-backup-minio/metadata/minio/ --recursive
```

### OpenSearch Backup

#### Manual Snapshot

```bash
# Set environment variables
export OPENSEARCH_ENDPOINT="https://opensearch.aivo.svc.cluster.local:9200"
export OPENSEARCH_USERNAME="admin"
export OPENSEARCH_PASSWORD="your-password"
export SNAPSHOT_BUCKET="aivo-backup-opensearch"

# Execute snapshot
cd /path/to/aivo-virtual-brains/infra/backup
chmod +x os-snapshots.sh
./os-snapshots.sh
```

#### Verify Snapshot Status

```bash
# List snapshots via API
curl -u admin:password -X GET \
  "https://opensearch.aivo.svc.cluster.local:9200/_snapshot/aivo-snapshots/_all" | jq '.'

# Check S3 storage
aws s3 ls s3://aivo-backup-opensearch/snapshots/ --recursive
```

## Restore Procedures

### PostgreSQL Restore

#### Point-in-Time Recovery (PITR)

```bash
# Stop PostgreSQL service
sudo systemctl stop postgresql

# Clear data directory (CAUTION: This deletes current data)
sudo rm -rf /var/lib/postgresql/15/main/*

# Restore to specific point in time
pgbackrest restore \
  --stanza=aivo-postgres \
  --type=time \
  --target="2024-08-20 12:00:00" \
  --target-action=promote

# Start PostgreSQL
sudo systemctl start postgresql

# Verify restoration
psql -h localhost -U postgres -c "SELECT now(), pg_is_in_recovery();"
```

#### Latest Backup Restore

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Restore latest backup
pgbackrest restore --stanza=aivo-postgres

# Start PostgreSQL
sudo systemctl start postgresql
```

#### Restore to Staging Environment

```bash
# Restore to staging database
pgbackrest restore \
  --stanza=aivo-postgres \
  --pg1-path=/var/lib/postgresql/staging \
  --recovery-option="primary_conninfo=host=staging-postgres port=5432"

# Update staging configuration
echo "port = 5433" >> /var/lib/postgresql/staging/postgresql.conf
```

### MinIO Restore

#### Full Bucket Restore

```bash
# Configure MinIO client for target
mc alias set restore-target http://minio-restore.local:9000 access-key secret-key

# List available backups
aws s3 ls s3://aivo-backup-minio/minio-data/

# Choose backup date and restore
BACKUP_DATE="20240820_020000"
aws s3 sync s3://aivo-backup-minio/minio-data/${BACKUP_DATE}/ /tmp/restore-staging/

# Upload to target MinIO
mc mirror /tmp/restore-staging/ restore-target/bucket-name/
```

#### Selective File Restore

```bash
# Download specific files
aws s3 cp s3://aivo-backup-minio/minio-data/20240820_020000/user-data/file.pdf \
  /tmp/restore-file.pdf

# Upload to MinIO
mc cp /tmp/restore-file.pdf restore-target/user-data/file.pdf
```

### OpenSearch Restore

#### Full Index Restore

```bash
# Close target indices
curl -u admin:password -X POST \
  "https://opensearch-restore.local:9200/index-name/_close"

# Restore snapshot
curl -u admin:password -X POST \
  "https://opensearch-restore.local:9200/_snapshot/aivo-snapshots/snapshot_20240820_040000/_restore" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": "index-name",
    "ignore_unavailable": true,
    "include_global_state": false
  }'

# Monitor restore progress
curl -u admin:password -X GET \
  "https://opensearch-restore.local:9200/_recovery/index-name?detailed=true"
```

#### Partial Restore

```bash
# Restore specific indices with renaming
curl -u admin:password -X POST \
  "https://opensearch-restore.local:9200/_snapshot/aivo-snapshots/snapshot_20240820_040000/_restore" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": "logs-*",
    "rename_pattern": "logs-(.+)",
    "rename_replacement": "restored-logs-$1",
    "include_global_state": false
  }'
```

## Monitoring and Alerting

### Backup Status Monitoring

```bash
# Check CronJob status
kubectl get cronjobs -n aivo-system

# View recent job executions
kubectl get jobs -n aivo-system --sort-by=.metadata.creationTimestamp

# Check job logs
kubectl logs -n aivo-system job/postgresql-backup-<timestamp>
```

### Alert Conditions

- Backup job failure (any component)
- Backup duration exceeds threshold
- Verification failure
- Storage capacity warnings
- KMS key access issues

### Prometheus Metrics

```promql
# Backup success rate
rate(backup_jobs_total{status="success"}[24h]) / rate(backup_jobs_total[24h])

# Backup duration
histogram_quantile(0.95, backup_duration_seconds_bucket)

# Storage utilization
s3_bucket_size_bytes{bucket=~"aivo-backup-.*"}
```

## Troubleshooting

### Common Issues

#### PostgreSQL Backup Failures

```bash
# Check pgBackRest logs
tail -f /var/log/pgbackrest/aivo-postgres-backup.log

# Verify stanza configuration
pgbackrest check --stanza=aivo-postgres

# Test repository access
pgbackrest info --stanza=aivo-postgres
```

#### MinIO Sync Issues

```bash
# Check MinIO connectivity
mc admin info source

# Verify S3 permissions
aws s3 ls s3://aivo-backup-minio

# Check disk space
df -h /tmp
```

#### OpenSearch Snapshot Problems

```bash
# Check cluster health
curl -u admin:password "https://opensearch.local:9200/_cluster/health"

# Verify repository settings
curl -u admin:password "https://opensearch.local:9200/_snapshot/aivo-snapshots"

# Check snapshot status
curl -u admin:password "https://opensearch.local:9200/_snapshot/aivo-snapshots/_status"
```

### Recovery Scenarios

#### Database Corruption

1. Stop application services
2. Restore from latest full backup
3. Apply incremental backups up to corruption point
4. Verify data integrity
5. Restart services

#### Storage System Failure

1. Provision new storage infrastructure
2. Restore all components from backups
3. Update configuration with new endpoints
4. Verify system functionality
5. Resume normal operations

#### Partial Data Loss

1. Identify affected data scope
2. Restore affected components to staging
3. Extract required data
4. Import into production system
5. Verify data consistency

## Compliance and Auditing

### Backup Verification

- Daily automated restore tests
- Monthly full system restore drills
- Quarterly disaster recovery exercises
- Annual backup strategy review

### Documentation Requirements

- Backup completion logs
- Restore test results
- RTO/RPO compliance reports
- Security audit trails

### Retention Policies

- Operational backups: 30 days
- Compliance backups: 7 years
- Audit logs: 3 years
- Disaster recovery documentation: 5 years

## Contact Information

### Escalation Path

1. **Level 1**: Data Reliability Engineering Team
2. **Level 2**: Infrastructure Engineering Manager
3. **Level 3**: CTO / VP Engineering

### Emergency Contacts

- **On-call Engineer**: +1-555-0123
- **Backup Infrastructure**: +1-555-0124
- **AWS Support**: Enterprise Support Portal
- **Security Team**: security@aivo.com
