"""
Benchmark: Token Cryptography Timings

Measures:
- Token signing time (ML-DSA)
- JWT verification time
- JWKS verification simulation
- Resource Server validation overhead
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from crypto.ml_dsa import MLDSA65
from utils.encoding import base64url_encode, base64url_decode
from utils.helpers import get_timestamp


def run_benchmark(config: dict):
    print("Running Token Crypto Benchmark...")
    runs = config.get('runs', 100)
    
    results = {
        'id_token_signing_s': [],
        'jwt_verification_s': [],
        'jwks_generation_s': [],
    }
    
    pk, sk = MLDSA65.generate_keypair()
    
    now = get_timestamp()
    payload = {
        'iss': 'auth-server',
        'sub': 'user-1',
        'exp': now + 3600,
        'session_binding_id': 'mocked_binding_id_testing_timing'
    }
    payload_str = json.dumps(payload).encode('utf-8')
    
    for _ in range(runs):
        # Signing (ID Token / Access Token)
        t0 = time.perf_counter()
        sig = MLDSA65.sign(sk, payload_str)
        t1 = time.perf_counter()
        results['id_token_signing_s'].append(t1 - t0)
        
        # Verify
        t0 = time.perf_counter()
        MLDSA65.verify(pk, payload_str, sig)
        t1 = time.perf_counter()
        results['jwt_verification_s'].append(t1 - t0)
        
        # JWKS (mocking key encoding/export)
        t0 = time.perf_counter()
        jwks = {
            "keys": [
                {
                    "kty": "LWE",
                    "alg": "DILITHIUM3",
                    "x": base64url_encode(pk)
                }
            ]
        }
        json.dumps(jwks)
        t1 = time.perf_counter()
        results['jwks_generation_s'].append(t1 - t0)

    os.makedirs('results', exist_ok=True)
    with open('results/raw_token_crypto.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Saved raw_token_crypto.json")


if __name__ == "__main__":
    with open('config.json') as f:
        config = json.load(f)
    run_benchmark(config)
