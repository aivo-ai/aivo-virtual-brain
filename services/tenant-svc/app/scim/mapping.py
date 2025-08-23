"""
SCIM 2.0 Mapping and Transformation

Bidirectional mapping between SCIM resources and internal models,
with support for complex attributes and enterprise extensions.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from ..models import User, Group, GroupMembership, get_version_etag
from ..schemas import (
    SCIMUser, SCIMGroup, SCIMName, SCIMEmail, SCIMPhoneNumber, 
    SCIMAddress, SCIMEnterpriseUser, SCIMMeta, SCIMGroupMember
)


class SCIMMapper:
    """Bidirectional mapping between SCIM resources and database models."""
    
    @staticmethod
    def user_to_scim(user: User, base_url: str = "", include_groups: bool = True) -> SCIMUser:
        """Convert User model to SCIM User resource."""
        
        # Build SCIM name object
        name = None
        if any([user.formatted_name, user.family_name, user.given_name, 
                user.middle_name, user.honorific_prefix, user.honorific_suffix]):
            name = SCIMName(
                formatted=user.formatted_name,
                familyName=user.family_name,
                givenName=user.given_name,
                middleName=user.middle_name,
                honorificPrefix=user.honorific_prefix,
                honorificSuffix=user.honorific_suffix
            )
        
        # Build emails
        emails = []
        if user.primary_email:
            emails.append(SCIMEmail(value=user.primary_email, type="work", primary=True))
        if user.work_email and user.work_email != user.primary_email:
            emails.append(SCIMEmail(value=user.work_email, type="work", primary=False))
        if user.home_email:
            emails.append(SCIMEmail(value=user.home_email, type="home", primary=False))
        
        # Build phone numbers
        phone_numbers = []
        if user.work_phone:
            phone_numbers.append(SCIMPhoneNumber(value=user.work_phone, type="work"))
        if user.home_phone:
            phone_numbers.append(SCIMPhoneNumber(value=user.home_phone, type="home"))
        if user.mobile_phone:
            phone_numbers.append(SCIMPhoneNumber(value=user.mobile_phone, type="mobile"))
        
        # Build addresses
        addresses = []
        if user.work_address:
            if isinstance(user.work_address, dict):
                addresses.append(SCIMAddress(
                    formatted=user.work_address.get('formatted'),
                    streetAddress=user.work_address.get('streetAddress'),
                    locality=user.work_address.get('locality'),
                    region=user.work_address.get('region'),
                    postalCode=user.work_address.get('postalCode'),
                    country=user.work_address.get('country'),
                    type="work"
                ))
        
        if user.home_address:
            if isinstance(user.home_address, dict):
                addresses.append(SCIMAddress(
                    formatted=user.home_address.get('formatted'),
                    streetAddress=user.home_address.get('streetAddress'),
                    locality=user.home_address.get('locality'),
                    region=user.home_address.get('region'),
                    postalCode=user.home_address.get('postalCode'),
                    country=user.home_address.get('country'),
                    type="home"
                ))
        
        # Build enterprise extension
        enterprise_user = None
        if any([user.employee_number, user.cost_center, user.organization, 
                user.division, user.department, user.manager_id]):
            
            manager = None
            if user.manager_id:
                manager = {
                    "value": str(user.manager_id),
                    "$ref": f"{base_url}/Users/{user.manager_id}",
                    "displayName": user.manager.display_name if user.manager else None
                }
            
            enterprise_user = SCIMEnterpriseUser(
                employeeNumber=user.employee_number,
                costCenter=user.cost_center,
                organization=user.organization,
                division=user.division,
                department=user.department,
                manager=manager
            )
        
        # Build groups
        groups = []
        if include_groups:
            for membership in user.group_memberships:
                groups.append({
                    "value": str(membership.group.id),
                    "$ref": f"{base_url}/Groups/{membership.group.id}",
                    "display": membership.group.display_name,
                    "type": "direct"
                })
        
        # Build metadata
        meta = SCIMMeta(
            resourceType="User",
            created=user.created_at,
            lastModified=user.updated_at,
            location=f"{base_url}/Users/{user.id}",
            version=get_version_etag(user)
        )
        
        return SCIMUser(
            id=str(user.id),
            externalId=user.external_id,
            userName=user.user_name,
            name=name,
            displayName=user.display_name,
            nickName=user.nick_name,
            profileUrl=user.profile_url,
            title=user.title,
            userType=user.user_type,
            preferredLanguage=user.locale,
            locale=user.locale,
            timezone=user.timezone,
            active=user.active,
            emails=emails,
            phoneNumbers=phone_numbers,
            addresses=addresses,
            groups=groups,
            meta=meta,
            **{"urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": enterprise_user.dict() if enterprise_user else None}
        )
    
    @staticmethod
    def scim_to_user(scim_user: Union[Dict[str, Any], SCIMUser], tenant_id: str) -> User:
        """Convert SCIM User resource to User model."""
        
        if isinstance(scim_user, dict):
            data = scim_user
        else:
            data = scim_user.dict(by_alias=True)
        
        # Extract name components
        name = data.get('name', {})
        
        # Extract primary email
        emails = data.get('emails', [])
        primary_email = None
        work_email = None
        home_email = None
        
        for email in emails:
            if email.get('primary'):
                primary_email = email.get('value')
            elif email.get('type') == 'work':
                work_email = email.get('value')
            elif email.get('type') == 'home':
                home_email = email.get('value')
        
        if not primary_email and emails:
            primary_email = emails[0].get('value')
        
        # Extract phone numbers
        phone_numbers = data.get('phoneNumbers', [])
        work_phone = None
        home_phone = None
        mobile_phone = None
        
        for phone in phone_numbers:
            if phone.get('type') == 'work':
                work_phone = phone.get('value')
            elif phone.get('type') == 'home':
                home_phone = phone.get('value')
            elif phone.get('type') == 'mobile':
                mobile_phone = phone.get('value')
        
        # Extract addresses
        addresses = data.get('addresses', [])
        work_address = None
        home_address = None
        
        for address in addresses:
            if address.get('type') == 'work':
                work_address = {
                    'formatted': address.get('formatted'),
                    'streetAddress': address.get('streetAddress'),
                    'locality': address.get('locality'),
                    'region': address.get('region'),
                    'postalCode': address.get('postalCode'),
                    'country': address.get('country')
                }
            elif address.get('type') == 'home':
                home_address = {
                    'formatted': address.get('formatted'),
                    'streetAddress': address.get('streetAddress'),
                    'locality': address.get('locality'),
                    'region': address.get('region'),
                    'postalCode': address.get('postalCode'),
                    'country': address.get('country')
                }
        
        # Extract enterprise extension
        enterprise = data.get('urn:ietf:params:scim:schemas:extension:enterprise:2.0:User', {})
        
        user = User(
            tenant_id=tenant_id,
            external_id=data.get('externalId'),
            user_name=data.get('userName'),
            display_name=data.get('displayName'),
            nick_name=data.get('nickName'),
            profile_url=data.get('profileUrl'),
            title=data.get('title'),
            user_type=data.get('userType'),
            locale=data.get('locale') or data.get('preferredLanguage'),
            timezone=data.get('timezone'),
            active=data.get('active', True),
            formatted_name=name.get('formatted'),
            family_name=name.get('familyName'),
            given_name=name.get('givenName'),
            middle_name=name.get('middleName'),
            honorific_prefix=name.get('honorificPrefix'),
            honorific_suffix=name.get('honorificSuffix'),
            primary_email=primary_email,
            work_email=work_email,
            home_email=home_email,
            work_phone=work_phone,
            home_phone=home_phone,
            mobile_phone=mobile_phone,
            work_address=work_address,
            home_address=home_address,
            employee_number=enterprise.get('employeeNumber'),
            cost_center=enterprise.get('costCenter'),
            organization=enterprise.get('organization'),
            division=enterprise.get('division'),
            department=enterprise.get('department')
        )
        
        # Handle password if provided
        password = data.get('password')
        if password:
            user.password = password  # Should be hashed by service
        
        return user
    
    @staticmethod
    def group_to_scim(group: Group, base_url: str = "") -> SCIMGroup:
        """Convert Group model to SCIM Group resource."""
        
        # Build members
        members = []
        for membership in group.memberships:
            members.append(SCIMGroupMember(
                value=str(membership.user.id),
                ref=f"{base_url}/Users/{membership.user.id}",
                type="User",
                display=membership.user.display_name
            ))
        
        # Build metadata
        meta = SCIMMeta(
            resourceType="Group",
            created=group.created_at,
            lastModified=group.updated_at,
            location=f"{base_url}/Groups/{group.id}",
            version=get_version_etag(group)
        )
        
        return SCIMGroup(
            id=str(group.id),
            externalId=group.external_id,
            displayName=group.display_name,
            members=members,
            meta=meta
        )
    
    @staticmethod
    def scim_to_group(scim_group: Union[Dict[str, Any], SCIMGroup], tenant_id: str) -> Group:
        """Convert SCIM Group resource to Group model."""
        
        if isinstance(scim_group, dict):
            data = scim_group
        else:
            data = scim_group.dict(by_alias=True)
        
        group = Group(
            tenant_id=tenant_id,
            external_id=data.get('externalId'),
            display_name=data.get('displayName')
        )
        
        return group
    
    @staticmethod
    def update_user_from_scim(user: User, scim_data: Dict[str, Any]) -> User:
        """Update existing User model from SCIM data."""
        
        # Update basic attributes
        if 'displayName' in scim_data:
            user.display_name = scim_data['displayName']
        if 'nickName' in scim_data:
            user.nick_name = scim_data['nickName']
        if 'profileUrl' in scim_data:
            user.profile_url = scim_data['profileUrl']
        if 'title' in scim_data:
            user.title = scim_data['title']
        if 'userType' in scim_data:
            user.user_type = scim_data['userType']
        if 'locale' in scim_data:
            user.locale = scim_data['locale']
        if 'timezone' in scim_data:
            user.timezone = scim_data['timezone']
        if 'active' in scim_data:
            user.active = scim_data['active']
        
        # Update name
        name = scim_data.get('name', {})
        if name:
            user.formatted_name = name.get('formatted', user.formatted_name)
            user.family_name = name.get('familyName', user.family_name)
            user.given_name = name.get('givenName', user.given_name)
            user.middle_name = name.get('middleName', user.middle_name)
            user.honorific_prefix = name.get('honorificPrefix', user.honorific_prefix)
            user.honorific_suffix = name.get('honorificSuffix', user.honorific_suffix)
        
        # Update emails
        emails = scim_data.get('emails', [])
        for email in emails:
            if email.get('primary') or email.get('type') == 'work':
                user.primary_email = email.get('value')
            elif email.get('type') == 'home':
                user.home_email = email.get('value')
        
        # Update enterprise extension
        enterprise = scim_data.get('urn:ietf:params:scim:schemas:extension:enterprise:2.0:User', {})
        if enterprise:
            user.employee_number = enterprise.get('employeeNumber', user.employee_number)
            user.cost_center = enterprise.get('costCenter', user.cost_center)
            user.organization = enterprise.get('organization', user.organization)
            user.division = enterprise.get('division', user.division)
            user.department = enterprise.get('department', user.department)
        
        return user
    
    @staticmethod
    def update_group_from_scim(group: Group, scim_data: Dict[str, Any]) -> Group:
        """Update existing Group model from SCIM data."""
        
        if 'displayName' in scim_data:
            group.display_name = scim_data['displayName']
        
        return group


class SCIMPatchProcessor:
    """Process SCIM PATCH operations."""
    
    @staticmethod
    def apply_patch_operations(resource: Union[User, Group], operations: List[Dict[str, Any]]):
        """Apply PATCH operations to resource."""
        
        for operation in operations:
            op_type = operation.get('op', '').lower()
            path = operation.get('path', '')
            value = operation.get('value')
            
            if op_type == 'replace':
                SCIMPatchProcessor._apply_replace(resource, path, value)
            elif op_type == 'add':
                SCIMPatchProcessor._apply_add(resource, path, value)
            elif op_type == 'remove':
                SCIMPatchProcessor._apply_remove(resource, path, value)
            else:
                raise ValueError(f"Unsupported PATCH operation: {op_type}")
    
    @staticmethod
    def _apply_replace(resource: Union[User, Group], path: str, value: Any):
        """Apply REPLACE operation."""
        if isinstance(resource, User):
            SCIMPatchProcessor._replace_user_attribute(resource, path, value)
        elif isinstance(resource, Group):
            SCIMPatchProcessor._replace_group_attribute(resource, path, value)
    
    @staticmethod
    def _apply_add(resource: Union[User, Group], path: str, value: Any):
        """Apply ADD operation."""
        # For simple attributes, ADD is same as REPLACE
        SCIMPatchProcessor._apply_replace(resource, path, value)
    
    @staticmethod
    def _apply_remove(resource: Union[User, Group], path: str, value: Any):
        """Apply REMOVE operation."""
        if isinstance(resource, User):
            SCIMPatchProcessor._remove_user_attribute(resource, path)
        elif isinstance(resource, Group):
            SCIMPatchProcessor._remove_group_attribute(resource, path)
    
    @staticmethod
    def _replace_user_attribute(user: User, path: str, value: Any):
        """Replace user attribute."""
        path_map = {
            'active': 'active',
            'displayName': 'display_name',
            'nickName': 'nick_name',
            'title': 'title',
            'userType': 'user_type',
            'locale': 'locale',
            'timezone': 'timezone',
            'name.familyName': 'family_name',
            'name.givenName': 'given_name',
            'name.formatted': 'formatted_name'
        }
        
        attr = path_map.get(path)
        if attr:
            setattr(user, attr, value)
    
    @staticmethod
    def _replace_group_attribute(group: Group, path: str, value: Any):
        """Replace group attribute."""
        if path == 'displayName':
            group.display_name = value
    
    @staticmethod
    def _remove_user_attribute(user: User, path: str):
        """Remove user attribute."""
        path_map = {
            'displayName': 'display_name',
            'nickName': 'nick_name',
            'title': 'title',
            'locale': 'locale',
            'timezone': 'timezone'
        }
        
        attr = path_map.get(path)
        if attr:
            setattr(user, attr, None)
