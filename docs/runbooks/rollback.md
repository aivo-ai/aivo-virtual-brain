# AIVO Virtual Brain Rollback Procedures

**Version:** 1.0  
**Last Updated:** August 21, 2025  
**Owner:** SRE Team  
**Stakeholders:** Engineering, Release Management, Support

## 🎯 Overview

This document outlines comprehensive rollback procedures for AIVO Virtual Brain production systems, including emergency rollback triggers, step-by-step procedures, data recovery, and communication protocols.

**Emergency Rollback Time:** < 15 minutes  
**Full System Restore Time:** < 60 minutes  
**Data Recovery Point Objective (RPO):** < 5 minutes  
**Recovery Time Objective (RTO):** < 30 minutes

---

## 🚨 Rollback Decision Matrix

### Immediate Rollback (Execute Within 5 Minutes)

**CRITICAL - Execute rollback immediately:**

1. **Security Incidents**
   - Data breach detected
   - Unauthorized access confirmed
   - Payment data exposure
   - Authentication bypass

2. **Data Corruption/Loss**
   - Student records corrupted
   - Grade data inconsistencies
   - Mass user account issues
   - Payment transaction failures

3. **System Availability Crisis**
   - Service availability < 90% for > 3 minutes
   - Database connectivity failures > 50%
   - Authentication system down
   - Payment processing offline

### Planned Rollback (Coordinate with Team)

**WARNING - Consider rollback within 30 minutes:**

1. **Performance Degradation**
   - Response times > 3000ms p95 consistently
   - Error rates > 2% sustained
   - Database performance issues
   - Memory/CPU exhaustion

2. **Business Impact**
   - Customer complaints spike
   - Revenue processing issues
   - Key feature unavailable
   - Legal/compliance concerns

---

## 🔄 Rollback Procedures

### Phase 1: Emergency Assessment (0-3 Minutes)

#### Immediate Actions

```bash
# 1. Activate incident response
!incident declare "Production Rollback - [REASON]"

# 2. Join war room
# Slack: #incident-response
# Zoom: https://aivo.zoom.us/emergency

# 3. Assess current state
kubectl get pods -n production | grep -v Running
curl -s https://api.aivo.edu/health | jq '.status'
```

#### Decision Tree

```
Is this a security incident?
├─ YES → Execute Emergency Security Rollback (Go to Phase 2A)
└─ NO → Continue assessment

Is data integrity compromised?
├─ YES → Execute Data Protection Rollback (Go to Phase 2B)
└─ NO → Continue assessment

Is system availability < 90%?
├─ YES → Execute Service Rollback (Go to Phase 2C)
└─ NO → Consider gradual rollback (Go to Phase 3)
```

### Phase 2A: Emergency Security Rollback

#### Step 1: Immediate Isolation (< 2 minutes)

```bash
# 1. Isolate production environment
kubectl scale deployment --all --replicas=0 -n production

# 2. Block all external traffic
aws elbv2 modify-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:123456789:targetgroup/aivo-prod-tg \
  --health-check-enabled false

# 3. Activate maintenance mode
kubectl apply -f maintenance-mode.yaml
```

#### Step 2: Secure Systems (< 5 minutes)

```bash
# 1. Rotate all credentials
aws iam update-access-key --status Inactive --access-key-id AKIAIOSFODNN7EXAMPLE
kubectl delete secret --all -n production

# 2. Review access logs
aws logs filter-log-events \
  --log-group-name /aws/apigateway/aivo-prod \
  --start-time $(date -d '1 hour ago' +%s)000

# 3. Snapshot evidence
aws rds create-db-snapshot \
  --db-instance-identifier aivo-prod-primary \
  --db-snapshot-identifier security-incident-$(date +%Y%m%d-%H%M)
```

### Phase 2B: Data Protection Rollback

#### Step 1: Stop All Writes (< 2 minutes)

```bash
# 1. Enable read-only mode
kubectl patch configmap app-config -n production -p '{"data":{"READ_ONLY_MODE":"true"}}'

# 2. Scale down write services
kubectl scale deployment user-service payment-service assessment-service --replicas=0 -n production

# 3. Verify no active transactions
kubectl exec -n production postgres-primary-0 -- psql -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
```

#### Step 2: Restore from Backup (< 10 minutes)

```bash
# 1. Identify last known good backup
aws rds describe-db-snapshots \
  --db-instance-identifier aivo-prod-primary \
  --snapshot-type automated \
  --max-items 5

# 2. Restore database
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier aivo-prod-primary-restore \
  --db-snapshot-identifier aivo-prod-primary-$(date +%Y%m%d)-pre-release

# 3. Update connection strings
kubectl patch configmap database-config -n production -p '{"data":{"DATABASE_URL":"postgresql://aivo-prod-primary-restore.xyz.rds.amazonaws.com:5432/aivo"}}'
```

### Phase 2C: Service Availability Rollback

#### Step 1: Revert to Previous Release (< 5 minutes)

