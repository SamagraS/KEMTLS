"""Benchmark: OIDC Flow Latency against the real KEMTLS OIDC apps."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kemtls.tcp_server import KEMTLSTCPServer
from client.kemtls_http_client import KEMTLSHttpClient
from client.oidc_client import OIDCClient
from oidc.auth_endpoints import InMemoryClientRegistry
from servers.auth_server_app import create_auth_server_app
from servers.resource_server_app import create_resource_server_app

from kemtls.pdk import PDKTrustStore
from utils.encoding import base64url_decode


BENCH_ISSUER_URL = 'kemtls://127.0.0.1:50001'


def start_real_servers() -> dict:
    base_dir = Path(__file__).parent.parent / 'keys'
    with open(base_dir / 'ca' / 'ca_keys.json', 'r', encoding='utf-8') as file_handle:
        ca_config = json.load(file_handle)
    with open(base_dir / 'auth_server' / 'as_config.json', 'r', encoding='utf-8') as file_handle:
        as_config = json.load(file_handle)
    with open(base_dir / 'resource_server' / 'rs_config.json', 'r', encoding='utf-8') as file_handle:
        rs_config = json.load(file_handle)
    with open(base_dir / 'pdk' / 'pdk_manifest.json', 'r', encoding='utf-8') as file_handle:
        pdk_manifest = json.load(file_handle)

    pdk_key_ids = {entry.get('identity'): entry.get('key_id') for entry in pdk_manifest}
    auth_app = create_auth_server_app(
        {
            'issuer': BENCH_ISSUER_URL,
            'issuer_public_key': base64url_decode(as_config['jwt_signing_pk']),
            'issuer_secret_key': base64url_decode(as_config['jwt_signing_sk']),
            'clients': {
                'bench-client': {
                    'redirect_uris': ['kemtls://127.0.0.1:50001/callback'],
                },
            },
            'demo_user': 'user-1',
            'introspection_endpoint': f'{BENCH_ISSUER_URL}/introspect',
        },
        stores={'client_registry': InMemoryClientRegistry({'bench-client': {'redirect_uris': ['kemtls://127.0.0.1:50001/callback']}})},
    )

    # Auth Server
    as_server = KEMTLSTCPServer(
        app=auth_app,
        server_identity='auth-server',
        server_lt_sk=base64url_decode(as_config['longterm_sk']),
        cert=as_config['certificate'],
        pdk_key_id=pdk_key_ids.get('auth-server'),
        port=50001
    )
    threading.Thread(target=as_server.start, daemon=True).start()

    # Resource Server
    rs_app = create_resource_server_app(
        {
            'issuer': BENCH_ISSUER_URL,
            'issuer_public_key': base64url_decode(as_config['jwt_signing_pk']),
            'resource_audience': None,
        }
    )
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
    auth_http_client = KEMTLSHttpClient(
        ca_pk=server_config['ca_pk'],
        pdk_store=server_config['pdk_store'],
        expected_identity="auth-server",
        mode=mode,
        keep_alive=True,
    )
    resource_http_client = KEMTLSHttpClient(
        ca_pk=server_config['ca_pk'],
        pdk_store=server_config['pdk_store'],
        expected_identity="resource-server",
        mode=mode,
        keep_alive=True,
    )
    
    oidc_client = OIDCClient(
        http_client=auth_http_client,
        client_id="bench-client",
        issuer_url=BENCH_ISSUER_URL,
        redirect_uri="kemtls://127.0.0.1:50001/callback"
    )

    times = {}

    # 1. /authorize
    t0 = time.perf_counter()
    auth_url = oidc_client.start_auth()
    resp = auth_http_client.get(auth_url)
    code = resp.get('body', {}).get('code')
    t1 = time.perf_counter()
    times['authorize_s'] = t1 - t0

    # 2. /token
    t0 = time.perf_counter()
    oidc_client.exchange_code(code)
    t1 = time.perf_counter()
    times['token_s'] = t1 - t0

    # 3. /resource using separate resource-server client
    t0 = time.perf_counter()
    resource_http_client.get(
        "kemtls://127.0.0.1:50002/userinfo",
        headers={'Authorization': f'Bearer {oidc_client.access_token}'},
    )
    t1 = time.perf_counter()
    times['resource_s'] = t1 - t0

    # 4. /refresh over the same auth channel used for /token
    t0 = time.perf_counter()
    oidc_client.refresh()
    t1 = time.perf_counter()
    times['refresh_s'] = t1 - t0

    times['total_login_s'] = times['authorize_s'] + times['token_s']

    auth_http_client.close()
    resource_http_client.close()

    return times


def run_benchmark(config: dict):
    print("Starting servers for OIDC Flow Benchmark...")
    server_config = start_real_servers()
    time.sleep(1)

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
