"""
SCIM 2.0 Schema and ResourceType Endpoints

Provides schema definitions and resource type discovery for SCIM clients.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ...models import Tenant
from ..auth import get_current_tenant, require_scim_permission

router = APIRouter(prefix="/scim/v2", tags=["SCIM Schemas"])


# SCIM Core User Schema
SCIM_USER_SCHEMA = {
    "id": "urn:ietf:params:scim:schemas:core:2.0:User",
    "name": "User",
    "description": "User Account",
    "attributes": [
        {
            "name": "userName",
            "type": "string",
            "multiValued": False,
            "description": "Unique identifier for the User, typically used by the user to directly authenticate",
            "required": True,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "server"
        },
        {
            "name": "name",
            "type": "complex",
            "multiValued": False,
            "description": "The components of the user's real name",
            "required": False,
            "subAttributes": [
                {
                    "name": "formatted",
                    "type": "string",
                    "multiValued": False,
                    "description": "The full name, including all middle names, titles, and suffixes",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "familyName",
                    "type": "string",
                    "multiValued": False,
                    "description": "The family name of the User, or last name",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "givenName",
                    "type": "string",
                    "multiValued": False,
                    "description": "The given name of the User, or first name",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "middleName",
                    "type": "string",
                    "multiValued": False,
                    "description": "The middle name(s) of the User",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "honorificPrefix",
                    "type": "string",
                    "multiValued": False,
                    "description": "The honorific prefix(es) of the User, or title",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "honorificSuffix",
                    "type": "string",
                    "multiValued": False,
                    "description": "The honorific suffix(es) of the User, or suffix",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                }
            ],
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "displayName",
            "type": "string",
            "multiValued": False,
            "description": "The name of the User, suitable for display",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "nickName",
            "type": "string",
            "multiValued": False,
            "description": "The casual way to address the user in real life",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "profileUrl",
            "type": "reference",
            "referenceTypes": ["external"],
            "multiValued": False,
            "description": "A fully qualified URL pointing to the User's public profile page",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "title",
            "type": "string",
            "multiValued": False,
            "description": "The user's title, such as Vice President",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "userType",
            "type": "string",
            "multiValued": False,
            "description": "Used to identify the relationship between the organization and the user",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "preferredLanguage",
            "type": "string",
            "multiValued": False,
            "description": "Indicates the User's preferred written or spoken language",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "locale",
            "type": "string",
            "multiValued": False,
            "description": "Used to indicate the User's default location",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "timezone",
            "type": "string",
            "multiValued": False,
            "description": "The User's time zone in the 'Olson' time zone database format",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "active",
            "type": "boolean",
            "multiValued": False,
            "description": "A Boolean value indicating the User's administrative status",
            "required": False,
            "mutability": "readWrite",
            "returned": "default"
        },
        {
            "name": "password",
            "type": "string",
            "multiValued": False,
            "description": "The User's cleartext password",
            "required": False,
            "caseExact": False,
            "mutability": "writeOnly",
            "returned": "never",
            "uniqueness": "none"
        },
        {
            "name": "emails",
            "type": "complex",
            "multiValued": True,
            "description": "Email addresses for the user",
            "required": False,
            "subAttributes": [
                {
                    "name": "value",
                    "type": "string",
                    "multiValued": False,
                    "description": "Email addresses for the user",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "display",
                    "type": "string",
                    "multiValued": False,
                    "description": "A human-readable name for the email",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "type",
                    "type": "string",
                    "multiValued": False,
                    "description": "A label indicating the attribute's function",
                    "required": False,
                    "caseExact": False,
                    "canonicalValues": ["work", "home", "other"],
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "primary",
                    "type": "boolean",
                    "multiValued": False,
                    "description": "A Boolean value indicating the 'primary' or preferred attribute value",
                    "required": False,
                    "mutability": "readWrite",
                    "returned": "default"
                }
            ],
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "phoneNumbers",
            "type": "complex",
            "multiValued": True,
            "description": "Phone numbers for the User",
            "required": False,
            "subAttributes": [
                {
                    "name": "value",
                    "type": "string",
                    "multiValued": False,
                    "description": "Phone number of the User",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "display",
                    "type": "string",
                    "multiValued": False,
                    "description": "A human-readable name for the phone number",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "type",
                    "type": "string",
                    "multiValued": False,
                    "description": "A label indicating the attribute's function",
                    "required": False,
                    "caseExact": False,
                    "canonicalValues": ["work", "home", "mobile", "fax", "pager", "other"],
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "primary",
                    "type": "boolean",
                    "multiValued": False,
                    "description": "A Boolean value indicating the 'primary' or preferred attribute value",
                    "required": False,
                    "mutability": "readWrite",
                    "returned": "default"
                }
            ],
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "addresses",
            "type": "complex",
            "multiValued": True,
            "description": "A physical mailing address for this User",
            "required": False,
            "subAttributes": [
                {
                    "name": "formatted",
                    "type": "string",
                    "multiValued": False,
                    "description": "The full mailing address, formatted for display",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "streetAddress",
                    "type": "string",
                    "multiValued": False,
                    "description": "The full street address component",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "locality",
                    "type": "string",
                    "multiValued": False,
                    "description": "The city or locality component",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "region",
                    "type": "string",
                    "multiValued": False,
                    "description": "The state or region component",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "postalCode",
                    "type": "string",
                    "multiValued": False,
                    "description": "The zip code or postal code component",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "country",
                    "type": "string",
                    "multiValued": False,
                    "description": "The country name component",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "type",
                    "type": "string",
                    "multiValued": False,
                    "description": "A label indicating the attribute's function",
                    "required": False,
                    "caseExact": False,
                    "canonicalValues": ["work", "home", "other"],
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                }
            ],
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "groups",
            "type": "complex",
            "multiValued": True,
            "description": "A list of groups to which the user belongs",
            "required": False,
            "subAttributes": [
                {
                    "name": "value",
                    "type": "string",
                    "multiValued": False,
                    "description": "The identifier of the User's group",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "$ref",
                    "type": "reference",
                    "referenceTypes": ["User", "Group"],
                    "multiValued": False,
                    "description": "The URI of the corresponding 'Group' resource",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "display",
                    "type": "string",
                    "multiValued": False,
                    "description": "A human-readable name for the Group",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "type",
                    "type": "string",
                    "multiValued": False,
                    "description": "A label indicating the attribute's function",
                    "required": False,
                    "caseExact": False,
                    "canonicalValues": ["direct", "indirect"],
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none"
                }
            ],
            "mutability": "readOnly",
            "returned": "default",
            "uniqueness": "none"
        }
    ],
    "meta": {
        "resourceType": "Schema",
        "location": "/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:User"
    }
}

# SCIM Core Group Schema
SCIM_GROUP_SCHEMA = {
    "id": "urn:ietf:params:scim:schemas:core:2.0:Group",
    "name": "Group",
    "description": "Group",
    "attributes": [
        {
            "name": "displayName",
            "type": "string",
            "multiValued": False,
            "description": "A human-readable name for the Group",
            "required": True,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "members",
            "type": "complex",
            "multiValued": True,
            "description": "A list of members of the Group",
            "required": False,
            "subAttributes": [
                {
                    "name": "value",
                    "type": "string",
                    "multiValued": False,
                    "description": "Identifier of the member of this Group",
                    "required": False,
                    "caseExact": False,
                    "mutability": "immutable",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "$ref",
                    "type": "reference",
                    "referenceTypes": ["User", "Group"],
                    "multiValued": False,
                    "description": "The URI corresponding to a SCIM resource that is a member of this Group",
                    "required": False,
                    "caseExact": False,
                    "mutability": "immutable",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "type",
                    "type": "string",
                    "multiValued": False,
                    "description": "A label indicating the type of resource",
                    "required": False,
                    "caseExact": False,
                    "canonicalValues": ["User", "Group"],
                    "mutability": "immutable",
                    "returned": "default",
                    "uniqueness": "none"
                }
            ],
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        }
    ],
    "meta": {
        "resourceType": "Schema",
        "location": "/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:Group"
    }
}

# SCIM Enterprise User Extension Schema
SCIM_ENTERPRISE_USER_SCHEMA = {
    "id": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
    "name": "EnterpriseUser",
    "description": "Enterprise User",
    "attributes": [
        {
            "name": "employeeNumber",
            "type": "string",
            "multiValued": False,
            "description": "Numeric or alphanumeric identifier assigned to a person",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "costCenter",
            "type": "string",
            "multiValued": False,
            "description": "Identifies the name of a cost center",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "organization",
            "type": "string",
            "multiValued": False,
            "description": "Identifies the name of an organization",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "division",
            "type": "string",
            "multiValued": False,
            "description": "Identifies the name of a division",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "department",
            "type": "string",
            "multiValued": False,
            "description": "Identifies the name of a department",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        },
        {
            "name": "manager",
            "type": "complex",
            "multiValued": False,
            "description": "The User's manager",
            "required": False,
            "subAttributes": [
                {
                    "name": "value",
                    "type": "string",
                    "multiValued": False,
                    "description": "The id of the SCIM resource representing the User's manager",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "$ref",
                    "type": "reference",
                    "referenceTypes": ["User"],
                    "multiValued": False,
                    "description": "The URI of the SCIM resource representing the User's manager",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none"
                },
                {
                    "name": "displayName",
                    "type": "string",
                    "multiValued": False,
                    "description": "The displayName of the User's manager",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none"
                }
            ],
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none"
        }
    ],
    "meta": {
        "resourceType": "Schema",
        "location": "/v2/Schemas/urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    }
}


@router.get("/Schemas")
async def list_schemas(
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("schemas:read"))
):
    """Get all supported SCIM schemas."""
    
    schemas = [
        SCIM_USER_SCHEMA,
        SCIM_GROUP_SCHEMA,
        SCIM_ENTERPRISE_USER_SCHEMA
    ]
    
    # Build response
    base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
    
    for schema in schemas:
        schema["meta"]["location"] = f"{base_url}/Schemas/{schema['id']}"
    
    response = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(schemas),
        "startIndex": 1,
        "itemsPerPage": len(schemas),
        "Resources": schemas
    }
    
    return JSONResponse(content=response)


@router.get("/Schemas/{schema_id}")
async def get_schema(
    schema_id: str,
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("schemas:read"))
):
    """Get specific SCIM schema by ID."""
    
    schemas = {
        "urn:ietf:params:scim:schemas:core:2.0:User": SCIM_USER_SCHEMA,
        "urn:ietf:params:scim:schemas:core:2.0:Group": SCIM_GROUP_SCHEMA,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": SCIM_ENTERPRISE_USER_SCHEMA
    }
    
    if schema_id not in schemas:
        return JSONResponse(
            status_code=404,
            content={
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "status": "404",
                "detail": f"Schema {schema_id} not found"
            }
        )
    
    schema = schemas[schema_id].copy()
    base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
    schema["meta"]["location"] = f"{base_url}/Schemas/{schema_id}"
    
    return JSONResponse(content=schema)


@router.get("/ResourceTypes")
async def list_resource_types(
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("schemas:read"))
):
    """Get all supported SCIM resource types."""
    
    base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
    
    resource_types = [
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "User",
            "name": "User",
            "endpoint": "/Users",
            "description": "User Account",
            "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
            "schemaExtensions": [
                {
                    "schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    "required": False
                }
            ],
            "meta": {
                "location": f"{base_url}/ResourceTypes/User",
                "resourceType": "ResourceType"
            }
        },
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "Group",
            "name": "Group",
            "endpoint": "/Groups",
            "description": "Group",
            "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
            "meta": {
                "location": f"{base_url}/ResourceTypes/Group",
                "resourceType": "ResourceType"
            }
        }
    ]
    
    response = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(resource_types),
        "startIndex": 1,
        "itemsPerPage": len(resource_types),
        "Resources": resource_types
    }
    
    return JSONResponse(content=response)


@router.get("/ResourceTypes/{resource_type_id}")
async def get_resource_type(
    resource_type_id: str,
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("schemas:read"))
):
    """Get specific SCIM resource type by ID."""
    
    base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
    
    resource_types = {
        "User": {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "User",
            "name": "User",
            "endpoint": "/Users",
            "description": "User Account",
            "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
            "schemaExtensions": [
                {
                    "schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    "required": False
                }
            ],
            "meta": {
                "location": f"{base_url}/ResourceTypes/User",
                "resourceType": "ResourceType"
            }
        },
        "Group": {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "Group",
            "name": "Group",
            "endpoint": "/Groups",
            "description": "Group",
            "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
            "meta": {
                "location": f"{base_url}/ResourceTypes/Group",
                "resourceType": "ResourceType"
            }
        }
    }
    
    if resource_type_id not in resource_types:
        return JSONResponse(
            status_code=404,
            content={
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "status": "404",
                "detail": f"ResourceType {resource_type_id} not found"
            }
        )
    
    return JSONResponse(content=resource_types[resource_type_id])


@router.get("/ServiceProviderConfig")
async def get_service_provider_config(
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("schemas:read"))
):
    """Get SCIM service provider configuration."""
    
    base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
    
    config = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "https://docs.aivo.com/scim",
        "patch": {
            "supported": True
        },
        "bulk": {
            "supported": False,
            "maxOperations": 0,
            "maxPayloadSize": 0
        },
        "filter": {
            "supported": True,
            "maxResults": 200
        },
        "changePassword": {
            "supported": True
        },
        "sort": {
            "supported": True
        },
        "etag": {
            "supported": True
        },
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Authentication scheme using the OAuth Bearer Token Standard",
                "specUri": "http://www.rfc-editor.org/info/rfc6750",
                "documentationUri": "https://docs.aivo.com/scim/auth",
                "primary": True
            }
        ],
        "meta": {
            "location": f"{base_url}/ServiceProviderConfig",
            "resourceType": "ServiceProviderConfig"
        }
    }
    
    return JSONResponse(content=config)
