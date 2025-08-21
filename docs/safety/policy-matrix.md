# Content Moderation & Safety Policy Matrix

## 🛡️ S4-12 — Subject-Aware Safety Filters

**GOAL**: Expand moderation in `inference-gateway-svc` with **subject-aware** rules (K-12 appropriateness), SEL sensitivity, and block lists.

### 📋 Overview

This document defines the comprehensive safety policy matrix for AIVO's content moderation system, featuring grade-band appropriate filtering, subject-aware rules, and Social-Emotional Learning (SEL) sensitivity detection.

### 🎯 Key Features

- **Grade-Band Appropriateness**: Different moderation thresholds for K-5, 6-8, 9-12, and Adult education
- **Subject-Aware Rules**: Context-sensitive moderation based on academic subject
- **SEL Sensitivity**: Automatic escalation for social-emotional learning concerns
- **Guardian/Teacher Notifications**: Automated alerts for concerning content
- **Audit Logging**: Complete audit trail for blocked/flagged content

### 📊 Grade Band Classification

| Grade Band     | Ages         | Description                                    | Moderation Level |
| -------------- | ------------ | ---------------------------------------------- | ---------------- |
| **Elementary** | K-5 (5-10)   | Strict content filtering with immediate blocks | **STRICT**       |
| **Middle**     | 6-8 (11-13)  | Moderate filtering with teacher review         | **MODERATE**     |
| **High**       | 9-12 (14-18) | Relaxed filtering with warnings and audits     | **RELAXED**      |
| **Adult**      | 18+          | Minimal restrictions for adult education       | **MINIMAL**      |

### 🔍 Content Severity Levels

| Severity          | Description                          | Typical Action |
| ----------------- | ------------------------------------ | -------------- |
| **SAFE**          | Appropriate for all ages             | Allow          |
| **MINOR_CONCERN** | Mild concern, may need review        | Warn           |
| **MODERATE**      | Requires attention/filtering         | Filter         |
| **SEVERE**        | Block immediately                    | Block          |
| **CRITICAL**      | Block + escalate to guardian/teacher | Escalate       |

### 📚 Subject-Specific Policies

#### 🧮 Mathematics

```yaml
Grade Band: Elementary (K-5)
Blocked Keywords: ["stupid", "dumb", "alcohol", "drugs", "gambling"]
Blocked Patterns: [r'\b(beer|wine|casino|bet)\b']
Thresholds:
  harassment: 0.3
  violence: 0.2
  sexual: 0.1
Action: BLOCK
```

#### 🔬 Science

```yaml
Grade Band: Middle (6-8)
Allowed Context: ["organism death", "natural selection", "predator-prey"]
Blocked Keywords: ["dangerous experiments", "explosive", "poison"]
Thresholds:
  violence: 0.4 # Higher tolerance for scientific context
  harassment: 0.5
Action: FILTER
```

#### 📖 English/Literature

```yaml
Grade Band: High (9-12)
Allowed Themes: ["mortality", "existential", "tragedy", "conflict"]
Blocked Keywords: ["explicit violence", "graphic content"]
Thresholds:
  violence: 0.6 # Literature context consideration
  sexual: 0.4
Action: WARN
```

#### 🎨 Arts & Music

```yaml
Grade Band: All
Allowed Expression: ["emotions", "abstract", "creative interpretation"]
Special Considerations: Artistic expression gets lenient treatment
Thresholds:
  violence: +0.2 # Higher tolerance for artistic context
Action: WARN
```

#### 🧠 Social-Emotional Learning (SEL)

```yaml
Grade Band: All
SEL Categories:
  - Mental Health: CRITICAL
  - Family Dynamics: MODERATE
  - Peer Pressure: MODERATE
  - Identity Issues: MINOR_CONCERN
  - Trauma: CRITICAL
Action: ESCALATE
```

### 🚨 SEL Sensitivity Matrix

#### Critical Escalation (Guardian + Teacher)

- **Mental Health Concerns**: Depression, anxiety, suicidal thoughts
- **Trauma References**: PTSD, abuse, assault, grief
- **Self-Harm Indicators**: Cutting, suicide, harmful behaviors

```regex
Mental Health Patterns:
- \b(depressed?|depression|anxiety|panic|suicidal?)\b
- \b(self.?harm|cutting|suicide)\b
- \b(therapy|counselor|medication)\b

Trauma Patterns:
- \b(trauma|ptsd|flashback)\b
- \b(abuse|assault|violence)\b
- \b(grief|loss|death)\b
```

#### Teacher Review (No Guardian Alert)

