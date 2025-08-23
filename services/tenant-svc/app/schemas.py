"""
SCIM 2.0 Schemas and Response Models

Complete implementation of SCIM 2.0 schema definitions, resource types,
and response models for users and groups.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class SCIMResourceType(str, Enum):
    """SCIM Resource Types."""
    USER = "User"
    GROUP = "Group"
    SCHEMA = "Schema"
    RESOURCE_TYPE = "ResourceType"
    SERVICE_PROVIDER_CONFIG = "ServiceProviderConfig"


class SCIMOperation(str, Enum):
    """SCIM PATCH Operations."""
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"


# SCIM Core Schemas
class SCIMError(BaseModel):
    """SCIM Error Response."""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]
    status: str
    scim_type: Optional[str] = Field(None, alias="scimType")
    detail: str


class SCIMListResponse(BaseModel):
    """SCIM List Response."""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    total_results: int = Field(alias="totalResults")
    start_index: int = Field(alias="startIndex")
    items_per_page: int = Field(alias="itemsPerPage")
    resources: List[Dict[str, Any]] = Field(alias="Resources")


class SCIMBulkRequest(BaseModel):
    """SCIM Bulk Request."""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"]
    operations: List[Dict[str, Any]] = Field(alias="Operations")
    fail_on_errors: Optional[int] = Field(None, alias="failOnErrors")


class SCIMBulkResponse(BaseModel):
    """SCIM Bulk Response."""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"]
    operations: List[Dict[str, Any]] = Field(alias="Operations")


# SCIM User Schema
class SCIMName(BaseModel):
    """SCIM Name Complex Type."""
    formatted: Optional[str] = None
    family_name: Optional[str] = Field(None, alias="familyName")
    given_name: Optional[str] = Field(None, alias="givenName")
    middle_name: Optional[str] = Field(None, alias="middleName")
    honorific_prefix: Optional[str] = Field(None, alias="honorificPrefix")
    honorific_suffix: Optional[str] = Field(None, alias="honorificSuffix")


class SCIMEmail(BaseModel):
    """SCIM Email Complex Type."""
    value: str
    type: Optional[str] = "work"  # work, home, other
    primary: Optional[bool] = False
    display: Optional[str] = None


class SCIMPhoneNumber(BaseModel):
    """SCIM Phone Number Complex Type."""
    value: str
    type: Optional[str] = "work"  # work, home, mobile, fax, pager, other
    primary: Optional[bool] = False
    display: Optional[str] = None


class SCIMAddress(BaseModel):
    """SCIM Address Complex Type."""
    formatted: Optional[str] = None
    street_address: Optional[str] = Field(None, alias="streetAddress")
    locality: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = Field(None, alias="postalCode")
    country: Optional[str] = None
    type: Optional[str] = "work"  # work, home, other
    primary: Optional[bool] = False


class SCIMPhoto(BaseModel):
    """SCIM Photo Complex Type."""
    value: str
    type: Optional[str] = None
    primary: Optional[bool] = False
    display: Optional[str] = None


class SCIMInstantMessaging(BaseModel):
    """SCIM IM Complex Type."""
    value: str
    type: Optional[str] = None
    primary: Optional[bool] = False
    display: Optional[str] = None


class SCIMEntitlement(BaseModel):
    """SCIM Entitlement Complex Type."""
    value: str
    type: Optional[str] = None
    primary: Optional[bool] = False
    display: Optional[str] = None


class SCIMRole(BaseModel):
    """SCIM Role Complex Type."""
    value: str
    type: Optional[str] = None
    primary: Optional[bool] = False
    display: Optional[str] = None


class SCIMX509Certificate(BaseModel):
    """SCIM X509Certificate Complex Type."""
    value: str
    type: Optional[str] = None
    primary: Optional[bool] = False
    display: Optional[str] = None


class SCIMEnterpriseUser(BaseModel):
    """SCIM Enterprise User Extension."""
    employee_number: Optional[str] = Field(None, alias="employeeNumber")
    cost_center: Optional[str] = Field(None, alias="costCenter")
    organization: Optional[str] = None
    division: Optional[str] = None
    department: Optional[str] = None
    manager: Optional[Dict[str, Any]] = None


class SCIMMeta(BaseModel):
    """SCIM Resource Metadata."""
    resource_type: str = Field(alias="resourceType")
    created: datetime
    last_modified: datetime = Field(alias="lastModified")
    location: Optional[str] = None
    version: str


class SCIMUser(BaseModel):
    """SCIM User Resource."""
    schemas: List[str] = [
        "urn:ietf:params:scim:schemas:core:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    ]
    id: str
    external_id: Optional[str] = Field(None, alias="externalId")
    user_name: str = Field(alias="userName")
    name: Optional[SCIMName] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    nick_name: Optional[str] = Field(None, alias="nickName")
    profile_url: Optional[str] = Field(None, alias="profileUrl")
    title: Optional[str] = None
    user_type: Optional[str] = Field(None, alias="userType")
    preferred_language: Optional[str] = Field(None, alias="preferredLanguage")
    locale: Optional[str] = None
    timezone: Optional[str] = None
    active: bool = True
    password: Optional[str] = None
    emails: List[SCIMEmail] = []
    phone_numbers: List[SCIMPhoneNumber] = Field(default=[], alias="phoneNumbers")
    ims: List[SCIMInstantMessaging] = []
    photos: List[SCIMPhoto] = []
    addresses: List[SCIMAddress] = []
    groups: List[Dict[str, Any]] = []
    entitlements: List[SCIMEntitlement] = []
    roles: List[SCIMRole] = []
    x509_certificates: List[SCIMX509Certificate] = Field(default=[], alias="x509Certificates")
    
    # Enterprise Extension
    enterprise_user: Optional[SCIMEnterpriseUser] = Field(
        None, 
        alias="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    
    # Metadata
    meta: SCIMMeta

    class Config:
        allow_population_by_field_name = True


class SCIMUserPatch(BaseModel):
    """SCIM User PATCH Request."""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    operations: List[Dict[str, Any]] = Field(alias="Operations")


class SCIMUserCreate(BaseModel):
    """SCIM User Creation Request."""
    schemas: List[str] = [
        "urn:ietf:params:scim:schemas:core:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    ]
    external_id: Optional[str] = Field(None, alias="externalId")
    user_name: str = Field(alias="userName")
    name: Optional[SCIMName] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    nick_name: Optional[str] = Field(None, alias="nickName")
    profile_url: Optional[str] = Field(None, alias="profileUrl")
    title: Optional[str] = None
    user_type: Optional[str] = Field(None, alias="userType")
    preferred_language: Optional[str] = Field(None, alias="preferredLanguage")
    locale: Optional[str] = None
    timezone: Optional[str] = None
    active: bool = True
    password: Optional[str] = None
    emails: List[SCIMEmail] = []
    phone_numbers: List[SCIMPhoneNumber] = Field(default=[], alias="phoneNumbers")
    ims: List[SCIMInstantMessaging] = []
    photos: List[SCIMPhoto] = []
    addresses: List[SCIMAddress] = []
    entitlements: List[SCIMEntitlement] = []
    roles: List[SCIMRole] = []
    x509_certificates: List[SCIMX509Certificate] = Field(default=[], alias="x509Certificates")
    
    # Enterprise Extension
    enterprise_user: Optional[SCIMEnterpriseUser] = Field(
        None, 
        alias="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )

    class Config:
        allow_population_by_field_name = True


# SCIM Group Schema
class SCIMGroupMember(BaseModel):
    """SCIM Group Member."""
    value: str
    ref: Optional[str] = Field(None, alias="$ref")
    type: str = "User"  # User or Group
    display: Optional[str] = None


class SCIMGroup(BaseModel):
    """SCIM Group Resource."""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    id: str
    external_id: Optional[str] = Field(None, alias="externalId")
    display_name: str = Field(alias="displayName")
    members: List[SCIMGroupMember] = []
    meta: SCIMMeta

    class Config:
        allow_population_by_field_name = True


class SCIMGroupCreate(BaseModel):
    """SCIM Group Creation Request."""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    external_id: Optional[str] = Field(None, alias="externalId")
    display_name: str = Field(alias="displayName")
    members: List[SCIMGroupMember] = []

    class Config:
        allow_population_by_field_name = True


class SCIMGroupPatch(BaseModel):
    """SCIM Group PATCH Request."""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    operations: List[Dict[str, Any]] = Field(alias="Operations")


# SCIM Schema Definitions
class SCIMAttribute(BaseModel):
    """SCIM Schema Attribute Definition."""
    name: str
    type: str
    multi_valued: bool = Field(alias="multiValued")
    description: str
    required: bool = False
    canonical_values: Optional[List[str]] = Field(None, alias="canonicalValues")
    case_exact: bool = Field(False, alias="caseExact")
    mutability: str = "readWrite"  # readOnly, readWrite, immutable, writeOnly
    returned: str = "default"  # always, never, default, request
    uniqueness: str = "none"  # none, server, global
    reference_types: Optional[List[str]] = Field(None, alias="referenceTypes")
    sub_attributes: Optional[List['SCIMAttribute']] = Field(None, alias="subAttributes")

    class Config:
        allow_population_by_field_name = True


class SCIMSchema(BaseModel):
    """SCIM Schema Definition."""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Schema"]
    id: str
    name: str
    description: str
    attributes: List[SCIMAttribute]
    meta: SCIMMeta

    class Config:
        allow_population_by_field_name = True


# SCIM Resource Type
class SCIMResourceTypeSchemaExtension(BaseModel):
    """SCIM Resource Type Schema Extension."""
    schema: str
    required: bool


class SCIMResourceTypeDefinition(BaseModel):
    """SCIM Resource Type Definition."""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    id: str
    name: str
    endpoint: str
    description: str
    schema: str
    schema_extensions: List[SCIMResourceTypeSchemaExtension] = Field(
        default=[], alias="schemaExtensions"
    )
    meta: SCIMMeta

    class Config:
        allow_population_by_field_name = True


# SCIM Service Provider Configuration
class SCIMAuthenticationScheme(BaseModel):
    """SCIM Authentication Scheme."""
    name: str
    description: str
    spec_uri: Optional[str] = Field(None, alias="specUri")
    documentation_uri: Optional[str] = Field(None, alias="documentationUri")
    type: str
    primary: bool = False


class SCIMBulkConfiguration(BaseModel):
    """SCIM Bulk Configuration."""
    supported: bool
    max_operations: int = Field(alias="maxOperations")
    max_payload_size: int = Field(alias="maxPayloadSize")


class SCIMFilterConfiguration(BaseModel):
    """SCIM Filter Configuration."""
    supported: bool
    max_results: int = Field(alias="maxResults")


class SCIMChangePasswordConfiguration(BaseModel):
    """SCIM Change Password Configuration."""
    supported: bool


class SCIMSortConfiguration(BaseModel):
    """SCIM Sort Configuration."""
    supported: bool


class SCIMPatchConfiguration(BaseModel):
    """SCIM Patch Configuration."""
    supported: bool


class SCIMETagConfiguration(BaseModel):
    """SCIM ETag Configuration."""
    supported: bool


class SCIMServiceProviderConfig(BaseModel):
    """SCIM Service Provider Configuration."""
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]
    documentation_uri: str = Field(alias="documentationUri")
    patch: SCIMPatchConfiguration
    bulk: SCIMBulkConfiguration
    filter: SCIMFilterConfiguration
    change_password: SCIMChangePasswordConfiguration = Field(alias="changePassword")
    sort: SCIMSortConfiguration
    etag: SCIMETagConfiguration
    authentication_schemes: List[SCIMAuthenticationScheme] = Field(alias="authenticationSchemes")
    meta: SCIMMeta

    class Config:
        allow_population_by_field_name = True


# Update forward references
SCIMAttribute.model_rebuild()
