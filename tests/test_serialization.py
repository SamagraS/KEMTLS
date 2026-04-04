"""
Tests for canonical message serialization (src/utils/serialization.py).
"""

import sys
import os
import pytest
import json

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.serialization import serialize_message, deserialize_message


def test_basic_serialization():
    """Test basic round-trip for standard JSON types."""
    msg = {'type': 'ServerHello', 'session_id': 'abc123', 'version': 1.2}
    serialized = serialize_message(msg)
    recovered = deserialize_message(serialized)
    assert recovered == msg


def test_deterministic_ordering():
    """Keys must always be sorted alphabetically for deterministic output."""
    msg1 = {'z': 1, 'a': 2, 'b': 3}
    msg2 = {'a': 2, 'b': 3, 'z': 1}
    assert serialize_message(msg1) == serialize_message(msg2)
    # Verify exact string content (no whitespace, sorted)
    assert serialize_message(msg1) == b'{"a":2,"b":3,"z":1}'


def test_binary_safe_handling():
    """Bytes must be automatically encoded to base64url."""
    msg = {
        'public_key': b'\x00\x01\x02\x03',
        'signature': b'signed_data'
    }
    serialized = serialize_message(msg)
    recovered = deserialize_message(serialized)
    
    # Expected base64url values from encoding.py
    assert recovered['public_key'] == 'AAECAw'
    assert recovered['signature'] == 'c2lnbmVkX2RhdGE'
    assert isinstance(recovered['public_key'], str)


def test_strict_compliance_nan_inf():
    """Serialization must fail for NaN, Infinity, and -Infinity."""
    msg_nan = {'val': float('nan')}
    with pytest.raises(ValueError, match="Out of range float values"):
        serialize_message(msg_nan)
        
    msg_inf = {'val': float('inf')}
    with pytest.raises(ValueError, match="Out of range float values"):
        serialize_message(msg_inf)


def test_no_whitespace():
    """Canonical JSON must not contain unnecessary whitespace."""
    msg = {'a': 1, 'b': 2}
    serialized = serialize_message(msg)
    # separators=(',', ':') ensures no spaces after colons or commas
    assert b' ' not in serialized


def test_unicode_handling():
    """UTF-8 should be handled correctly."""
    msg = {'greet': '你好'}
    serialized = serialize_message(msg)
    recovered = deserialize_message(serialized)
    assert recovered == msg


def test_invalid_input_types():
    """Check TypeError for invalid inputs."""
    with pytest.raises(TypeError, match="Message must be a dictionary"):
        serialize_message(["not", "a", "dict"])
        
    with pytest.raises(TypeError, match="Data must be bytes"):
        deserialize_message('{"a":1}')


def test_invalid_json_deserialization():
    """Check ValueError for malformed JSON."""
    with pytest.raises(ValueError, match="Invalid JSON data"):
        deserialize_message(b'{"a":1')


def test_complex_nesting():
    """Deeply nested structures with bytes."""
    msg = {
        'outer': {
            'inner': b'data',
            'list': [1, b'two', 3]
        }
    }
    serialized = serialize_message(msg)
    # b'data' -> 'ZGF0YQ'
    # b'two' -> 'dHdv'
    assert b'"inner":"ZGF0YQ"' in serialized
    assert b'"dHdv"' in serialized