- **Peer Pressure**: Bullying, social exclusion, loneliness
- **Family Dynamics**: Divorce, family problems, custody issues
- **Identity Issues**: Self-worth, confidence, belonging

```regex
Peer Pressure Patterns:
- \b(bullying|bullied|bully)\b
- \b(peer.?pressure|social.?pressure)\b
- \b(excluded|isolation|lonely)\b

Family Dynamics Patterns:
- \b(divorce|abuse|neglect|domestic)\b
- \b(family.?problem|parent.?issue)\b
- \b(custody|separation)\b
```

### 📊 Threshold Matrix by Grade Band

#### Elementary (K-5) - STRICT

| Category          | Threshold | Action   | Escalation         |
| ----------------- | --------- | -------- | ------------------ |
| Harassment        | 0.3       | BLOCK    | Yes                |
| Hate Speech       | 0.2       | BLOCK    | Yes                |
| Violence          | 0.2       | BLOCK    | Yes                |
| Sexual Content    | 0.1       | BLOCK    | Yes                |
| Profanity         | 0.2       | BLOCK    | No                 |
| SEL Mental Health | 0.0       | ESCALATE | Guardian + Teacher |

#### Middle School (6-8) - MODERATE

| Category          | Threshold | Action   | Escalation         |
| ----------------- | --------- | -------- | ------------------ |
| Harassment        | 0.5       | FILTER   | Teacher            |
| Hate Speech       | 0.3       | BLOCK    | Teacher            |
| Violence          | 0.3       | FILTER   | Teacher            |
| Sexual Content    | 0.2       | BLOCK    | Teacher            |
| Profanity         | 0.4       | WARN     | No                 |
| SEL Mental Health | 0.0       | ESCALATE | Guardian + Teacher |

#### High School (9-12) - RELAXED

| Category          | Threshold | Action   | Escalation |
| ----------------- | --------- | -------- | ---------- |
| Harassment        | 0.7       | WARN     | No         |
| Hate Speech       | 0.5       | FILTER   | Teacher    |
| Violence          | 0.5       | WARN     | No         |
| Sexual Content    | 0.4       | WARN     | No         |
| Profanity         | 0.6       | ALLOW    | No         |
| SEL Mental Health | 0.0       | ESCALATE | Teacher    |

#### Adult Education - MINIMAL

| Category          | Threshold | Action | Escalation |
| ----------------- | --------- | ------ | ---------- |
| Harassment        | 0.8       | WARN   | No         |
| Hate Speech       | 0.7       | WARN   | No         |
| Violence          | 0.7       | ALLOW  | No         |
| Sexual Content    | 0.7       | ALLOW  | No         |
| Profanity         | 0.8       | ALLOW  | No         |
| SEL Mental Health | 0.2       | AUDIT  | No         |

### 🔒 Block Lists by Category

#### Universal Block List (All Grade Bands)

```yaml
Explicit Violence:
  - "kill yourself"
  - "commit suicide"
  - "murder someone"
  - "mass shooting"

Hate Speech:
  - "racial slurs"
  - "discriminatory language"
  - "supremacist content"

Illegal Activities:
  - "how to make bombs"
  - "illegal drug manufacturing"
  - "fraud instructions"
```

#### Elementary-Specific Block List

```yaml
Inappropriate Language:
  - "stupid", "dumb", "idiot", "loser"
  - "shut up", "hate you"
  - "kill", "die", "death"

Adult Topics:
  - "alcohol", "beer", "wine", "drunk"
  - "smoking", "cigarettes", "drugs"
  - "gambling", "casino", "betting"
```

#### Middle School Additional Blocks

```yaml
Cyberbullying Terms:
  - "nobody likes you"
  - "you're worthless"
  - "kill yourself"

Inappropriate Content:
  - "explicit images"
  - "pornography"
  - "sexual acts"
```

### 📧 Notification & Escalation Workflows

#### Guardian Notification (Critical)

```json
{
  "trigger": "SEL mental health or trauma detected",
  "recipients": ["guardian@email.com", "counselor@school.edu"],
  "template": "critical_sel_alert",
  "urgency": "immediate",
  "follow_up": "within 24 hours"
}
```

#### Teacher Notification (Standard)

```json
{
  "trigger": "Content violations or SEL concerns",
  "recipients": ["teacher@school.edu", "principal@school.edu"],
  "template": "content_review_alert",
  "urgency": "normal",
  "follow_up": "within 48 hours"
}
```

### 📝 Audit Log Structure

