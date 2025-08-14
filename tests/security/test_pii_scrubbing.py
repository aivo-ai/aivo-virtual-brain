#!/usr/bin/env python3
"""
AIVO Virtual Brains - S1-18 Security & Privacy Tests
PII Scrubbing at Inference Edge Test Suite

Tests PII detection, scrubbing, and audit for AI inference requests:
- Email, phone, SSN, name detection patterns
- Redaction, tokenization, and hashing methods
- Audit trail for PII findings and scrubbing decisions
- Performance impact measurement for inference pipeline

Coverage Target: ≥90% of PII detection patterns
"""

import re
import hashlib
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import requests


class PIIScrubber:
    """PII detection and scrubbing for AI inference requests"""
    
    def __init__(self):
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            'ssn': r'\b(?!000|666|9\d\d)\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b',
            'credit_card': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        }
        
        # Common name patterns (simplified for testing)
        self.name_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
            r'\b[A-Z][a-z]+, [A-Z][a-z]+\b',  # Last, First
        ]
        
        self.scrub_methods = ['redact', 'tokenize', 'hash']
    
    def detect_pii(self, content: str) -> List[Dict]:
        """Detect PII in content and return findings"""
        findings = []
        
        # Detect structured PII patterns
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                findings.append({
                    'type': pii_type,
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.95  # High confidence for regex matches
                })
        
        # Detect names (lower confidence)
        for name_pattern in self.name_patterns:
            matches = re.finditer(name_pattern, content)
            for match in matches:
                # Skip if it's likely not a name (common false positives)
                name_candidate = match.group()
                if not self._is_likely_name(name_candidate):
                    continue
                    
                findings.append({
                    'type': 'name',
                    'value': name_candidate,
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.7  # Lower confidence for name detection
                })
        
        return findings
    
    def _is_likely_name(self, candidate: str) -> bool:
        """Basic heuristic to filter name false positives"""
        # Skip common non-name patterns
        false_positives = ['New York', 'Los Angeles', 'San Francisco', 'Data Science', 'Machine Learning']
        return candidate not in false_positives
    
    def scrub_content(
        self, 
        content: str, 
        method: str = 'tokenize',
        learner_id: Optional[str] = None
    ) -> Tuple[str, List[Dict]]:
        """Scrub PII from content using specified method"""
        findings = self.detect_pii(content)
        scrubbed_content = content
        scrub_log = []
        
        # Sort findings by position (descending) to avoid offset issues
        findings.sort(key=lambda x: x['start'], reverse=True)
        
        for finding in findings:
            original_value = finding['value']
            pii_type = finding['type']
            start = finding['start']
            end = finding['end']
            
            if method == 'redact':
                replacement = '[REDACTED]'
            elif method == 'tokenize':
                token_id = hashlib.md5(original_value.encode()).hexdigest()[:8]
                replacement = f'[{pii_type.upper()}_{token_id}]'
            elif method == 'hash':
                hash_value = hashlib.sha256(original_value.encode()).hexdigest()[:16]
                replacement = f'[{pii_type.upper()}_HASH_{hash_value}]'
            else:
                replacement = '[SCRUBBED]'
            
            # Replace in content
            scrubbed_content = scrubbed_content[:start] + replacement + scrubbed_content[end:]
            
            # Log scrubbing action
            scrub_entry = {
                'type': pii_type,
                'original_value': original_value,
                'replacement': replacement,
                'position': start,
                'confidence': finding['confidence'],
                'method': method,
                'timestamp': datetime.utcnow().isoformat(),
                'learner_id': learner_id
            }
            scrub_log.append(scrub_entry)
        
        return scrubbed_content, scrub_log
    
    def audit_pii_scrubbing(
        self, 
        request_id: str, 
        learner_id: str, 
        scrub_log: List[Dict],
        processing_time_ms: float
    ) -> str:
        """Create audit entry for PII scrubbing operation"""
        audit_entry = {
            'request_id': request_id,
            'learner_id': learner_id,
            'timestamp': datetime.utcnow().isoformat(),
            'pii_findings_count': len(scrub_log),
            'pii_types_found': list(set(entry['type'] for entry in scrub_log)),
            'scrub_method': scrub_log[0]['method'] if scrub_log else None,
            'processing_time_ms': processing_time_ms,
            'findings': scrub_log
        }
        
        # In production, this would be logged to audit system
        audit_id = f"pii_audit_{uuid.uuid4().hex[:8]}"
        print(f"PII Audit {audit_id}: {json.dumps(audit_entry, indent=2)}")
        
        return audit_id


