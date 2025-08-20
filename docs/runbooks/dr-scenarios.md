# Disaster Recovery Scenarios Runbook

## Overview

This runbook defines disaster recovery (DR) scenarios for the AIVO Virtual Brains platform, providing step-by-step procedures to restore service availability within defined Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO).

## Service Level Objectives

- **RPO (Recovery Point Objective)**: ≤ 1 hour
- **RTO (Recovery Time Objective)**: ≤ 2 hours
- **Availability Target**: 99.9% uptime
- **Data Loss Tolerance**: Minimal (≤ 1 hour of data)

## Disaster Categories

### Category 1: Infrastructure Failures

- Single component failures (database, storage, compute)
- Network connectivity issues
- DNS resolution problems

### Category 2: Regional Outages

- AWS region unavailability
- Multi-AZ failures
- Cross-region network partitions

### Category 3: Data Corruption/Loss

- Database corruption
- Storage system failures
- Ransomware attacks

### Category 4: Application Failures

- Software bugs causing data corruption
- Configuration errors
- Security breaches

## DR Scenario 1: PostgreSQL Database Failure

### Impact Assessment

- **Services Affected**: All data-dependent services
- **Expected RTO**: 1 hour
- **Expected RPO**: 15 minutes (incremental backup frequency)

### Detection

```bash
# Automated monitoring alerts
- Database connection failures
- High error rates in application logs
- PostgreSQL service down alerts
```

### Response Procedure

#### Step 1: Immediate Assessment (5 minutes)

```bash
# Check database status
kubectl get pods -n aivo-system -l app=postgresql
kubectl logs -n aivo-system postgresql-0 --tail=100

# Verify backup availability
aws s3 ls s3://aivo-backup-postgres/backup/aivo-postgres/ | tail -10
```

#### Step 2: Activate DR Site (10 minutes)

```bash
# Scale up standby database in DR region
kubectl patch statefulset postgresql -n aivo-system-dr -p '{"spec":{"replicas":1}}'

# Update DNS to point to DR database
aws route53 change-resource-record-sets --hosted-zone-id Z123456789 \
  --change-batch file://dns-failover-postgres.json
```

#### Step 3: Data Recovery (30 minutes)

```bash
# If primary is recoverable, sync recent data
pg_basebackup -h primary-db -D /var/lib/postgresql/data -U replication -v -P

# If primary is lost, restore from backup
pgbackrest restore --stanza=aivo-postgres --type=latest

# Verify data integrity
psql -h dr-postgres -U postgres -c "SELECT count(*) FROM users;"
```

#### Step 4: Application Reconfiguration (10 minutes)

```bash
# Update application config to use DR database
kubectl patch configmap app-config -n aivo-system \
  -p '{"data":{"DATABASE_URL":"postgresql://dr-postgres:5432/aivo"}}'

# Restart application pods
kubectl rollout restart deployment -n aivo-system
```

#### Step 5: Verification (5 minutes)

```bash
# Test application functionality
curl -H "Authorization: Bearer $TOKEN" https://api.aivo.com/health
curl -H "Authorization: Bearer $TOKEN" https://api.aivo.com/users/me

# Monitor error rates
kubectl logs -n aivo-system -l app=api-gateway --tail=100
```

### Rollback Procedure

```bash
# When primary is restored
# 1. Sync data from DR to primary
# 2. Update DNS back to primary
# 3. Scale down DR resources
```

## DR Scenario 2: MinIO Storage System Failure

### Impact Assessment

- **Services Affected**: File upload/download, media services
- **Expected RTO**: 30 minutes
- **Expected RPO**: 24 hours (daily backup)

### Response Procedure

#### Step 1: Immediate Response (5 minutes)

```bash
# Check MinIO cluster status
kubectl get pods -n aivo-system -l app=minio
mc admin info primary-minio

# Verify backup availability
aws s3 ls s3://aivo-backup-minio/minio-data/ | tail -5
```

#### Step 2: Activate Backup Storage (15 minutes)

