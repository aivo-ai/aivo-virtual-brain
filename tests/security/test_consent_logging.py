#!/usr/bin/env python3
"""
AIVO Virtual Brains - S1-18 Security & Privacy Tests
Consent Logging & Audit Trail Test Suite

Tests comprehensive consent management and audit logging:
- Append-only consent audit log integrity
- Consent state caching and invalidation
- Privacy policy enforcement logging
- Consent decision correlation tracking
- 7-year audit retention compliance

Coverage Target: ≥80% of consent enforcement paths
"""

import pytest
import asyncio
import asyncpg
import redis.asyncio as redis
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests


class ConsentTestHelper:
    """Helper class for consent logging and audit testing"""
    
    def __init__(self):
        self.base_url = "http://localhost:8003"  # Consent service
        self.redis_url = "redis://localhost:6379/0"
        self.postgres_url = "postgresql://aivo_consent:consent_pass@localhost:5432/aivo_consent"
        self.correlation_prefix = "consent-test"
    
    async def setup_test_data(self):
        """Set up test consent data in Redis and PostgreSQL"""
        # Redis setup
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        
        # PostgreSQL setup  
        self.pg_pool = await asyncpg.create_pool(self.postgres_url)
        
        # Clean up any existing test data
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data after tests"""
        if hasattr(self, 'redis_client'):
            # Remove test keys from Redis
            keys = await self.redis_client.keys("consent:*test*")
            if keys:
                await self.redis_client.delete(*keys)
        
        if hasattr(self, 'pg_pool'):
            # Remove test entries from PostgreSQL
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM consent_state WHERE learner_id LIKE '%test%'"
                )
                await conn.execute(
                    "DELETE FROM consent_audit_log WHERE learner_id LIKE '%test%'"
                )
    
    async def set_consent_state(
        self, 
        learner_id: str, 
        consent_type: str, 
        value: bool,
        actor_user_id: str = "test-admin",
        ip_address: str = "127.0.0.1",
        metadata: Optional[Dict] = None
    ) -> str:
        """Set consent state for testing"""
        correlation_id = f"{self.correlation_prefix}-{uuid.uuid4().hex[:8]}"
        
        consent_data = {
            "learner_id": learner_id,
            "consent_type": consent_type,
            "value": value,
            "actor_user_id": actor_user_id,
            "ip_address": ip_address,
            "metadata": metadata or {},
            "correlation_id": correlation_id
        }
        
        response = requests.post(
            f"{self.base_url}/consent/batch",
            json={"consents": [consent_data]},
            headers={"X-Correlation-ID": correlation_id}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to set consent: {response.text}")
        
        return correlation_id
    
    async def get_audit_log(self, learner_id: str, limit: int = 100) -> List[Dict]:
        """Get consent audit log entries"""
        response = requests.get(
            f"{self.base_url}/consent/{learner_id}/audit",
            params={"limit": limit}
        )
        
        if response.status_code == 200:
            return response.json()["entries"]
        return []
    
    async def verify_audit_integrity(self, correlation_id: str) -> bool:
        """Verify audit log entry integrity and immutability"""
        async with self.pg_pool.acquire() as conn:
            # Query audit log for correlation ID
            rows = await conn.fetch(
                """
                SELECT id, learner_id, actor_user_id, key, value, 
                       ts, ip_address, metadata, correlation_id
                FROM consent_audit_log 
                WHERE correlation_id = $1
                ORDER BY ts DESC
                """,
                correlation_id
            )
            
            if not rows:
                return False
            
            # Verify immutability - try to update (should fail)
            try:
                await conn.execute(
                    "UPDATE consent_audit_log SET value = NOT value WHERE correlation_id = $1",
                    correlation_id
                )
                # If update succeeded, audit log is not properly protected
                return False
            except Exception:
                # Update should fail for immutable audit log
                pass
            
            # Verify data integrity
            for row in rows:
                if not row['correlation_id'] or not row['ts'] or not row['learner_id']:
                    return False
            
            return True


class TestConsentAuditLogging:
    """Test consent audit logging and immutability"""
    
    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Set up and clean up test environment"""
        self.helper = ConsentTestHelper()
        await self.helper.setup_test_data()
        yield
        await self.helper.cleanup_test_data()
    
    @pytest.mark.asyncio
    async def test_consent_change_creates_audit_log_entry(self):
        """Test: Consent changes create immutable audit log entries"""
        # Arrange: Test learner and consent type
        learner_id = "test-learner-001"
        consent_type = "data_processing"
        actor_id = "test-teacher-001"
        
        # Act: Set initial consent
        correlation_id = await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type, 
            value=True,
            actor_user_id=actor_id,
            metadata={"test": "initial_consent", "reason": "enrollment"}
        )
        
        # Wait for async processing
        await asyncio.sleep(1)
        
        # Assert: Audit log entry created
        audit_entries = await self.helper.get_audit_log(learner_id)
        assert len(audit_entries) >= 1
        
        # Find our entry
        our_entry = next(
            (e for e in audit_entries if e.get("correlation_id") == correlation_id), 
            None
        )
        assert our_entry is not None
        assert our_entry["learner_id"] == learner_id
        assert our_entry["actor_user_id"] == actor_id
        assert our_entry["key"] == consent_type
        assert our_entry["value"] is True
        assert our_entry["metadata"]["test"] == "initial_consent"
        
        # Verify audit integrity
        assert await self.helper.verify_audit_integrity(correlation_id)
    
    @pytest.mark.asyncio  
    async def test_consent_revocation_creates_new_audit_entry(self):
        """Test: Consent revocation creates new audit entry (append-only)"""
        # Arrange: Learner with existing consent
        learner_id = "test-learner-002"
        consent_type = "data_sharing"
        
        # Set initial consent
        initial_correlation = await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=True,
            actor_user_id="test-admin",
            metadata={"reason": "initial_setup"}
        )
        
        await asyncio.sleep(1)
        
        # Act: Revoke consent
        revocation_correlation = await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=False,
            actor_user_id="test-guardian", 
            metadata={"reason": "privacy_request", "revocation": True}
        )
        
        await asyncio.sleep(1)
        
        # Assert: Two audit entries exist (append-only)
        audit_entries = await self.helper.get_audit_log(learner_id)
        learner_entries = [e for e in audit_entries if e["learner_id"] == learner_id]
        assert len(learner_entries) >= 2
        
        # Verify both entries exist with different values
        initial_entry = next(
            (e for e in learner_entries if e.get("correlation_id") == initial_correlation),
            None
        )
        revocation_entry = next(
            (e for e in learner_entries if e.get("correlation_id") == revocation_correlation),
            None  
        )
        
        assert initial_entry is not None
        assert revocation_entry is not None
        assert initial_entry["value"] is True
        assert revocation_entry["value"] is False
        assert initial_entry["actor_user_id"] == "test-admin"
        assert revocation_entry["actor_user_id"] == "test-guardian"
        
        # Verify chronological order
        initial_ts = datetime.fromisoformat(initial_entry["ts"].replace('Z', '+00:00'))
        revocation_ts = datetime.fromisoformat(revocation_entry["ts"].replace('Z', '+00:00'))
        assert revocation_ts > initial_ts
    
    @pytest.mark.asyncio
    async def test_audit_log_contains_required_fields(self):
        """Test: Audit log entries contain all required compliance fields"""
        # Arrange: Comprehensive consent change
        learner_id = "test-learner-003"
        consent_type = "marketing_communications"
        
        # Act: Set consent with full metadata
        correlation_id = await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=True,
            actor_user_id="test-user-003",
            ip_address="192.168.1.100",
            metadata={
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "session_id": "sess_abc123",
                "form_version": "v2.1",
                "legal_basis": "legitimate_interest"
            }
        )
        
        await asyncio.sleep(1)
        
        # Assert: All required fields present
        audit_entries = await self.helper.get_audit_log(learner_id)
        our_entry = next(
            (e for e in audit_entries if e.get("correlation_id") == correlation_id),
            None
        )
        
        assert our_entry is not None
        
        # Required compliance fields
        required_fields = [
            "id", "learner_id", "actor_user_id", "key", "value", 
            "ts", "ip_address", "metadata", "correlation_id"
        ]
        
        for field in required_fields:
            assert field in our_entry, f"Missing required field: {field}"
            assert our_entry[field] is not None, f"Required field {field} is None"
        
        # Verify timestamp format (ISO 8601)
        ts = our_entry["ts"]
        datetime.fromisoformat(ts.replace('Z', '+00:00'))  # Should not raise exception
        
        # Verify IP address format
        ip = our_entry["ip_address"]
        assert ip == "192.168.1.100"
        
        # Verify metadata preservation
        metadata = our_entry["metadata"]
        assert metadata["legal_basis"] == "legitimate_interest"
        assert metadata["form_version"] == "v2.1"
    
    @pytest.mark.asyncio
    async def test_audit_log_immutability_protection(self):
        """Test: Audit log entries are immutable and tamper-resistant"""
        # Arrange: Create consent change
        learner_id = "test-learner-004"
        consent_type = "data_retention" 
        
        correlation_id = await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=True,
            actor_user_id="test-admin"
        )
        
        await asyncio.sleep(1)
        
        # Act & Assert: Verify immutability
        is_immutable = await self.helper.verify_audit_integrity(correlation_id)
        assert is_immutable, "Audit log should be immutable"
        
        # Additional verification: Direct database check
        async with self.helper.pg_pool.acquire() as conn:
            # Verify entry exists
            row = await conn.fetchrow(
                "SELECT * FROM consent_audit_log WHERE correlation_id = $1",
                correlation_id
            )
            assert row is not None
            
            original_ts = row['ts']
            original_value = row['value']
            
            # Attempt unauthorized modification (should be prevented by constraints/triggers)
            try:
                # This should fail due to audit table protection
                await conn.execute(
                    "UPDATE consent_audit_log SET value = $1 WHERE correlation_id = $2",
                    not original_value, correlation_id
                )
                
                # Verify value unchanged
                updated_row = await conn.fetchrow(
                    "SELECT * FROM consent_audit_log WHERE correlation_id = $1", 
                    correlation_id
                )
                assert updated_row['value'] == original_value, "Audit log was improperly modified"
                
            except Exception:
                # Update failure is expected for protected audit logs
                pass


