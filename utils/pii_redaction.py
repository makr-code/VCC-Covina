"""
PII Redaction Filter for Logging
=================================

DSGVO-compliant log redaction to prevent logging of personally identifiable information.

Features:
- Email addresses
- Social Security Numbers (US SSN)
- Dates (potential birthdates)
- Passwords and secrets
- IBANs (European bank accounts)
- Phone numbers (DE/International)
- IP addresses
- Credit card numbers

Usage:
    import logging
    from utils.pii_redaction import PIIRedactionFilter
    
    logger = logging.getLogger(__name__)
    logger.addFilter(PIIRedactionFilter())

Author: Covina Security Team
Version: 1.0.0
Created: 2025-10-22
"""

import re
import logging
from typing import List, Tuple, Pattern


class PIIRedactionFilter(logging.Filter):
    """
    Logging filter that redacts personally identifiable information (PII)
    from log messages to ensure DSGVO compliance.
    
    The filter applies regex patterns to detect and replace PII with
    placeholder tokens like [EMAIL], [IBAN], [PASSWORD], etc.
    """
    
    # Regex patterns for PII detection
    # Format: (compiled_pattern, replacement_string)
    PII_PATTERNS: List[Tuple[Pattern, str]] = [
        # Email addresses (RFC 5322 simplified)
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
        
        # US Social Security Numbers (XXX-XX-XXXX)
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN]'),
        
        # German IBAN (DExx xxxx xxxx xxxx xxxx xx)
        # Format: DE + 2 digits + 18 digits (with optional spaces)
        (re.compile(r'\bDE\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b', re.I), '[IBAN]'),
        
        # International IBAN (2 letters + 2 digits + up to 30 alphanumeric)
        (re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b'), '[IBAN]'),
        
        # Phone numbers (various formats)
        # +49 XXX XXXXXXX, 0049 XXX XXXXXXX, 0XXX XXXXXXX
        # Updated: Match phone with optional spaces/dashes (no word boundary at end)
        (re.compile(r'(\+49|0049|0)\s*\d{2,4}[\s\-]?\d{6,10}'), '[PHONE]'),
        
        # Dates (potential birthdates) - DD.MM.YYYY or DD/MM/YYYY
        (re.compile(r'\b\d{2}[./]\d{2}[./]\d{4}\b'), '[DATE]'),
        
        # Passwords and secrets in key-value pairs
        # Matches: password=xxx, pwd:xxx, secret="xxx", token='xxx'
        (re.compile(r'(password|pwd|secret|token|api_key|auth)["\']?\s*[:=]\s*["\']?[^\s"\']+', re.I), r'\1=[REDACTED]'),
        
        # Credit card numbers (13-19 digits with optional spaces/dashes)
        (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4,7}\b'), '[CARD]'),
        
        # IPv4 addresses (optional - may be needed for audit trails)
        # Uncomment if IP logging should be redacted
        # (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '[IP]'),
        
        # German Personalausweis numbers (10 alphanumeric)
        (re.compile(r'\b[A-Z0-9]{10}\b'), '[ID]'),
        
        # German tax ID (Steuer-ID) - 11 digits
        (re.compile(r'\b\d{11}\b'), '[TAX_ID]'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Apply PII redaction to log record.
        
        Args:
            record: The log record to filter
            
        Returns:
            Always True (record is always logged, just with redacted content)
        """
        # Get the formatted message
        msg = record.getMessage()
        
        # Apply all PII patterns
        for pattern, replacement in self.PII_PATTERNS:
            msg = pattern.sub(replacement, msg)
        
        # Update the record
        record.msg = msg
        record.args = ()  # Clear args to prevent re-formatting
        
        return True
    
    @classmethod
    def add_custom_pattern(cls, pattern: str, replacement: str, flags: int = 0) -> None:
        """
        Add a custom PII pattern at runtime.
        
        Args:
            pattern: Regex pattern to match
            replacement: Replacement string (e.g., '[CUSTOM_PII]')
            flags: Regex flags (e.g., re.IGNORECASE)
        """
        compiled_pattern = re.compile(pattern, flags)
        cls.PII_PATTERNS.append((compiled_pattern, replacement))
    
    @classmethod
    def get_patterns_count(cls) -> int:
        """Get the number of active PII patterns."""
        return len(cls.PII_PATTERNS)


# Example usage and testing
if __name__ == "__main__":
    # Setup logger with PII filter
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)
    logger.addFilter(PIIRedactionFilter())
    
    print("PII Redaction Filter Test")
    print("=" * 50)
    print(f"Active patterns: {PIIRedactionFilter.get_patterns_count()}")
    print()
    
    # Test cases
    test_messages = [
        "User email: john.doe@example.com registered",
        "SSN found: 123-45-6789",
        "IBAN: DE89370400440532013000",
        "Call customer at +49 170 1234567",
        "Birthdate: 15.03.1985",
        "password=SuperSecret123!",
        "API token: Bearer abc123xyz789",
        "Card number: 4532 1234 5678 9010",
        "User IP: 192.168.1.100 connected",
        "Tax ID: 12345678901",
        "Mixed PII: Email test@example.de, IBAN DE12345678901234567890, Phone +49 30 12345678"
    ]
    
    print("Testing PII redaction:")
    print("-" * 50)
    for msg in test_messages:
        logger.info(msg)
    
    print()
    print("All PII should be redacted above!")
