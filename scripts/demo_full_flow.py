"""
End-to-End KEMTLS OIDC Demonstration

Flow:
1. Initialize OIDCClient (baseline/pdk/auto)
2. Login (start_auth -> exchange_code)
3. Access Resource (expect success)
4. Replay Attack (new session, old token -> expect failure)
5. Refresh Flow
6. Performance Comparison (Baseline vs PDK)
"""

import os
import json
import sys
import time
from pathlib import Path

# Ensure src in path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client.kemtls_http_client import KEMTLSHttpClient
from client.oidc_client import OIDCClient
from kemtls.pdk import PDKTrustStore
from utils.encoding import base64url_decode


def load_config():
    base_dir = Path(__file__).parent.parent / 'keys'
    ca_path = base_dir / 'ca' / 'ca_keys.json'
    as_path = base_dir / 'auth_server' / 'as_config.json'
    rs_path = base_dir / 'resource_server' / 'rs_config.json'
    pdk_path = base_dir / 'pdk' / 'pdk_manifest.json'
    
    if not all(os.path.exists(p) for p in [ca_path, as_path, rs_path, pdk_path]):
        raise RuntimeError("Artifacts missing. Run bootstrap_ca.py first.")
        
    with open(ca_path) as f: ca_config = json.load(f)
    with open(as_path) as f: as_config = json.load(f)
    with open(rs_path) as f: rs_config = json.load(f)
    with open(pdk_path) as f: pdk_manifest = json.load(f)
    
    # Setup PDK Store
    pdk_store = PDKTrustStore()
    for entry in pdk_manifest:
        pdk_store.add_entry(
            entry['key_id'], 
            entry['identity'], 
            base64url_decode(entry['ml_kem_public_key'])
        )
        
    return {
        'ca_pk': base64url_decode(ca_config['public_key']),
        'pdk_store': pdk_store,
        'as_url': 'kemtls://127.0.0.1:4433',
        'rs_url': 'kemtls://127.0.0.1:4434'
    }


def run_demo(mode="auto"):
    print(f"\n{'='*20} Starting Demo (Mode: {mode}) {'='*20}")
    config = load_config()
    
    # 1. Initialize OIDC Client
    http_client = KEMTLSHttpClient(
        ca_pk=config['ca_pk'],
        pdk_store=config['pdk_store'],
        expected_identity="auth-server",
        mode=mode
    )
    
    client = OIDCClient(
        http_client=http_client,
        client_id="demo-client",
        issuer_url=config['as_url'],
        redirect_uri="kemtls://localhost/callback"
    )
    
    # 2. Login Flow
    print("\n[HANDSHAKE] Starting Login Flow...")
    auth_url = client.start_auth()
    # auth_url would normally be used in a browser redirect. 
    # Here, we simulate the redirect response from AS:
    import urllib.parse
    parsed_auth_url = urllib.parse.urlparse(auth_url)
    params = urllib.parse.parse_qs(parsed_auth_url.query)
    
    # Simulate Auth Server response (via direct call for demo simplicity)
    # Normally this would be a separate KEMTLS connection from the browser/agent
    print(f"[AUTH] Simulating /authorize call for: {params.get('client_id')}")
    mock_auth_resp = http_client.get(f"{config['as_url']}/authorize")
    code = mock_auth_resp.get('body', {}).get('code')
    print(f"[AUTH] Received code: {code}")
    
    print("\n[HANDSHAKE] Exchanging code for tokens...")
    token_resp = client.exchange_code(code)
    print(f"[TOKEN] Access Token issued. Binding ID: {token_resp.get('session_binding_id', 'Bound')}")
    
    # 3. Access Resource
    print("\n[RESOURCE] Accessing protected resource...")
    # Update expected identity for the HTTP client to RS
    http_client.expected_identity = "resource-server"
    resource_resp = client.call_api(f"{config['rs_url']}/resource")
    
    if resource_resp.get('status') == 200:
        print(f"[SUCCESS] Resource accessed: {resource_resp.get('body', {}).get('message')}")
    else:
        print(f"[FAILURE] Resource access denied: {resource_resp.get('body')}")

    # 4. Replay Attack
    print("\n[SECURITY] Testing Replay Attack (New KEMTLS session, old token)...")
    replay_resp = client.replay_attack(f"{config['rs_url']}/resource")
    
    if replay_resp.get('status') == 403:
        print(f"[SUCCESS] Replay attack blocked (403 Forbidden).")
        print(f"[SUCCESS] Server rejected binding mismatch correctly.")
    else:
        print(f"[FAILURE] Replay attack was NOT blocked (Status {replay_resp.get('status')})!")

    # 5. Telemetry
    telemetry = client.get_telemetry()
    print("\n[TELEMETRY] Metrics for this run:")
    for hs in telemetry['handshakes']:
        print(f" - Handshake Duration: {hs['duration_ms']:.2f} ms")
        print(f" - Negotiated Mode: {hs['mode']}")
    for tok in telemetry['tokens']:
        print(f" - Token Size: {tok['size_bytes']} bytes")
        print(f" - Binding Claim: {tok['binding_claim']}")


if __name__ == "__main__":
    # Ensure servers are running (must be started manually or in background by user)
    # For this demo, we assume run_kemtls_auth_server.py 
    # and run_kemtls_resource_server.py have been started.
    try:
        run_demo(mode="baseline")
        run_demo(mode="pdk")
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        print("Note: Ensure Auth and Resource servers are running in separate terminals.")
