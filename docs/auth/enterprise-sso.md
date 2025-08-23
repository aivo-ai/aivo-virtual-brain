# Enterprise SSO Setup Guide

This guide covers the setup and configuration of Enterprise SSO for staff authentication using SAML 2.0 and OpenID Connect (OIDC) with popular Identity Providers.

## Overview

The Auth Service provides enterprise SSO capabilities with:

- **SAML 2.0**: Full Service Provider (SP) implementation supporting both SP and IdP-initiated flows
- **OpenID Connect**: Complete OIDC client implementation with discovery support
- **Just-In-Time (JIT) Provisioning**: Automatic user creation with approval workflows
- **Group Mapping**: Flexible mapping of IdP groups to application roles
- **Session Management**: Secure session tracking with configurable TTL
- **Audit Logging**: Comprehensive security audit trail

## Supported Identity Providers

### Microsoft Azure AD / Entra ID

#### SAML Configuration

1. **Register Application in Azure AD**:

   ```
   - Go to Azure Portal > Azure Active Directory > Enterprise Applications
   - Click "New application" > "Non-gallery application"
   - Name: "AIVO Platform"
   ```

2. **Configure SAML Settings**:

   ```
   Basic SAML Configuration:
   - Identifier (Entity ID): https://auth.aivo.local/saml/sp
   - Reply URL (ACS): https://auth.aivo.local/sso/saml/acs
   - Sign on URL: https://auth.aivo.local/sso/saml/login/{tenant_id}/azure-saml
   ```

3. **Download Certificate**:

   ```
   - In SAML Signing Certificate section
   - Download "Certificate (Base64)"
   ```

4. **Configure Claims**:

   ```json
   {
     "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "user.mail",
     "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "user.displayname",
     "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": "user.givenname",
     "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": "user.surname",
     "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups": "user.groups"
   }
   ```

5. **Create SSO Provider Configuration**:
   ```bash
   curl -X POST "https://auth.aivo.local/api/v1/sso/providers/{tenant_id}" \
     -H "Content-Type: application/json" \
     -d '{
       "provider_type": "saml",
       "provider_name": "azure-saml",
       "config": {
         "saml_idp_entity_id": "https://sts.windows.net/{tenant-id}/",
         "saml_idp_sso_url": "https://login.microsoftonline.com/{tenant-id}/saml2",
         "saml_idp_sls_url": "https://login.microsoftonline.com/{tenant-id}/saml2",
         "saml_idp_x509_cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
         "saml_name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
       },
       "group_mapping_config": {
         "explicit_mappings": {
           "AIVO-Admins": ["admin"],
           "AIVO-Support": ["support"],
           "AIVO-Staff": ["staff"]
         },
         "pattern_mappings": [
           {"pattern": "AIVO-*", "roles": ["staff"]}
         ],
         "require_staff_role": true
       },
       "jit_enabled": true,
       "jit_require_approval": false,
       "enabled": true
     }'
   ```

#### OIDC Configuration

1. **Register Application in Azure AD**:

   ```
   - Go to Azure Portal > Azure Active Directory > App registrations
   - Click "New registration"
   - Name: "AIVO Platform OIDC"
   - Redirect URI: https://auth.aivo.local/sso/oidc/callback
   ```

2. **Configure Authentication**:

   ```
   - Platform: Web
   - Redirect URIs: https://auth.aivo.local/sso/oidc/callback
   - Logout URL: https://auth.aivo.local/logout
   - ID tokens: Enabled
   ```

3. **Configure API Permissions**:

   ```
   Microsoft Graph:
   - openid (delegated)
   - profile (delegated)
   - email (delegated)
   - Group.Read.All (delegated)
   ```

4. **Create Client Secret**:

   ```
   - Go to Certificates & secrets
   - New client secret
   - Copy the secret value
   ```

5. **Create SSO Provider Configuration**:
   ```bash
   curl -X POST "https://auth.aivo.local/api/v1/sso/providers/{tenant_id}" \
     -H "Content-Type: application/json" \
     -d '{
       "provider_type": "oidc",
       "provider_name": "azure-oidc",
       "config": {
         "oidc_issuer": "https://login.microsoftonline.com/{tenant-id}/v2.0",
         "oidc_client_id": "{application-id}",
         "oidc_client_secret": "{client-secret}"
       },
       "group_mapping_config": {
         "explicit_mappings": {
           "AIVO-Admins": ["admin"],
           "AIVO-Support": ["support"]
         },
         "default_admin_patterns": ["admin", "administrator"],
         "require_staff_role": true
       },
       "jit_enabled": true,
       "jit_require_approval": true,
       "enabled": true
     }'
   ```

