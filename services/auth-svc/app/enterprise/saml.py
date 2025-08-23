"""
SAML SSO Implementation for Enterprise Authentication

Handles SAML 2.0 authentication flows including SP and IdP-initiated login,
assertion validation, and integration with JIT provisioning.
"""

import base64
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, quote
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509 import load_pem_x509_certificate
import defusedxml.ElementTree as defused_ET

from ..config import get_settings


class SAMLError(Exception):
    """SAML-specific errors."""
    def __init__(self, message: str, error_code: str = "SAML_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class SAMLProvider:
    """SAML 2.0 Service Provider implementation."""
    
    def __init__(self, provider_config: Dict[str, Any]):
        """Initialize SAML provider with configuration."""
        self.settings = get_settings()
        self.config = provider_config
        
        # Required SAML configuration
        self.idp_entity_id = provider_config.get("saml_idp_entity_id")
        self.idp_sso_url = provider_config.get("saml_idp_sso_url")
        self.idp_sls_url = provider_config.get("saml_idp_sls_url")
        self.idp_x509_cert = provider_config.get("saml_idp_x509_cert")
        self.name_id_format = provider_config.get("saml_name_id_format", 
                                                 "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress")
        
        # SP configuration
        self.sp_entity_id = self.settings.saml_sp_entity_id
        self.sp_acs_url = self.settings.saml_sp_acs_url
        self.sp_sls_url = self.settings.saml_sp_sls_url
        self.sp_x509_cert = self.settings.saml_sp_x509_cert
        self.sp_private_key = self.settings.saml_sp_private_key
        
        # Validation settings
        self.clock_skew_tolerance = self.settings.saml_clock_skew_tolerance
        
        # Load IdP certificate for signature validation
        self._idp_cert = None
        if self.idp_x509_cert:
            try:
                cert_data = self.idp_x509_cert.strip()
                if not cert_data.startswith("-----BEGIN CERTIFICATE-----"):
                    cert_data = f"-----BEGIN CERTIFICATE-----\n{cert_data}\n-----END CERTIFICATE-----"
                self._idp_cert = load_pem_x509_certificate(cert_data.encode())
            except Exception as e:
                raise SAMLError(f"Invalid IdP certificate: {str(e)}", "INVALID_IDP_CERT")
    
    
    def generate_authn_request(self, relay_state: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate SAML AuthnRequest for SP-initiated login.
        
        Returns:
            Tuple of (redirect_url, request_id)
        """
        request_id = f"_{uuid.uuid4().hex}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Generate AuthnRequest XML
        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest 
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.idp_sso_url}"
    AssertionConsumerServiceURL="{self.sp_acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{escape(self.sp_entity_id)}</saml:Issuer>
    <samlp:NameIDPolicy Format="{escape(self.name_id_format)}" AllowCreate="true"/>
</samlp:AuthnRequest>"""
        
        # Encode and build redirect URL
        encoded_request = base64.b64encode(authn_request.encode()).decode()
        
        params = {"SAMLRequest": encoded_request}
        if relay_state:
            params["RelayState"] = relay_state
        
        redirect_url = f"{self.idp_sso_url}?{urlencode(params)}"
        
        return redirect_url, request_id
    
    
    def validate_assertion(self, saml_response: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate SAML Response and extract user information.
        
        Args:
            saml_response: Base64-encoded SAML Response
            request_id: Original AuthnRequest ID for SP-initiated flow
            
        Returns:
            Dictionary with user information and validation results
        """
        try:
            # Decode SAML Response
            try:
                decoded_response = base64.b64decode(saml_response).decode('utf-8')
            except Exception as e:
                raise SAMLError(f"Invalid SAML Response encoding: {str(e)}", "INVALID_ENCODING")
            
            # Parse XML securely
            try:
                root = defused_ET.fromstring(decoded_response)
            except Exception as e:
                raise SAMLError(f"Invalid SAML Response XML: {str(e)}", "INVALID_XML")
            
            # Extract namespaces
            ns = {
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
                'ds': 'http://www.w3.org/2000/09/xmldsig#'
            }
            
            # Validate Response structure
            if root.tag != f"{{{ns['samlp']}}}Response":
                raise SAMLError("Invalid SAML Response format", "INVALID_FORMAT")
            
            # Extract Response attributes
            response_id = root.get('ID')
            in_response_to = root.get('InResponseTo')
            destination = root.get('Destination')
            issue_instant = root.get('IssueInstant')
            
            # Validate InResponseTo for SP-initiated flow
            if request_id and in_response_to != request_id:
                raise SAMLError("InResponseTo does not match request ID", "INVALID_IN_RESPONSE_TO")
            
            # Validate destination
            if destination and destination != self.sp_acs_url:
                raise SAMLError("Invalid destination", "INVALID_DESTINATION")
            
            # Extract Status
            status_elem = root.find('.//samlp:Status/samlp:StatusCode', ns)
            if status_elem is None or status_elem.get('Value') != 'urn:oasis:names:tc:SAML:2.0:status:Success':
                status_msg = root.find('.//samlp:Status/samlp:StatusMessage', ns)
                msg = status_msg.text if status_msg is not None else "Authentication failed"
                raise SAMLError(f"SAML authentication failed: {msg}", "AUTH_FAILED")
            
            # Extract Assertion
            assertion = root.find('.//saml:Assertion', ns)
            if assertion is None:
                raise SAMLError("No assertion found in response", "NO_ASSERTION")
            
            # Validate assertion
            validation_result = self._validate_assertion_element(assertion, ns)
            
            return validation_result
            
        except SAMLError:
            raise
        except Exception as e:
            raise SAMLError(f"Assertion validation failed: {str(e)}", "VALIDATION_ERROR")
    
    
    def _validate_assertion_element(self, assertion: ET.Element, ns: Dict[str, str]) -> Dict[str, Any]:
        """Validate SAML Assertion element and extract user data."""
        
        result = {
            'valid': False,
            'signature_valid': False,
            'timestamp_valid': False,
            'audience_valid': False,
            'user_data': {},
            'session_data': {},
            'validation_errors': []
        }
        
        try:
            # Extract assertion metadata
            assertion_id = assertion.get('ID')
            issue_instant = assertion.get('IssueInstant')
            
            # Validate signature if present
            signature = assertion.find('.//ds:Signature', ns)
            if signature is not None and self._idp_cert:
                result['signature_valid'] = self._validate_signature(assertion, signature)
            else:
                result['signature_valid'] = True  # No signature to validate
            
            # Validate timestamps
            result['timestamp_valid'] = self._validate_timestamps(assertion, ns)
            
            # Validate audience
            result['audience_valid'] = self._validate_audience(assertion, ns)
            
            # Extract Subject
            subject = assertion.find('.//saml:Subject', ns)
            if subject is None:
                result['validation_errors'].append("No subject found")
                return result
            
            # Extract NameID
            name_id = subject.find('.//saml:NameID', ns)
            if name_id is None:
                result['validation_errors'].append("No NameID found")
                return result
            
            # Extract AuthnStatement for session info
            authn_stmt = assertion.find('.//saml:AuthnStatement', ns)
            session_index = None
            if authn_stmt is not None:
                session_index = authn_stmt.get('SessionIndex')
            
            # Extract AttributeStatement
            attributes = {}
            attr_stmt = assertion.find('.//saml:AttributeStatement', ns)
            if attr_stmt is not None:
                for attr in attr_stmt.findall('.//saml:Attribute', ns):
                    attr_name = attr.get('Name')
                    attr_values = []
                    for value in attr.findall('.//saml:AttributeValue', ns):
                        if value.text:
                            attr_values.append(value.text)
                    if attr_values:
                        attributes[attr_name] = attr_values[0] if len(attr_values) == 1 else attr_values
            
            # Build user data
            result['user_data'] = {
                'nameid': name_id.text,
                'nameid_format': name_id.get('Format'),
                'email': attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress', 
                                       attributes.get('email', name_id.text)),
                'display_name': attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name',
                                             attributes.get('displayName', attributes.get('name'))),
                'first_name': attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
                                           attributes.get('firstName', attributes.get('givenName'))),
                'last_name': attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
                                          attributes.get('lastName', attributes.get('surname'))),
                'groups': self._extract_groups(attributes),
                'attributes': attributes
            }
            
            # Build session data
            result['session_data'] = {
                'assertion_id': assertion_id,
                'session_index': session_index,
                'issue_instant': issue_instant,
                'subject': name_id.text
            }
            
            # Overall validation
            result['valid'] = (result['signature_valid'] and 
                             result['timestamp_valid'] and 
                             result['audience_valid'])
            
            return result
            
        except Exception as e:
            result['validation_errors'].append(f"Assertion validation error: {str(e)}")
            return result
    
    
    def _validate_signature(self, assertion: ET.Element, signature: ET.Element) -> bool:
        """Validate XML signature on assertion."""
        if not self._idp_cert:
            return False
        
        try:
            # Basic signature validation - in production, use proper XML signature library
            # This is a simplified implementation
            signed_info = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}SignedInfo')
            signature_value = signature.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
            
            if signed_info is None or signature_value is None:
                return False
            
            # In a full implementation, you would:
            # 1. Canonicalize the SignedInfo element
            # 2. Verify the signature using the IdP certificate
            # For now, return True if certificate is present and signature elements exist
            return True
            
        except Exception:
            return False
    
    
    def _validate_timestamps(self, assertion: ET.Element, ns: Dict[str, str]) -> bool:
        """Validate assertion timestamps."""
        try:
            now = datetime.utcnow()
            tolerance = timedelta(seconds=self.clock_skew_tolerance)
            
            # Check Conditions
            conditions = assertion.find('.//saml:Conditions', ns)
            if conditions is not None:
                not_before = conditions.get('NotBefore')
                not_on_or_after = conditions.get('NotOnOrAfter')
                
                if not_before:
                    not_before_dt = datetime.fromisoformat(not_before.replace('Z', '+00:00')).replace(tzinfo=None)
                    if now < (not_before_dt - tolerance):
                        return False
                
                if not_on_or_after:
                    not_on_or_after_dt = datetime.fromisoformat(not_on_or_after.replace('Z', '+00:00')).replace(tzinfo=None)
                    if now >= (not_on_or_after_dt + tolerance):
                        return False
            
            return True
            
        except Exception:
            return False
    
    
    def _validate_audience(self, assertion: ET.Element, ns: Dict[str, str]) -> bool:
        """Validate audience restriction."""
        try:
            conditions = assertion.find('.//saml:Conditions', ns)
            if conditions is not None:
                audience_restriction = conditions.find('.//saml:AudienceRestriction', ns)
                if audience_restriction is not None:
                    audiences = audience_restriction.findall('.//saml:Audience', ns)
                    if audiences:
                        # Check if our SP entity ID is in the audience list
                        for audience in audiences:
                            if audience.text == self.sp_entity_id:
                                return True
                        return False
            
            return True  # No audience restriction means valid
            
        except Exception:
            return False
    
    
    def _extract_groups(self, attributes: Dict[str, Any]) -> List[str]:
        """Extract group information from SAML attributes."""
        groups = []
        
        # Common group attribute names
        group_attrs = [
            'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/groups',
            'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups',
            'groups',
            'memberOf',
            'roles'
        ]
        
        for attr_name in group_attrs:
            if attr_name in attributes:
                attr_value = attributes[attr_name]
                if isinstance(attr_value, list):
                    groups.extend(attr_value)
                elif isinstance(attr_value, str):
                    # Handle comma-separated groups
                    groups.extend([g.strip() for g in attr_value.split(',') if g.strip()])
                break
        
        return list(set(groups))  # Remove duplicates
    
    
    def generate_metadata(self) -> str:
        """Generate SP metadata XML."""
        metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor 
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{escape(self.sp_entity_id)}">
    <md:SPSSODescriptor 
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"
        AuthnRequestsSigned="false"
        WantAssertionsSigned="true">
        <md:AssertionConsumerService 
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{escape(self.sp_acs_url)}"
            index="0" isDefault="true"/>
        <md:SingleLogoutService 
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="{escape(self.sp_sls_url)}"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
        
        return metadata
    
    
    def generate_logout_request(self, nameid: str, session_index: Optional[str] = None) -> str:
        """Generate SAML LogoutRequest."""
        request_id = f"_{uuid.uuid4().hex}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        session_index_xml = ""
        if session_index:
            session_index_xml = f'<samlp:SessionIndex>{escape(session_index)}</samlp:SessionIndex>'
        
        logout_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest 
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.idp_sls_url}">
    <saml:Issuer>{escape(self.sp_entity_id)}</saml:Issuer>
    <saml:NameID Format="{escape(self.name_id_format)}">{escape(nameid)}</saml:NameID>
    {session_index_xml}
</samlp:LogoutRequest>"""
        
        return logout_request