```json
{
  "timestamp": "2025-08-20T15:30:00Z",
  "event_type": "content_moderation",
  "content_hash": "abc123456",
  "content_length": 150,
  "subject": "math",
  "grade_band": "elementary",
  "user_id": "student_789",
  "tenant_id": "school_district_123",
  "flagged": true,
  "severity": "severe",
  "action": "block",
  "triggered_rules": [
    "elementary_safe_content:keyword:stupid",
    "elementary_safe_content:pattern:alcohol"
  ],
  "sel_categories": ["peer_pressure"],
  "requires_escalation": true,
  "guardian_notification": false,
  "teacher_notification": true,
  "processing_time_ms": 45,
  "provider_used": "openai",
  "confidence": 0.92
}
```

### ⚙️ Configuration Examples

#### Basic Configuration

```yaml
safety_engine:
  default_grade_band: "adult"
  default_subject: "general"
  audit_logging: true

  custom_safety_policies:
    - subject: "math"
      grade_band: "elementary"
      custom_thresholds:
        harassment: 0.2
        violence: 0.1
      blocked_topics: ["gambling", "alcohol"]
      guardian_webhook: "https://api.school.edu/guardian-notify"
      teacher_webhook: "https://api.school.edu/teacher-notify"
```

#### Advanced SEL Configuration

```yaml
sel_sensitivity:
  escalation_enabled: true
  categories:
    mental_health:
      threshold: 0.0
      action: "escalate"
      notify_guardian: true
      notify_teacher: true

    peer_pressure:
      threshold: 0.0
      action: "audit"
      notify_teacher: true

    family_dynamics:
      threshold: 0.0
      action: "audit"
      notify_teacher: true
```

### 🧪 Testing Scenarios

#### Safe Content (Should Pass)

```text
✅ "What is 2 + 2?"
✅ "The water cycle includes evaporation"
✅ "George Washington was the first president"
✅ "Draw a picture of your favorite animal"
✅ "Practice your piano scales"
```

#### Flagged Content (Should Filter/Block)

```text
❌ "This math problem is so stupid" (Elementary)
❌ "I want to hurt someone" (All grades)
❌ "If John drinks 5 beers..." (Elementary)
❌ "Let's talk about explicit content" (K-8)
❌ "How to make dangerous chemicals" (All grades)
```

#### SEL Escalation (Should Alert)

```text
🚨 "I feel so depressed and anxious" (Critical)
🚨 "Kids are bullying me at school" (Teacher alert)
🚨 "My parents are getting divorced" (Teacher alert)
🚨 "I have thoughts of hurting myself" (Critical)
🚨 "I can't stop having flashbacks" (Critical)
```

### 📈 Performance Metrics

#### Target Response Times

- **Simple Content**: < 50ms
- **Complex Analysis**: < 200ms
- **SEL Pattern Matching**: < 100ms
- **Batch Processing**: < 1000ms for 10 items

#### Accuracy Targets

- **False Positive Rate**: < 5%
- **False Negative Rate**: < 2%
- **SEL Detection Accuracy**: > 95%
- **Grade-Band Appropriateness**: > 98%

### 🔧 Implementation Notes

#### Provider Integration

```python
# Example usage in inference gateway
safety_engine = SafetyEngine(config)

result = await safety_engine.moderate_content(
    content="Student's question or response",
    subject=Subject.MATH,
    grade_band=GradeBand.ELEMENTARY,
    user_id="student_123",
    tenant_id="school_456"
)

if result.action == ModerationAction.BLOCK:
    return {"error": "Content not appropriate for grade level"}
elif result.requires_escalation:
    await notify_guardians_and_teachers(result)
```

#### Custom Rule Addition

```python
# Adding custom moderation rules
custom_rule = ModerationRule(
    name="chemistry_safety",
    description="Block dangerous chemistry references",
    grade_bands=[GradeBand.ELEMENTARY, GradeBand.MIDDLE],
    subjects=[Subject.SCIENCE],
    blocked_keywords=["explosive", "toxic", "poisonous"],
    action=ModerationAction.BLOCK,
    audit_log=True
)

safety_engine.add_custom_rule(custom_rule)
```

### 📞 Emergency Procedures

#### Immediate Response Protocol

1. **Critical SEL Detection**: Automatic notification within 5 minutes
2. **Violence Threats**: Immediate blocking + school admin alert
3. **Self-Harm Indicators**: Guardian + counselor notification
4. **System Failures**: Fail-safe to most restrictive mode

#### Escalation Chain

1. **Tier 1**: Automated filtering/blocking
2. **Tier 2**: Teacher notification and review
3. **Tier 3**: Guardian notification + counselor involvement
4. **Tier 4**: School administration + emergency services

---

**Document Version**: 1.0.0  
**Last Updated**: August 20, 2025  
**Owner**: Safety Engineering Team  
**Reviewers**: Education Team, Legal, Child Safety Board
