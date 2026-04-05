#!/usr/bin/env python3
"""Diagnostic for PDK mode handshake in live server scenario."""

import json
import threading
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent))

from scripts.run_kemtls_auth_server import create_auth_app, load_pdk_key_id
from kemtls.tcp_server import KEMTLSTCPServer
from utils.encoding import base64url_decode
from scripts.demo_full_flow import load_config
from client.kemtls_http_client import KEMTLSHttpClient
from kemtls.handshake import deserialize_message, ClientHandshake

# 1. Start server on port 5568
print("[SERVER] Starting auth server on port 5568...")
base = Path('keys')
as_cfg = json.load(open(base / 'auth_server' / 'as_config.json'))
app = create_auth_app(as_cfg)
pdk_key_id = load_pdk_key_id(base, 'auth-server')
print(f"[SERVER] Loaded PDK key_id: {pdk_key_id}")

server = KEMTLSTCPServer(
    app=app,
    server_identity='auth-server',
    server_lt_sk=base64url_decode(as_cfg['longterm_sk']),
    cert=as_cfg['certificate'],
    pdk_key_id=pdk_key_id,
    host='127.0.0.1',
    port=5568
)
t = threading.Thread(target=server.start, daemon=True)
t.start()
time.sleep(0.3)

# 2. Analyze what client_hello sends in PDK mode
print("\n[CLIENT] Analyzing ClientHello...")
cfg = load_config()
ch = ClientHandshake(
    'auth-server',
    ca_pk=None,  # PDK mode doesn't need CA cert
    pdk_store=cfg['pdk_store'],
    mode='pdk'
)
ch_bytes = ch.client_hello()
ch_msg = deserialize_message(ch_bytes)
print(f"  - ClientHello.modes: {ch_msg.get('modes')}")
print(f"  - ClientHello.expected_identity: {ch_msg.get('expected_identity')}")
if cfg['pdk_store']:
    print(f"  - PDK store initialized")
    try:
        entry = cfg['pdk_store'].resolve_expected_identity('auth-server', 'as-key-1')
        print(f"  - Can resolve 'auth-server' with key_id 'as-key-1': YES")
    except Exception as e:
        print(f"  - Can resolve 'auth-server' with key_id 'as-key-1': NO ({e})")
else:
    print(f"  - PDK store is None!")

# 3. Attempt connection with PDK mode
print("\n[CLIENT] Attempting GET request with mode='pdk'...")
http_client = KEMTLSHttpClient(
    ca_pk=cfg['ca_pk'],
    pdk_store=cfg['pdk_store'],
    expected_identity='auth-server',
    mode='pdk'
)

try:
    resp = http_client.get('kemtls://127.0.0.1:5568/authorize')
    print(f"[SUCCESS] Response status: {resp.get('status')}")
    print(f"  - Mode negotiated: {resp.get('kemtls_metadata', {}).get('mode')}")
    print(f"  - Session ID: {resp.get('kemtls_metadata', {}).get('session_id')}")
    print(f"  - Trusted key ID: {resp.get('kemtls_metadata', {}).get('trusted_key_id')}")
except Exception as e:
    print(f"[FAILED] Error: {e}")
    import traceback
    traceback.print_exc()

# Wait briefly for server to process
time.sleep(0.2)
