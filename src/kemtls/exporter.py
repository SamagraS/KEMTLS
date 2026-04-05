"""
Exporter and Session Binding ID Derivation for KEMTLS.
"""

from typing import Optional
from crypto.key_schedule import hkdf_expand_label, HASH_LEN
from utils.encoding import base64url_encode


def derive_exporter_secret(app_secret: bytes, transcript_hash_3: bytes) -> bytes:
    """
    Derive the base exporter secret from the master secret.
    
    Args:
        app_secret: The master/application secret derived after handshake.
        transcript_hash_3: The SHA-256 hash of the complete handshake transcript.
        
    Returns:
        bytes: 32-byte exporter secret.
    """
    return hkdf_expand_label(app_secret, b"exporter", transcript_hash_3, HASH_LEN)


def derive_session_binding_id(
    exporter_secret: bytes,
    context_label: bytes = b"oidc-access-token",
    length: int = 32,
    as_base64: bool = True
) -> str | bytes:
    """
    Derive a deterministic binding ID for OIDC access tokens.
    """
    binding_bytes = hkdf_expand_label(exporter_secret, context_label, b"", length)
    return base64url_encode(binding_bytes) if as_base64 else binding_bytes


def derive_refresh_binding_id(
    exporter_secret: bytes,
    context_label: bytes = b"oidc-refresh-token",
    length: int = 32,
    as_base64: bool = True
) -> str | bytes:
    """
    Derive a deterministic binding ID for OIDC refresh tokens.
    """
    binding_bytes = hkdf_expand_label(exporter_secret, context_label, b"", length)
    return base64url_encode(binding_bytes) if as_base64 else binding_bytes
