"""
Base64url Encoding/Decoding

This module provides Base64url encoding and decoding functions as specified
in RFC 4648. Base64url is used in JWTs and other web-safe contexts where
standard Base64's '+' and '/' characters would cause issues in URLs.

Base64url replaces:
    '+' → '-'
    '/' → '_'
    '=' padding is removed

Usage:
    >>> from utils.encoding import base64url_encode, base64url_decode
    >>> 
    >>> data = b"Hello, World!"
    >>> encoded = base64url_encode(data)
    >>> decoded = base64url_decode(encoded)
    >>> assert decoded == data

Tests:
    Run "pytest tests/test_encoding.py" to run the tests.
"""

import base64
import binascii
import re

__all__ = ["base64url_encode", "base64url_decode"]

# Matches only valid Base64url characters (RFC 4648 §5)
_BASE64URL_PATTERN = re.compile(r'^[A-Za-z0-9_-]*$')


def base64url_encode(data: bytes) -> str:
    """
    Encode bytes to Base64url string.
    
    Performs standard Base64 encoding, then:
    1. Replace '+' with '-'
    2. Replace '/' with '_'
    3. Remove '=' padding
    
    Args:
        data (bytes): Binary data to encode
    
    Returns:
        str: Base64url-encoded string
    
    Raises:
        TypeError: If data is not bytes
    
    Example:
        >>> base64url_encode(b"Hello")
        'SGVsbG8'
        >>> base64url_encode(b"\\x00\\x01\\x02")
        'AAEC'
    """
    if not isinstance(data, bytes):
        raise TypeError("Data must be bytes")
    
    # Standard Base64url encoding, strip padding
    encoded = base64.urlsafe_b64encode(data)
    return encoded.rstrip(b'=').decode('ascii')


def base64url_decode(encoded: str) -> bytes:
    """
    Decode Base64url string to bytes.
    
    Performs the reverse of base64url_encode:
    1. Validate input contains only Base64url characters
    2. Add padding if needed
    3. Decode using URL-safe Base64
    
    Args:
        encoded (str): Base64url-encoded string
    
    Returns:
        bytes: Decoded binary data
    
    Raises:
        TypeError: If encoded is not a string
        ValueError: If encoded string contains invalid characters or is malformed
    
    Example:
        >>> base64url_decode('SGVsbG8')
        b'Hello'
        >>> base64url_decode('AAEC')
        b'\\x00\\x01\\x02'
    """
    if not isinstance(encoded, str):
        raise TypeError("Encoded data must be a string")
    
    # Validate characters before attempting decode
    if not _BASE64URL_PATTERN.match(encoded):
        raise ValueError(
            "Invalid Base64url string: contains characters outside [A-Za-z0-9_-]"
        )
    
    # Convert to bytes and add padding
    encoded_bytes = encoded.encode('ascii')
    padding_needed = (4 - len(encoded_bytes) % 4) % 4
    encoded_bytes += b'=' * padding_needed
    
    # Decode
    try:
        return base64.urlsafe_b64decode(encoded_bytes)
    except binascii.Error as e:
        raise ValueError(f"Invalid Base64url encoding: {e}")