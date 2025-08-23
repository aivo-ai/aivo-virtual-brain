"""
Tax ID and billing address validators
"""

import re
import structlog
from typing import Optional, Tuple, Dict, Any, List
from pydantic import BaseModel, Field, validator

logger = structlog.get_logger(__name__)


class TaxIDValidator:
    """Validator for various tax identification numbers"""
    
    # Tax ID patterns for different countries/regions
    TAX_ID_PATTERNS = {
        "us_ein": r"^\d{2}-?\d{7}$",  # US EIN: XX-XXXXXXX
        "us_ssn": r"^\d{3}-?\d{2}-?\d{4}$",  # US SSN: XXX-XX-XXXX
        "eu_vat": r"^[A-Z]{2}\d{8,12}$",  # EU VAT: CCXXXXXXXXXX
        "gb_vat": r"^GB\d{9}$",  # UK VAT: GBXXXXXXXXX
        "ca_gst": r"^\d{9}RT\d{4}$",  # Canada GST: XXXXXXXXXRTXXXX
        "au_abn": r"^\d{11}$",  # Australia ABN: 11 digits
        "au_acn": r"^\d{9}$",  # Australia ACN: 9 digits
    }
    
    @classmethod
    def validate_format(cls, tax_id: str, country: str) -> Tuple[bool, Optional[str]]:
        """
        Validate tax ID format based on country
        
        Args:
            tax_id: Tax identification number
            country: Country code (ISO 3166-1 alpha-2)
            
        Returns:
            Tuple of (is_valid, tax_id_type)
        """
        if not tax_id:
            return False, None
            
        # Clean tax ID
        clean_tax_id = tax_id.replace(" ", "").replace("-", "").upper()
        
        # Determine tax ID type based on country and format
        tax_id_type = cls._detect_tax_id_type(clean_tax_id, country)
        
        if tax_id_type == "unknown":
            return False, None
            
        # Validate format
        pattern = cls.TAX_ID_PATTERNS.get(tax_id_type)
        if not pattern:
            return False, None
            
        is_valid = bool(re.match(pattern, clean_tax_id))
        return is_valid, tax_id_type if is_valid else None
    
    @classmethod
    def _detect_tax_id_type(cls, clean_tax_id: str, country: str) -> str:
        """Detect tax ID type based on format and country"""
        
        # US tax IDs
        if country == "US":
            if len(clean_tax_id) == 9 and clean_tax_id.isdigit():
                return "us_ein"
            elif len(clean_tax_id) == 11 and clean_tax_id.isdigit():
                return "us_ssn"
        
        # EU VAT IDs
        elif country in ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"]:
            if clean_tax_id.startswith(country) and len(clean_tax_id) >= 10:
                return "eu_vat"
        
        # UK VAT
        elif country == "GB":
            if clean_tax_id.startswith("GB") and len(clean_tax_id) == 11:
                return "gb_vat"
        
        # Canada GST/HST
        elif country == "CA":
            if len(clean_tax_id) == 15 and clean_tax_id.endswith("RT"):
                return "ca_gst"
        
        # Australia
        elif country == "AU":
            if len(clean_tax_id) == 11 and clean_tax_id.isdigit():
                return "au_abn"
            elif len(clean_tax_id) == 9 and clean_tax_id.isdigit():
                return "au_acn"
        
        return "unknown"
    
    @classmethod
    def get_tax_id_requirements(cls, country: str) -> Dict[str, Any]:
        """
        Get tax ID requirements for a specific country
        
        Args:
            country: Country code
            
        Returns:
            Dictionary with tax ID requirements
        """
        requirements = {
            "US": {
                "required": False,
                "types": ["us_ein", "us_ssn"],
                "labels": ["EIN (Federal Tax ID)", "SSN (Individual)"],
                "description": "For business accounts, provide EIN. For individual accounts, SSN is optional."
            },
            "GB": {
                "required": True,
                "types": ["gb_vat"],
                "labels": ["VAT Number"],
                "description": "UK VAT registration number is required for business accounts."
            },
            "CA": {
                "required": False,
                "types": ["ca_gst"],
                "labels": ["GST/HST Number"],
                "description": "GST/HST number required for registered businesses."
            },
            "AU": {
                "required": False,
                "types": ["au_abn", "au_acn"],
                "labels": ["ABN", "ACN"],
                "description": "Australian Business Number (ABN) or Company Number (ACN)."
            }
        }
        
        # Default for EU countries
        if country in ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"]:
            requirements[country] = {
                "required": True,
                "types": ["eu_vat"],
                "labels": ["VAT Number"],
                "description": f"EU VAT registration number required for {country} businesses."
            }
        
        return requirements.get(country, {
            "required": False,
            "types": [],
            "labels": [],
            "description": "No specific tax ID requirements for this country."
        })


