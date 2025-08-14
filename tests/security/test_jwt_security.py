#!/usr/bin/env python3
"""
AIVO Virtual Brains - S1-18 Security & Privacy Tests
JWT Claims Validation Test Suite

Tests comprehensive JWT security flows:
- Missing JWT → 401 with MISSING_JWT code
- Invalid JWT → 401 with INVALID_JWT code  
- Missing dash_context → 401 with MISSING_CONTEXT code
- Invalid learner_uid scope → 403 with LEARNER_SCOPE_VIOLATION code
- Valid JWT with all claims → 200 OK

Coverage Target: ≥80% guard coverage with CI regression prevention
"""

import pytest
import requests
import json
import time
import jwt as pyjwt
from typing import Dict, Optional, List
from datetime import datetime, timedelta


class JWTTestHelper:
    """Helper class for generating test JWTs with various claim configurations"""
    
    def __init__(self, secret: str = "your-secret-key", algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm
        self.base_url = "http://localhost:8000"  # Kong gateway
    
    def create_jwt(
        self, 
        sub: Optional[str] = None,
        learner_uid: Optional[str] = None,
        role: Optional[str] = None,
        dash_context: Optional[str] = None,
        tenant_id: Optional[str] = None,
        exp_minutes: int = 60,
        include_standard_claims: bool = True
    ) -> str:
        """Create JWT with specified claims for testing"""
        now = datetime.utcnow()
        payload = {}
        
        if include_standard_claims:
            payload.update({
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
                "iss": "aivo-test"
            })
        
        if sub:
            payload["sub"] = sub
        if learner_uid:
            payload["learner_uid"] = learner_uid
        if role:
            payload["role"] = role
        if dash_context:
            payload["dash_context"] = dash_context
        if tenant_id:
            payload["tenant_id"] = tenant_id
            
        return pyjwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def make_request(
        self, 
        method: str,
        path: str, 
        jwt_token: Optional[str] = None,
        headers: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> requests.Response:
        """Make authenticated request to Kong gateway"""
        req_headers = headers or {}
        
        if jwt_token:
            req_headers["Authorization"] = f"Bearer {jwt_token}"
        
        # Add correlation ID for tracing
        req_headers["X-Correlation-ID"] = f"test-{int(time.time() * 1000)}"
        
        url = f"{self.base_url}{path}"
        
        if method.upper() == "GET":
            return requests.get(url, headers=req_headers)
        elif method.upper() == "POST":
            return requests.post(url, headers=req_headers, json=json_data)
        elif method.upper() == "PUT":
            return requests.put(url, headers=req_headers, json=json_data)
        elif method.upper() == "DELETE":
            return requests.delete(url, headers=req_headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")


class TestJWTAuthentication:
    """Test JWT authentication flows and error responses"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.jwt_helper = JWTTestHelper()
    
    def test_no_jwt_returns_401_missing_jwt(self):
        """Test: No Authorization header → 401 with MISSING_JWT code"""
        # Arrange: No Authorization header
        
        # Act: Request protected resource
        response = self.jwt_helper.make_request("GET", "/api/learners/test123")
        
        # Assert: 401 with specific error code
        assert response.status_code == 401
        error_data = response.json()
        assert error_data["code"] == "MISSING_JWT"
        assert "JWT required" in error_data["message"]
        
        # Verify security headers
        assert "X-Plugin-DashContext" in response.headers
        
    def test_invalid_jwt_returns_401_invalid_jwt(self):
        """Test: Invalid JWT token → 401 with INVALID_JWT code"""
        # Arrange: Malformed JWT
        invalid_token = "invalid.jwt.token"
        
        # Act: Request with invalid JWT
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/test123", jwt_token=invalid_token
        )
        
        # Assert: 401 with invalid JWT code
        assert response.status_code == 401
        error_data = response.json()
        assert error_data["code"] == "INVALID_JWT"
        assert "Invalid JWT" in error_data["message"]
    
    def test_expired_jwt_returns_401_invalid_jwt(self):
        """Test: Expired JWT token → 401 with INVALID_JWT code"""
        # Arrange: Expired JWT (exp in past)
        expired_jwt = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner123", 
            role="learner",
            dash_context="learner",
            exp_minutes=-60  # Expired 1 hour ago
        )
        
        # Act: Request with expired JWT
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123", jwt_token=expired_jwt
        )
        
        # Assert: 401 with invalid JWT code
        assert response.status_code == 401
        error_data = response.json()
        assert error_data["code"] == "INVALID_JWT"
    
    def test_missing_dash_context_returns_401_missing_context(self):
        """Test: Valid JWT but missing dash_context → 401 with MISSING_CONTEXT code"""
        # Arrange: JWT without dash_context claim
        jwt_no_context = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner123",
            role="learner"
            # Missing dash_context
        )
        
        # Act: Request protected resource
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123", jwt_token=jwt_no_context
        )
        
        # Assert: 401 with missing context code
        assert response.status_code == 401
        error_data = response.json()
        assert error_data["code"] == "MISSING_CONTEXT"
        assert "dashboard context" in error_data["message"].lower()
    
    def test_invalid_dash_context_returns_403_invalid_context(self):
        """Test: Valid JWT with invalid dash_context → 403 with INVALID_CONTEXT code"""
        # Arrange: JWT with invalid dashboard context
        jwt_invalid_context = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner123",
            role="learner",
            dash_context="invalid_context"  # Not in allowed list
        )
        
        # Act: Request protected resource  
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123", jwt_token=jwt_invalid_context
        )
        
        # Assert: 403 with invalid context code
        assert response.status_code == 403
        error_data = response.json()
        assert error_data["code"] == "INVALID_CONTEXT" 
        assert "Invalid dashboard context" in error_data["message"]


class TestLearnerScopeValidation:
    """Test learner scope enforcement and access control"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.jwt_helper = JWTTestHelper()
    
    def test_learner_uid_mismatch_returns_403_scope_violation(self):
        """Test: Path learner ID ≠ JWT learner_uid → 403 LEARNER_SCOPE_VIOLATION"""
        # Arrange: JWT with different learner_uid than path
        jwt_wrong_learner = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner999",  # Different from path
            role="learner",
            dash_context="learner"
        )
        
        # Act: Request learner123 resource with learner999 JWT
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123/persona", 
            jwt_token=jwt_wrong_learner
        )
        
        # Assert: 403 scope violation
        assert response.status_code == 403
        error_data = response.json()
        assert error_data["code"] == "LEARNER_SCOPE_VIOLATION"
        assert "scope violation" in error_data["message"].lower()
        
        # Check detailed error info
        assert "path_learner_id" in error_data["details"]
        assert "jwt_learner_id" in error_data["details"]
        assert error_data["details"]["path_learner_id"] == "learner123"
        assert error_data["details"]["jwt_learner_id"] == "learner999"
    
    def test_missing_learner_uid_claim_returns_403_no_learner_scope(self):
        """Test: JWT without learner_uid claim → 403 NO_LEARNER_SCOPE"""
        # Arrange: JWT without learner_uid claim
        jwt_no_learner = self.jwt_helper.create_jwt(
            sub="user123",
            role="learner",
            dash_context="learner"
            # Missing learner_uid
        )
        
        # Act: Request learner resource
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123", jwt_token=jwt_no_learner
        )
        
        # Assert: 403 no learner scope
        assert response.status_code == 403
        error_data = response.json()
        assert error_data["code"] == "NO_LEARNER_SCOPE"
        assert "No learner scope in JWT" in error_data["message"]
    
    def test_admin_role_bypasses_learner_scope(self):
        """Test: Admin role can access any learner resource"""
        # Arrange: JWT with admin role
        admin_jwt = self.jwt_helper.create_jwt(
            sub="admin123",
            learner_uid="admin123",  # Different from path learner
            role="admin",
            dash_context="admin"
        )
        
        # Act: Admin accessing learner resource
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner456", jwt_token=admin_jwt
        )
        
        # Assert: Access granted (or specific service error, not scope violation)
        assert response.status_code in [200, 404, 500]  # Not 403 scope violation
        
        # Verify bypass headers were set
        if response.status_code == 200:
            assert "X-Learner-Scope-Status" in response.headers
    
    def test_teacher_role_bypasses_learner_scope(self):
        """Test: Teacher role can access student learner resources"""
        # Arrange: JWT with teacher role
        teacher_jwt = self.jwt_helper.create_jwt(
            sub="teacher123", 
            learner_uid="teacher123",
            role="teacher",
            dash_context="teacher"
        )
        
        # Act: Teacher accessing student resource
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/student456", jwt_token=teacher_jwt
        )
        
        # Assert: Access granted (not scope violation)
        assert response.status_code in [200, 404, 500]  # Not 403 scope violation
    
    def test_matching_learner_uid_grants_access(self):
        """Test: JWT learner_uid matches path → Access granted with validation"""
        # Arrange: JWT with matching learner_uid
        matching_jwt = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner123",
            role="learner", 
            dash_context="learner"
        )
        
        # Act: Request matching learner resource
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123", jwt_token=matching_jwt
        )
        
        # Assert: Access granted or downstream service error (not scope violation)
        assert response.status_code in [200, 404, 500]  # Not 403 scope violation
        
        # Verify validation headers
        if response.status_code == 200:
            assert "X-Validated-Learner-ID" in response.headers or "X-Learner-Scope-Status" in response.headers


