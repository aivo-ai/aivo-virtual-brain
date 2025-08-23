"""
Assertion Consumer Service (ACS) for SAML SSO

Handles SAML Response processing, validation, and user session creation.
Integrates with JIT provisioning and group mapping.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .saml import SAMLProvider, SAMLError
from .oidc import OIDCProvider, OIDCError
from .group_map import GroupMapper
from ..models import SSOProvider, SSOSession, SSOAssertionLog, JITApprovalRequest
from ..config import get_settings


class ACSProcessor:
    """Assertion Consumer Service processor for SAML and OIDC."""
    
    def __init__(self, db_session: Session):
        """Initialize ACS processor."""
        self.db = db_session
        self.settings = get_settings()
        self.group_mapper = GroupMapper()
    
    
    async def process_saml_response(
        self, 
        tenant_id: UUID, 
        provider_name: str, 
        saml_response: str,
        relay_state: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process SAML Response and create user session.
        
        Args:
            tenant_id: Tenant ID
            provider_name: SSO provider name
            saml_response: Base64-encoded SAML Response
            relay_state: SAML RelayState parameter
            request_id: Original AuthnRequest ID (for SP-initiated)
            
        Returns:
            Dictionary with session information and user data
        """
        try:
            # Get provider configuration
            provider_config = self._get_provider_config(tenant_id, provider_name, "saml")
            
            # Initialize SAML provider
            saml_provider = SAMLProvider(provider_config.config)
            
            # Validate SAML assertion
            validation_result = saml_provider.validate_assertion(saml_response, request_id)
            
            # Log assertion for audit
            assertion_log = await self._log_saml_assertion(
                provider_config, validation_result, tenant_id
            )
            
            if not validation_result['valid']:
                raise HTTPException(
                    status_code=400,
                    detail=f"SAML assertion validation failed: {validation_result.get('validation_errors', [])}"
                )
            
            # Process user and create session
            session_result = await self._process_user_and_create_session(
                provider_config=provider_config,
                user_data=validation_result['user_data'],
                session_data=validation_result['session_data'],
                tenant_id=tenant_id,
                assertion_log_id=assertion_log.id
            )
            
            return {
                **session_result,
                'relay_state': relay_state,
                'assertion_log_id': str(assertion_log.id)
            }
            
        except SAMLError as e:
            # Log failed assertion
            await self._log_failed_assertion(
                tenant_id, provider_name, "saml", e.error_code, e.message
            )
            raise HTTPException(status_code=400, detail=f"SAML error: {e.message}")
        
        except Exception as e:
            # Log unexpected error
            await self._log_failed_assertion(
                tenant_id, provider_name, "saml", "PROCESSING_ERROR", str(e)
            )
            raise HTTPException(status_code=500, detail=f"SAML processing failed: {str(e)}")
    
    
    async def process_oidc_callback(
        self,
        tenant_id: UUID,
        provider_name: str,
        code: str,
        state: str,
        expected_state: str,
        nonce: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process OIDC authorization callback.
        
        Args:
            tenant_id: Tenant ID
            provider_name: SSO provider name
            code: Authorization code
            state: State parameter
            expected_state: Expected state value
            nonce: Expected nonce value
            
        Returns:
            Dictionary with session information and user data
        """
        try:
            # Get provider configuration
            provider_config = self._get_provider_config(tenant_id, provider_name, "oidc")
            
            # Initialize OIDC provider
            oidc_provider = OIDCProvider(provider_config.config)
            
            # Exchange code for tokens
            token_result = await oidc_provider.exchange_code_for_tokens(code, state, expected_state)
            
            # Extract user data
            user_data = oidc_provider.extract_user_data(
                token_result['user_info'],
                token_result['id_token_claims']
            )
            
            # Create session data
            session_data = {
                'subject': user_data['subject'],
                'tokens': token_result['tokens']
            }
            
            # Log assertion for audit
            assertion_log = await self._log_oidc_assertion(
                provider_config, user_data, session_data, tenant_id
            )
            
            # Process user and create session
            session_result = await self._process_user_and_create_session(
                provider_config=provider_config,
                user_data=user_data,
                session_data=session_data,
                tenant_id=tenant_id,
                assertion_log_id=assertion_log.id
            )
            
            return {
                **session_result,
                'assertion_log_id': str(assertion_log.id)
            }
            
        except OIDCError as e:
            # Log failed assertion
            await self._log_failed_assertion(
                tenant_id, provider_name, "oidc", e.error_code, e.message
            )
            raise HTTPException(status_code=400, detail=f"OIDC error: {e.message}")
        
        except Exception as e:
            # Log unexpected error
            await self._log_failed_assertion(
                tenant_id, provider_name, "oidc", "PROCESSING_ERROR", str(e)
            )
            raise HTTPException(status_code=500, detail=f"OIDC processing failed: {str(e)}")
    
    
    async def _process_user_and_create_session(
        self,
        provider_config: SSOProvider,
        user_data: Dict[str, Any],
        session_data: Dict[str, Any],
        tenant_id: UUID,
        assertion_log_id: UUID
    ) -> Dict[str, Any]:
        """Process user data and create SSO session."""
        
        # Map groups to roles
        mapped_roles = self.group_mapper.map_groups_to_roles(
            user_data.get('groups', []),
            provider_config.group_mapping_config or {}
        )
        
        # Check if user exists or needs JIT provisioning
        user_id = None
        jit_status = None
        jit_approval_request_id = None
        
        if provider_config.jit_enabled:
            # Attempt JIT provisioning
            jit_result = await self._handle_jit_provisioning(
                provider_config=provider_config,
                user_data=user_data,
                mapped_roles=mapped_roles,
                tenant_id=tenant_id
            )
            
            user_id = jit_result.get('user_id')
            jit_status = jit_result.get('status')
            jit_approval_request_id = jit_result.get('approval_request_id')
        
        # Create SSO session
        session_expires = datetime.utcnow() + timedelta(
            minutes=self.settings.sso_session_ttl_minutes
        )
        
        sso_session = SSOSession(
            provider_id=provider_config.id,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=str(uuid4()),
            nameid=user_data.get('nameid') or user_data.get('subject'),
            subject=user_data.get('subject'),
            email=user_data.get('email'),
            display_name=user_data.get('display_name'),
            groups=user_data.get('groups'),
            attributes=user_data.get('attributes'),
            session_state="active",
            jit_status=jit_status,
            jit_approval_request_id=jit_approval_request_id,
            expires_at=session_expires
        )
        
        self.db.add(sso_session)
        self.db.commit()
        self.db.refresh(sso_session)
        
        # Update assertion log with results
        assertion_log = self.db.query(SSOAssertionLog).filter(
            SSOAssertionLog.id == assertion_log_id
        ).first()
        
        if assertion_log:
            assertion_log.user_created = jit_result.get('user_created', False) if provider_config.jit_enabled else False
            assertion_log.user_updated = jit_result.get('user_updated', False) if provider_config.jit_enabled else False
            assertion_log.roles_assigned = mapped_roles
            assertion_log.jit_approval_required = (jit_status == "pending")
            self.db.commit()
        
        return {
            'session_id': sso_session.session_id,
            'user_id': str(user_id) if user_id else None,
            'jit_status': jit_status,
            'jit_approval_request_id': str(jit_approval_request_id) if jit_approval_request_id else None,
            'mapped_roles': mapped_roles,
            'expires_at': session_expires.isoformat(),
            'user_data': {
                'email': user_data.get('email'),
                'display_name': user_data.get('display_name'),
                'groups': user_data.get('groups', [])
            }
        }
    
    
    async def _handle_jit_provisioning(
        self,
        provider_config: SSOProvider,
        user_data: Dict[str, Any],
        mapped_roles: List[str],
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Handle Just-In-Time user provisioning."""
        
        email = user_data.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email required for JIT provisioning")
        
        try:
            # Check if user already exists in user service
            user_exists_result = await self._check_user_exists(tenant_id, email)
            
            if user_exists_result['exists']:
                # User exists - update roles if needed
                user_id = user_exists_result['user_id']
                await self._update_user_roles(tenant_id, user_id, mapped_roles)
                
                return {
                    'user_id': user_id,
                    'status': 'existing',
                    'user_created': False,
                    'user_updated': True
                }
            
            else:
                # User doesn't exist - create or request approval
                if provider_config.jit_require_approval:
                    # Create approval request
                    approval_request = await self._create_jit_approval_request(
                        tenant_id=tenant_id,
                        user_data=user_data,
                        mapped_roles=mapped_roles
                    )
                    
                    return {
                        'user_id': None,
                        'status': 'pending',
                        'approval_request_id': approval_request.id,
                        'user_created': False,
                        'user_updated': False
                    }
                
                else:
                    # Create user automatically
                    user_id = await self._create_user_in_user_service(
                        tenant_id=tenant_id,
                        user_data=user_data,
                        roles=mapped_roles
                    )
                    
                    return {
                        'user_id': user_id,
                        'status': 'created',
                        'user_created': True,
                        'user_updated': False
                    }
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"JIT provisioning failed: {str(e)}"
            )
    
    
    async def _check_user_exists(self, tenant_id: UUID, email: str) -> Dict[str, Any]:
        """Check if user exists in user service."""
        # This would make an API call to the user service
        # For now, return a mock response
        return {
            'exists': False,
            'user_id': None
        }
    
    
    async def _create_user_in_user_service(
        self,
        tenant_id: UUID,
        user_data: Dict[str, Any],
        roles: List[str]
    ) -> UUID:
        """Create user in user service."""
        # This would make an API call to the user service
        # For now, return a mock user ID
        return uuid4()
    
    
    async def _update_user_roles(self, tenant_id: UUID, user_id: UUID, roles: List[str]):
        """Update user roles in user service."""
        # This would make an API call to the user service
        pass
    
    
    async def _create_jit_approval_request(
        self,
        tenant_id: UUID,
        user_data: Dict[str, Any],
        mapped_roles: List[str]
    ) -> JITApprovalRequest:
        """Create JIT approval request."""
        
        approval_request = JITApprovalRequest(
            tenant_id=tenant_id,
            email=user_data.get('email'),
            display_name=user_data.get('display_name'),
            requested_roles=mapped_roles,
            justification=f"SSO login from {user_data.get('email')}",
            expires_at=datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
        )
        
        self.db.add(approval_request)
        self.db.commit()
        self.db.refresh(approval_request)
        
        # Send approval request to approval service
        await self._send_approval_request(approval_request)
        
        return approval_request
    
    
    async def _send_approval_request(self, approval_request: JITApprovalRequest):
        """Send approval request to approval service."""
        # This would make an API call to the approval service
        pass
    
    
    def _get_provider_config(
        self, 
        tenant_id: UUID, 
        provider_name: str, 
        provider_type: str
    ) -> SSOProvider:
        """Get SSO provider configuration."""
        
        provider_config = self.db.query(SSOProvider).filter(
            SSOProvider.tenant_id == tenant_id,
            SSOProvider.provider_name == provider_name,
            SSOProvider.provider_type == provider_type,
            SSOProvider.enabled == True
        ).first()
        
        if not provider_config:
            raise HTTPException(
                status_code=404,
                detail=f"SSO provider '{provider_name}' not found or disabled"
            )
        
        return provider_config
    
    
    async def _log_saml_assertion(
        self,
        provider_config: SSOProvider,
        validation_result: Dict[str, Any],
        tenant_id: UUID
    ) -> SSOAssertionLog:
        """Log SAML assertion for audit."""
        
        user_data = validation_result.get('user_data', {})
        session_data = validation_result.get('session_data', {})
        
        # Hash subject for privacy
        subject = user_data.get('subject') or user_data.get('nameid', '')
        subject_hash = hashlib.sha256(subject.encode()).hexdigest()
        
        assertion_log = SSOAssertionLog(
            provider_id=provider_config.id,
            tenant_id=tenant_id,
            assertion_id=session_data.get('assertion_id'),
            subject_hash=subject_hash,
            session_index=session_data.get('session_index'),
            signature_valid=validation_result.get('signature_valid', False),
            timestamp_valid=validation_result.get('timestamp_valid', False),
            audience_valid=validation_result.get('audience_valid', False),
            overall_valid=validation_result.get('valid', False),
            assertion_timestamp=datetime.fromisoformat(
                session_data.get('issue_instant', '').replace('Z', '+00:00')
            ).replace(tzinfo=None) if session_data.get('issue_instant') else None
        )
        
        self.db.add(assertion_log)
        self.db.commit()
        self.db.refresh(assertion_log)
        
        return assertion_log
    
    
    async def _log_oidc_assertion(
        self,
        provider_config: SSOProvider,
        user_data: Dict[str, Any],
        session_data: Dict[str, Any],
        tenant_id: UUID
    ) -> SSOAssertionLog:
        """Log OIDC assertion for audit."""
        
        # Hash subject for privacy
        subject = user_data.get('subject', '')
        subject_hash = hashlib.sha256(subject.encode()).hexdigest()
        
        # Extract jti from ID token if available
        id_token_claims = session_data.get('tokens', {}).get('id_token_claims', {})
        assertion_id = id_token_claims.get('jti')
        
        assertion_log = SSOAssertionLog(
            provider_id=provider_config.id,
            tenant_id=tenant_id,
            assertion_id=assertion_id,
            subject_hash=subject_hash,
            signature_valid=True,  # OIDC tokens are validated during exchange
            timestamp_valid=True,
            audience_valid=True,
            overall_valid=True
        )
        
        self.db.add(assertion_log)
        self.db.commit()
        self.db.refresh(assertion_log)
        
        return assertion_log
    
    
    async def _log_failed_assertion(
        self,
        tenant_id: UUID,
        provider_name: str,
        provider_type: str,
        error_code: str,
        error_message: str
    ):
        """Log failed assertion attempt."""
        
        try:
            provider_config = self._get_provider_config(tenant_id, provider_name, provider_type)
            
            assertion_log = SSOAssertionLog(
                provider_id=provider_config.id,
                tenant_id=tenant_id,
                subject_hash="",  # No subject available for failed assertion
                signature_valid=False,
                timestamp_valid=False,
                audience_valid=False,
                overall_valid=False,
                error_code=error_code,
                error_message=error_message
            )
            
            self.db.add(assertion_log)
            self.db.commit()
            
        except Exception:
            # Don't fail the main flow if logging fails
            pass
