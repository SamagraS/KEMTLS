"""
Benchmark: OIDC Flow Latency

Measures:
- /authorize latency
- /token latency
- Resource access latency
- Refresh latency
- Total login time
"""

import os
import sys
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kemtls.tcp_server import KEMTLSTCPServer
from client.kemtls_http_client import KEMTLSHttpClient
from client.oidc_client import OIDCClient

# We dynamically import the apps defined in the scripts
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
try:
    from run_kemtls_auth_server import create_auth_app
    from run_kemtls_resource_server import create_rs_app
except ImportError:
    pass

from utils.encoding import base64url_decode
from kemtls.pdk import PDKTrustStore


def start_mock_servers() -> dict:
    base_dir = Path(__file__).parent.parent / 'keys'
    with open(base_dir / 'ca' / 'ca_keys.json') as f: ca_config = json.load(f)
    with open(base_dir / 'auth_server' / 'as_config.json') as f: as_config = json.load(f)
    with open(base_dir / 'resource_server' / 'rs_config.json') as f: rs_config = json.load(f)
    with open(base_dir / 'pdk' / 'pdk_manifest.json') as f: pdk_manifest = json.load(f)

    pdk_key_ids = {entry.get('identity'): entry.get('key_id') for entry in pdk_manifest}

    # Auth Server
    as_app = create_auth_app(as_config)
    as_server = KEMTLSTCPServer(
        app=as_app,
        server_identity='auth-server',
        server_lt_sk=base64url_decode(as_config['longterm_sk']),
        cert=as_config['certificate'],
        pdk_key_id=pdk_key_ids.get('auth-server'),
        port=50001
    )
    threading.Thread(target=as_server.start, daemon=True).start()

    # Resource Server
    rs_app = create_rs_app(base64url_decode(as_config['jwt_signing_pk']))
    rs_server = KEMTLSTCPServer(
        app=rs_app,
        server_identity='resource-server',
        server_lt_sk=base64url_decode(rs_config['longterm_sk']),
        cert=rs_config['certificate'],
        pdk_key_id=pdk_key_ids.get('resource-server'),
        port=50002
    )
    threading.Thread(target=rs_server.start, daemon=True).start()

    # PDK setup
    pdk_store = PDKTrustStore()
    for entry in pdk_manifest:
        pdk_store.add_entry(entry['key_id'], entry['identity'], base64url_decode(entry['ml_kem_public_key']))

    return {
        'ca_pk': base64url_decode(ca_config['public_key']),
        'pdk_store': pdk_store
    }


def bench_flow(mode: str, config: dict, server_config: dict) -> Dict[str, Any]:
    http_client = KEMTLSHttpClient(
        ca_pk=server_config['ca_pk'],
        pdk_store=server_config['pdk_store'],
        expected_identity="auth-server",
        mode=mode
    )
    
    oidc_client = OIDCClient(
        http_client=http_client,
        client_id="bench-client",
        issuer_url="kemtls://127.0.0.1:50001",
        redirect_uri="kemtls://127.0.0.1/callback"
    )

    times = {}

    # 1. /authorize (mock local for client generation, plus simple GET)
    t0 = time.perf_counter()
    auth_url = oidc_client.start_auth()
    resp = http_client.get(auth_url.replace('/authorize', '/authorize'))
    code = resp.get('body', {}).get('code')
    t1 = time.perf_counter()
    times['authorize_s'] = t1 - t0

    # 2. /token
    t0 = time.perf_counter()
    oidc_client.exchange_code(code)
    t1 = time.perf_counter()
    times['token_s'] = t1 - t0

    # 3. /resource (switch identity)
    http_client.expected_identity = "resource-server"
    t0 = time.perf_counter()
    oidc_client.call_api("kemtls://127.0.0.1:50002/resource")
    t1 = time.perf_counter()
    times['resource_s'] = t1 - t0

    # 4. /refresh (switch back identity)
    http_client.expected_identity = "auth-server"
    t0 = time.perf_counter()
    oidc_client.refresh()
    t1 = time.perf_counter()
    times['refresh_s'] = t1 - t0

    times['total_login_s'] = times['authorize_s'] + times['token_s']

    return times


def run_benchmark(config: dict):
    print("Starting Servers for OIDC Flow Benchmark...")
    server_config = start_mock_servers()
    time.sleep(1) # Let servers boot

    runs = config.get('runs', 100)
    results = {'kemtls': [], 'kemtls_pdk': []}

    print(f"Running Flow Benchmarks ({runs} iterations)...")
    for i in range(runs):
        if i % 10 == 0: print(f"Progress: {i}/{runs}")
        results['kemtls'].append(bench_flow('baseline', config, server_config))
        results['kemtls_pdk'].append(bench_flow('pdk', config, server_config))

    os.makedirs('results', exist_ok=True)
    with open('results/raw_oidc_flow.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Saved raw_oidc_flow.json")

    # Give servers time to cleanly shutdown threads (or just exit)


if __name__ == "__main__":
    with open('config.json') as f:
        config = json.load(f)
    run_benchmark(config)
