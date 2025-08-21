# AIVO Virtual Brain On-Call Schedule

**Version:** 1.0  
**Last Updated:** August 21, 2025  
**Owner:** SRE Team  
**Next Review:** September 21, 2025

## 🎯 Overview

This document outlines the on-call schedule, responsibilities, escalation procedures, and operational guidelines for AIVO Virtual Brain production systems support.

**On-Call Coverage:** 24/7/365  
**Response Time SLA:** < 15 minutes  
**Escalation Time:** 30 minutes maximum  
**Rotation Period:** 1 week per engineer

---

## 📅 Current On-Call Rotation

### Q4 2025 Schedule

| Week         | Primary On-Call  | Secondary On-Call | Escalation Lead  |
| ------------ | ---------------- | ----------------- | ---------------- |
| Aug 18-24    | Marcus Rodriguez | Emily Watson      | Jennifer Liu     |
| Aug 25-31    | Emily Watson     | Alex Thompson     | David Park       |
| Sep 1-7      | Alex Thompson    | Jennifer Liu      | Marcus Rodriguez |
| Sep 8-14     | Jennifer Liu     | Marcus Rodriguez  | Emily Watson     |
| Sep 15-21    | Marcus Rodriguez | Emily Watson      | Alex Thompson    |
| Sep 22-28    | Emily Watson     | Alex Thompson     | Jennifer Liu     |
| Sep 29-Oct 5 | Alex Thompson    | Jennifer Liu      | David Park       |

### Holiday Coverage

**Labor Day Weekend (Aug 30 - Sep 2, 2025)**

- Primary: Emily Watson
- Secondary: Marcus Rodriguez
- Holiday Escalation: David Park (VP Engineering)

**Thanksgiving (Nov 27-29, 2025)**

- Primary: Jennifer Liu
- Secondary: Alex Thompson
- Holiday Escalation: Sarah Kim (CTO)

---

## 👥 On-Call Team

### Primary On-Call Engineers

#### Marcus Rodriguez - Senior SRE

- **Experience:** 5 years SRE, 3 years with AIVO
- **Specialties:** Kubernetes, Database Performance, Security
- **Contact:**
  - Phone: +1-555-0124
  - Slack: @marcus.rodriguez
  - Email: marcus.rodriguez@aivo.edu
- **Timezone:** EST (UTC-5)
- **Backup Contact:** Jessica Rodriguez (spouse) +1-555-0124

#### Emily Watson - Senior Platform Engineer

- **Experience:** 4 years Platform Engineering, 2 years with AIVO
- **Specialties:** AWS Infrastructure, Monitoring, CI/CD
- **Contact:**
  - Phone: +1-555-0135
  - Slack: @emily.watson
  - Email: emily.watson@aivo.edu
- **Timezone:** PST (UTC-8)
- **Backup Contact:** Michael Watson (partner) +1-555-0144

#### Alex Thompson - DevOps Lead

- **Experience:** 6 years DevOps, 4 years with AIVO
- **Specialties:** Network Architecture, Security, Automation
- **Contact:**
  - Phone: +1-555-0136
  - Slack: @alex.thompson
  - Email: alex.thompson@aivo.edu
- **Timezone:** CST (UTC-6)
- **Backup Contact:** Alex Thompson Sr. (father) +1-555-0146

#### Jennifer Liu - Senior Backend Engineer

- **Experience:** 7 years Backend Development, 3 years with AIVO
- **Specialties:** API Design, Database Architecture, Performance
- **Contact:**
  - Phone: +1-555-0125
  - Slack: @jennifer.liu
  - Email: jennifer.liu@aivo.edu
- **Timezone:** EST (UTC-5)
- **Backup Contact:** David Liu (spouse) +1-555-0145

### Escalation Contacts

#### David Park - VP Engineering

- **Contact:**
  - Phone: +1-555-0137
  - Email: david.park@aivo.edu
  - Slack: @david.park
- **Escalation Level:** Level 2 (30 minutes)

#### Sarah Kim - CTO

- **Contact:**
  - Phone: +1-555-0138
  - Email: sarah.kim@aivo.edu
  - Slack: @sarah.kim
- **Escalation Level:** Level 3 (60 minutes)

#### Michael Chen - CEO

- **Contact:**
  - Phone: +1-555-0139
  - Email: michael.chen@aivo.edu
  - Slack: @michael.chen
- **Escalation Level:** Level 4 (Major incidents only)

---

## 🚨 On-Call Responsibilities

### Primary On-Call Engineer

#### During Business Hours (8 AM - 6 PM Local Time)

1. **Alert Response**
   - Acknowledge all alerts within 5 minutes
   - Begin investigation within 10 minutes
   - Provide initial status update within 15 minutes

2. **Incident Management**
   - Lead incident response
   - Coordinate with engineering teams
   - Communicate with stakeholders
   - Document all actions taken

3. **Preventive Monitoring**
   - Review system health dashboards hourly
   - Check backup status daily
   - Monitor security alerts
   - Verify monitoring system health