### Okta

#### SAML Configuration

1. **Create SAML Application in Okta**:

   ```
   - Go to Okta Admin Console > Applications
   - Click "Create App Integration"
   - Sign-in method: SAML 2.0
   ```

2. **Configure SAML Settings**:

   ```
   General Settings:
   - App name: AIVO Platform

   SAML Settings:
   - Single sign on URL: https://auth.aivo.local/sso/saml/acs
   - Audience URI: https://auth.aivo.local/saml/sp
   - Name ID format: EmailAddress
   - Application username: Email
   ```

3. **Configure Attribute Statements**:

   ```
   - email: user.email
   - firstName: user.firstName
   - lastName: user.lastName
   - displayName: user.displayName
   - groups: user.groups (Group attribute filter: Matches regex .*)
   ```

4. **Get IdP Metadata**:

   ```
   - In application settings, go to "Sign On" tab
   - Copy "Identity Provider metadata" link
   - Download the metadata XML
   ```

5. **Create SSO Provider Configuration**:
   ```bash
   curl -X POST "https://auth.aivo.local/api/v1/sso/providers/{tenant_id}" \
     -H "Content-Type: application/json" \
     -d '{
       "provider_type": "saml",
       "provider_name": "okta-saml",
       "config": {
         "saml_idp_entity_id": "http://www.okta.com/{idp-id}",
         "saml_idp_sso_url": "https://{domain}.okta.com/app/{app-id}/sso/saml",
         "saml_idp_sls_url": "https://{domain}.okta.com/app/{app-id}/slo/saml",
         "saml_idp_x509_cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
       },
       "group_mapping_config": {
         "explicit_mappings": {
           "AIVO Administrators": ["admin"],
           "AIVO Support": ["support"]
         },
         "pattern_mappings": [
           {"pattern": "AIVO *", "roles": ["staff"]}
         ]
       },
       "jit_enabled": true,
       "jit_require_approval": false,
       "enabled": true
     }'
   ```

#### OIDC Configuration

1. **Create OIDC Application in Okta**:

   ```
   - Go to Okta Admin Console > Applications
   - Click "Create App Integration"
   - Sign-in method: OIDC - OpenID Connect
   - Application type: Web Application
   ```

2. **Configure Application Settings**:

   ```
   General Settings:
   - App integration name: AIVO Platform OIDC
   - Grant type: Authorization Code
   - Sign-in redirect URIs: https://auth.aivo.local/sso/oidc/callback
   - Sign-out redirect URIs: https://auth.aivo.local/logout
   ```

3. **Configure Assignments**:

   ```
   - Assign to groups or users who should have access
   - Configure group claims in token
   ```

4. **Create SSO Provider Configuration**:
   ```bash
   curl -X POST "https://auth.aivo.local/api/v1/sso/providers/{tenant_id}" \
     -H "Content-Type: application/json" \
     -d '{
       "provider_type": "oidc",
       "provider_name": "okta-oidc",
       "config": {
         "oidc_issuer": "https://{domain}.okta.com",
         "oidc_client_id": "{client-id}",
         "oidc_client_secret": "{client-secret}"
       },
       "group_mapping_config": {
         "explicit_mappings": {
           "AIVO Administrators": ["admin"],
           "AIVO Support": ["support"]
         }
       },
       "jit_enabled": true,
       "jit_require_approval": false,
       "enabled": true
     }'
   ```

### Google Workspace

#### SAML Configuration

1. **Configure SAML App in Google Admin Console**:

   ```
   - Go to Google Admin Console > Apps > Web and mobile apps
   - Click "Add app" > "Add custom SAML app"
   - App name: AIVO Platform
   ```

2. **Download IdP Metadata**:

   ```
   - In Step 2 of setup, download metadata or note:
     - SSO URL
     - Entity ID
     - Certificate
   ```

3. **Configure Service Provider Details**:

   ```
   - ACS URL: https://auth.aivo.local/sso/saml/acs
   - Entity ID: https://auth.aivo.local/saml/sp
   - Name ID format: EMAIL
   - Name ID: Basic Information > Primary email
   ```

4. **Configure Attribute Mapping**:

   ```
   - first_name: Basic Information > First name
   - last_name: Basic Information > Last name
   - email: Basic Information > Primary email
   - groups: Directory API > Groups
   ```