```bash
# 1. Get previous release version
PREVIOUS_RELEASE=$(helm history aivo-platform -n production | awk 'NR==3{print $1}')

# 2. Rollback application
helm rollback aivo-platform $PREVIOUS_RELEASE -n production --timeout 300s

# 3. Verify rollback
kubectl rollout status deployment -n production --timeout=300s
```

#### Step 2: Restore Service Health (< 10 minutes)

```bash
# 1. Restart failed services
kubectl delete pods -l app=failing-service -n production

# 2. Clear problematic data/cache
kubectl exec -n production redis-master-0 -- redis-cli FLUSHALL

# 3. Health check all services
./scripts/health-check-production.sh --detailed
```

### Phase 3: Gradual Rollback

#### Traffic Diversion Method

```bash
# 1. Reduce traffic to new version gradually
# 100% → 50% → 25% → 0%

# Update load balancer weights
aws elbv2 modify-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:123456789:targetgroup/aivo-prod-new \
  --weight 50

# Wait and monitor for 10 minutes
sleep 600

# Continue reducing if issues persist
aws elbv2 modify-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:123456789:targetgroup/aivo-prod-new \
  --weight 25
```

#### Feature Flag Method

```bash
# 1. Disable new features via feature flags
curl -X PATCH https://api.launchdarkly.com/api/v2/flags/aivo-new-features \
  -H "Authorization: api-key-xxx" \
  -d '{"operations": [{"op": "replace", "path": "/environments/production/on", "value": false}]}'

# 2. Monitor impact
./scripts/monitor-feature-rollback.sh
```

---

## 💾 Data Recovery Procedures

### Database Rollback

#### Point-in-Time Recovery

```bash
# 1. Determine recovery point
RECOVERY_TIME="2025-08-21 14:30:00"

# 2. Create point-in-time recovery
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier aivo-prod-primary \
  --target-db-instance-identifier aivo-prod-recovery \
  --restore-time "$RECOVERY_TIME"

# 3. Validate recovered data
kubectl exec -n staging postgres-client -- psql -h aivo-prod-recovery.xyz.rds.amazonaws.com -c "SELECT count(*) FROM users WHERE created_at < '$RECOVERY_TIME';"
```

#### Selective Data Recovery

```bash
# 1. Export specific data from backup
pg_dump -h backup-db.xyz.rds.amazonaws.com \
  --table=grades \
  --table=assessments \
  --where="updated_at >= '2025-08-21 14:00:00'" \
  aivo > recovery_data.sql

# 2. Review and apply selective restore
psql -h aivo-prod-primary.xyz.rds.amazonaws.com aivo < recovery_data.sql
```

### File System Recovery

```bash
# 1. Restore from S3 backup
aws s3 sync s3://aivo-backups/user-uploads/2025-08-21/ /mnt/user-uploads/ --delete

# 2. Restore application logs
aws s3 sync s3://aivo-logs-backup/2025-08-21/ /var/log/aivo/ --delete

# 3. Verify file integrity
find /mnt/user-uploads -type f -exec sha256sum {} \; | diff - /mnt/checksums.txt
```

---

## 📱 Communication During Rollback

### Immediate Notifications (< 5 minutes)

```bash
# Slack notification
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🚨 EMERGENCY ROLLBACK IN PROGRESS\nReason: [SPECIFIC_REASON]\nETA: 15 minutes\nStatus: https://status.aivo.edu"}' \
  $SLACK_EMERGENCY_WEBHOOK

# Email notification to executives
aws ses send-email \
  --source alerts@aivo.edu \
  --destination ToAddresses=ceo@aivo.edu,cto@aivo.edu \
  --message Subject={Data="URGENT: Production Rollback In Progress"},Body={Text={Data="Emergency rollback initiated due to [REASON]. ETA 15 minutes."}}
```

### Status Page Updates

```bash
# Update status page
curl -X POST https://api.statuspage.io/v1/pages/xyz/incidents \
  -H "Authorization: OAuth abc123" \
  -d '{
    "incident": {
      "name": "Service Degradation - Rollback in Progress",
      "status": "investigating",
      "impact_override": "major",
      "body": "We are experiencing technical difficulties and are rolling back to a previous version. Expected resolution in 15 minutes."
    }
  }'
```

### Customer Communication Template

```
🚨 SERVICE ALERT - AIVO Virtual Brain

We are currently experiencing technical difficulties and are implementing immediate fixes.

⚠️ **Status:** Rolling back to previous version
⏱️ **Expected Resolution:** 15 minutes
📊 **Impact:** Temporary service interruption

What we're doing:
- Restoring service to previous stable version
- Investigating root cause
- Monitoring all systems

We sincerely apologize for the inconvenience and will provide updates every 10 minutes.

Latest updates: https://status.aivo.edu
Support: help@aivo.edu
```

---

## ✅ Post-Rollback Validation

### System Health Verification

