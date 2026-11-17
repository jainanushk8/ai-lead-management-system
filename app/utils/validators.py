"""
app/utils/validators.py
Input validation utilities for lead data.

HOW IT WORKS:
- validate_email() uses a regex pattern that covers standard email formats.
  It rejects obviously malformed addresses before they reach the database.
- validate_phone() strips common formatting characters (spaces, dashes,
  parentheses, dots, plus signs) and checks that the remaining digits are
  between 7 and 15 characters long (ITU-T E.164 range).
- sanitize_string() strips leading/trailing whitespace and collapses internal
  whitespace runs. This prevents storing "  John   Doe  " as a name.

INTERVIEW NOTES:
- These validators run BEFORE the database layer. Even though Pydantic
  validates types, these functions enforce business-level format rules.
- The email regex is intentionally kept practical rather than fully RFC 5322
  compliant. A production system would additionally verify via SMTP or a
  dedicated validation API.
"""

import re

# Email pattern: local-part @ domain with at least one dot in domain.
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# Characters that are acceptable formatting in phone numbers but not digits.
_PHONE_STRIP_CHARS = re.compile(r"[\s\-\(\)\.\+]")


def validate_email(email: str) -> bool:
    """
    Return True if the email string matches a standard email format.

    Examples:
        validate_email("john@example.com")  -> True
        validate_email("not-an-email")      -> False
        validate_email("")                  -> False
    """
    if not email or not isinstance(email, str):
        return False
    return bool(_EMAIL_PATTERN.match(email.strip()))


def validate_phone(phone: str) -> bool:
    """
    Return True if the phone string contains 7-15 digits after stripping
    common formatting characters.

    Examples:
        validate_phone("+1 (555) 123-4567")  -> True
        validate_phone("12345")              -> False (too short)
        validate_phone("not-a-phone")        -> False
    """
    if not phone or not isinstance(phone, str):
        return False
    digits_only = _PHONE_STRIP_CHARS.sub("", phone.strip())
    if not digits_only.isdigit():
        return False
    return 7 <= len(digits_only) <= 15


def sanitize_string(value: str) -> str:
    """
    Strip leading/trailing whitespace and collapse internal whitespace runs
    to a single space.

    Examples:
        sanitize_string("  John   Doe  ") -> "John Doe"
        sanitize_string("  ")             -> ""
    """
    if not value or not isinstance(value, str):
        return ""
    return " ".join(value.split())
