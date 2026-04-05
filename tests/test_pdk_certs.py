"""
Comprehensive tests for PDKTrustStore and KEMTLS certificates.
"""

import os
import sys
import pytest
import time

# Ensure src is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from kemtls.pdk import PDKTrustStore
from kemtls.certs import create_certificate, validate_certificate
from crypto.ml_kem import MLKEM768
from crypto.ml_dsa import MLDSA65
from utils.helpers import get_timestamp


def test_pdk_trust_store():
    """Test functionality and error handling of PDKTrustStore."""
    store = PDKTrustStore()
    
    # Setup some test keys
    # Use real key generation for validity
    alice_pk, _ = MLKEM768.generate_keypair()
    bob_pk, _ = MLKEM768.generate_keypair()
    
    # 1. Success: Add and retrieve by ID
    store.add_entry("alice-key-1", "Alice", alice_pk)
    entry = store.get_entry_by_id("alice-key-1")
    assert entry['identity'] == "Alice"
    assert entry['ml_kem_public_key'] == alice_pk
    
    # 2. Success: Retrieve by Identity
    entry = store.get_entry_by_identity("Alice")
    assert entry['key_id'] == "alice-key-1"
    
    # 3. Success: Resolve expected identity (with ID)
    entry = store.resolve_expected_identity("Alice", "alice-key-1")
    assert entry['ml_kem_public_key'] == alice_pk
    
    # 4. Success: Resolve expected identity (without ID)
    entry = store.resolve_expected_identity("Alice")
    assert entry['ml_kem_public_key'] == alice_pk
    
    # 5. Failure: Unknown Key ID
    with pytest.raises(KeyError, match="not found"):
        store.get_entry_by_id("unknown-id")
    
    # 6. Failure: Identity mismatch
    with pytest.raises(ValueError, match="Identity mismatch"):
        store.resolve_expected_identity("Bob", "alice-key-1")
        
    # 7. Failure: Ambiguous identity
    # Add a second key for Alice
    alice_pk_2, _ = MLKEM768.generate_keypair()
    store.add_entry("alice-key-2", "Alice", alice_pk_2)
    with pytest.raises(ValueError, match="Ambiguous identity"):
        store.get_entry_by_identity("Alice")
    
    # 8. Failure: No keys for identity
    with pytest.raises(ValueError, match="No trusted keys found"):
        store.get_entry_by_identity("Eve")


def test_certificate_lifecycle():
    """Test full certificate lifecycle: creation and validation."""
    # Setup test keys
    # Subject: Alice
    alice_kem_pk, _ = MLKEM768.generate_keypair()
    
    # CA: Root CA
    ca_pk, ca_sk = MLDSA65.generate_keypair()
    
    current_time = get_timestamp()
    valid_from = current_time - 10  # 10s ago
    valid_to = current_time + 3600  # 1h from now
    
    # 1. Create Certificate
    cert = create_certificate(
        subject="Alice",
        kem_pk=alice_kem_pk,
        ca_sk=ca_sk,
        issuer="Root CA",
        valid_from=valid_from,
        valid_to=valid_to
    )
    
    assert cert['subject'] == "Alice"
    assert cert['issuer'] == "Root CA"
    assert 'signature' in cert
    
    # 2. Success: Validate Certificate
    pk = validate_certificate(cert, ca_pk, "Alice")
    assert pk == alice_kem_pk


def test_certificate_failures():
    """Test various failure conditions for certificate validation."""
    alice_kem_pk, _ = MLKEM768.generate_keypair()
    ca_pk, ca_sk = MLDSA65.generate_keypair()
    
    current_time = get_timestamp()
    
    # 1. Failure: Signature Mismatch (Wrong CA)
    wrong_pk, _ = MLDSA65.generate_keypair()
    cert = create_certificate("Alice", alice_kem_pk, ca_sk, "Root CA", current_time - 1, current_time + 10)
    with pytest.raises(ValueError, match="signature verification failed"):
        validate_certificate(cert, wrong_pk, "Alice")
        
    # 2. Failure: Expired Certificate
    expired_cert = create_certificate("Alice", alice_kem_pk, ca_sk, "Root CA", current_time - 100, current_time - 1)
    with pytest.raises(ValueError, match="Certificate has expired"):
        validate_certificate(expired_cert, ca_pk, "Alice")
        
    # 3. Failure: Not yet valid
    future_cert = create_certificate("Alice", alice_kem_pk, ca_sk, "Root CA", current_time + 100, current_time + 200)
    with pytest.raises(ValueError, match="Certificate is not yet valid"):
        validate_certificate(future_cert, ca_pk, "Alice")
        
    # 4. Failure: Identity Mismatch
    with pytest.raises(ValueError, match="Identity mismatch"):
        validate_certificate(cert, ca_pk, "Bob")
        
    # 5. Failure: Signature Mismatch (Tampering)
    tampered_cert = cert.copy()
    tampered_cert['subject'] = "Bob"  # Tamper with the identity field
    with pytest.raises(ValueError, match="signature verification failed"):
        validate_certificate(tampered_cert, ca_pk, "Bob")


if __name__ == "__main__":
    pytest.main([__file__])
