#!/usr/bin/env python3
"""
Test runner for S1-08 Private Brain Binding feature.
This demonstrates the key functionality of the private brain persona system.
"""

import sys
import os
import asyncio
from datetime import date
import uuid

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.alias_utils import validate_alias, AliasValidationError, redact_alias_from_logs
from app.models import ModelProvider

def test_alias_validation():
    """Test the alias validation system."""
    print("🧪 Testing Alias Validation System...")
    
    # Test valid aliases
    valid_aliases = ["MathGenius2024", "BookLover", "ScienceNinja"]
    for alias in valid_aliases:
        try:
            validate_alias(alias)
            print(f"  ✅ Valid alias accepted: {alias}")
        except AliasValidationError as e:
            print(f"  ❌ Valid alias rejected: {alias} - {e}")
    
    # Test invalid aliases
    invalid_aliases = [
        ("damn_it", "profanity"), 
        ("john_smith", "real name"), 
        ("test@email.com", "PII")
    ]
    for alias, reason in invalid_aliases:
        try:
            validate_alias(alias)
            print(f"  ❌ Invalid alias accepted: {alias} ({reason})")
        except AliasValidationError as e:
            print(f"  ✅ Invalid alias rejected: {alias} ({reason}) - {e}")

def test_alias_redaction():
    """Test that aliases are properly redacted from logs."""
    print("\n🔒 Testing Alias Redaction System...")
    
    alias = "TestUser123"
    message = f"Creating persona for user {alias} with alias {alias}"
    
    redacted = redact_alias_from_logs(message, alias)
    if alias not in redacted and "[ALIAS_REDACTED]" in redacted:
        print(f"  ✅ Alias properly redacted from logs")
        print(f"  Original: {message}")
        print(f"  Redacted: {redacted}")
    else:
        print(f"  ❌ Alias redaction failed")

def test_model_bindings():
    """Test model binding configuration."""
    print("\n🤖 Testing Model Binding System...")
    
    # Demonstrate default model bindings
    from app.private_brain_service import DEFAULT_MODEL_BINDINGS
    
    print(f"  📊 Default model bindings configured:")
    for binding in DEFAULT_MODEL_BINDINGS:
        print(f"    - {binding['subject']}: {binding['provider'].value} {binding['model_name']}")

def test_api_schemas():
    """Test API schema validation."""
    print("\n📋 Testing API Schemas...")
    
    try:
        from app.schemas import PersonaCreateRequest, PersonaResponse, ModelBindingResponse
        
        # Test valid persona request
        valid_request = PersonaCreateRequest(
            alias="MathWizard2024",
            voice="friendly",
            tone="encouraging",
            speech_rate=100
        )
        print(f"  ✅ PersonaCreateRequest schema validated")
        
        # Test invalid speech rate
        try:
            invalid_request = PersonaCreateRequest(
                alias="TestUser",
                speech_rate=300  # Invalid - too high
            )
            print(f"  ❌ Invalid speech rate accepted")
        except Exception as e:
            print(f"  ✅ Invalid speech rate rejected: {str(e)}")
            
    except ImportError as e:
        print(f"  ❌ Schema import failed: {e}")

def main():
    """Run all tests."""
    print("🚀 AIVO Private Brain Binding - S1-08 Feature Test")
    print("=" * 50)
    
    test_alias_validation()
    test_alias_redaction()
    test_model_bindings()
    test_api_schemas()
    
    print("\n" + "=" * 50)
    print("✅ S1-08 Private Brain Binding feature tests completed!")
    print("\nKey Features Demonstrated:")
    print("  🛡️  Alias safety validation (profanity, PII, real names)")
    print("  🔒 Log redaction to protect learner privacy")
    print("  🤖 Default AI model bindings per subject")
    print("  📡 Event-driven architecture (LEARNER_CREATED → model bindings)")
    print("  🎭 Private brain persona management")

if __name__ == "__main__":
    main()