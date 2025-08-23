"""
Enterprise SSO Routes

Provides endpoints for SAML and OIDC SSO flows including SP metadata,
ACS endpoints, and SSO initiation.
"""

import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..enterprise import SAMLProvider, OIDCProvider, ACSProcessor
from ..models import SSOProvider, SSOSession
from ..config import get_settings

router = APIRouter()
settings = get_settings()


# SAML Endpoints

@router.get("/saml/metadata/{tenant_id}/{provider_name}")
async def get_saml_metadata(
    tenant_id: UUID,
    provider_name: str,
    db: Session = Depends(get_db)
):
    """Get SAML SP metadata for a specific provider."""
    
    try:
        # Get provider configuration
        provider_config = db.query(SSOProvider).filter(
            SSOProvider.tenant_id == tenant_id,
            SSOProvider.provider_name == provider_name,
            SSOProvider.provider_type == "saml",
            SSOProvider.enabled == True
        ).first()
        
        if not provider_config:
            raise HTTPException(status_code=404, detail="SAML provider not found")
        
        # Generate metadata
        saml_provider = SAMLProvider(provider_config.config)
        metadata_xml = saml_provider.generate_metadata()
        
        return Response(
            content=metadata_xml,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=sp-metadata-{provider_name}.xml"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate metadata: {str(e)}")