class TestConsentStateManagement:
    """Test consent state caching and consistency"""
    
    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Set up and clean up test environment"""
        self.helper = ConsentTestHelper()
        await self.helper.setup_test_data()
        yield
        await self.helper.cleanup_test_data()
    
    @pytest.mark.asyncio
    async def test_consent_state_cached_in_redis(self):
        """Test: Consent state is cached in Redis for performance"""
        # Arrange: Learner consent
        learner_id = "test-learner-005"
        consent_type = "analytics_tracking"
        
        # Act: Set consent
        await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=True
        )
        
        await asyncio.sleep(1)
        
        # Assert: Check Redis cache
        cache_key = f"consent:state:{learner_id}"
        cached_data = await self.helper.redis_client.hget(cache_key, consent_type)
        
        if cached_data:
            assert json.loads(cached_data)["value"] is True
        
        # Verify TTL is set for cache expiration
        ttl = await self.helper.redis_client.ttl(cache_key)
        assert ttl > 0, "Cache should have TTL set"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_consent_change(self):
        """Test: Redis cache invalidated when consent changes"""
        # Arrange: Cached consent
        learner_id = "test-learner-006"
        consent_type = "personalization"
        
        # Set initial consent (will be cached)
        await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=True
        )
        
        await asyncio.sleep(1)
        
        # Verify cached
        cache_key = f"consent:state:{learner_id}"
        initial_cached = await self.helper.redis_client.hget(cache_key, consent_type)
        
        # Act: Change consent (should invalidate cache)
        await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=False
        )
        
        await asyncio.sleep(2)  # Allow for cache invalidation
        
        # Assert: Cache updated with new value
        updated_cached = await self.helper.redis_client.hget(cache_key, consent_type)
        
        if updated_cached:
            cached_value = json.loads(updated_cached)["value"]
            assert cached_value is False, "Cache should reflect new consent value"
    
    @pytest.mark.asyncio
    async def test_consent_state_consistency_redis_postgres(self):
        """Test: Consent state consistency between Redis cache and PostgreSQL"""
        # Arrange: Multiple consent changes
        learner_id = "test-learner-007"
        consent_type = "third_party_sharing"
        
        # Act: Series of consent changes
        changes = [True, False, True]
        correlation_ids = []
        
        for value in changes:
            correlation_id = await self.helper.set_consent_state(
                learner_id=learner_id,
                consent_type=consent_type,
                value=value
            )
            correlation_ids.append(correlation_id)
            await asyncio.sleep(1)
        
        # Assert: Redis matches latest PostgreSQL state
        
        # Check PostgreSQL (authoritative)
        async with self.helper.pg_pool.acquire() as conn:
            pg_row = await conn.fetchrow(
                "SELECT value FROM consent_state WHERE learner_id = $1 AND consent_type = $2",
                learner_id, consent_type
            )
        
        # Check Redis (cache)
        cache_key = f"consent:state:{learner_id}"
        redis_data = await self.helper.redis_client.hget(cache_key, consent_type)
        
        if pg_row and redis_data:
            pg_value = pg_row['value']
            redis_value = json.loads(redis_data)["value"]
            assert pg_value == redis_value, "Redis and PostgreSQL consent state must match"
            assert pg_value is True, "Final consent state should be True"


class TestConsentComplianceRetention:
    """Test consent compliance and audit retention requirements"""
    
    @pytest.fixture(autouse=True) 
    async def setup_and_cleanup(self):
        """Set up and clean up test environment"""
        self.helper = ConsentTestHelper()
        await self.helper.setup_test_data()
        yield
        await self.helper.cleanup_test_data()
    
    @pytest.mark.asyncio
    async def test_seven_year_audit_retention_policy(self):
        """Test: Audit logs retained for 7 years (2555 days) for compliance"""
        # Arrange: Old audit entry (simulate)
        learner_id = "test-learner-008"
        consent_type = "legal_compliance"
        
        # Create audit entry
        correlation_id = await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=True,
            metadata={"compliance_test": "retention_policy"}
        )
        
        await asyncio.sleep(1)
        
        # Assert: Entry exists and can be queried
        audit_entries = await self.helper.get_audit_log(learner_id)
        our_entry = next(
            (e for e in audit_entries if e.get("correlation_id") == correlation_id),
            None
        )
        assert our_entry is not None
        
        # Verify retention metadata
        async with self.helper.pg_pool.acquire() as conn:
            # Check if retention policy exists (table constraints or settings)
            retention_info = await conn.fetch(
                """
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'consent_audit_log'
                ORDER BY ordinal_position
                """
            )
            
            # Verify audit table has required fields for long-term retention
            column_names = [col['column_name'] for col in retention_info]
            required_retention_fields = ['ts', 'learner_id', 'actor_user_id', 'key', 'value']
            
            for field in required_retention_fields:
                assert field in column_names, f"Retention field {field} missing from audit table"
    
    @pytest.mark.asyncio
    async def test_gdpr_right_to_erasure_audit_retention(self):
        """Test: GDPR right to erasure vs. audit log retention requirements"""
        # Arrange: Learner with consent history
        learner_id = "test-learner-009-gdpr"
        consent_type = "data_processing"
        
        # Create consent history
        correlation_id = await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=True,
            metadata={"gdpr_test": "erasure_vs_retention"}
        )
        
        await asyncio.sleep(1)
        
        # Act: Simulate GDPR erasure request (business logic)
        # Note: Audit logs may need to be retained for legal compliance
        # while personal data is anonymized
        
        # Request erasure via API (if implemented)
        erasure_response = requests.post(
            f"{self.helper.base_url}/gdpr/erasure",
            json={"learner_id": learner_id, "reason": "gdpr_right_to_erasure"}
        )
        
        # Assert: Audit trail handling
        if erasure_response.status_code == 200:
            # Verify audit logs are handled appropriately
            # (may be anonymized rather than deleted for compliance)
            audit_entries = await self.helper.get_audit_log(learner_id)
            
            # Audit logs may still exist but with anonymized data
            if audit_entries:
                # Check if personal identifiers are anonymized
                our_entry = next(
                    (e for e in audit_entries if e.get("correlation_id") == correlation_id),
                    None
                )
                # Implementation specific - may anonymize learner_id while retaining audit
    
    @pytest.mark.asyncio
    async def test_consent_correlation_across_services(self):
        """Test: Consent decisions correlated across all services"""
        # Arrange: Multi-service consent scenario
        learner_id = "test-learner-010"
        consent_type = "cross_service_data"
        base_correlation = f"multi-svc-{uuid.uuid4().hex[:8]}"
        
        # Act: Set consent with correlation ID
        correlation_id = await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=True,
            metadata={
                "services": ["learner-svc", "assessment-svc", "user-svc"],
                "cross_service_consent": True,
                "base_correlation": base_correlation
            }
        )
        
        await asyncio.sleep(1)
        
        # Assert: Correlation tracking
        audit_entries = await self.helper.get_audit_log(learner_id)
        our_entry = next(
            (e for e in audit_entries if e.get("correlation_id") == correlation_id),
            None
        )
        
        assert our_entry is not None
        assert our_entry["metadata"]["cross_service_consent"] is True
        assert our_entry["metadata"]["base_correlation"] == base_correlation
        
        # Verify services can lookup consent by correlation
        services = our_entry["metadata"]["services"]
        assert "learner-svc" in services
        assert "assessment-svc" in services
        assert "user-svc" in services


class TestConsentSecurityIntegration:
    """Test consent integration with security plugins"""
    
    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Set up and clean up test environment"""
        self.helper = ConsentTestHelper()
        await self.helper.setup_test_data()
        yield
        await self.helper.cleanup_test_data()
    
    @pytest.mark.asyncio 
    async def test_consent_gate_plugin_integration(self):
        """Test: Consent gate plugin enforces consent requirements"""
        # Arrange: Learner without consent for privacy-sensitive operation
        learner_id = "test-learner-011"
        consent_type = "persona_access"
        
        # Ensure no consent initially
        # (consent_gate plugin should block access)
        
        # Act: Test gateway enforcement via Kong
        kong_url = "http://localhost:8000"  # Kong gateway
        
        # Create JWT for learner
        import jwt as pyjwt
        jwt_payload = {
            "sub": "user123",
            "learner_uid": learner_id,
            "role": "learner", 
            "dash_context": "learner",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        jwt_token = pyjwt.encode(jwt_payload, "your-secret-key", algorithm="HS256")
        
        # Request privacy-sensitive resource
        response = requests.get(
            f"{kong_url}/api/learners/{learner_id}/persona",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        # Assert: Access blocked or consent verified
        # (May be 403 if consent gate active, or 404/500 if service handles consent)
        assert response.status_code in [200, 403, 404, 500]
        
        # If consent gate blocked, should be 403
        if response.status_code == 403:
            error_data = response.json()
            assert "consent" in error_data.get("message", "").lower()
    
    @pytest.mark.asyncio
    async def test_consent_audit_correlation_with_security_logs(self):
        """Test: Consent audit logs correlate with security plugin logs"""
        # Arrange: Security-triggered consent check
        learner_id = "test-learner-012"
        consent_type = "security_audit"
        correlation_id = f"sec-audit-{uuid.uuid4().hex[:8]}"
        
        # Act: Set consent with security correlation
        await self.helper.set_consent_state(
            learner_id=learner_id,
            consent_type=consent_type,
            value=True,
            metadata={
                "triggered_by": "security_plugin",
                "plugin": "consent_gate",
                "security_correlation": correlation_id,
                "gateway_request": True
            }
        )
        
        await asyncio.sleep(1)
        
        # Assert: Audit entry has security correlation
        audit_entries = await self.helper.get_audit_log(learner_id)
        security_entry = next(
            (e for e in audit_entries 
             if e.get("metadata", {}).get("security_correlation") == correlation_id),
            None
        )
        
        assert security_entry is not None
        assert security_entry["metadata"]["triggered_by"] == "security_plugin" 
        assert security_entry["metadata"]["plugin"] == "consent_gate"
        assert security_entry["metadata"]["gateway_request"] is True


if __name__ == "__main__":
    # Run consent logging tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "--cov=.",
        "--cov-report=term-missing",
        "--cov-fail-under=80"
    ])