class BillingAddressValidator:
    """Validator for billing addresses with country-specific rules"""
    
    # Postal code patterns by country
    POSTAL_CODE_PATTERNS = {
        "US": r"^\d{5}(-\d{4})?$",  # 12345 or 12345-6789
        "CA": r"^[A-Z]\d[A-Z] \d[A-Z]\d$",  # A1A 1A1
        "GB": r"^[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}$",  # SW1A 1AA
        "DE": r"^\d{5}$",  # 12345
        "FR": r"^\d{5}$",  # 12345
        "AU": r"^\d{4}$",  # 1234
        "NL": r"^\d{4} [A-Z]{2}$",  # 1234 AB
    }
    
    @classmethod
    def validate_postal_code(cls, postal_code: str, country: str) -> bool:
        """
        Validate postal code format for specific country
        
        Args:
            postal_code: Postal/ZIP code
            country: Country code
            
        Returns:
            True if valid format
        """
        if not postal_code:
            return False
            
        pattern = cls.POSTAL_CODE_PATTERNS.get(country)
        if not pattern:
            # For countries without specific patterns, just check it's not empty
            return len(postal_code.strip()) > 0
            
        return bool(re.match(pattern, postal_code.upper().strip()))
    
    @classmethod
    def validate_address(cls, address_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate complete billing address
        
        Args:
            address_data: Address dictionary with line1, city, country, etc.
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Required fields
        if not address_data.get("line1", "").strip():
            errors.append("Address line 1 is required")
            
        if not address_data.get("city", "").strip():
            errors.append("City is required")
            
        if not address_data.get("country", "").strip():
            errors.append("Country is required")
        else:
            country = address_data["country"].upper()
            
            # Validate postal code if provided
            postal_code = address_data.get("postal_code", "")
            if postal_code and not cls.validate_postal_code(postal_code, country):
                errors.append(f"Invalid postal code format for {country}")
            
            # State required for US and CA
            if country in ["US", "CA"] and not address_data.get("state", "").strip():
                errors.append(f"State/Province is required for {country}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_address_requirements(cls, country: str) -> Dict[str, Any]:
        """
        Get address field requirements for a specific country
        
        Args:
            country: Country code
            
        Returns:
            Dictionary with address requirements
        """
        requirements = {
            "US": {
                "required_fields": ["line1", "city", "state", "postal_code", "country"],
                "optional_fields": ["line2"],
                "postal_code_label": "ZIP Code",
                "postal_code_example": "12345 or 12345-6789",
                "state_label": "State"
            },
            "CA": {
                "required_fields": ["line1", "city", "state", "postal_code", "country"],
                "optional_fields": ["line2"],
                "postal_code_label": "Postal Code",
                "postal_code_example": "A1A 1A1",
                "state_label": "Province"
            },
            "GB": {
                "required_fields": ["line1", "city", "postal_code", "country"],
                "optional_fields": ["line2", "state"],
                "postal_code_label": "Postcode",
                "postal_code_example": "SW1A 1AA",
                "state_label": "County"
            },
            "AU": {
                "required_fields": ["line1", "city", "state", "postal_code", "country"],
                "optional_fields": ["line2"],
                "postal_code_label": "Postcode",
                "postal_code_example": "1234",
                "state_label": "State"
            }
        }
        
        # Default for other countries
        return requirements.get(country, {
            "required_fields": ["line1", "city", "country"],
            "optional_fields": ["line2", "state", "postal_code"],
            "postal_code_label": "Postal Code",
            "postal_code_example": "",
            "state_label": "State/Province"
        })