@router.get("/saml/login/{tenant_id}/{provider_name}")
async def initiate_saml_login(
    tenant_id: UUID,
    provider_name: str,
    relay_state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Initiate SP-initiated SAML login."""
    
    try:
        # Get provider configuration
        provider_config = db.query(SSOProvider).filter(
            SSOProvider.tenant_id == tenant_id,
            SSOProvider.provider_name == provider_name,
            SSOProvider.provider_type == "saml",
            SSOProvider.enabled == True
        ).first()
        
        if not provider_config:
            raise HTTPException(status_code=404, detail="SAML provider not found")
        
        # Generate AuthnRequest
        saml_provider = SAMLProvider(provider_config.config)
        redirect_url, request_id = saml_provider.generate_authn_request(relay_state)
        
        # Store request ID for validation (in production, use Redis or database)
        # For now, we'll include it in the RelayState
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate SAML login: {str(e)}")


@router.post("/saml/acs")
async def saml_assertion_consumer_service(
    request: Request,
    SAMLResponse: str = Form(...),
    RelayState: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """SAML Assertion Consumer Service endpoint."""
    
    try:
        # Extract tenant and provider from RelayState or form data
        # In production, you would have a more robust way to identify the tenant/provider
        tenant_id = None
        provider_name = None
        
        if RelayState:
            # Parse RelayState to extract routing information
            # Format: tenant_id:provider_name:original_relay_state
            parts = RelayState.split(":", 2)
            if len(parts) >= 2:
                try:
                    tenant_id = UUID(parts[0])
                    provider_name = parts[1]
                except ValueError:
                    pass
        
        if not tenant_id or not provider_name:
            raise HTTPException(
                status_code=400,
                detail="Invalid RelayState - cannot determine tenant and provider"
            )
        
        # Process SAML response
        acs_processor = ACSProcessor(db)
        result = await acs_processor.process_saml_response(
            tenant_id=tenant_id,
            provider_name=provider_name,
            saml_response=SAMLResponse,
            relay_state=RelayState
        )
        
        # Handle different JIT statuses
        if result.get('jit_status') == 'pending':
            # Redirect to approval pending page
            return _generate_jit_pending_response(result)
        
        elif result.get('jit_status') in ['created', 'existing']:
            # Generate session token and redirect to application
            session_token = await _generate_session_token(result)
            return _generate_successful_login_response(session_token, result)
        
        else:
            raise HTTPException(status_code=400, detail="Unexpected JIT status")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAML ACS processing failed: {str(e)}")


# OIDC Endpoints

@router.get("/oidc/login/{tenant_id}/{provider_name}")
async def initiate_oidc_login(
    tenant_id: UUID,
    provider_name: str,
    redirect_uri: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Initiate OIDC authorization flow."""
    
    try:
        # Get provider configuration
        provider_config = db.query(SSOProvider).filter(
            SSOProvider.tenant_id == tenant_id,
            SSOProvider.provider_name == provider_name,
            SSOProvider.provider_type == "oidc",
            SSOProvider.enabled == True
        ).first()
        
        if not provider_config:
            raise HTTPException(status_code=404, detail="OIDC provider not found")
        
        # Initialize OIDC provider and discover configuration
        oidc_provider = OIDCProvider(provider_config.config)
        await oidc_provider.discover_configuration()
        
        # Generate authorization URL
        auth_data = oidc_provider.generate_authorization_url()
        
        # Store state and nonce for validation (in production, use Redis)
        # For now, encode tenant/provider info in state
        enhanced_state = f"{tenant_id}:{provider_name}:{auth_data['state']}"
        
        # Replace state in URL
        auth_url = auth_data['authorization_url'].replace(
            f"state={auth_data['state']}",
            f"state={enhanced_state}"
        )
        
        return RedirectResponse(url=auth_url, status_code=302)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate OIDC login: {str(e)}")


@router.get("/oidc/callback")
async def oidc_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """OIDC authorization callback endpoint."""
    
    try:
        # Handle error responses
        if error:
            raise HTTPException(
                status_code=400,
                detail=f"OIDC authorization failed: {error} - {error_description or ''}"
            )
        
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing code or state parameter")
        
        # Parse state to extract tenant and provider info
        state_parts = state.split(":", 2)
        if len(state_parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        try:
            tenant_id = UUID(state_parts[0])
            provider_name = state_parts[1]
            original_state = state_parts[2]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid state format")
        
        # Process OIDC callback
        acs_processor = ACSProcessor(db)
        result = await acs_processor.process_oidc_callback(
            tenant_id=tenant_id,
            provider_name=provider_name,
            code=code,
            state=state,
            expected_state=original_state
        )
        
        # Handle different JIT statuses
        if result.get('jit_status') == 'pending':
            # Redirect to approval pending page
            return _generate_jit_pending_response(result)
        
        elif result.get('jit_status') in ['created', 'existing']:
            # Generate session token and redirect to application
            session_token = await _generate_session_token(result)
            return _generate_successful_login_response(session_token, result)
        
        else:
            raise HTTPException(status_code=400, detail="Unexpected JIT status")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OIDC callback processing failed: {str(e)}")


# Session Management

@router.get("/session/{session_id}")
async def get_sso_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get SSO session information."""
    
    try:
        sso_session = db.query(SSOSession).filter(
            SSOSession.session_id == session_id,
            SSOSession.session_state == "active",
            SSOSession.expires_at > datetime.utcnow()
        ).first()
        
        if not sso_session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Update last accessed time
        sso_session.last_accessed = datetime.utcnow()
        db.commit()
        
        return {
            "session_id": sso_session.session_id,
            "user_id": str(sso_session.user_id) if sso_session.user_id else None,
            "tenant_id": str(sso_session.tenant_id),
            "email": sso_session.email,
            "display_name": sso_session.display_name,
            "groups": sso_session.groups,
            "jit_status": sso_session.jit_status,
            "expires_at": sso_session.expires_at.isoformat(),
            "last_accessed": sso_session.last_accessed.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.post("/session/{session_id}/logout")
async def logout_sso_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Logout SSO session."""
    
    try:
        sso_session = db.query(SSOSession).filter(
            SSOSession.session_id == session_id,
            SSOSession.session_state == "active"
        ).first()
        
        if not sso_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Mark session as logged out
        sso_session.session_state = "logged_out"
        db.commit()
        
        # TODO: Initiate IdP logout if supported
        
        return {"message": "Session logged out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to logout session: {str(e)}")


# JIT Support Token Endpoints

@router.post("/jit/support-token")
async def create_jit_support_token(
    session_id: str,
    justification: str,
    db: Session = Depends(get_db)
):
    """Create time-boxed read-only support token for JIT pending users."""
    
    try:
        # Get session with pending JIT status
        sso_session = db.query(SSOSession).filter(
            SSOSession.session_id == session_id,
            SSOSession.jit_status == "pending",
            SSOSession.expires_at > datetime.utcnow()
        ).first()
        
        if not sso_session:
            raise HTTPException(
                status_code=404,
                detail="Session not found or not eligible for support token"
            )
        
        # Generate support token with limited scope
        support_token_data = {
            "session_id": session_id,
            "user_email": sso_session.email,
            "tenant_id": str(sso_session.tenant_id),
            "scope": "read-only",
            "justification": justification,
            "expires_at": (datetime.utcnow() + 
                         timedelta(minutes=settings.jit_support_token_ttl_minutes)).isoformat()
        }
        
        # In production, this would create a proper JWT token
        support_token = base64.b64encode(str(support_token_data).encode()).decode()
        
        return {
            "support_token": support_token,
            "expires_at": support_token_data["expires_at"],
            "scope": "read-only",
            "note": "This token requires guardian approval for full access"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create support token: {str(e)}")


# Helper Functions

def _generate_jit_pending_response(result: Dict[str, Any]) -> HTMLResponse:
    """Generate HTML response for JIT approval pending."""
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Account Approval Pending</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
            .container {{ max-width: 500px; margin: 0 auto; }}
            .status {{ color: #f39c12; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="status">Account Approval Pending</h1>
            <p>Your account access is currently pending approval.</p>
            <p><strong>Email:</strong> {result.get('user_data', {}).get('email', 'N/A')}</p>
            <p><strong>Approval Request ID:</strong> {result.get('jit_approval_request_id', 'N/A')}</p>
            <p>An administrator will review your request shortly. You will receive an email notification once approved.</p>
            <p>If you need immediate assistance, please contact your system administrator.</p>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


def _generate_successful_login_response(session_token: str, result: Dict[str, Any]) -> HTMLResponse:
    """Generate HTML response for successful login."""
    
    user_data = result.get('user_data', {})
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login Successful</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
            .container {{ max-width: 500px; margin: 0 auto; }}
            .success {{ color: #27ae60; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="success">Login Successful</h1>
            <p>Welcome, {user_data.get('display_name', user_data.get('email', 'User'))}!</p>
            <p><strong>Session Token:</strong> {session_token}</p>
            <p><strong>Roles:</strong> {', '.join(result.get('mapped_roles', []))}</p>
            <p>You will be redirected to the application shortly.</p>
            <script>
                // In production, this would redirect to the application with the session token
                setTimeout(function() {{
                    window.location.href = '/app?token=' + encodeURIComponent('{session_token}');
                }}, 3000);
            </script>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


async def _generate_session_token(result: Dict[str, Any]) -> str:
    """Generate session token for successful login."""
    
    # In production, this would generate a proper JWT token
    token_data = {
        "session_id": result.get('session_id'),
        "user_id": result.get('user_id'),
        "roles": result.get('mapped_roles', []),
        "expires_at": result.get('expires_at')
    }
    
    return base64.b64encode(str(token_data).encode()).decode()