5. **Create SSO Provider Configuration**:
   ```bash
   curl -X POST "https://auth.aivo.local/api/v1/sso/providers/{tenant_id}" \
     -H "Content-Type: application/json" \
     -d '{
       "provider_type": "saml",
       "provider_name": "google-saml",
       "config": {
         "saml_idp_entity_id": "https://accounts.google.com/o/saml2?idpid={idp-id}",
         "saml_idp_sso_url": "https://accounts.google.com/o/saml2/idp?idpid={idp-id}",
         "saml_idp_x509_cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
       },
       "group_mapping_config": {
         "explicit_mappings": {
           "aivo-admins@company.com": ["admin"],
           "aivo-support@company.com": ["support"]
         },
         "pattern_mappings": [
           {"pattern": "aivo-*@company.com", "roles": ["staff"]}
         ]
       },
       "jit_enabled": true,
       "jit_require_approval": false,
       "enabled": true
     }'
   ```

#### OIDC Configuration

1. **Create OAuth 2.0 Client in Google Cloud Console**:

   ```
   - Go to Google Cloud Console > APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Application type: Web application
   - Authorized redirect URIs: https://auth.aivo.local/sso/oidc/callback
   ```

2. **Configure OAuth Consent Screen**:

   ```
   - Configure consent screen with appropriate scopes:
     - openid
     - email
     - profile
   ```

3. **Create SSO Provider Configuration**:
   ```bash
   curl -X POST "https://auth.aivo.local/api/v1/sso/providers/{tenant_id}" \
     -H "Content-Type: application/json" \
     -d '{
       "provider_type": "oidc",
       "provider_name": "google-oidc",
       "config": {
         "oidc_issuer": "https://accounts.google.com",
         "oidc_client_id": "{client-id}.apps.googleusercontent.com",
         "oidc_client_secret": "{client-secret}"
       },
       "group_mapping_config": {
         "explicit_mappings": {
           "aivo-admins@company.com": ["admin"]
         },
         "default_admin_patterns": ["admin"],
         "require_staff_role": true
       },
       "jit_enabled": true,
       "jit_require_approval": true,
       "enabled": true
     }'
   ```

## Group Mapping Configuration

### Basic Configuration

```json
{
  "explicit_mappings": {
    "Domain Admins": ["admin"],
    "IT Support": ["support"],
    "All Staff": ["staff"]
  },
  "pattern_mappings": [
    {
      "pattern": "*admin*",
      "roles": ["admin"]
    },
    {
      "pattern": "regex:^support.*",
      "roles": ["support"]
    }
  ],
  "role_hierarchy": {
    "admin": ["staff", "support"],
    "support": ["staff"]
  },
  "role_restrictions": {
    "max_roles_per_user": 3,
    "role_priority": ["admin", "support", "staff"],
    "required_roles": ["staff"]
  },
  "require_staff_role": true,
  "default_admin_patterns": ["admin", "administrator", "manager"],
  "default_support_patterns": ["support", "help", "assist"]
}
```

### Advanced Mapping Examples

#### Complex Role Hierarchy

```json
{
  "explicit_mappings": {
    "Global Administrators": ["global_admin"],
    "Tenant Administrators": ["tenant_admin"],
    "Help Desk Tier 1": ["support_l1"],
    "Help Desk Tier 2": ["support_l2"],
    "Teaching Staff": ["teacher"],
    "Administrative Staff": ["admin_staff"]
  },
  "role_hierarchy": {
    "global_admin": ["tenant_admin", "support_l2", "support_l1", "staff"],
    "tenant_admin": ["support_l2", "support_l1", "staff"],
    "support_l2": ["support_l1", "staff"],
    "support_l1": ["staff"],
    "teacher": ["staff"],
    "admin_staff": ["staff"]
  },
  "role_restrictions": {
    "forbidden_combinations": [
      ["teacher", "support_l1"],
      ["teacher", "support_l2"]
    ],
    "max_roles_per_user": 4
  }
}
```

## JIT Provisioning Configuration

### Automatic Provisioning

```json
{
  "jit_enabled": true,
  "jit_require_approval": false,
  "jit_default_role": "staff",
  "attribute_mapping": {
    "email": "email",
    "first_name": "first_name",
    "last_name": "last_name",
    "display_name": "display_name",
    "department": "department"
  }
}
```

### Approval-Based Provisioning

