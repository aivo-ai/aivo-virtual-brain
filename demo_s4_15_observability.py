#!/usr/bin/env python3
"""
S4-15 Observability Demo Script
Demonstrates RUM, service trace maps, and error correlation
"""

import time
import json
import hashlib
import uuid
from typing import Dict, Any

def hash_learner_id(learner_id: str) -> str:
    """Hash learner ID for privacy protection"""
    return hashlib.sha256(f"learner:{learner_id}".encode()).hexdigest()[:16]

def generate_session_id() -> str:
    """Generate unique session ID"""
    return f"sess_{int(time.time())}_{str(uuid.uuid4())[:8]}"

def simulate_rum_events():
    """Simulate Real User Monitoring events"""
    session_id = generate_session_id()
    learner_id = "student-12345"
    hashed_learner_id = hash_learner_id(learner_id)
    
    print("🌐 RUM Events Simulation")
    print("=" * 50)
    
    # Web Vitals
    web_vitals = {
        "LCP": {"value": 1245, "rating": "good", "timestamp": int(time.time() * 1000)},
        "FID": {"value": 85, "rating": "good", "timestamp": int(time.time() * 1000)},
        "CLS": {"value": 0.08, "rating": "good", "timestamp": int(time.time() * 1000)},
        "FCP": {"value": 1100, "rating": "good", "timestamp": int(time.time() * 1000)},
        "TTFB": {"value": 650, "rating": "good", "timestamp": int(time.time() * 1000)}
    }
    
    print("📊 Web Vitals Collected:")
    for metric, data in web_vitals.items():
        print(f"  {metric}: {data['value']}ms ({data['rating']})")
    
    # User Interactions
    interactions = [
        {
            "type": "page.load",
            "url": "/dashboard",
            "session_id": session_id,
            "user_id_hashed": hashed_learner_id,
            "timestamp": int(time.time() * 1000)
        },
        {
            "type": "click",
            "element": "start-assessment-btn",
            "session_id": session_id,
            "user_id_hashed": hashed_learner_id,
            "timestamp": int(time.time() * 1000)
        },
        {
            "type": "navigation",
            "from": "/dashboard",
            "to": "/assessment/math-grade-6",
            "session_id": session_id,
            "user_id_hashed": hashed_learner_id,
            "timestamp": int(time.time() * 1000)
        }
    ]
    
    print("\n🖱️  User Interactions Tracked:")
    for interaction in interactions:
        print(f"  {interaction['type']}: {interaction.get('element', interaction.get('to', 'N/A'))}")
    
    return session_id, hashed_learner_id, web_vitals, interactions

def simulate_service_trace_map():
    """Simulate service dependencies and trace flow"""
    print("\n🗺️  Service Trace Map")
    print("=" * 50)
    
    # Service dependency graph
    service_map = {
        "aivo-web-client": {
            "calls": ["config-svc", "user-svc", "auth-svc"],
            "instance_id": "web-client-prod-1",
            "avg_latency_ms": 45
        },
        "config-svc": {
            "calls": ["redis-cache"],
            "instance_id": "config-svc-prod-2",
            "avg_latency_ms": 12
        },
        "user-svc": {
            "calls": ["postgres-db", "auth-svc"],
            "instance_id": "user-svc-prod-3",
            "avg_latency_ms": 28
        },
        "auth-svc": {
            "calls": ["postgres-db", "external-identity-provider"],
            "instance_id": "auth-svc-prod-1",
            "avg_latency_ms": 156
        },
        "assessment-svc": {
            "calls": ["postgres-db", "analytics-svc"],
            "instance_id": "assessment-svc-prod-2",
            "avg_latency_ms": 89
        },
        "analytics-svc": {
            "calls": ["clickhouse-db", "kafka-stream"],
            "instance_id": "analytics-svc-prod-1",
            "avg_latency_ms": 34
        }
    }
    
    print("📈 Service Dependencies:")
    for service, data in service_map.items():
        print(f"  {service} ({data['instance_id']}):")
        print(f"    → Calls: {', '.join(data['calls'])}")
        print(f"    → Avg Latency: {data['avg_latency_ms']}ms")
    
    return service_map

