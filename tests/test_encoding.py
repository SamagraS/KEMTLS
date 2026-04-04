"""
Tests for Base64url encoding/decoding (src/utils/encoding.py).

Covers round-trip correctness, URL-safety guarantees, edge cases,
input validation, and error handling.
"""

import sys
import os
import pytest

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.encoding import base64url_encode, base64url_decode


# ── Round-trip tests ──────────────────────────────────────────────────

class TestRoundTrip:
    """Encode then decode should return the original bytes."""

    @pytest.mark.parametrize("data", [
        b"Hello, World!",
        b"",
        b"\x00\x01\x02\x03\x04",
        b"A" * 100,
        b"The quick brown fox jumps over the lazy dog",
        b"\xff" * 32,          # all-high bytes (common in key material)
        bytes(range(256)),     # every possible byte value
    ])
    def test_round_trip(self, data):
        encoded = base64url_encode(data)
        decoded = base64url_decode(encoded)
        assert decoded == data

    def test_single_byte_values(self):
        """Every single-byte value round-trips correctly."""
        for i in range(256):
            data = bytes([i])
            assert base64url_decode(base64url_encode(data)) == data


# ── URL-safety tests ─────────────────────────────────────────────────

class TestURLSafety:
    """Encoded output must not contain +, /, or = characters."""

    @pytest.mark.parametrize("data", [
        b"\xfb\xff\xfe",      # would produce '+' and '/' in standard Base64
        b"\x00\x01\x02",
        b"A" * 100,
        b"",
    ])
    def test_no_unsafe_characters(self, data):
        encoded = base64url_encode(data)
        assert '+' not in encoded, f"Found '+' in encoded output: {encoded}"
        assert '/' not in encoded, f"Found '/' in encoded output: {encoded}"
        assert '=' not in encoded, f"Found '=' in encoded output: {encoded}"


# ── Input validation tests ───────────────────────────────────────────

class TestInputValidation:
    """Functions must reject invalid input types and malformed strings."""

    def test_encode_rejects_str(self):
        with pytest.raises(TypeError, match="Data must be bytes"):
            base64url_encode("not bytes")

    def test_encode_rejects_int(self):
        with pytest.raises(TypeError, match="Data must be bytes"):
            base64url_encode(42)

    def test_encode_rejects_none(self):
        with pytest.raises(TypeError, match="Data must be bytes"):
            base64url_encode(None)

    def test_decode_rejects_bytes(self):
        with pytest.raises(TypeError, match="Encoded data must be a string"):
            base64url_decode(b"SGVsbG8")

    def test_decode_rejects_int(self):
        with pytest.raises(TypeError, match="Encoded data must be a string"):
            base64url_decode(42)

    def test_decode_rejects_none(self):
        with pytest.raises(TypeError, match="Encoded data must be a string"):
            base64url_decode(None)

    def test_decode_rejects_standard_base64_chars(self):
        """'+' and '/' are valid in standard Base64 but invalid in Base64url."""
        with pytest.raises(ValueError, match="Invalid Base64url string"):
            base64url_decode("SGVs+G8=")

    def test_decode_rejects_padding(self):
        """Padding '=' should be rejected in input."""
        with pytest.raises(ValueError, match="Invalid Base64url string"):
            base64url_decode("SGVsbG8=")

    def test_decode_rejects_spaces(self):
        with pytest.raises(ValueError, match="Invalid Base64url string"):
            base64url_decode("SGVs bG8")

    def test_decode_rejects_special_chars(self):
        with pytest.raises(ValueError, match="Invalid Base64url string"):
            base64url_decode("SGVs!bG8")


# ── Edge cases ────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases for encoding/decoding."""

    def test_empty_bytes_encode(self):
        assert base64url_encode(b"") == ""

    def test_empty_string_decode(self):
        assert base64url_decode("") == b""

    def test_known_vectors(self):
        """RFC 4648 test vectors adapted for url-safe variant."""
        assert base64url_encode(b"f") == "Zg"
        assert base64url_encode(b"fo") == "Zm8"
        assert base64url_encode(b"foo") == "Zm9v"
        assert base64url_encode(b"foob") == "Zm9vYg"
        assert base64url_encode(b"fooba") == "Zm9vYmE"
        assert base64url_encode(b"foobar") == "Zm9vYmFy"

    def test_decode_known_vectors(self):
        assert base64url_decode("Zg") == b"f"
        assert base64url_decode("Zm8") == b"fo"
        assert base64url_decode("Zm9v") == b"foo"
        assert base64url_decode("Zm9vYg") == b"foob"
        assert base64url_decode("Zm9vYmE") == b"fooba"
        assert base64url_decode("Zm9vYmFy") == b"foobar"
