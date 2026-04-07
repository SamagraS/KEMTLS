import os
import sys
import time
import uuid
import csv
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from crypto.ml_dsa import MLDSA65
from utils.encoding import base64url_encode
from oidc.jwt_handler import PQJWT
from servers.auth_server_app import create_auth_server_app
from servers.resource_server_app import create_resource_server_app
from utils.telemetry import OIDCClientFlowCollector

def _challenge(verifier: str) -> str:
    return base64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())

class DummySession:
    session_binding_id = b"a" * 32
    refresh_binding_id = b"b" * 32
    handshake_mode = "baseline"

def run():
    run_id = str(uuid.uuid4())[:8]
    
    issuer_public_key, issuer_secret_key = MLDSA65.generate_keypair()
    auth_app = create_auth_server_app({
        "issuer": "https://issuer.example",
        "issuer_public_key": issuer_public_key,
        "issuer_secret_key": issuer_secret_key,
        "clients": {"client123": {"redirect_uris": ["https://client.example/cb"]}},
        "demo_user": "alice",
        "kemtls_modes_supported": ["baseline"]
    })
    resource_app = create_resource_server_app({
        "issuer": "https://issuer.example",
        "issuer_public_key": issuer_public_key,
        "resource_audience": "client123"
    })
    
    auth_client = auth_app.test_client()
    resource_client = resource_app.test_client()
    
    session = DummySession()
    verifier = "bench-verifier"
    
    jwt = PQJWT()
    claims = {"sub": "alice", "iss": "https://issuer.example", "aud": "client123", "exp": int(time.time())+3600}
    
    out_path = os.path.join(os.path.dirname(__file__), 'oidc_results.csv')
    with open(out_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['run_id', 'protocol', 'scenario', 't_discovery_ms', 't_authorize_ms', 't_token_ms', 't_userinfo_ms', 't_auth_total_ms', 't_jwt_sign_ms', 't_jwt_verify_ms', 's_id_token_bytes', 's_id_token_sig'])
        
        print("[*] Running OIDC warmups (50 iterations)...")
        for _ in range(50):
            auth_client.get("/.well-known/openid-configuration")
            url = f"/authorize?response_type=code&client_id=client123&redirect_uri=https://client.example/cb&scope=openid profile&state=1&code_challenge={_challenge(verifier)}&code_challenge_method=S256"
            res = auth_client.get(url)
            code = res.get_json()["code"]
            payload = {"grant_type": "authorization_code", "client_id": "client123", "redirect_uri": "https://client.example/cb", "code": code, "code_verifier": verifier}
            res = auth_client.post("/token", json=payload, environ_overrides={"kemtls.session": session})
            acc = res.get_json()["access_token"]
            resource_client.get("/userinfo", headers={"Authorization": f"Bearer {acc}"}, environ_overrides={"kemtls.session": session})
        
        print("[*] Running OIDC measurements (1000 iterations)...")
        for _ in range(1000):
            client_flow = OIDCClientFlowCollector()
            client_flow.total_flow_timer.start()
            
            client_flow.discovery_timer.start()
            auth_client.get("/.well-known/openid-configuration")
            client_flow.discovery_timer.stop()
            
            # Authorize
            url = f"/authorize?response_type=code&client_id=client123&redirect_uri=https://client.example/cb&scope=openid profile&state=1&code_challenge={_challenge(verifier)}&code_challenge_method=S256"
            client_flow.authorization_timer.start()
            auth_res = auth_client.get(url)
            client_flow.authorization_timer.stop()
            code = auth_res.get_json()["code"]
            
            # Token
            payload = {"grant_type": "authorization_code", "client_id": "client123", "redirect_uri": "https://client.example/cb", "code": code, "code_verifier": verifier}
            client_flow.token_exchange_timer.start()
            tok_res = auth_client.post("/token", json=payload, environ_overrides={"kemtls.session": session})
            client_flow.token_exchange_timer.stop()
            tok_json = tok_res.get_json()
            access_token = tok_json["access_token"]
            
            # Userinfo
            headers = {"Authorization": f"Bearer {access_token}"}
            client_flow.userinfo_timer.start()
            usr_res = resource_client.get("/userinfo", headers=headers, environ_overrides={"kemtls.session": session})
            client_flow.userinfo_timer.stop()
            usr_json = usr_res.get_json()
            
            client_flow.total_flow_timer.stop()
            
            # Extract server-side telemetry
            t_tok_metric = tok_json.get("_telemetry", {})
            t_usr_metric = usr_json.get("_telemetry", {})
            
            t_disc = client_flow.discovery_timer.ms
            t_auth = client_flow.authorization_timer.ms
            t_tok = client_flow.token_exchange_timer.ms
            t_usr = client_flow.userinfo_timer.ms
            t_total = client_flow.total_flow_timer.ms
            
            t_sign = t_tok_metric.get("jwt_signing_timing_ms", 0.0)
            t_verify = t_usr_metric.get("jwt_verification_timing_ms", 0.0)
            
            sizes = t_tok_metric.get("token_sizes", {})
            s_id_token = sizes.get("id_token", 0)
            s_sig = sizes.get("signature", 3309)
            
            w.writerow([run_id, 'OIDC', 'baseline', t_disc, t_auth, t_tok, t_usr, t_total, t_sign, t_verify, s_id_token, s_sig])
            
    print(f"[*] OIDC benchmarks saved to {out_path}")

if __name__ == "__main__":
    run()