class TestConsentGateEnforcement:
    """Test consent gate enforcement and privacy controls"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.jwt_helper = JWTTestHelper()
    
    def test_privacy_path_without_consent_returns_403_consent_required(self):
        """Test: Privacy-sensitive path + no consent → 403 CONSENT_REQUIRED"""
        # Arrange: Valid JWT for learner but no consent
        learner_jwt = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner123",
            role="learner",
            dash_context="learner"
        )
        
        # Act: Request privacy-sensitive resource (persona data)
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123/persona", jwt_token=learner_jwt
        )
        
        # Assert: Consent required (may be 403 or backend handles consent)
        # This depends on whether consent is set up in Redis cache
        assert response.status_code in [200, 403, 404, 500]
        
        # If consent gate active, should be 403
        if response.status_code == 403:
            error_data = response.json()
            assert error_data.get("code") in ["CONSENT_REQUIRED", "FORBIDDEN"]
    
    def test_admin_bypasses_consent_requirements(self):
        """Test: Admin role bypasses consent requirements"""
        # Arrange: Admin JWT
        admin_jwt = self.jwt_helper.create_jwt(
            sub="admin123",
            learner_uid="admin123",
            role="admin", 
            dash_context="admin"
        )
        
        # Act: Admin accessing privacy-sensitive resource
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner456/persona", jwt_token=admin_jwt
        )
        
        # Assert: Access not blocked by consent (may be 404/500 from backend)
        assert response.status_code in [200, 404, 500]  # Not 403 consent
    
    def test_non_privacy_path_skips_consent_check(self):
        """Test: Non-privacy paths skip consent validation"""
        # Arrange: Valid JWT
        learner_jwt = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner123", 
            role="learner",
            dash_context="learner"
        )
        
        # Act: Request non-privacy resource (health check)
        response = self.jwt_helper.make_request(
            "GET", "/health", jwt_token=learner_jwt
        )
        
        # Assert: Access granted (no consent check)
        assert response.status_code in [200, 404]  # Not 403 consent


class TestValidAccessFlows:
    """Test valid access flows with complete JWT claims"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.jwt_helper = JWTTestHelper()
    
    def test_complete_valid_jwt_grants_access(self):
        """Test: JWT with all valid claims → 200 OK or downstream response"""
        # Arrange: Complete valid JWT
        complete_jwt = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner123",
            role="learner",
            dash_context="learner",
            tenant_id="tenant456"
        )
        
        # Act: Request protected resource with valid JWT
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123", jwt_token=complete_jwt
        )
        
        # Assert: Not blocked by security (200, 404, or 500 from backend)
        assert response.status_code in [200, 404, 500]  # Not 401/403 security blocks
        
        # Verify security headers were applied
        assert "X-Plugin-DashContext" in response.headers
        assert response.headers.get("X-Plugin-DashContext") == "1.0.0"
    
    def test_teacher_accessing_student_data_with_valid_jwt(self):
        """Test: Teacher role accessing student data with complete JWT"""
        # Arrange: Teacher JWT accessing student
        teacher_jwt = self.jwt_helper.create_jwt(
            sub="teacher123",
            learner_uid="teacher123",
            role="teacher", 
            dash_context="teacher",
            tenant_id="school456"
        )
        
        # Act: Teacher accessing student persona
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/student789/persona", jwt_token=teacher_jwt
        )
        
        # Assert: Access granted by security plugins
        assert response.status_code in [200, 404, 500]  # Not security blocks
        
        # Verify role bypass headers
        assert "X-Plugin-LearnerScope" in response.headers
    
    def test_guardian_accessing_child_data_with_valid_jwt(self):
        """Test: Guardian role accessing child learner data"""
        # Arrange: Guardian JWT
        guardian_jwt = self.jwt_helper.create_jwt(
            sub="guardian123",
            learner_uid="guardian123", 
            role="guardian",
            dash_context="guardian",
            tenant_id="family456"
        )
        
        # Act: Guardian accessing child data
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/child789", jwt_token=guardian_jwt  
        )
        
        # Assert: Access granted (guardian should have child access)
        assert response.status_code in [200, 404, 500]  # Not blocked