#### During Off-Hours (6 PM - 8 AM, Weekends, Holidays)

1. **Critical Alert Response**
   - Respond to P0/P1 alerts within 15 minutes
   - Begin mitigation within 30 minutes
   - Escalate if needed within 30 minutes

2. **Non-Critical Issues**
   - Acknowledge P2/P3 alerts within 1 hour
   - Document for business hours follow-up
   - Take action if escalation risk exists

### Secondary On-Call Engineer

1. **Backup Response**
   - Be available if primary is unreachable
   - Support complex incident resolution
   - Provide technical expertise as needed

2. **Handoff Support**
   - Available during shift transitions
   - Assist with knowledge transfer
   - Cover planned primary absences

---

## 📱 Alert Channels & Tools

### Primary Communication Channels

#### PagerDuty Integration

- **Service:** AIVO Production Systems
- **Escalation Policy:** Primary → Secondary → VP Eng → CTO
- **Response Time:** 15 minutes per level
- **Phone Numbers:** All on-call engineers configured

#### Slack Channels

- **#incident-response** - Active incident coordination
- **#alerts-production** - Automated alert notifications
- **#on-call-handoff** - Shift change coordination
- **#sre-team** - Team communication and updates

#### Monitoring Tools

- **Grafana:** <https://grafana.aivo.edu/dashboards>
- **Datadog:** <https://app.datadoghq.com/dashboard/aivo-prod>
- **Sentry:** <https://sentry.io/organizations/aivo/issues>
- **AWS CloudWatch:** <https://console.aws.amazon.com/cloudwatch>

### Emergency Conference Bridge

- **Zoom Room:** <https://aivo.zoom.us/j/emergency>
- **Meeting ID:** 123-456-7890
- **Passcode:** aivo2025
- **Available:** 24/7 for incident response

---

## ⚡ Escalation Procedures

### Level 1: Primary On-Call (0-15 minutes)

**Trigger:** Alert fired
**Actions:**

- Acknowledge alert in PagerDuty
- Join #incident-response Slack channel
- Begin initial investigation
- Update stakeholders on status

### Level 2: Secondary On-Call (15-30 minutes)

**Trigger:** Primary unreachable OR complex incident
**Actions:**

- Secondary joins incident response
- Parallel investigation and resolution
- Coordinate team resources
- Consider expert escalation

### Level 3: Engineering Leadership (30-60 minutes)

**Trigger:** No progress OR major impact
**Actions:**

- VP Engineering joins response
- Resource allocation decisions
- Executive communication
- Customer impact assessment

### Level 4: Executive Team (60+ minutes)

**Trigger:** Extended outage OR security incident
**Actions:**

- CTO/CEO involvement
- External communication decisions
- Legal/compliance consultation
- Media/PR coordination

### Auto-Escalation Triggers

**Immediate Executive Escalation:**

- Security breach confirmed
- Data loss detected
- Revenue impact > $50,000/hour
- Customer data exposure
- Legal/regulatory violation

---

## 📊 On-Call Metrics & SLAs

### Response Time Targets

| Alert Priority | Acknowledgment | Initial Response  | Resolution Target |
| -------------- | -------------- | ----------------- | ----------------- |
| P0 - Critical  | 5 minutes      | 15 minutes        | 1 hour            |
| P1 - High      | 15 minutes     | 30 minutes        | 4 hours           |
| P2 - Medium    | 1 hour         | 2 hours           | 24 hours          |
| P3 - Low       | 4 hours        | Next business day | 72 hours          |

### Service Level Objectives

**System Availability:** 99.9% uptime

- Maximum downtime: 8.77 hours/year
- Target downtime: < 4 hours/year

**Response Performance:**

- Alert acknowledgment: > 95% within SLA
- Incident resolution: > 90% within target
- Escalation adherence: 100% compliance

### On-Call Health Metrics

**Engineer Workload:**

- Maximum alerts per week: 50
- Target mean time to acknowledge: < 10 minutes
- Burnout prevention: No more than 2 consecutive weeks

**System Health:**

- False positive rate: < 5%
- Alert coverage: > 95% of incidents
- Escalation rate: < 20% of incidents

---

## 🛠️ On-Call Preparation

### Pre-Shift Checklist

**24 hours before shift:**

- [ ] Review system health and recent changes
- [ ] Check upcoming deployments/maintenance
- [ ] Verify contact information is current
- [ ] Test PagerDuty notification delivery
- [ ] Review recent incident reports

**Start of shift:**

- [ ] Connect to VPN and verify access
- [ ] Check all monitoring dashboards
- [ ] Review active alerts and ongoing issues
- [ ] Attend handoff meeting with previous on-call
- [ ] Update Slack status to "On-Call"

### Required Access & Tools

**Infrastructure Access:**

- AWS Console with emergency access
- Kubernetes cluster admin privileges
- Database read/write access
- Monitoring system admin access

**Communication Tools:**

- PagerDuty mobile app configured
- Slack with push notifications enabled
- Zoom client ready for conference calls
- Corporate VPN configured

**Documentation Access:**