```bash
# Deploy MinIO in DR mode
kubectl apply -f infra/minio/dr-deployment.yaml

# Restore latest backup
LATEST_BACKUP=$(aws s3 ls s3://aivo-backup-minio/minio-data/ | sort | tail -1 | awk '{print $2}')
aws s3 sync s3://aivo-backup-minio/minio-data/${LATEST_BACKUP} /tmp/minio-restore/

# Upload to DR MinIO
mc mirror /tmp/minio-restore/ dr-minio/
```

#### Step 3: Update Application Configuration (5 minutes)

```bash
# Update MinIO endpoints
kubectl patch configmap minio-config -n aivo-system \
  -p '{"data":{"MINIO_ENDPOINT":"dr-minio.aivo.svc.cluster.local:9000"}}'

# Restart dependent services
kubectl rollout restart deployment -n aivo-system -l component=file-service
```

#### Step 4: Verification (5 minutes)

```bash
# Test file operations
curl -X POST -F "file=@test.pdf" https://api.aivo.com/files/upload
curl https://api.aivo.com/files/test.pdf -o downloaded-test.pdf
```

## DR Scenario 3: OpenSearch Cluster Failure

### Impact Assessment

- **Services Affected**: Search, analytics, logging
- **Expected RTO**: 45 minutes
- **Expected RPO**: 24 hours (daily snapshots)

### Response Procedure

#### Step 1: Assessment (5 minutes)

```bash
# Check cluster health
curl -u admin:password "https://opensearch.local:9200/_cluster/health"

# Check available snapshots
aws s3 ls s3://aivo-backup-opensearch/snapshots/
```

#### Step 2: Deploy DR Cluster (20 minutes)

```bash
# Deploy OpenSearch in DR region
kubectl apply -f infra/opensearch/dr-cluster.yaml

# Wait for cluster to be ready
kubectl wait --for=condition=ready pod -l app=opensearch -n aivo-system-dr --timeout=600s
```

#### Step 3: Restore Data (15 minutes)

```bash
# Setup snapshot repository on DR cluster
curl -u admin:password -X PUT \
  "https://opensearch-dr.local:9200/_snapshot/backup-repo" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "s3",
    "settings": {
      "bucket": "aivo-backup-opensearch",
      "base_path": "snapshots"
    }
  }'

# Restore latest snapshot
LATEST_SNAPSHOT=$(curl -s -u admin:password \
  "https://opensearch-dr.local:9200/_snapshot/backup-repo/_all" | \
  jq -r '.snapshots | sort_by(.start_time_in_millis) | last | .snapshot')

curl -u admin:password -X POST \
  "https://opensearch-dr.local:9200/_snapshot/backup-repo/${LATEST_SNAPSHOT}/_restore"
```

#### Step 4: Application Updates (5 minutes)

```bash
# Update OpenSearch endpoints
kubectl patch configmap opensearch-config -n aivo-system \
  -p '{"data":{"OPENSEARCH_URL":"https://opensearch-dr.local:9200"}}'

# Restart search services
kubectl rollout restart deployment -n aivo-system -l component=search
```

## DR Scenario 4: Complete Regional Failure

### Impact Assessment

- **Services Affected**: All services
- **Expected RTO**: 2 hours
- **Expected RPO**: 1 hour

### Response Procedure

#### Step 1: Emergency Assessment (10 minutes)

```bash
# Check primary region status
aws ec2 describe-regions --region us-east-1
aws rds describe-db-instances --region us-east-1

# Verify DR region readiness
aws eks describe-cluster --name aivo-dr --region us-west-2
```

#### Step 2: DNS Failover (5 minutes)

```bash
# Update Route53 to point to DR region
aws route53 change-resource-record-sets --hosted-zone-id Z123456789 \
  --change-batch file://dr-dns-failover.json

# Verify DNS propagation
dig @8.8.8.8 api.aivo.com
```

#### Step 3: Infrastructure Activation (30 minutes)