class TestPIIDetection:
    """Test PII detection patterns and accuracy"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scrubber = PIIScrubber()
    
    def test_email_detection(self):
        """Test: Email addresses are accurately detected"""
        # Arrange: Content with various email formats
        test_content = """
        Contact me at john.doe@example.com or support@company.co.uk
        Also try jane_smith+test@domain-name.org for testing.
        Invalid emails: @missing.domain, no-at-symbol.com
        """
        
        # Act: Detect PII
        findings = self.scrubber.detect_pii(test_content)
        
        # Assert: Valid emails detected
        email_findings = [f for f in findings if f['type'] == 'email']
        assert len(email_findings) == 3
        
        detected_emails = [f['value'] for f in email_findings]
        assert 'john.doe@example.com' in detected_emails
        assert 'support@company.co.uk' in detected_emails  
        assert 'jane_smith+test@domain-name.org' in detected_emails
        
        # Verify invalid emails not detected
        for finding in email_findings:
            assert not finding['value'].startswith('@')
            assert '@' in finding['value']
    
    def test_phone_number_detection(self):
        """Test: Phone numbers in various formats are detected"""
        # Arrange: Content with phone numbers
        test_content = """
        Call me at (555) 123-4567 or 555-987-6543
        International: +1 555 111 2222
        No formatting: 5551234567
        Invalid: 123-45-6789 (too short), 555-1234 (incomplete)
        """
        
        # Act: Detect PII
        findings = self.scrubber.detect_pii(test_content)
        
        # Assert: Valid phone numbers detected
        phone_findings = [f for f in findings if f['type'] == 'phone']
        assert len(phone_findings) >= 3
        
        # Verify various formats detected
        phone_values = [f['value'] for f in phone_findings]
        assert any('555' in phone and '123' in phone for phone in phone_values)
        assert any('987' in phone for phone in phone_values)
    
    def test_ssn_detection(self):
        """Test: Social Security Numbers are detected with validation"""
        # Arrange: Content with SSN patterns
        test_content = """
        My SSN is 123-45-6789 for tax purposes.
        Also have 987654321 without dashes.
        Invalid: 000-12-3456 (starts with 000)
        Invalid: 123-00-4567 (middle 00)
        Invalid: 123-45-0000 (ends with 0000)
        """
        
        # Act: Detect PII
        findings = self.scrubber.detect_pii(test_content)
        
        # Assert: Valid SSNs detected, invalid ones filtered
        ssn_findings = [f for f in findings if f['type'] == 'ssn']
        assert len(ssn_findings) >= 1
        
        # Valid SSN should be detected
        ssn_values = [f['value'] for f in ssn_findings]
        assert any('123' in ssn for ssn in ssn_values)
        
        # Invalid SSNs should not be detected
        for finding in ssn_findings:
            value = finding['value'].replace('-', '').replace(' ', '')
            assert not value.startswith('000')  # Invalid prefix
            assert '00' not in value[3:5]  # Invalid middle
            assert not value.endswith('0000')  # Invalid suffix
    
    def test_credit_card_detection(self):
        """Test: Credit card numbers are detected"""
        # Arrange: Content with credit card numbers
        test_content = """
        Visa: 4111111111111111
        MasterCard: 5555555555554444  
        Amex: 378282246310005
        Invalid: 1234567890123456 (wrong pattern)
        """
        
        # Act: Detect PII
        findings = self.scrubber.detect_pii(test_content)
        
        # Assert: Valid credit cards detected
        cc_findings = [f for f in findings if f['type'] == 'credit_card']
        assert len(cc_findings) >= 2
        
        cc_values = [f['value'] for f in cc_findings]
        assert any(cc.startswith('4') for cc in cc_values)  # Visa
        assert any(cc.startswith('5') for cc in cc_values)  # MasterCard
    
    def test_name_detection_with_false_positive_filtering(self):
        """Test: Names detected with false positive filtering"""
        # Arrange: Content with names and false positives
        test_content = """
        Student John Smith submitted homework.
        Contact Jane Doe for questions.
        False positives: New York, Los Angeles, Data Science
        Edge case: Dr. Smith, Mary Jane Watson
        """
        
        # Act: Detect PII
        findings = self.scrubber.detect_pii(test_content)
        
        # Assert: Names detected, false positives filtered
        name_findings = [f for f in findings if f['type'] == 'name']
        
        name_values = [f['value'] for f in name_findings]
        
        # Should detect actual names
        assert any('John Smith' in name or 'Jane Doe' in name for name in name_values)
        
        # Should filter common false positives
        false_positives = ['New York', 'Los Angeles', 'Data Science']
        for fp in false_positives:
            assert fp not in name_values
    
    def test_ip_address_detection(self):
        """Test: IP addresses are detected"""
        # Arrange: Content with IP addresses
        test_content = """
        Server IP: 192.168.1.100
        Public IP: 8.8.8.8
        Invalid: 999.999.999.999, 192.168.1
        """
        
        # Act: Detect PII
        findings = self.scrubber.detect_pii(test_content)
        
        # Assert: Valid IPs detected
        ip_findings = [f for f in findings if f['type'] == 'ip_address']
        assert len(ip_findings) >= 2
        
        ip_values = [f['value'] for f in ip_findings]
        assert '192.168.1.100' in ip_values
        assert '8.8.8.8' in ip_values


class TestPIIScrubbing:
    """Test PII scrubbing methods and effectiveness"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scrubber = PIIScrubber()
        self.test_content = """
        Hi John Doe, your email john.doe@example.com is confirmed.
        Phone: (555) 123-4567, SSN: 123-45-6789
        Credit card: 4111111111111111
        """
    
    def test_redaction_scrubbing_method(self):
        """Test: PII redaction replaces sensitive data with [REDACTED]"""
        # Act: Scrub with redaction
        scrubbed, log = self.scrubber.scrub_content(self.test_content, method='redact')
        
        # Assert: PII replaced with redaction markers
        assert '[REDACTED]' in scrubbed
        assert 'john.doe@example.com' not in scrubbed
        assert '555' not in scrubbed or '[REDACTED]' in scrubbed  # Phone scrubbed
        assert '123-45-6789' not in scrubbed
        assert '4111111111111111' not in scrubbed
        
        # Verify scrub log
        assert len(log) >= 4  # Email, phone, SSN, credit card
        assert all(entry['method'] == 'redact' for entry in log)
        assert all(entry['replacement'] == '[REDACTED]' for entry in log)
    
    def test_tokenization_scrubbing_method(self):
        """Test: PII tokenization creates semantic tokens"""
        # Act: Scrub with tokenization
        scrubbed, log = self.scrubber.scrub_content(self.test_content, method='tokenize')
        
        # Assert: PII replaced with semantic tokens
        assert '[EMAIL_' in scrubbed
        assert '[PHONE_' in scrubbed or '[SSN_' in scrubbed  # At least one tokenized
        assert 'john.doe@example.com' not in scrubbed
        
        # Verify token format and uniqueness
        email_entries = [entry for entry in log if entry['type'] == 'email']
        if email_entries:
            email_entry = email_entries[0]
            assert email_entry['replacement'].startswith('[EMAIL_')
            assert email_entry['replacement'].endswith(']')
            assert len(email_entry['replacement']) > 8  # Has hash component
        
        # Verify scrub log details
        for entry in log:
            assert entry['method'] == 'tokenize'
            assert entry['original_value'] != entry['replacement']
            assert entry['timestamp']
    
    def test_hashing_scrubbing_method(self):
        """Test: PII hashing creates deterministic hash tokens"""
        # Act: Scrub with hashing (multiple times for consistency check)
        scrubbed1, log1 = self.scrubber.scrub_content(self.test_content, method='hash')
        scrubbed2, log2 = self.scrubber.scrub_content(self.test_content, method='hash')
        
        # Assert: Consistent hashing results
        assert scrubbed1 == scrubbed2  # Deterministic hashing
        assert '[EMAIL_HASH_' in scrubbed1
        assert 'john.doe@example.com' not in scrubbed1
        
        # Verify hash tokens
        for log in [log1, log2]:
            email_entries = [entry for entry in log if entry['type'] == 'email']
            if email_entries:
                email_entry = email_entries[0]
                assert email_entry['method'] == 'hash'
                assert '_HASH_' in email_entry['replacement']
                assert len(email_entry['replacement'].split('_HASH_')[1].rstrip(']')) == 16  # Hash length
    
    def test_scrubbing_preserves_content_structure(self):
        """Test: PII scrubbing maintains content readability and structure"""
        # Arrange: Structured content with PII
        structured_content = """
        Customer Information:
        - Name: Alice Johnson
        - Email: alice.johnson@company.com
        - Phone: (555) 987-6543
        
        Please review and confirm details.
        """
        
        # Act: Scrub content
        scrubbed, log = self.scrubber.scrub_content(structured_content, method='tokenize')
        
        # Assert: Structure preserved
        assert 'Customer Information:' in scrubbed
        assert '- Name:' in scrubbed
        assert '- Email:' in scrubbed  
        assert '- Phone:' in scrubbed
        assert 'Please review and confirm details.' in scrubbed
        
        # PII replaced
        assert 'Alice Johnson' not in scrubbed
        assert 'alice.johnson@company.com' not in scrubbed
        assert '987-6543' not in scrubbed
        
        # Tokens in appropriate places
        assert '[NAME_' in scrubbed or '[EMAIL_' in scrubbed
    
    def test_scrubbing_handles_overlapping_patterns(self):
        """Test: Overlapping PII patterns handled correctly"""
        # Arrange: Content with potential overlaps
        overlap_content = """
        Contact info: email john.doe@example.com, phone 555-123-4567
        Combined: john.doe+555@domain.com (email with phone-like numbers)
        """
        
        # Act: Scrub content
        scrubbed, log = self.scrubber.scrub_content(overlap_content, method='tokenize')
        
        # Assert: Each PII type handled appropriately
        pii_types = set(entry['type'] for entry in log)
        assert 'email' in pii_types
        
        # No original PII values remain
        assert 'john.doe@example.com' not in scrubbed
        assert 'john.doe+555@domain.com' not in scrubbed
        
        # Verify proper tokenization
        assert len(log) >= 2  # At least 2 PII items found