```bash
# 1. Comprehensive health check
./scripts/full-health-check.sh --production --verbose

# Expected outputs:
# ✅ Database: Healthy (connections: 45/100)
# ✅ Redis: Healthy (memory: 2.1GB/8GB)
# ✅ Services: All 18 services responding
# ✅ Load balancer: Healthy targets: 12/12
# ✅ CDN: Cache hit rate: 94%
```

### Data Integrity Check

```bash
# 1. Verify critical data counts
kubectl exec -n production postgres-primary-0 -- psql -c "
SELECT
  'users' as table_name, count(*) as count FROM users
UNION ALL
SELECT
  'students' as table_name, count(*) as count FROM students
UNION ALL
SELECT
  'grades' as table_name, count(*) as count FROM grades
UNION ALL
SELECT
  'assessments' as table_name, count(*) as count FROM assessments;
"

# 2. Check data consistency
./scripts/data-integrity-check.sh --full
```

### Business Function Testing

```bash
# 1. Test critical user journeys
./scripts/smoke-test-production.sh --critical-path

# Tests:
# ✅ User registration: PASS
# ✅ Login/authentication: PASS
# ✅ Student dashboard: PASS
# ✅ Teacher gradebook: PASS
# ✅ Assessment submission: PASS
# ✅ Payment processing: PASS
```

---

## 📊 Rollback Metrics & SLAs

### Recovery Time Objectives (RTO)

| Incident Type        | Target RTO | Maximum RTO |
| -------------------- | ---------- | ----------- |
| Security Incident    | 5 minutes  | 10 minutes  |
| Data Corruption      | 15 minutes | 30 minutes  |
| Service Availability | 10 minutes | 20 minutes  |
| Performance Issues   | 20 minutes | 45 minutes  |

### Recovery Point Objectives (RPO)

| Data Type      | Target RPO | Maximum RPO |
| -------------- | ---------- | ----------- |
| User accounts  | 1 minute   | 5 minutes   |
| Student grades | 1 minute   | 5 minutes   |
| Payment data   | 30 seconds | 2 minutes   |
| User content   | 5 minutes  | 15 minutes  |

### Success Criteria

**Rollback is considered successful when:**

- [ ] **System availability:** > 99% within 30 minutes
- [ ] **Response times:** < 500ms p95 within 15 minutes
- [ ] **Error rates:** < 0.1% within 10 minutes
- [ ] **Data integrity:** All critical data verified intact
- [ ] **Business functions:** All critical paths operational
- [ ] **Security:** No ongoing security concerns

---

## 🔍 Post-Rollback Analysis

### Immediate Actions (< 2 hours)

1. **Root Cause Analysis Initiation**
   - Collect all relevant logs and metrics
   - Interview team members involved
   - Document timeline of events

2. **Customer Impact Assessment**
   - Count affected users
   - Measure revenue impact
   - Analyze support ticket volume

3. **Communication Followup**
   - Update status page with resolution
   - Send customer notification
   - Brief executive team

### Follow-up Actions (< 24 hours)

1. **Detailed Post-Mortem**
   - Schedule blameless post-mortem
   - Create incident report
   - Identify improvement actions

2. **Process Improvements**
   - Update rollback procedures
   - Enhance monitoring/alerting
   - Improve testing coverage

3. **Team Debrief**
   - Recognize response efforts
   - Discuss lessons learned
   - Plan prevention measures

---

## 📞 Emergency Contacts

### On-Call Escalation

**Level 1 - SRE On-Call**

- Primary: Marcus Rodriguez (+1-555-0124)
- Secondary: Emily Watson (+1-555-0135)
- Escalation time: 5 minutes

**Level 2 - Engineering Lead**

- Primary: Jennifer Liu (+1-555-0125)
- Secondary: Alex Thompson (+1-555-0136)
- Escalation time: 10 minutes

**Level 3 - Executive Team**

- VP Engineering: David Park (+1-555-0137)
- CTO: Sarah Kim (+1-555-0138)
- CEO: Michael Chen (+1-555-0139)

### Vendor Emergency Contacts

**AWS Support**

- Enterprise Support: +1-206-266-4064
- Account Manager: aws-tam@aivo.edu
- TAM: Sarah Wilson (+1-555-0140)

**Database Vendor (PostgreSQL)**

- Enterprise Support: +1-888-333-9200
- Support Portal: https://support.postgresql.org

**CDN Provider (CloudFlare)**

- Emergency Support: +1-888-993-5273
- Account Manager: cf-team@aivo.edu

---

## 📚 Related Documentation

- [Go-Live Checklist](./go-live.md)
- [Incident Response Plan](./incident-response.md)
- [Disaster Recovery Plan](./disaster-recovery.md)
- [Business Continuity Plan](./business-continuity.md)
- [On-Call Schedule](../oncall/schedule.md)

---

**Document Version:** 1.0  
**Next Review Date:** September 21, 2025  
**Owner:** SRE Team  
**Approvers:** VP Engineering, CTO, Release Manager
