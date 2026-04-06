"""
Benchmark: Token and Payload Sizes

Measures:
- ID token size (bytes)
- Access token size (bytes)
- Size growth from binding claim
- JWKS size
- OIDC metadata size
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from crypto.ml_dsa import MLDSA65
from utils.encoding import base64url_encode
from utils.helpers import get_timestamp


def run_benchmark(config: dict):
    print("Computing Token Sizes...")
    
    # 1. Setup simulated keys and context
    pk, sk = MLDSA65.generate_keypair()
    now = get_timestamp()
    
    # Standard Claims
    base_claims = {
        'iss': 'kemtls://auth-server',
        'sub': 'user-identifier-12345',
        'aud': 'client-app-xyz',
        'iat': now,
        'exp': now + 3600
    }
    
    # Claim with session binding
    binding_claims = base_claims.copy()
    binding_id = "vV8q3xOpQxR9N_LhA_GzPZ-KwT3y5eRz-pQm_" # typical length
    binding_claims['session_binding_id'] = binding_id
    
    # 2. Token Generation
    base_payload = json.dumps(base_claims).encode('utf-8')
    base_sig = MLDSA65.sign(sk, base_payload)
    base_token = f"{base64url_encode(base_payload)}.{base64url_encode(base_sig)}"
    
    binding_payload = json.dumps(binding_claims).encode('utf-8')
    binding_sig = MLDSA65.sign(sk, binding_payload)
    binding_token = f"{base64url_encode(binding_payload)}.{base64url_encode(binding_sig)}"
    
    # 3. JWKS and metadata
    jwks = {
        "keys": [
            {
                "kty": "LWE",
                "alg": "DILITHIUM3",
                "use": "sig",
                "x": base64url_encode(pk)
            }
        ]
    }
    jwks_size = len(json.dumps(jwks).encode('utf-8'))
    
    metadata = {
        "issuer": "kemtls://auth-server",
        "authorization_endpoint": "kemtls://auth-server/authorize",
        "token_endpoint": "kemtls://auth-server/token",
        "jwks_uri": "kemtls://auth-server/jwks",
        "scopes_supported": ["openid", "profile", "email"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic"]
    }
    metadata_size = len(json.dumps(metadata).encode('utf-8'))

    results = {
        'id_token_base_bytes': len(base_token),
        'access_token_bound_bytes': len(binding_token),
        'binding_overhead_bytes': len(binding_token) - len(base_token),
        'jwks_size_bytes': jwks_size,
        'oidc_metadata_size_bytes': metadata_size
    }

    os.makedirs('results', exist_ok=True)
    with open('results/raw_sizes.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Saved raw_sizes.json")


if __name__ == "__main__":
    with open('config.json') as f:
        config = json.load(f)
    run_benchmark(config)
