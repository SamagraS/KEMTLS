"""
Resource Server Implementation over KEMTLS

Endpoints:
- /resource: Protected endpoint with session-bound JWT verification
"""

import os
import json
import sys
from pathlib import Path
from typing import Optional
from flask import Flask, request, jsonify

# Ensure src in path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kemtls.tcp_server import KEMTLSTCPServer
from utils.encoding import base64url_decode, base64url_encode
from crypto.ml_dsa import MLDSA65
from utils.helpers import get_timestamp


def load_pdk_key_id(base_dir: Path, identity: str) -> Optional[str]:
    manifest_path = base_dir / 'pdk' / 'pdk_manifest.json'
    if not os.path.exists(manifest_path):
        return None

    with open(manifest_path) as f:
        manifest = json.load(f)

    for entry in manifest:
        if entry.get('identity') == identity:
            return entry.get('key_id')

    return None


def create_rs_app(as_jwt_pk: bytes):
    app = Flask(__name__)
    
    @app.route('/resource')
    def resource():
        # 1. Fetch Session Binding from KEMTLS Context
        session = request.environ.get('kemtls.session')
        if not session:
            return jsonify({'error': 'no_kemtls_session'}), 401
            
        current_binding_id = session.session_binding_id
        
        # 2. Extract Authorization: Bearer Token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'missing_token'}), 401
            
        token = auth_header.split(' ')[1]
        
        try:
            # 3. Parse and Verify JWT
            parts = token.split('.')
            if len(parts) != 2:
                raise ValueError("Malformed token")
                
            body_bytes = base64url_decode(parts[0])
            signature = base64url_decode(parts[1])
            
            # Verify signature using ML-DSA
            if not MLDSA65.verify(as_jwt_pk, body_bytes, signature):
                raise ValueError("Invalid signature")
                
            claims = json.loads(body_bytes.decode('utf-8'))
            
            # 4. Enforce Expiry
            if get_timestamp() > claims.get('exp', 0):
                raise ValueError("Token expired")
                
            # 5. Enforce Session Binding (Transport Layer)
            token_binding_id = claims.get('session_binding_id')
            if token_binding_id != current_binding_id:
                print(f"SECURITY ALERT: Binding Mis-match! Expected {token_binding_id}, got {current_binding_id}")
                return jsonify({'error': 'binding_mismatch', 'details': 'TBT violation'}), 403
                
        except Exception as e:
            return jsonify({'error': 'invalid_token', 'details': str(e)}), 401

        return jsonify({
            'status': 'access_granted',
            'user': claims.get('sub'),
            'binding_id': current_binding_id,
            'message': 'This resource is binded to your KEMTLS session.'
        })

    return app


def main():
    base_dir = Path(__file__).parent.parent / 'keys'
    rs_config_path = base_dir / 'resource_server' / 'rs_config.json'
    as_config_path = base_dir / 'auth_server' / 'as_config.json'
    
    if not os.path.exists(rs_config_path) or not os.path.exists(as_config_path):
        print("Required config not found. Run bootstrap_ca.py first.")
        return
        
    with open(rs_config_path) as f:
        rs_config = json.load(f)
    with open(as_config_path) as f:
        as_config = json.load(f)
        
    rs_lt_sk = base64url_decode(rs_config['longterm_sk'])
    rs_cert = rs_config['certificate']
    rs_pdk_key_id = load_pdk_key_id(base_dir, 'resource-server')
    as_jwt_pk = base64url_decode(as_config['jwt_signing_pk'])
    print(f"Resource server PDK key id: {rs_pdk_key_id}")
    
    app = create_rs_app(as_jwt_pk)
    server = KEMTLSTCPServer(
        app=app,
        server_identity='resource-server',
        server_lt_sk=rs_lt_sk,
        cert=rs_cert,
        pdk_key_id=rs_pdk_key_id,
        host='127.0.0.1',
        port=4434
    )
    
    print("Starting Resource Server on port 4434...")
    server.start()


if __name__ == "__main__":
    main()