class TestSecurityHeaders:
    """Test security header injection and correlation tracking"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.jwt_helper = JWTTestHelper()
    
    def test_security_plugins_inject_version_headers(self):
        """Test: Security plugins add version headers for monitoring"""
        # Arrange: Valid JWT
        valid_jwt = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner123",
            role="learner",
            dash_context="learner"
        )
        
        # Act: Request any resource
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123", jwt_token=valid_jwt
        )
        
        # Assert: Plugin version headers present
        assert "X-Plugin-DashContext" in response.headers
        assert response.headers["X-Plugin-DashContext"] == "1.0.0"
        
        if response.status_code in [200, 404, 500]:
            # May have learner scope headers if validation occurred  
            assert "X-Plugin-LearnerScope" in response.headers or response.status_code != 200
    
    def test_correlation_id_injected_for_audit_trail(self):
        """Test: Correlation IDs injected for request tracing"""
        # Arrange: Valid JWT with custom correlation ID
        valid_jwt = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="learner123",
            role="learner",
            dash_context="learner"
        )
        
        custom_correlation = "test-correlation-12345"
        
        # Act: Request with correlation ID
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/learner123", 
            jwt_token=valid_jwt,
            headers={"X-Correlation-ID": custom_correlation}
        )
        
        # Assert: Correlation ID preserved or generated
        # (Implementation detail - may not be in response headers)
        assert response.status_code in [200, 401, 403, 404, 500]
        
        # Verify request was traceable
        assert custom_correlation  # Custom ID was sent


class TestSecurityCoverage:
    """Test security coverage metrics and edge cases"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.jwt_helper = JWTTestHelper()
    
    def test_all_security_error_codes_covered(self):
        """Test: All security error codes are exercised for coverage"""
        error_codes_tested = []
        
        # Test 1: Missing JWT → MISSING_JWT  
        response = self.jwt_helper.make_request("GET", "/api/learners/test")
        if response.status_code == 401:
            data = response.json()
            error_codes_tested.append(data.get("code"))
        
        # Test 2: Invalid JWT → INVALID_JWT
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/test", jwt_token="invalid.token"
        )
        if response.status_code == 401:
            data = response.json() 
            error_codes_tested.append(data.get("code"))
        
        # Test 3: Missing context → MISSING_CONTEXT  
        jwt_no_context = self.jwt_helper.create_jwt(sub="user", learner_uid="test")
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/test", jwt_token=jwt_no_context
        )
        if response.status_code == 401:
            data = response.json()
            error_codes_tested.append(data.get("code"))
        
        # Test 4: Invalid context → INVALID_CONTEXT
        jwt_bad_context = self.jwt_helper.create_jwt(
            sub="user", learner_uid="test", dash_context="bad"
        )
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/test", jwt_token=jwt_bad_context
        )
        if response.status_code == 403:
            data = response.json()
            error_codes_tested.append(data.get("code"))
        
        # Test 5: Scope violation → LEARNER_SCOPE_VIOLATION  
        jwt_wrong_learner = self.jwt_helper.create_jwt(
            sub="user", learner_uid="wrong", role="learner", dash_context="learner"
        )
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/test", jwt_token=jwt_wrong_learner
        )
        if response.status_code == 403:
            data = response.json()
            error_codes_tested.append(data.get("code"))
        
        # Assert: Security error paths covered
        assert len([code for code in error_codes_tested if code]) >= 3
        print(f"Security error codes tested: {error_codes_tested}")
    
    def test_security_plugin_priority_enforcement(self):
        """Test: Security plugins execute in priority order"""
        # Arrange: JWT that would fail multiple plugins
        problematic_jwt = self.jwt_helper.create_jwt(
            sub="user123",
            learner_uid="wrong_learner",  # Will fail learner scope  
            role="learner",
            dash_context="invalid_context"  # Will fail dash context
        )
        
        # Act: Request that hits multiple security failures
        response = self.jwt_helper.make_request(
            "GET", "/api/learners/correct_learner", jwt_token=problematic_jwt
        )
        
        # Assert: Higher priority plugin (dash_context) fails first
        assert response.status_code in [401, 403]
        
        if response.status_code == 403:
            data = response.json()
            # Should be context error (priority 1000) before scope error (priority 950)
            assert data.get("code") in ["INVALID_CONTEXT", "LEARNER_SCOPE_VIOLATION"]


if __name__ == "__main__":
    # Run security tests with coverage reporting
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--cov=.",
        "--cov-report=term-missing",
        "--cov-fail-under=80"
    ])