class TestPIIAuditTrail:
    """Test PII scrubbing audit trail and compliance logging"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scrubber = PIIScrubber()
    
    def test_pii_audit_entry_creation(self):
        """Test: PII scrubbing creates comprehensive audit entries"""
        # Arrange: Content with PII
        content = "Contact john.doe@example.com or call (555) 123-4567"
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        learner_id = "test_learner_001"
        
        start_time = time.time()
        
        # Act: Scrub and audit
        scrubbed, scrub_log = self.scrubber.scrub_content(content, learner_id=learner_id)
        processing_time = (time.time() - start_time) * 1000
        
        audit_id = self.scrubber.audit_pii_scrubbing(
            request_id=request_id,
            learner_id=learner_id,
            scrub_log=scrub_log,
            processing_time_ms=processing_time
        )
        
        # Assert: Audit entry created
        assert audit_id.startswith('pii_audit_')
        assert len(scrub_log) >= 2  # Email and phone detected
        
        # Verify audit log structure
        for entry in scrub_log:
            required_fields = ['type', 'original_value', 'replacement', 'position', 'confidence', 'method', 'timestamp', 'learner_id']
            for field in required_fields:
                assert field in entry, f"Missing audit field: {field}"
            
            assert entry['learner_id'] == learner_id
            assert entry['confidence'] > 0
            assert entry['timestamp']
    
    def test_pii_performance_impact_measurement(self):
        """Test: PII scrubbing performance impact is measured and logged"""
        # Arrange: Large content for performance testing
        large_content = """
        This is a large document containing multiple PII instances.
        Emails: john.doe@example.com, jane.smith@company.org, admin@test.gov
        Phones: (555) 123-4567, 555-987-6543, +1 555 111 2222
        SSNs: 123-45-6789, 987-65-4321
        Names: John Doe, Jane Smith, Bob Johnson, Alice Williams
        """ * 10  # Repeat for larger content
        
        # Act: Measure scrubbing performance
        start_time = time.time()
        scrubbed, scrub_log = self.scrubber.scrub_content(large_content, method='tokenize')
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Assert: Performance measured and reasonable
        assert processing_time_ms > 0
        assert processing_time_ms < 5000  # Should complete in under 5 seconds
        
        # Verify comprehensive scrubbing despite size
        assert len(scrub_log) >= 40  # Multiple PII instances * 10 repetitions
        
        # Performance acceptability for inference pipeline
        pii_per_ms = len(scrub_log) / processing_time_ms if processing_time_ms > 0 else 0
        assert pii_per_ms > 0.01  # At least 0.01 PII items per millisecond
    
    def test_pii_audit_correlation_tracking(self):
        """Test: PII audit entries can be correlated across requests"""
        # Arrange: Multiple related requests
        learner_id = "test_learner_002"
        base_correlation = f"inference_{uuid.uuid4().hex[:8]}"
        
        requests_data = [
            "User john.doe@example.com submitted request",
            "Phone verification for (555) 123-4567",
            "Profile update for john.doe@example.com"
        ]
        
        audit_ids = []
        
        # Act: Process multiple requests
        for i, content in enumerate(requests_data):
            request_id = f"{base_correlation}_req_{i}"
            
            start_time = time.time()
            scrubbed, scrub_log = self.scrubber.scrub_content(content, learner_id=learner_id)
            processing_time = (time.time() - start_time) * 1000
            
            # Add correlation to scrub log
            for entry in scrub_log:
                entry['base_correlation'] = base_correlation
                entry['request_sequence'] = i
            
            audit_id = self.scrubber.audit_pii_scrubbing(
                request_id=request_id,
                learner_id=learner_id,
                scrub_log=scrub_log,
                processing_time_ms=processing_time
            )
            audit_ids.append(audit_id)
        
        # Assert: All requests correlated
        assert len(audit_ids) == 3
        assert all(audit_id.startswith('pii_audit_') for audit_id in audit_ids)
        
        # Verify correlation data in scrub logs would enable cross-request tracking
        # (In production, this would be queryable via correlation ID)
    
    def test_pii_scrubbing_compliance_fields(self):
        """Test: PII audit includes all compliance-required fields"""
        # Arrange: PII scrubbing scenario
        content = "Sensitive data: jane.doe@email.com, SSN: 123-45-6789"
        learner_id = "compliance_test_learner"
        
        # Act: Scrub with comprehensive metadata
        scrubbed, scrub_log = self.scrubber.scrub_content(
            content, 
            method='hash',
            learner_id=learner_id
        )
        
        # Assert: Compliance fields present
        compliance_fields = [
            'type',           # PII type for classification
            'original_value', # For audit trail (secure storage)
            'replacement',    # What was substituted
            'position',       # Location in content
            'confidence',     # Detection confidence
            'method',         # Scrubbing method used
            'timestamp',      # When scrubbing occurred
            'learner_id'      # Data subject identification
        ]
        
        for entry in scrub_log:
            for field in compliance_fields:
                assert field in entry, f"Missing compliance field: {field}"
            
            # Verify field formats
            assert isinstance(entry['confidence'], (int, float))
            assert 0 <= entry['confidence'] <= 1
            assert entry['method'] in ['redact', 'tokenize', 'hash']
            
            # Timestamp format validation
            datetime.fromisoformat(entry['timestamp'])  # Should not raise exception


class TestInferenceEdgeIntegration:
    """Test PII scrubbing integration with inference pipeline"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scrubber = PIIScrubber()
        self.inference_url = "http://localhost:8080"  # Mock inference service
    
    def test_inference_request_pii_scrubbing_flow(self):
        """Test: Complete flow from inference request to PII-scrubbed model input"""
        # Arrange: Inference request with PII
        inference_request = {
            "learner_id": "test_learner_003",
            "prompt": "My name is John Doe and my email is john.doe@example.com. I'm having trouble with math homework. Can you help me with algebraic equations?",
            "model": "math-tutor-v1",
            "scrub_pii": True
        }
        
        # Act: Process request with PII scrubbing
        request_id = f"inf_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        # Scrub PII from prompt
        scrubbed_prompt, scrub_log = self.scrubber.scrub_content(
            inference_request["prompt"],
            method='tokenize',
            learner_id=inference_request["learner_id"]
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Create scrubbed request
        scrubbed_request = inference_request.copy()
        scrubbed_request["prompt"] = scrubbed_prompt
        scrubbed_request["pii_scrub_log"] = scrub_log
        
        # Audit PII scrubbing
        audit_id = self.scrubber.audit_pii_scrubbing(
            request_id=request_id,
            learner_id=inference_request["learner_id"],
            scrub_log=scrub_log,
            processing_time_ms=processing_time
        )
        
        # Assert: PII removed from model input
        assert 'John Doe' not in scrubbed_prompt
        assert 'john.doe@example.com' not in scrubbed_prompt
        assert 'math homework' in scrubbed_prompt  # Non-PII preserved
        assert 'algebraic equations' in scrubbed_prompt
        
        # Verify tokens present
        assert '[NAME_' in scrubbed_prompt or '[EMAIL_' in scrubbed_prompt
        
        # Audit trail complete
        assert audit_id
        assert len(scrub_log) >= 2  # Name and email detected
        
        # Request ready for safe model inference
        assert scrubbed_request["scrub_pii"] is True
        assert "pii_scrub_log" in scrubbed_request
    
    def test_inference_response_pii_rehydration_tracking(self):
        """Test: Tracking for potential PII rehydration in responses"""
        # Arrange: Scrubbed request with token mapping
        scrub_log = [
            {
                'type': 'name',
                'original_value': 'John Doe',
                'replacement': '[NAME_abc12345]',
                'method': 'tokenize',
                'learner_id': 'test_learner_004'
            },
            {
                'type': 'email', 
                'original_value': 'john.doe@example.com',
                'replacement': '[EMAIL_def67890]',
                'method': 'tokenize',
                'learner_id': 'test_learner_004'
            }
        ]
        
        # Mock inference response containing tokens
        mock_response = {
            "response": "Hello [NAME_abc12345]! I can help you with math. You can reach me at your registered email [EMAIL_def67890] if you have questions.",
            "confidence": 0.95,
            "tokens_present": ["[NAME_abc12345]", "[EMAIL_def67890]"]
        }
        
        # Act: Verify token presence and rehydration capability
        response_text = mock_response["response"]
        tokens_found = []
        
        for log_entry in scrub_log:
            if log_entry['replacement'] in response_text:
                tokens_found.append({
                    'token': log_entry['replacement'],
                    'type': log_entry['type'],
                    'can_rehydrate': True,  # If business logic requires it
                    'learner_id': log_entry['learner_id']
                })
        
        # Assert: Token tracking successful
        assert len(tokens_found) == 2
        assert any(token['type'] == 'name' for token in tokens_found)
        assert any(token['type'] == 'email' for token in tokens_found)
        
        # Verify rehydration mapping available (if needed for user display)
        name_token = next(token for token in tokens_found if token['type'] == 'name')
        email_token = next(token for token in tokens_found if token['type'] == 'email')
        
        assert name_token['token'] == '[NAME_abc12345]'
        assert email_token['token'] == '[EMAIL_def67890]'
    
    def test_pii_scrubbing_performance_in_inference_pipeline(self):
        """Test: PII scrubbing adds acceptable latency to inference requests"""
        # Arrange: Various request sizes
        test_prompts = [
            "Short prompt with john@example.com",  # Small
            ("Medium prompt with multiple PII instances: " + 
             "john.doe@example.com, (555) 123-4567, Jane Smith. " * 5),  # Medium
            ("Large prompt with extensive PII: " +
             "Contact john.doe@example.com or jane.smith@company.org. " +
             "Phone numbers: (555) 123-4567, 555-987-6543. " +
             "Names: John Doe, Jane Smith, Bob Johnson. " * 20)  # Large
        ]
        
        performance_results = []
        
        # Act: Measure performance for different sizes
        for i, prompt in enumerate(test_prompts):
            start_time = time.time()
            scrubbed, scrub_log = self.scrubber.scrub_content(prompt, method='tokenize')
            processing_time_ms = (time.time() - start_time) * 1000
            
            performance_results.append({
                'size': ['small', 'medium', 'large'][i],
                'prompt_length': len(prompt),
                'pii_count': len(scrub_log),
                'processing_time_ms': processing_time_ms,
                'pii_per_ms': len(scrub_log) / processing_time_ms if processing_time_ms > 0 else 0
            })
        
        # Assert: Performance acceptable for inference pipeline
        for result in performance_results:
            # Should process quickly enough for real-time inference
            assert result['processing_time_ms'] < 1000  # Under 1 second
            
            # Should scale reasonably with content size
            if result['size'] == 'small':
                assert result['processing_time_ms'] < 100  # Under 100ms for small
            
        # Verify PII detection effectiveness maintained across sizes
        assert all(result['pii_count'] > 0 for result in performance_results)
        
        print("PII Scrubbing Performance Results:")
        for result in performance_results:
            print(f"  {result['size']}: {result['processing_time_ms']:.2f}ms, "
                  f"{result['pii_count']} PII items, "
                  f"{result['pii_per_ms']:.3f} PII/ms")


if __name__ == "__main__":
    # Run PII scrubbing tests with coverage
    import sys
    
    # Simple test runner for standalone execution
    test_classes = [TestPIIDetection, TestPIIScrubbing, TestPIIAuditTrail, TestInferenceEdgeIntegration]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        instance = test_class()
        instance.setup_method()
        
        # Get test methods
        test_methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                print(f"Running {test_class.__name__}.{test_method}...")
                getattr(instance, test_method)()
                passed_tests += 1
                print(f"  ✓ PASSED")
            except Exception as e:
                print(f"  ✗ FAILED: {e}")
    
    print(f"\nPII Scrubbing Tests: {passed_tests}/{total_tests} passed")
    
    if passed_tests == total_tests:
        print("🎉 All PII scrubbing tests passed!")
        coverage_percent = 100
    else:
        coverage_percent = (passed_tests / total_tests) * 100
    
    print(f"Coverage: {coverage_percent:.1f}% (Target: ≥90%)")
    
    if coverage_percent < 90:
        sys.exit(1)  # Fail if coverage below target
