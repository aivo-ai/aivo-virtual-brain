# AIVO IEP Service - E-Signature Service
# S1-11 Implementation - Electronic Signature Workflow Management

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging
import hashlib
import hmac
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SignatureStatus(Enum):
    """E-signature status enumeration."""
    PENDING = "pending"
    INVITED = "invited"
    VIEWED = "viewed"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

@dataclass
class SigningSession:
    """Signing session metadata."""
    session_id: str
    iep_id: str
    signer_id: str
    signer_email: str
    status: SignatureStatus
    expires_at: datetime
    created_at: datetime
    signed_at: Optional[datetime] = None
    signature_hash: Optional[str] = None

class ESignatureService:
    """
    Electronic signature service for IEP document workflow.
    
    Handles invitation, authentication, signing, and verification processes
    with legal compliance and audit trail support.
    """
    
    def __init__(self, signing_secret: str = "default-signing-secret"):
        self.signing_secret = signing_secret
        self.active_sessions: Dict[str, SigningSession] = {}
    
    def create_signing_invitation(
        self,
        iep_id: str,
        signer_id: str,
        signer_email: str,
        signer_name: str,
        signer_role: str,
        expires_hours: int = 72
    ) -> Dict[str, Any]:
        """
        Create an e-signature invitation for an IEP signer.
        
        Returns signing session information and invitation URL.
        """
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Calculate expiration
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
            
            # Create signing session
            session = SigningSession(
                session_id=session_id,
                iep_id=iep_id,
                signer_id=signer_id,
                signer_email=signer_email,
                status=SignatureStatus.PENDING,
                expires_at=expires_at,
                created_at=datetime.now(timezone.utc)
            )
            
            # Store session
            self.active_sessions[session_id] = session
            
            # Generate secure signing token
            signing_token = self._generate_signing_token(session_id, signer_email)
            
            # Create signing URL
            signing_url = f"https://iep.aivo.ai/sign/{session_id}?token={signing_token}"
            
            # Prepare invitation data
            invitation_data = {
                "session_id": session_id,
                "iep_id": iep_id,
                "signer_name": signer_name,
                "signer_email": signer_email,
                "signer_role": signer_role,
                "signing_url": signing_url,
                "expires_at": expires_at.isoformat(),
                "legal_notice": self._get_legal_notice(),
                "instructions": self._get_signing_instructions(signer_role)
            }
            
            logger.info(f"Created signing invitation for {signer_email} on IEP {iep_id}")
            
            return {
                "success": True,
                "invitation": invitation_data,
                "message": "Signing invitation created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating signing invitation: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to create signing invitation: {str(e)}"
            }
    
    def validate_signing_session(
        self, 
        session_id: str, 
        signing_token: str
    ) -> Dict[str, Any]:
        """
        Validate a signing session and token.
        
        Returns session validation result and signer information.
        """
        try:
            # Check if session exists
            if session_id not in self.active_sessions:
                return {
                    "valid": False,
                    "message": "Invalid signing session"
                }
            
            session = self.active_sessions[session_id]
            
            # Check if session is expired
            if datetime.now(timezone.utc) > session.expires_at:
                session.status = SignatureStatus.EXPIRED
                return {
                    "valid": False,
                    "message": "Signing session has expired"
                }
            
            # Validate signing token
            expected_token = self._generate_signing_token(session_id, session.signer_email)
            if not hmac.compare_digest(signing_token, expected_token):
                return {
                    "valid": False,
                    "message": "Invalid signing token"
                }
            
            # Update session status if first time viewed
            if session.status == SignatureStatus.PENDING:
                session.status = SignatureStatus.VIEWED
            
            return {
                "valid": True,
                "session": {
                    "session_id": session_id,
                    "iep_id": session.iep_id,
                    "signer_email": session.signer_email,
                    "status": session.status.value,
                    "expires_at": session.expires_at.isoformat()
                },
                "message": "Valid signing session"
            }
            
        except Exception as e:
            logger.error(f"Error validating signing session: {str(e)}")
            return {
                "valid": False,
                "message": f"Session validation error: {str(e)}"
            }
    
    def process_signature(
        self,
        session_id: str,
        signing_token: str,
        signature_data: Dict[str, Any],
        signer_ip: str,
        signer_user_agent: str
    ) -> Dict[str, Any]:
        """
        Process an electronic signature submission.
        
        Returns signature processing result and verification data.
        """
        try:
            # Validate session first
            validation_result = self.validate_signing_session(session_id, signing_token)
            if not validation_result["valid"]:
                return validation_result
            
            session = self.active_sessions[session_id]
            
            # Check if already signed
            if session.status == SignatureStatus.SIGNED:
                return {
                    "success": False,
                    "message": "Document has already been signed by this user"
                }
            
            # Process signature data
            signature_method = signature_data.get("method", "electronic_consent")
            consent_text = signature_data.get("consent_text", "")
            signature_image = signature_data.get("signature_image")  # Base64 encoded
            
            # Generate signature hash
            signature_content = f"{session_id}:{session.signer_email}:{consent_text}:{datetime.now(timezone.utc).isoformat()}"
            signature_hash = hashlib.sha256(signature_content.encode()).hexdigest()
            
            # Update session
            session.status = SignatureStatus.SIGNED
            session.signed_at = datetime.now(timezone.utc)
            session.signature_hash = signature_hash
            
            # Prepare signature record
            signature_record = {
                "session_id": session_id,
                "iep_id": session.iep_id,
                "signer_id": session.signer_id,
                "signer_email": session.signer_email,
                "signature_hash": signature_hash,
                "signature_method": signature_method,
                "signed_at": session.signed_at.isoformat(),
                "authentication": {
                    "ip_address": signer_ip,
                    "user_agent": signer_user_agent,
                    "timestamp": session.signed_at.isoformat()
                },
                "legal_metadata": {
                    "consent_text": consent_text,
                    "signature_image_provided": signature_image is not None,
                    "legal_notices_acknowledged": True
                }
            }
            
            logger.info(f"Processed signature for session {session_id}")
            
            return {
                "success": True,
                "signature": signature_record,
                "message": "Signature processed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error processing signature: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to process signature: {str(e)}"
            }
    
    def get_signature_status(self, iep_id: str) -> Dict[str, Any]:
        """
        Get signature status summary for an IEP.
        
        Returns signature completion status and pending signers.
        """
        try:
            iep_sessions = [s for s in self.active_sessions.values() if s.iep_id == iep_id]
            
            total_signers = len(iep_sessions)
            signed_count = len([s for s in iep_sessions if s.status == SignatureStatus.SIGNED])
            pending_count = len([s for s in iep_sessions if s.status in [SignatureStatus.PENDING, SignatureStatus.INVITED, SignatureStatus.VIEWED]])
            
            pending_signers = [
                {
                    "signer_email": s.signer_email,
                    "status": s.status.value,
                    "expires_at": s.expires_at.isoformat()
                }
                for s in iep_sessions 
                if s.status != SignatureStatus.SIGNED
            ]
            
            is_complete = signed_count == total_signers and total_signers > 0
            
            return {
                "iep_id": iep_id,
                "signature_status": {
                    "is_complete": is_complete,
                    "total_signers": total_signers,
                    "signed_count": signed_count,
                    "pending_count": pending_count,
                    "completion_percentage": (signed_count / total_signers * 100) if total_signers > 0 else 0
                },
                "pending_signers": pending_signers
            }
            
        except Exception as e:
            logger.error(f"Error getting signature status: {str(e)}")
            return {
                "iep_id": iep_id,
                "error": str(e)
            }
    
    def _generate_signing_token(self, session_id: str, signer_email: str) -> str:
        """Generate secure signing token using HMAC."""
        message = f"{session_id}:{signer_email}".encode()
        return hmac.new(
            self.signing_secret.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
    
    def _get_legal_notice(self) -> str:
        """Get legal notice text for e-signature."""
        return """
        By electronically signing this Individual Education Program (IEP), you acknowledge that:
        
        1. You have read and reviewed the complete IEP document
        2. Your electronic signature has the same legal effect as a handwritten signature
        3. You consent to conducting this transaction electronically
        4. You have the authority to sign on behalf of the indicated role
        5. This signature is binding and legally enforceable
        
        This electronic signature process complies with the Electronic Signatures in Global 
        and National Commerce Act (E-SIGN) and the Uniform Electronic Transactions Act (UETA).
        """
    
    def _get_signing_instructions(self, signer_role: str) -> str:
        """Get role-specific signing instructions."""
        instructions = {
            "parent_guardian": "As the parent or legal guardian, please review all sections of this IEP and confirm your agreement with the proposed educational plan.",
            "teacher": "As the teacher, please confirm that you have reviewed the goals, accommodations, and services outlined in this IEP.",
            "case_manager": "As the case manager, please verify that all required sections are complete and accurate.",
            "administrator": "As the administrator, please confirm approval of the IEP and associated resource allocations.",
            "student": "As the student, please review your IEP and indicate your understanding and agreement (if age appropriate)."
        }
        
        return instructions.get(signer_role, "Please review the complete IEP document before signing.")