def simulate_error_correlation():
    """Simulate error correlation with session tracking"""
    print("\n🚨 Error Correlation")
    print("=" * 50)
    
    session_id = generate_session_id()
    hashed_learner_id = hash_learner_id("error-test-student")
    
    # Simulated errors with session correlation
    errors = [
        {
            "error_id": str(uuid.uuid4()),
            "service": "aivo-web-client",
            "type": "JavaScript Error",
            "message": "Cannot read property 'score' of undefined",
            "stack": "AssessmentComponent.render (assessment.js:245)",
            "session_id": session_id,
            "user_id_hashed": hashed_learner_id,
            "user_role": "student",
            "grade_band": "6-8",
            "timestamp": int(time.time() * 1000)
        },
        {
            "error_id": str(uuid.uuid4()),
            "service": "assessment-svc",
            "type": "HTTP 500",
            "message": "Database connection timeout",
            "session_id": session_id,
            "user_id_hashed": hashed_learner_id,
            "user_role": "student",
            "grade_band": "6-8",
            "timestamp": int(time.time() * 1000)
        },
        {
            "error_id": str(uuid.uuid4()),
            "service": "user-svc",
            "type": "HTTP 404",
            "message": "User profile not found",
            "session_id": session_id,
            "user_id_hashed": hashed_learner_id,
            "user_role": "student",
            "grade_band": "6-8",
            "timestamp": int(time.time() * 1000)
        }
    ]
    
    print("🔗 Correlated Errors by Session:")
    print(f"   Session ID: {session_id}")
    print(f"   User ID (Hashed): {hashed_learner_id}")
    print()
    
    for error in errors:
        print(f"  ❌ {error['service']}: {error['type']}")
        print(f"     Message: {error['message']}")
        print(f"     Error ID: {error['error_id']}")
        print()
    
    return session_id, errors

def demonstrate_privacy_compliance():
    """Demonstrate privacy-first observability"""
    print("\n🔐 Privacy Compliance")
    print("=" * 50)
    
    # Original PII data (would never be in traces)
    original_data = {
        "learner_id": "student-12345",
        "email": "jane.doe@school.edu",
        "name": "Jane Doe",
        "phone": "+1-555-123-4567"
    }
    
    # What actually goes into traces (privacy-compliant)
    trace_data = {
        "user_id_hashed": hash_learner_id(original_data["learner_id"]),
        "user_role": "student",
        "grade_band": "6-8",
        "tenant_id": "school-district-123",
        "session_id": generate_session_id()
    }
    
    print("❌ Original PII (NEVER in traces):")
    for key, value in original_data.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Privacy-Compliant Trace Data:")
    for key, value in trace_data.items():
        print(f"   {key}: {value}")
    
    print(f"\n🔒 Hash Protection: {original_data['learner_id']} → {trace_data['user_id_hashed']}")
    
    return trace_data

def simulate_feature_flag_correlation():
    """Simulate feature flag evaluation correlation"""
    print("\n🚩 Feature Flag Correlation")
    print("=" * 50)
    
    session_id = generate_session_id()
    hashed_learner_id = hash_learner_id("flag-test-student")
    
    flag_evaluations = [
        {
            "flag_key": "adaptive_learning_enabled",
            "value": True,
            "reason": "grade_band_targeting",
            "session_id": session_id,
            "user_id_hashed": hashed_learner_id,
            "context": {
                "grade_band": "6-8",
                "user_role": "student",
                "tenant_id": "school-district-123"
            }
        },
        {
            "flag_key": "gamification_features",
            "value": False,
            "reason": "tenant_override",
            "session_id": session_id,
            "user_id_hashed": hashed_learner_id,
            "context": {
                "grade_band": "6-8",
                "user_role": "student",
                "tenant_id": "school-district-123"
            }
        },
        {
            "flag_key": "assessment_ai_hints",
            "value": True,
            "reason": "user_experiment_group",
            "session_id": session_id,
            "user_id_hashed": hashed_learner_id,
            "context": {
                "grade_band": "6-8",
                "user_role": "student",
                "tenant_id": "school-district-123"
            }
        }
    ]
    
    print("🎯 Feature Flag Evaluations:")
    for flag in flag_evaluations:
        status = "✅ Enabled" if flag["value"] else "❌ Disabled"
        print(f"   {flag['flag_key']}: {status} ({flag['reason']})")
    
    return flag_evaluations

