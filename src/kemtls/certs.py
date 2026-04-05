"""
KEMTLS Certificate Handling

Functions for creating and validating post-quantum certificates signed with ML-DSA-65.
"""

import json
from typing import Dict, Any, Optional, Tuple
from crypto.ml_dsa import MLDSA65
from utils.serialization import serialize_message, deserialize_message
from utils.encoding import base64url_encode, base64url_decode
from utils.helpers import get_timestamp


def create_certificate(
    subject: str,
    kem_pk: bytes,
    ca_sk: bytes,
    issuer: str,
    valid_from: int,
    valid_to: int
) -> Dict[str, Any]:
    """
    Create a signed post-quantum certificate.
    
    Args:
        subject: The certificate's subject identity
        kem_pk: The ML-KEM public key for the subject
        ca_sk: The certificate authority's secret key (ML-DSA-65)
        issuer: The name of the certificate authority
        valid_from: Unix timestamp for certificate start
        valid_to: Unix timestamp for certificate expiration
        
    Returns:
        Dict: Signed certificate dictionary
    """
    # 1. Build the certificate body
    cert = {
        'subject': subject,
        'kem_public_key': base64url_encode(kem_pk),
        'issuer': issuer,
        'valid_from': valid_from,
        'valid_to': valid_to,
        'key_usage': 'kemtls'
    }
    
    # 2. Serialize the body (deterministic JSON)
    serialized_body = serialize_message(cert)
    
    # 3. Sign the body using the CA's secret key
    signature = MLDSA65.sign(ca_sk, serialized_body)
    
    # 4. Attach base64-encoded signature to the dictionary
    cert['signature'] = base64url_encode(signature)
    
    return cert


def validate_certificate(
    cert: Dict[str, Any],
    ca_pk: bytes,
    expected_identity: str
) -> bytes:
    """
    Validate a post-quantum certificate and return the embedded public key.
    
    Args:
        cert: Certificate dictionary to validate
        ca_pk: The certificate authority's public key (ML-DSA-65)
        expected_identity: The expected subject identity
        
    Returns:
        bytes: The decoded ML-KEM public key
        
    Raises:
        ValueError: If validation fails (signature, time, identity, or usage)
    """
    # 1. Extract and remove the signature for verification
    if 'signature' not in cert:
        raise ValueError("Certificate is missing signature field")
        
    signature_b64 = cert['signature']
    signature = base64url_decode(signature_b64)
    
    # 2. Re-create the body (remaining fields)
    body = {k: v for k, v in cert.items() if k != 'signature'}
    
    # 3. Serialize and verify the signature
    serialized_body = serialize_message(body)
    if not MLDSA65.verify(ca_pk, serialized_body, signature):
        raise ValueError("Certificate signature verification failed")
    
    # 4. Check the time window
    current_time = get_timestamp()
    if current_time < cert['valid_from']:
        raise ValueError("Certificate is not yet valid")
    if current_time > cert['valid_to']:
        raise ValueError("Certificate has expired")
    
    # 5. Check key usage
    if cert.get('key_usage') != 'kemtls':
        raise ValueError(f"Invalid key usage: expected 'kemtls', got '{cert.get('key_usage')}'")
    
    # 6. Check identity match
    if cert.get('subject') != expected_identity:
        raise ValueError(
            f"Identity mismatch: certificate is for '{cert['subject']}', but expected '{expected_identity}'"
        )
        
    # 7. Decode and return the embedded ML-KEM public key
    return base64url_decode(cert['kem_public_key'])