```bash
# Scale up EKS cluster in DR region
aws eks update-nodegroup-config \
  --cluster-name aivo-dr \
  --nodegroup-name aivo-dr-nodes \
  --scaling-config minSize=3,maxSize=20,desiredSize=10

# Deploy core infrastructure
kubectl apply -f infra/dr/namespace.yaml
kubectl apply -f infra/dr/postgresql.yaml
kubectl apply -f infra/dr/minio.yaml
kubectl apply -f infra/dr/opensearch.yaml
```

#### Step 4: Data Restoration (60 minutes)

```bash
# Restore PostgreSQL
pgbackrest restore --stanza=aivo-postgres --type=latest

# Restore MinIO data
LATEST_BACKUP=$(aws s3 ls s3://aivo-backup-minio/minio-data/ | sort | tail -1 | awk '{print $2}')
aws s3 sync s3://aivo-backup-minio/minio-data/${LATEST_BACKUP} /mnt/minio-data/

# Restore OpenSearch snapshots
curl -u admin:password -X POST \
  "https://opensearch-dr.local:9200/_snapshot/backup-repo/${LATEST_SNAPSHOT}/_restore"
```

#### Step 5: Application Deployment (30 minutes)

```bash
# Deploy applications in priority order
kubectl apply -f apps/core/
kubectl apply -f apps/api/
kubectl apply -f apps/web/

# Verify deployment status
kubectl get pods -n aivo-system --field-selector=status.phase!=Running
```

#### Step 6: Verification and Monitoring (15 minutes)

```bash
# Run health checks
./scripts/dr-health-check.sh

# Enable monitoring
kubectl apply -f monitoring/dr-alerting.yaml

# Notify stakeholders
curl -X POST "$SLACK_WEBHOOK" \
  -d '{"text":"🚨 DR activation completed. System running in us-west-2."}'
```

## DR Scenario 5: Data Corruption from Ransomware

### Impact Assessment

- **Services Affected**: All data services
- **Expected RTO**: 4 hours
- **Expected RPO**: 24 hours (clean backup before infection)

### Response Procedure

#### Step 1: Immediate Isolation (15 minutes)

```bash
# Isolate affected systems
kubectl patch networkpolicy default-deny -n aivo-system \
  -p '{"spec":{"podSelector":{},"policyTypes":["Ingress","Egress"]}}'

# Stop all write operations
kubectl scale deployment --replicas=0 -n aivo-system -l tier=application

# Preserve evidence
kubectl logs -n aivo-system --all-containers=true > incident-logs.txt
```

#### Step 2: Threat Assessment (30 minutes)

```bash
# Analyze infection scope
grep -r "ransomware\|encrypted\|.locked" /var/log/
find /data -name "*.encrypted" -o -name "README.txt"

# Identify last clean backup
aws s3 ls s3://aivo-backup-postgres/backup/aivo-postgres/ | \
  grep "$(date -d '48 hours ago' +%Y%m%d)"
```

#### Step 3: Clean Environment Rebuild (2 hours)

```bash
# Deploy fresh cluster
terraform apply -var="cluster_name=aivo-clean" \
  -var="region=us-west-2"

# Install base systems with security hardening
kubectl apply -f infra/security/
kubectl apply -f infra/clean-deployment/
```

#### Step 4: Data Restoration from Clean Backup (1.5 hours)

```bash
# Identify last verified clean backup (48+ hours old)
CLEAN_BACKUP="20240818_020000"  # Verified clean backup

# Restore PostgreSQL
pgbackrest restore --stanza=aivo-postgres \
  --type=time --target="2024-08-18 02:00:00"

# Restore MinIO from clean backup
aws s3 sync s3://aivo-backup-minio/minio-data/${CLEAN_BACKUP}/ \
  s3://aivo-clean-minio/

# Restore OpenSearch from clean snapshot
curl -u admin:password -X POST \
  "https://opensearch-clean.local:9200/_snapshot/backup-repo/snapshot_${CLEAN_BACKUP}/_restore"
```

#### Step 5: Security Validation (30 minutes)

```bash
# Run security scans
kubectl apply -f security/malware-scan.yaml
kubectl apply -f security/vulnerability-scan.yaml

# Verify data integrity
./scripts/data-integrity-check.sh

# Update all credentials
./scripts/rotate-all-credentials.sh
```