def generate_grafana_queries():
    """Generate sample Grafana queries for the dashboard"""
    print("\n📊 Grafana Dashboard Queries")
    print("=" * 50)
    
    queries = {
        "service_map": {
            "query": '{} | rate() by (resource.service.name, span.name)',
            "description": "Service dependency graph with request rates"
        },
        "error_correlation": {
            "query": '{status.code="error"} | select(resource.service.name, session.id, user.id.hashed, error.message)',
            "description": "Errors correlated by session and user"
        },
        "web_vitals": {
            "query": '{resource.service.name="aivo-web-client" && name=~"web.vital.*"} | rate() by (web.vital.name)',
            "description": "Web Vitals metrics from RUM"
        },
        "feature_flags": {
            "query": '{name="feature.flag.evaluation"} | count() by (feature.flag.key, feature.flag.value)',
            "description": "Feature flag usage distribution"
        },
        "user_sessions": {
            "query": '{session.id!=""} | select(session.id, user.id.hashed, user.role, user.grade_band)',
            "description": "Active user sessions with privacy-compliant identifiers"
        }
    }
    
    print("🔍 Sample Tempo Queries for Grafana:")
    for name, query_info in queries.items():
        print(f"\n   {name.replace('_', ' ').title()}:")
        print(f"     Query: {query_info['query']}")
        print(f"     Description: {query_info['description']}")
    
    return queries

def main():
    """Main demo execution"""
    print("🚀 S4-15 OBSERVABILITY DEEP DIVE DEMO")
    print("=" * 60)
    print("Demonstrating RUM + Service Trace Maps + Error Correlation")
    print("=" * 60)
    
    # Run all demonstrations
    session_id, hashed_learner_id, web_vitals, interactions = simulate_rum_events()
    service_map = simulate_service_trace_map()
    error_session, errors = simulate_error_correlation()
    trace_data = demonstrate_privacy_compliance()
    flag_evaluations = simulate_feature_flag_correlation()
    grafana_queries = generate_grafana_queries()
    
    # Summary
    print("\n🎯 IMPLEMENTATION SUMMARY")
    print("=" * 60)
    print("✅ RUM (Real User Monitoring):")
    print("   • Web Vitals collection (LCP, FID, CLS, FCP, TTFB)")
    print("   • User interaction tracking")
    print("   • Performance metrics to OTEL collector")
    print()
    print("✅ Service Trace Maps:")
    print("   • Service dependency visualization")
    print("   • Request flow tracking")
    print("   • Latency correlation across services")
    print()
    print("✅ Error Correlation:")
    print("   • Session-based error tracking")
    print("   • Cross-service error correlation")
    print("   • Hashed learner ID for privacy")
    print()
    print("✅ Privacy Compliance:")
    print("   • No PII in traces")
    print("   • Hashed learner IDs only")
    print("   • OTEL collector PII filtering")
    print()
    print("✅ Grafana Integration:")
    print("   • Service map dashboard")
    print("   • Error correlation views")
    print("   • Real-time observability")
    
    print("\n" + "=" * 60)
    print("S4-15 OBSERVABILITY DEEP DIVE - COMPLETE! 🎉")
    print("=" * 60)

if __name__ == "__main__":
    main()
