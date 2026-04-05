"""
Bootstrap KEMTLS OIDC Trust Artifacts

Generates:
1. CA signing keys (ML-DSA)
2. AS/RS long-term KEM keys (ML-KEM)
3. AS/RS certificates
4. AS JWT signing keys (ML-DSA)
5. PDK trust manifest
"""

import os
import json
import sys
from pathlib import Path

# Ensure src in path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from crypto.ml_dsa import MLDSA65
from crypto.ml_kem import MLKEM768
from kemtls.certs import create_certificate
from utils.encoding import base64url_encode
from utils.helpers import get_timestamp


def save_artifact(path: Path, data: dict):
    os.makedirs(path.parent, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    base_dir = Path(__file__).parent.parent / 'keys'
    now = get_timestamp()
    expiry = now + (365 * 24 * 3600)  # 1 year
    
    print("Bootstrapping CA...")
    ca_pk, ca_sk = MLDSA65.generate_keypair()
    save_artifact(base_dir / 'ca' / 'ca_keys.json', {
        'public_key': base64url_encode(ca_pk),
        'secret_key': base64url_encode(ca_sk)
    })
    
    print("Bootstrapping Authorization Server...")
    as_lt_pk, as_lt_sk = MLKEM768.generate_keypair()
    as_cert = create_certificate(
        subject="auth-server",
        kem_pk=as_lt_pk,
        ca_sk=ca_sk,
        issuer="Root CA",
        valid_from=now,
        valid_to=expiry
    )
    as_jwt_pk, as_jwt_sk = MLDSA65.generate_keypair()
    
    save_artifact(base_dir / 'auth_server' / 'as_config.json', {
        'identity': 'auth-server',
        'longterm_pk': base64url_encode(as_lt_pk),
        'longterm_sk': base64url_encode(as_lt_sk),
        'certificate': as_cert,
        'jwt_signing_pk': base64url_encode(as_jwt_pk),
        'jwt_signing_sk': base64url_encode(as_jwt_sk)
    })
    
    print("Bootstrapping Resource Server...")
    rs_lt_pk, rs_lt_sk = MLKEM768.generate_keypair()
    rs_cert = create_certificate(
        subject="resource-server",
        kem_pk=rs_lt_pk,
        ca_sk=ca_sk,
        issuer="Root CA",
        valid_from=now,
        valid_to=expiry
    )
    
    save_artifact(base_dir / 'resource_server' / 'rs_config.json', {
        'identity': 'resource-server',
        'longterm_pk': base64url_encode(rs_lt_pk),
        'longterm_sk': base64url_encode(rs_lt_sk),
        'certificate': rs_cert
    })
    
    print("Generating PDK manifest...")
    pdk_manifest = [
        {
            'key_id': 'as-key-1',
            'identity': 'auth-server',
            'ml_kem_public_key': base64url_encode(as_lt_pk)
        },
        {
            'key_id': 'rs-key-1',
            'identity': 'resource-server',
            'ml_kem_public_key': base64url_encode(rs_lt_pk)
        }
    ]
    save_artifact(base_dir / 'pdk' / 'pdk_manifest.json', pdk_manifest)
    
    print(f"Artifacts generated successfully in {base_dir}")


if __name__ == "__main__":
    main()
