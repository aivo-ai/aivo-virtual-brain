"""
Tests for Enterprise SSO and JIT Provisioning

Covers SAML and OIDC authentication flows, JIT user provisioning,
group mapping, and security validations.
"""

import base64
import json
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models import SSOProvider, SSOSession, SSOAssertionLog
from app.enterprise import SAMLProvider, OIDCProvider, ACSProcessor, GroupMapper
from app.config import get_settings

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sso.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module")
def setup_database():
    """Setup test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Create database session for testing."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_tenant_id():
    """Test tenant ID."""
    return uuid4()


@pytest.fixture
def saml_provider_config(test_tenant_id, db_session):
    """Create test SAML provider configuration."""
    config = SSOProvider(
        id=uuid4(),
        tenant_id=test_tenant_id,
        provider_type="saml",
        provider_name="test-saml",
        enabled=True,
        saml_idp_entity_id="https://idp.test.com",
        saml_idp_sso_url="https://idp.test.com/sso",
        saml_idp_sls_url="https://idp.test.com/sls",
        saml_idp_x509_cert="test-cert",
        saml_name_id_format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        group_mapping_config={
            "explicit_mappings": {
                "Administrators": ["admin"],
                "Support Staff": ["support"]
            },
            "require_staff_role": True
        },
        jit_enabled=True,
        jit_default_role="staff",
        jit_require_approval=False
    )
    
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    
    return config


@pytest.fixture
def oidc_provider_config(test_tenant_id, db_session):
    """Create test OIDC provider configuration."""
    config = SSOProvider(
        id=uuid4(),
        tenant_id=test_tenant_id,
        provider_type="oidc",
        provider_name="test-oidc",
        enabled=True,
        oidc_issuer="https://oidc.test.com",
        oidc_authorization_endpoint="https://oidc.test.com/auth",
        oidc_token_endpoint="https://oidc.test.com/token",
        oidc_userinfo_endpoint="https://oidc.test.com/userinfo",
        oidc_jwks_uri="https://oidc.test.com/jwks",
        oidc_client_id="test-client-id",
        oidc_client_secret="test-client-secret",
        group_mapping_config={
            "explicit_mappings": {
                "admin-group": ["admin"],
                "support-group": ["support"]
            },
            "require_staff_role": True
        },
        jit_enabled=True,
        jit_default_role="staff",
        jit_require_approval=True
    )
    
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    
    return config


class TestSAMLAuthentication:
    """Test SAML authentication flows."""
    
    def test_saml_metadata_generation(self, setup_database, saml_provider_config):
        """Test SAML SP metadata generation."""
        response = client.get(
            f"/sso/saml/metadata/{saml_provider_config.tenant_id}/{saml_provider_config.provider_name}"
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml; charset=utf-8"
        assert "EntityDescriptor" in response.text
        assert "SPSSODescriptor" in response.text
    
    
    def test_saml_login_initiation(self, setup_database, saml_provider_config):
        """Test SP-initiated SAML login."""
        response = client.get(
            f"/sso/saml/login/{saml_provider_config.tenant_id}/{saml_provider_config.provider_name}",
            allow_redirects=False
        )
        
        assert response.status_code == 302
        redirect_url = response.headers["location"]
        assert "https://idp.test.com/sso" in redirect_url
        assert "SAMLRequest=" in redirect_url
    
    
    def test_saml_assertion_validation_success(self, setup_database):
        """Test successful SAML assertion validation."""
        # Create mock SAML response
        saml_response = self._create_mock_saml_response(
            subject="test@example.com",
            groups=["Administrators"],
            valid=True
        )
        
        with patch('app.enterprise.saml.SAMLProvider.validate_assertion') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'signature_valid': True,
                'timestamp_valid': True,
                'audience_valid': True,
                'user_data': {
                    'nameid': 'test@example.com',
                    'email': 'test@example.com',
                    'display_name': 'Test User',
                    'groups': ['Administrators'],
                    'subject': 'test@example.com'
                },
                'session_data': {
                    'assertion_id': 'test-assertion-id',
                    'session_index': 'test-session-index'
                }
            }
            
            with patch('app.enterprise.acs.ACSProcessor._check_user_exists') as mock_user_exists:
                mock_user_exists.return_value = {'exists': False, 'user_id': None}
                
                with patch('app.enterprise.acs.ACSProcessor._create_user_in_user_service') as mock_create_user:
                    mock_create_user.return_value = uuid4()
                    
                    response = client.post(
                        "/sso/saml/acs",
                        data={
                            "SAMLResponse": saml_response,
                            "RelayState": f"{uuid4()}:test-saml:original-state"
                        }
                    )
                    
                    assert response.status_code == 200
                    assert "Login Successful" in response.text
    
    
    def test_saml_assertion_validation_failure(self, setup_database):
        """Test SAML assertion validation failure."""
        # Create invalid SAML response
        saml_response = base64.b64encode(b"invalid-saml-response").decode()
        
        response = client.post(
            "/sso/saml/acs",
            data={
                "SAMLResponse": saml_response,
                "RelayState": f"{uuid4()}:test-saml:original-state"
            }
        )
        
        assert response.status_code == 400
        assert "SAML" in response.json()["detail"]
    
    
    def _create_mock_saml_response(self, subject: str, groups: list, valid: bool) -> str:
        """Create mock SAML response for testing."""
        # This would create a proper SAML response XML in a real implementation
        mock_response = {
            "subject": subject,
            "groups": groups,
            "valid": valid
        }
        return base64.b64encode(json.dumps(mock_response).encode()).decode()


class TestOIDCAuthentication:
    """Test OIDC authentication flows."""
    
    def test_oidc_login_initiation(self, setup_database, oidc_provider_config):
        """Test OIDC authorization flow initiation."""
        with patch('app.enterprise.oidc.OIDCProvider.discover_configuration') as mock_discover:
            mock_discover.return_value = {
                "authorization_endpoint": "https://oidc.test.com/auth",
                "token_endpoint": "https://oidc.test.com/token"
            }
            
            response = client.get(
                f"/sso/oidc/login/{oidc_provider_config.tenant_id}/{oidc_provider_config.provider_name}",
                allow_redirects=False
            )
            
            assert response.status_code == 302
            redirect_url = response.headers["location"]
            assert "https://oidc.test.com/auth" in redirect_url
            assert "response_type=code" in redirect_url
            assert "client_id=test-client-id" in redirect_url
    
    
    @patch('app.enterprise.oidc.OIDCProvider.exchange_code_for_tokens')
    @patch('app.enterprise.acs.ACSProcessor._check_user_exists')
    @patch('app.enterprise.acs.ACSProcessor._create_jit_approval_request')
    def test_oidc_callback_with_jit_approval(
        self,
        mock_create_approval,
        mock_user_exists,
        mock_exchange_tokens,
        setup_database,
        oidc_provider_config
    ):
        """Test OIDC callback with JIT approval required."""
        
        # Mock token exchange
        mock_exchange_tokens.return_value = {
            'tokens': {'access_token': 'test-token'},
            'id_token_claims': {'sub': 'test-user-id'},
            'user_info': {
                'sub': 'test-user-id',
                'email': 'test@example.com',
                'name': 'Test User',
                'groups': ['admin-group']
            }
        }
        
        # Mock user doesn't exist
        mock_user_exists.return_value = {'exists': False, 'user_id': None}
        
        # Mock approval request creation
        mock_approval_request = Mock()
        mock_approval_request.id = uuid4()
        mock_create_approval.return_value = mock_approval_request
        
        state = f"{oidc_provider_config.tenant_id}:{oidc_provider_config.provider_name}:test-state"
        
        response = client.get(
            "/sso/oidc/callback",
            params={
                "code": "test-auth-code",
                "state": state
            }
        )
        
        assert response.status_code == 200
        assert "Account Approval Pending" in response.text
    
    
    def test_oidc_callback_error(self, setup_database):
        """Test OIDC callback with error response."""
        response = client.get(
            "/sso/oidc/callback",
            params={
                "error": "access_denied",
                "error_description": "User denied access",
                "state": "test-state"
            }
        )
        
        assert response.status_code == 400
        assert "access_denied" in response.json()["detail"]


class TestGroupMapping:
    """Test group to role mapping functionality."""
    
    def test_explicit_group_mapping(self):
        """Test explicit group to role mapping."""
        mapper = GroupMapper()
        
        mapping_config = {
            "explicit_mappings": {
                "Domain Admins": ["admin"],
                "IT Support": ["support"],
                "Staff": ["staff"]
            },
            "require_staff_role": True
        }
        
        # Test admin group
        roles = mapper.map_groups_to_roles(["Domain Admins"], mapping_config)
        assert "admin" in roles
        assert "staff" in roles  # Should include staff role
        
        # Test support group
        roles = mapper.map_groups_to_roles(["IT Support"], mapping_config)
        assert "support" in roles
        assert "staff" in roles
        
        # Test unknown group
        roles = mapper.map_groups_to_roles(["Unknown Group"], mapping_config)
        assert roles == ["staff"]  # Should default to staff
    
    
    def test_pattern_based_mapping(self):
        """Test pattern-based group mapping."""
        mapper = GroupMapper()
        
        mapping_config = {
            "pattern_mappings": [
                {"pattern": "*admin*", "roles": ["admin"]},
                {"pattern": "regex:^support.*", "roles": ["support"]}
            ],
            "require_staff_role": True
        }
        
        # Test pattern matching
        roles = mapper.map_groups_to_roles(["system-admin"], mapping_config)
        assert "admin" in roles
        
        roles = mapper.map_groups_to_roles(["support-team"], mapping_config)
        assert "support" in roles
    
    
    def test_role_hierarchy(self):
        """Test role hierarchy application."""
        mapper = GroupMapper()
        
        mapping_config = {
            "explicit_mappings": {"Admins": ["admin"]},
            "role_hierarchy": {
                "admin": ["staff", "support"]
            },
            "require_staff_role": False
        }
        
        roles = mapper.map_groups_to_roles(["Admins"], mapping_config)
        assert "admin" in roles
        assert "staff" in roles
        assert "support" in roles
    
    
    def test_mapping_config_validation(self):
        """Test mapping configuration validation."""
        mapper = GroupMapper()
        
        # Valid config
        valid_config = {
            "explicit_mappings": {"Group1": ["role1"]},
            "pattern_mappings": [{"pattern": "*test*", "roles": ["test"]}]
        }
        
        result = mapper.validate_mapping_config(valid_config)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        
        # Invalid config
        invalid_config = {
            "explicit_mappings": "not-a-dict",
            "pattern_mappings": [{"pattern": "*test*"}]  # Missing roles
        }
        
        result = mapper.validate_mapping_config(invalid_config)
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestJITProvisioning:
    """Test Just-In-Time user provisioning."""
    
    @patch('app.enterprise.acs.ACSProcessor._check_user_exists')
    @patch('app.enterprise.acs.ACSProcessor._create_user_in_user_service')
    def test_jit_auto_provisioning(
        self,
        mock_create_user,
        mock_user_exists,
        setup_database,
        db_session
    ):
        """Test automatic JIT user creation."""
        
        mock_user_exists.return_value = {'exists': False, 'user_id': None}
        new_user_id = uuid4()
        mock_create_user.return_value = new_user_id
        
        # Create provider with auto JIT
        provider_config = SSOProvider(
            tenant_id=uuid4(),
            provider_type="oidc",
            provider_name="test-auto-jit",
            jit_enabled=True,
            jit_require_approval=False,
            group_mapping_config={}
        )
        
        db_session.add(provider_config)
        db_session.commit()
        
        acs_processor = ACSProcessor(db_session)
        
        user_data = {
            'subject': 'test-user',
            'email': 'test@example.com',
            'display_name': 'Test User',
            'groups': []
        }
        
        session_data = {'subject': 'test-user'}
        
        result = await acs_processor._process_user_and_create_session(
            provider_config=provider_config,
            user_data=user_data,
            session_data=session_data,
            tenant_id=provider_config.tenant_id,
            assertion_log_id=uuid4()
        )
        
        assert result['user_id'] == str(new_user_id)
        assert result['jit_status'] == 'created'
        
        # Verify session was created
        session = db_session.query(SSOSession).filter(
            SSOSession.session_id == result['session_id']
        ).first()
        
        assert session is not None
        assert session.user_id == new_user_id
        assert session.email == 'test@example.com'
    
    
    @patch('app.enterprise.acs.ACSProcessor._check_user_exists')
    @patch('app.enterprise.acs.ACSProcessor._send_approval_request')
    def test_jit_approval_required(
        self,
        mock_send_approval,
        mock_user_exists,
        setup_database,
        db_session
    ):
        """Test JIT provisioning with approval required."""
        
        mock_user_exists.return_value = {'exists': False, 'user_id': None}
        mock_send_approval.return_value = None
        
        # Create provider requiring approval
        provider_config = SSOProvider(
            tenant_id=uuid4(),
            provider_type="saml",
            provider_name="test-approval-jit",
            jit_enabled=True,
            jit_require_approval=True,
            group_mapping_config={}
        )
        
        db_session.add(provider_config)
        db_session.commit()
        
        acs_processor = ACSProcessor(db_session)
        
        user_data = {
            'subject': 'test-user',
            'email': 'approval@example.com',
            'display_name': 'Approval User',
            'groups': ['admin-group']
        }
        
        session_data = {'subject': 'test-user'}
        
        result = await acs_processor._process_user_and_create_session(
            provider_config=provider_config,
            user_data=user_data,
            session_data=session_data,
            tenant_id=provider_config.tenant_id,
            assertion_log_id=uuid4()
        )
        
        assert result['user_id'] is None
        assert result['jit_status'] == 'pending'
        assert result['jit_approval_request_id'] is not None
        
        # Verify session was created with pending status
        session = db_session.query(SSOSession).filter(
            SSOSession.session_id == result['session_id']
        ).first()
        
        assert session is not None
        assert session.user_id is None
        assert session.jit_status == 'pending'


class TestSessionManagement:
    """Test SSO session management."""
    
    def test_get_session_info(self, setup_database, db_session):
        """Test retrieving session information."""
        
        # Create test session
        session = SSOSession(
            provider_id=uuid4(),
            tenant_id=uuid4(),
            session_id="test-session-123",
            subject="test-user",
            email="test@example.com",
            display_name="Test User",
            session_state="active",
            expires_at=datetime.utcnow() + timedelta(hours=8)
        )
        
        db_session.add(session)
        db_session.commit()
        
        response = client.get("/sso/session/test-session-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["email"] == "test@example.com"
        assert data["display_name"] == "Test User"
    
    
    def test_session_logout(self, setup_database, db_session):
        """Test session logout."""
        
        # Create test session
        session = SSOSession(
            provider_id=uuid4(),
            tenant_id=uuid4(),
            session_id="test-logout-session",
            subject="test-user",
            email="test@example.com",
            session_state="active",
            expires_at=datetime.utcnow() + timedelta(hours=8)
        )
        
        db_session.add(session)
        db_session.commit()
        
        response = client.post("/sso/session/test-logout-session/logout")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Session logged out successfully"
        
        # Verify session state changed
        db_session.refresh(session)
        assert session.session_state == "logged_out"
    
    
    def test_support_token_creation(self, setup_database, db_session):
        """Test JIT support token creation."""
        
        # Create pending JIT session
        session = SSOSession(
            provider_id=uuid4(),
            tenant_id=uuid4(),
            session_id="test-pending-session",
            subject="test-user",
            email="pending@example.com",
            jit_status="pending",
            session_state="active",
            expires_at=datetime.utcnow() + timedelta(hours=8)
        )
        
        db_session.add(session)
        db_session.commit()
        
        response = client.post(
            "/sso/jit/support-token",
            json={
                "session_id": "test-pending-session",
                "justification": "Emergency access needed"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "support_token" in data
        assert data["scope"] == "read-only"
        assert "expires_at" in data


class TestSecurityValidations:
    """Test security validations and error handling."""
    
    def test_invalid_saml_signature(self, setup_database):
        """Test handling of invalid SAML signatures."""
        
        with patch('app.enterprise.saml.SAMLProvider.validate_assertion') as mock_validate:
            mock_validate.return_value = {
                'valid': False,
                'signature_valid': False,
                'timestamp_valid': True,
                'audience_valid': True,
                'validation_errors': ['Invalid signature']
            }
            
            response = client.post(
                "/sso/saml/acs",
                data={
                    "SAMLResponse": "invalid-signature-response",
                    "RelayState": f"{uuid4()}:test-saml:state"
                }
            )
            
            assert response.status_code == 400
            assert "validation failed" in response.json()["detail"]
    
    
    def test_expired_saml_assertion(self, setup_database):
        """Test handling of expired SAML assertions."""
        
        with patch('app.enterprise.saml.SAMLProvider.validate_assertion') as mock_validate:
            mock_validate.return_value = {
                'valid': False,
                'signature_valid': True,
                'timestamp_valid': False,
                'audience_valid': True,
                'validation_errors': ['Assertion expired']
            }
            
            response = client.post(
                "/sso/saml/acs",
                data={
                    "SAMLResponse": "expired-assertion",
                    "RelayState": f"{uuid4()}:test-saml:state"
                }
            )
            
            assert response.status_code == 400
    
    
    def test_missing_required_attributes(self, setup_database):
        """Test handling of missing required attributes."""
        
        with patch('app.enterprise.saml.SAMLProvider.validate_assertion') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'signature_valid': True,
                'timestamp_valid': True,
                'audience_valid': True,
                'user_data': {
                    'nameid': 'test-user',
                    'subject': 'test-user',
                    # Missing email
                    'groups': []
                }
            }
            
            with patch('app.enterprise.acs.ACSProcessor._handle_jit_provisioning') as mock_jit:
                mock_jit.side_effect = Exception("Email required for JIT provisioning")
                
                response = client.post(
                    "/sso/saml/acs",
                    data={
                        "SAMLResponse": "missing-email-response",
                        "RelayState": f"{uuid4()}:test-saml:state"
                    }
                )
                
                assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