```json
{
  "jit_enabled": true,
  "jit_require_approval": true,
  "jit_default_role": "staff",
  "approval_workflow": {
    "approval_timeout_hours": 24,
    "auto_approve_domains": ["company.com", "trusted-partner.com"],
    "require_manager_approval": true,
    "escalation_levels": [
      { "role": "tenant_admin", "timeout_hours": 8 },
      { "role": "global_admin", "timeout_hours": 16 }
    ]
  }
}
```

## Session Management

### Session Configuration

```bash
# Environment variables
export SSO_SESSION_TTL_MINUTES=480  # 8 hours
export JIT_SUPPORT_TOKEN_TTL_MINUTES=60  # 1 hour

# Database cleanup job (run daily)
DELETE FROM sso_sessions
WHERE session_state = 'expired'
   OR expires_at < NOW() - INTERVAL '7 days';

DELETE FROM sso_assertion_logs
WHERE processed_at < NOW() - INTERVAL '90 days';
```

### Session Validation

```javascript
// Client-side session validation
async function validateSession(sessionToken) {
  const response = await fetch("/sso/session/validate", {
    headers: {
      Authorization: `Bearer ${sessionToken}`,
    },
  });

  if (response.status === 401) {
    // Session expired, redirect to SSO
    window.location.href = "/sso/saml/login/tenant-id/provider-name";
  }

  return response.json();
}
```

## Security Considerations

### SAML Security

- Always validate signatures on assertions
- Implement proper clock skew tolerance (default: 5 minutes)
- Validate audience restrictions
- Use secure random request IDs
- Implement replay attack protection

### OIDC Security

- Validate state parameter to prevent CSRF
- Use nonce to prevent replay attacks
- Validate ID token signatures using JWKS
- Implement proper token expiration handling
- Secure client secrets

### General Security

- Use HTTPS for all SSO endpoints
- Implement rate limiting on SSO endpoints
- Log all authentication attempts
- Regular security audits of SSO configurations
- Implement session fixation protection

## Troubleshooting

### Common SAML Issues

1. **Invalid Signature Error**:

   ```
   Check:
   - IdP certificate is correctly configured
   - Certificate format (Base64, PEM)
   - Clock synchronization between SP and IdP
   ```

2. **Audience Validation Failed**:

   ```
   Check:
   - SP Entity ID matches expected audience
   - Case sensitivity in Entity ID
   ```

3. **Assertion Expired**:
   ```
   Check:
   - Clock skew tolerance setting
   - IdP and SP time synchronization
   - Assertion validity period
   ```

### Common OIDC Issues

1. **Invalid Client Error**:

   ```
   Check:
   - Client ID configuration
   - Redirect URI exact match
   - Client secret if required
   ```

2. **Invalid Scope Error**:
   ```
   Check:
   - Requested scopes are configured in IdP
   - Scope permissions granted to application
   ```

### JIT Provisioning Issues

1. **Email Required Error**:

   ```
   Check:
   - Email attribute mapping
   - IdP configuration for email claim
   - Required attribute configuration
   ```

2. **Role Mapping Failed**:
   ```
   Check:
   - Group attribute mapping
   - Group name case sensitivity
   - Pattern matching syntax
   ```

## Monitoring and Alerting

### Key Metrics

- SSO authentication success/failure rates
- JIT provisioning success rates
- Session duration and timeout rates
- Failed assertion validation counts

### Recommended Alerts

- High authentication failure rate (> 10% in 5 minutes)
- JIT approval queue buildup (> 50 pending requests)
- SSO provider connection failures
- Unusual geographic login patterns

### Log Analysis Queries

```sql
-- Failed authentication attempts
SELECT COUNT(*), provider_id, error_code
FROM sso_assertion_logs
WHERE overall_valid = false
  AND processed_at > NOW() - INTERVAL '1 hour'
GROUP BY provider_id, error_code;

-- JIT provisioning stats
SELECT COUNT(*), jit_status
FROM sso_sessions
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY jit_status;
```

## Best Practices

1. **Provider Configuration**:
   - Use descriptive provider names
   - Implement proper error handling
   - Test with multiple user scenarios
   - Document group mapping logic

2. **Security**:
   - Regular certificate rotation
   - Monitor for deprecated protocols
   - Implement defense in depth
   - Regular security assessments

3. **User Experience**:
   - Clear error messages
   - Graceful fallback mechanisms
   - Consistent branding across SSO flows
   - User education and documentation

4. **Operations**:
   - Automated monitoring and alerting
   - Regular backup of configurations
   - Disaster recovery procedures
   - Performance optimization
