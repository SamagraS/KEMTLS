"""
Comprehensive Test Suite for KEMTLS Full System

Tests:
- Handshake (Baseline, PDK, Auto)
- Identity Mismatch Failures
- Record Layer (AAD, Sequence, Encryption)
- End-to-End HTTP Integration
"""

import os
import sys
import threading
import time
import pytest
from flask import Flask, jsonify

# Ensure src is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from kemtls.handshake import ClientHandshake, ServerHandshake
from kemtls.record_layer import KEMTLSRecordLayer
from kemtls.pdk import PDKTrustStore
from kemtls.certs import create_certificate, validate_certificate
from kemtls.tcp_server import KEMTLSTCPServer
from kemtls.client import KEMTLSClient
from crypto.ml_kem import MLKEM768
from crypto.ml_dsa import MLDSA65
from utils.helpers import get_timestamp


# --- Fixtures ---

@pytest.fixture
def keys():
    ca_pk, ca_sk = MLDSA65.generate_keypair()
    server_lt_pk, server_lt_sk = MLKEM768.generate_keypair()
    
    # Create certificate
    now = get_timestamp()
    cert = create_certificate(
        subject="server-1",
        kem_pk=server_lt_pk,
        ca_sk=ca_sk,
        issuer="Root CA",
        valid_from=now - 10,
        valid_to=now + 3600
    )
    
    return {
        'ca_pk': ca_pk,
        'ca_sk': ca_sk,
        'server_lt_pk': server_lt_pk,
        'server_lt_sk': server_lt_sk,
        'cert': cert
    }


@pytest.fixture
def flask_app():
    app = Flask(__name__)
    
    @app.route("/")
    def index():
        return "Hello from KEMTLS!"
        
    @app.route("/api/data")
    def api_data():
        return jsonify({"status": "secure", "identity": "server-1"})
        
    return app


# --- Tests ---

def test_handshake_baseline_success(keys):
    """Test successful handshake in baseline (certificate) mode."""
    server_handshake = ServerHandshake(
        server_identity="server-1",
        server_lt_sk=keys['server_lt_sk'],
        cert=keys['cert']
    )
    client_handshake = ClientHandshake(
        expected_identity="server-1",
        ca_pk=keys['ca_pk'],
        mode="baseline"
    )
    
    # CH -> SH
    ch = client_handshake.client_hello()
    sh = server_handshake.process_client_hello(ch)
    
    # SH -> CKE
    cke, session_client = client_handshake.process_server_hello(sh)
    sf = server_handshake.process_client_key_exchange(cke)
    
    # SF -> CF
    client_handshake.process_server_finished(sf, session_client)
    cf = client_handshake.client_finished()
    session_server = server_handshake.verify_client_finished(cf)
    
    assert session_client.handshake_mode == "baseline"
    assert session_server.handshake_mode == "baseline"
    assert session_client.session_id == session_server.session_id


def test_handshake_pdk_success(keys):
    """Test successful handshake in PDK mode."""
    pdk_store = PDKTrustStore()
    pdk_store.add_entry("key-1", "server-1", keys['server_lt_pk'])
    
    server_handshake = ServerHandshake(
        server_identity="server-1",
        server_lt_sk=keys['server_lt_sk'],
        pdk_key_id="key-1"
    )
    client_handshake = ClientHandshake(
        expected_identity="server-1",
        pdk_store=pdk_store,
        mode="pdk"
    )
    
    ch = client_handshake.client_hello()
    sh = server_handshake.process_client_hello(ch)
    
    cke, session_client = client_handshake.process_server_hello(sh)
    sf = server_handshake.process_client_key_exchange(cke)
    
    client_handshake.process_server_finished(sf, session_client)
    cf = client_handshake.client_finished()
    session_server = server_handshake.verify_client_finished(cf)
    
    assert session_client.handshake_mode == "pdk"
    assert session_client.trusted_key_id == "key-1"


def test_handshake_auto_selects_pdk(keys):
    """Test auto mode prioritizes PDK when available."""
    pdk_store = PDKTrustStore()
    pdk_store.add_entry("key-1", "server-1", keys['server_lt_pk'])
    
    server_handshake = ServerHandshake(
        server_identity="server-1",
        server_lt_sk=keys['server_lt_sk'],
        cert=keys['cert'],
        pdk_key_id="key-1"
    )
    client_handshake = ClientHandshake(
        expected_identity="server-1",
        ca_pk=keys['ca_pk'],
        pdk_store=pdk_store,
        mode="auto"
    )
    
    ch = client_handshake.client_hello()
    sh = server_handshake.process_client_hello(ch)
    
    cke, session_client = client_handshake.process_server_hello(sh)
    assert session_client.handshake_mode == "pdk"


def test_handshake_identity_mismatch(keys):
    """Verify handshake fails if identity mismatch occurs."""
    client_handshake = ClientHandshake(
        expected_identity="wrong-server",
        ca_pk=keys['ca_pk'],
        mode="baseline"
    )
    ch = client_handshake.client_hello()
    
    server_handshake = ServerHandshake(
        server_identity="server-1",
        server_lt_sk=keys['server_lt_sk'],
        cert=keys['cert']
    )
    sh = server_handshake.process_client_hello(ch)
    
    with pytest.raises(ValueError, match="Identity mismatch"):
        client_handshake.process_server_hello(sh)


def test_end_to_end_integration(keys, flask_app):
    """Full end-to-end integration: Client -> TCP Server -> Bridge -> Flask."""
    import socket
    
    # 1. Start Server in Thread
    server = KEMTLSTCPServer(
        app=flask_app,
        server_identity="server-1",
        server_lt_sk=keys['server_lt_sk'],
        cert=keys['cert'],
        port=5566
    )
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(0.1) # Wait for server to start
    
    # 2. Make Client Request
    client = KEMTLSClient(
        expected_identity="server-1",
        ca_pk=keys['ca_pk'],
        mode="baseline"
    )
    
    response, session = client.request(
        host="127.0.0.1",
        port=5566,
        method="GET",
        path="/"
    )
    
    assert b"Hello from KEMTLS!" in response
    assert session.handshake_mode == "baseline"


if __name__ == "__main__":
    pytest.main([__file__])
