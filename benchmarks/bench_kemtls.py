"""
Benchmark: KEMTLS Handshake Latency and Validation Overheads

Measures:
- Handshake Latency (Full)
- Bytes Transferred
- ServerHello size
- Certificate validation time
- PDK trust lookup time
"""

import os
import sys
import json
import time
import socket
import threading
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kemtls.handshake import ClientHandshake, ServerHandshake
from kemtls.pdk import PDKTrustStore
from kemtls.certs import validate_certificate
from utils.encoding import base64url_decode
from crypto.ml_kem import MLKEM768
from crypto.ml_dsa import MLDSA65


def load_keys():
    base_dir = Path(__file__).parent.parent / 'keys'
    with open(base_dir / 'ca' / 'ca_keys.json') as f: ca_config = json.load(f)
    with open(base_dir / 'auth_server' / 'as_config.json') as f: as_config = json.load(f)
    with open(base_dir / 'pdk' / 'pdk_manifest.json') as f: pdk_manifest = json.load(f)

    pdk_store = PDKTrustStore()
    for entry in pdk_manifest:
        pdk_store.add_entry(entry['key_id'], entry['identity'], base64url_decode(entry['ml_kem_public_key']))

    return {
        'ca_pk': base64url_decode(ca_config['public_key']),
        'server_sk': base64url_decode(as_config['longterm_sk']),
        'server_cert': as_config['certificate'],
        'pdk_store': pdk_store
    }


def simulate_pqtls_handshake_time() -> float:
    """
    Since exact PQ-TLS 1.3 is not fully implemented in the repo, 
    we approximate the extra overhead based on literature (CCS2020).
    PQ-TLS requires ML-DSA signature generation on the server and 
    verification on the client, whereas KEMTLS replaces this with KEM encapsulation.
    """
    start = time.perf_counter()
    # Server signing (TLS 1.3 CertificateVerify)
    dummy_data = b"x" * 1024
    ca_pk, ca_sk = MLDSA65.generate_keypair()
    sig = MLDSA65.sign(ca_sk, dummy_data)
    # Client verifying
    MLDSA65.verify(ca_pk, dummy_data, sig)
    # Plus ML-KEM exchange
    pk, sk = MLKEM768.generate_keypair()
    ct, ss1 = MLKEM768.encapsulate(pk)
    MLKEM768.decapsulate(sk, ct)
    # Base latency approximate model (ignores full transcript hashing for brevity in simulation)
    return time.perf_counter() - start


def bench_handshake_local(mode: str, keys: dict) -> Dict[str, Any]:
    """Execute a local, back-to-back handshake without sockets to isolate crypto time."""
    client = ClientHandshake(
        expected_identity="auth-server",
        ca_pk=keys['ca_pk'],
        pdk_store=keys['pdk_store'],
        mode=mode
    )
    server = ServerHandshake(
        server_identity="auth-server",
        server_lt_sk=keys['server_sk'],
        cert=keys['server_cert'],
        pdk_key_id="as-key-1"
    )

    t_start = time.perf_counter()
    
    ch = client.client_hello()
    sh = server.process_client_hello(ch)
    
    cke, session_c = client.process_server_hello(sh)
    sf = server.process_client_key_exchange(cke)
    
    session_s = client.process_server_finished(sf, session_c)
    cf = client.client_finished()
    server.verify_client_finished(cf)
    
    duration = time.perf_counter() - t_start

    # Collect size metrics
    sh_size = len(sh)
    total_bytes = len(ch) + len(sh) + len(cke) + len(sf) + len(cf)

    return {
        'latency_s': duration,
        'sh_size_bytes': sh_size,
        'total_bytes': total_bytes
    }


def run_benchmark(config: dict):
    print("Running Handshake Benchmark...")
    keys = load_keys()
    
    runs = config.get('runs', 100)
    results = {'kemtls': [], 'kemtls_pdk': [], 'pqtls_simulated': []}
    
    # 1. Component Overheads
    # Cert Validation
    t0 = time.perf_counter()
    validate_certificate(keys['server_cert'], keys['ca_pk'], "auth-server")
    t1 = time.perf_counter()
    cert_val_time = t1 - t0
    
    # PDK Lookup
    t0 = time.perf_counter()
    keys['pdk_store'].resolve_expected_identity("auth-server", "as-key-1")
    t1 = time.perf_counter()
    pdk_val_time = t1 - t0

    # 2. Protocol Runs
    for _ in range(runs):
        results['kemtls'].append(bench_handshake_local('baseline', keys))
        results['kemtls_pdk'].append(bench_handshake_local('pdk', keys))
        
        # Simulate PQ-TLS
        pqtls_time = simulate_pqtls_handshake_time()
        # PQ-TLS sizes: Standard PQ-TLS 1.3 transmits Certificates & Signatures in handshake
        # Approx sizes based on ML-DSA-65 (~3300 bytes cert + ~3300 bytes sig)
        pqtls_total_bytes = 12000
        results['pqtls_simulated'].append({
            'latency_s': pqtls_time,
            'sh_size_bytes': 3400, # Approx size of ServerHello + Certificate + CertificateVerify
            'total_bytes': pqtls_total_bytes
        })

    # Save raw results
    output = {
        'component_times_s': {
            'cert_validation': cert_val_time,
            'pdk_lookup': pdk_val_time
        },
        'runs': results
    }
    
    os.makedirs('results', exist_ok=True)
    with open('results/raw_kemtls.json', 'w') as f:
        json.dump(output, f, indent=2)
    print("Saved raw_kemtls.json")


if __name__ == "__main__":
    with open('config.json') as f:
        config = json.load(f)
    run_benchmark(config)