- Production runbooks and procedures
- Architecture diagrams and documentation
- Emergency contact information
- Escalation and communication procedures

---

## 📞 Shift Handoff Procedures

### Handoff Meeting Schedule

**Weekday Handoffs:** 8:00 AM local time (both engineers)
**Weekend Handoffs:** Friday 5:00 PM → Monday 8:00 AM

### Handoff Checklist

**Outgoing Engineer:**

- [ ] **System Status:** Current health and performance
- [ ] **Active Issues:** Ongoing incidents or concerns
- [ ] **Recent Changes:** Deployments, configurations, fixes
- [ ] **Planned Work:** Scheduled maintenance or updates
- [ ] **Escalations:** Any executive or vendor communications
- [ ] **Follow-ups:** Actions needed during next shift

**Incoming Engineer:**

- [ ] **Review Notes:** Read handoff documentation
- [ ] **Verify Access:** Test all systems and tools
- [ ] **Check Alerts:** Review current monitoring status
- [ ] **Confirm Understanding:** Ask questions about ongoing issues
- [ ] **Update Status:** Set Slack/PagerDuty to active on-call

### Handoff Documentation Template

```text
=== ON-CALL HANDOFF ===
Date: YYYY-MM-DD
Outgoing: [Name]
Incoming: [Name]

SYSTEM STATUS:
- Overall health: [Green/Yellow/Red]
- Active alerts: [Number and summary]
- Performance: [Any concerns]

ONGOING ISSUES:
- [Issue 1]: [Status and next steps]
- [Issue 2]: [Status and next steps]

RECENT CHANGES:
- [Change 1]: [Impact and monitoring]
- [Change 2]: [Impact and monitoring]

UPCOMING:
- [Scheduled maintenance]
- [Planned deployments]
- [Known issues to watch]

ESCALATIONS:
- [Any active escalations]
- [Executive communications]

FOLLOW-UP REQUIRED:
- [Action 1]: [By when]
- [Action 2]: [By when]

ADDITIONAL NOTES:
[Any other relevant information]
```

---

## 🎯 On-Call Best Practices

### During Incidents

1. **Stay Calm and Methodical**
   - Follow established procedures
   - Document all actions taken
   - Communicate clearly and frequently

2. **Focus on Impact Reduction**
   - Prioritize user experience
   - Consider quick mitigations over perfect fixes
   - Escalate early if uncertain

3. **Communication Protocol**
   - Use #incident-response for coordination
   - Update status page within 10 minutes
   - Notify stakeholders of major impacts

### Preventive Actions

1. **Daily Health Checks**
   - Review key metrics and trends
   - Verify backup completion
   - Check certificate expiration dates
   - Monitor disk space and performance

2. **Proactive Monitoring**
   - Watch for degrading trends
   - Address warnings before they become critical
   - Validate monitoring coverage

3. **Knowledge Sharing**
   - Document new procedures
   - Update runbooks based on experience
   - Share learnings with team

---

## 📚 Emergency Procedures

### Quick Reference Links

- **[Incident Response Plan](./incident-response.md)**
- **[Rollback Procedures](./rollback.md)**
- **[Go-Live Checklist](./go-live.md)**
- **[Security Incident Response](../security/incident-response.md)**

### Emergency Commands Cheat Sheet

```bash
# Check overall system health
./scripts/health-check-production.sh --critical

# View active alerts
curl -s https://api.pagerduty.com/incidents | jq '.incidents[] | select(.status=="triggered")'

# Emergency rollback
helm rollback aivo-platform -n production

# Enable maintenance mode
kubectl apply -f emergency-maintenance.yaml

# Check database connections
kubectl exec -n production postgres-primary-0 -- psql -c "SELECT count(*) FROM pg_stat_activity;"

# Restart failed services
kubectl delete pods -l health=unhealthy -n production
```

### Emergency Contact Quick Dial

```text
Primary On-Call: [Current engineer] - [Phone]
Secondary On-Call: [Backup engineer] - [Phone]
VP Engineering: David Park - +1-555-0137
AWS TAM: Sarah Wilson - +1-555-0140
Security Team: security@aivo.edu - +1-555-HELP
```

---

## 📈 Performance & Improvement

### Monthly On-Call Review

**Metrics Reviewed:**

- Response time performance
- Incident resolution effectiveness
- Alert quality and false positive rate
- Engineer feedback and burnout indicators

**Improvement Actions:**

- Update procedures based on incidents
- Enhance monitoring and alerting
- Provide additional training as needed
- Adjust rotation schedule if necessary

### On-Call Feedback

**Engineer Survey (Monthly):**

- Workload and stress levels
- Tool effectiveness
- Documentation quality
- Process improvement suggestions

**Continuous Improvement:**

- Regular procedure updates
- Tool and process optimization
- Training program enhancement
- Work-life balance monitoring

---

**Document Owner:** SRE Team  
**Review Frequency:** Monthly  
**Last Updated:** August 21, 2025  
**Next Review:** September 21, 2025  
**Approvers:** VP Engineering, SRE Team Lead