#### Step 6: Graduated Restoration (15 minutes)

```bash
# Restore services gradually
kubectl scale deployment api-gateway --replicas=1 -n aivo-system
# Wait and verify...
kubectl scale deployment user-service --replicas=2 -n aivo-system
# Continue pattern...
```

## DR Testing and Validation

### Monthly DR Drills

#### Test Schedule

- **Week 1**: Database failover test
- **Week 2**: Storage system recovery test
- **Week 3**: Application-level DR test
- **Week 4**: Full regional failover test

#### Test Execution

```bash
# Automated DR test script
./scripts/dr-test.sh --scenario=database-failover --environment=staging

# Manual verification checklist
- [ ] RTO/RPO objectives met
- [ ] Data integrity verified
- [ ] Application functionality confirmed
- [ ] Monitoring and alerting operational
- [ ] Documentation updated
```

### Metrics and Reporting

#### Key Metrics

```bash
# RTO Measurement
echo "DR activation time: $((end_time - start_time)) seconds"

# RPO Measurement
echo "Data loss window: $((corruption_time - last_backup_time)) seconds"

# Success Rate
echo "DR test success rate: $(successful_tests / total_tests * 100)%"
```

#### Reporting Template

```markdown
## DR Test Report - $(date +%Y-%m-%d)

**Scenario**: Database Failover Test
**Start Time**: 2024-08-20 10:00:00 UTC
**End Time**: 2024-08-20 10:45:00 UTC
**RTO Achieved**: 45 minutes ✅
**RPO Achieved**: 15 minutes ✅

### Issues Identified

- DNS propagation delay (5 minutes)
- Application restart timeout

### Action Items

- [ ] Optimize DNS TTL settings
- [ ] Increase application startup timeout
- [ ] Update runbook procedures
```

## Communication Plan

### Stakeholder Notification

#### Internal Escalation

```bash
# Automated notifications
curl -X POST "$SLACK_WEBHOOK" -d '{
  "text": "🚨 DR Scenario Activated",
  "attachments": [{
    "color": "danger",
    "fields": [
      {"title": "Scenario", "value": "Database Failure", "short": true},
      {"title": "ETA", "value": "60 minutes", "short": true},
      {"title": "Impact", "value": "All services degraded", "short": false}
    ]
  }]
}'

# Executive notification
aws sns publish --topic-arn arn:aws:sns:us-east-1:123456789012:executive-alerts \
  --message "DR activation in progress. RTO target: 2 hours."
```

#### External Communication

```bash
# Status page update
curl -X POST "https://api.statuspage.io/v1/pages/$PAGE_ID/incidents" \
  -H "Authorization: OAuth $STATUS_PAGE_TOKEN" \
  -d '{
    "incident": {
      "name": "Service Degradation - DR Activation",
      "status": "investigating",
      "impact_override": "major"
    }
  }'
```

## Post-Incident Procedures

### Documentation Requirements

- Incident timeline and root cause analysis
- RTO/RPO metrics and compliance assessment
- Lessons learned and improvement recommendations
- Updated runbook procedures

### Review Process

1. **24-hour post-incident review**: Technical team
2. **1-week retrospective**: All stakeholders
3. **1-month follow-up**: Implementation of improvements
4. **Quarterly review**: Overall DR strategy assessment

### Continuous Improvement

- Update runbooks based on lessons learned
- Enhance automation and monitoring
- Regular training and certification
- Technology and process optimization

## Contact Information

### Emergency Response Team

- **Incident Commander**: +1-555-0100
- **Database Team Lead**: +1-555-0101
- **Infrastructure Lead**: +1-555-0102
- **Security Team Lead**: +1-555-0103

### External Contacts

- **AWS Enterprise Support**: 1-800-AWS-SUPPORT
- **Security Incident Hotline**: +1-555-0199
- **Legal/Compliance**: legal@aivo.com
- **Executive Leadership**: exec@aivo.com
