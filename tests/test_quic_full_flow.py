import hashlib
import json
import threading
import time
from pathlib import Path

from client.kemtls_http_client import KEMTLSHttpClient
from client.oidc_client import OIDCClient
from kemtls.pdk import PDKTrustStore
from kemtls.quic_server import KEMTLSQUICServer
from oidc.auth_endpoints import InMemoryClientRegistry
from servers.auth_server_app import create_auth_server_app
from servers.resource_server_app import create_resource_server_app
from utils.encoding import base64url_decode
from utils.encoding import base64url_encode


def _challenge(verifier: str) -> str:
    return base64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())


def _load_material():
    base_dir = Path(__file__).parent.parent / "keys"
    with open(base_dir / "ca" / "ca_keys.json", "r", encoding="utf-8") as file_handle:
        ca_cfg = json.load(file_handle)
    with open(base_dir / "auth_server" / "as_config.json", "r", encoding="utf-8") as file_handle:
        as_cfg = json.load(file_handle)
    with open(base_dir / "resource_server" / "rs_config.json", "r", encoding="utf-8") as file_handle:
        rs_cfg = json.load(file_handle)
    with open(base_dir / "pdk" / "pdk_manifest.json", "r", encoding="utf-8") as file_handle:
        pdk_manifest = json.load(file_handle)

    pdk_store = PDKTrustStore()
    auth_pdk_key_id = None
    resource_pdk_key_id = None
    for entry in pdk_manifest:
        pdk_store.add_entry(
            entry["key_id"],
            entry["identity"],
            base64url_decode(entry["ml_kem_public_key"]),
        )
        if entry.get("identity") == "auth-server":
            auth_pdk_key_id = entry["key_id"]
        if entry.get("identity") == "resource-server":
            resource_pdk_key_id = entry["key_id"]

    return {
        "ca_pk": base64url_decode(ca_cfg["public_key"]),
        "issuer_pk": base64url_decode(as_cfg["jwt_signing_pk"]),
        "issuer_sk": base64url_decode(as_cfg["jwt_signing_sk"]),
        "auth_lt_sk": base64url_decode(as_cfg["longterm_sk"]),
        "auth_cert": as_cfg["certificate"],
        "resource_lt_sk": base64url_decode(rs_cfg["longterm_sk"]),
        "resource_cert": rs_cfg["certificate"],
        "auth_pdk_key_id": auth_pdk_key_id,
        "resource_pdk_key_id": resource_pdk_key_id,
        "pdk_store": pdk_store,
    }


def test_quic_full_oidc_flow_and_replay_rejection():
    material = _load_material()

    auth_port = 45443
    resource_port = 45444
    issuer_url = f"kemtls://127.0.0.1:{auth_port}"
    userinfo_url = f"kemtls://127.0.0.1:{resource_port}/userinfo"

    client_id = "quic-client"
    redirect_uri = f"{issuer_url}/callback"

    auth_app = create_auth_server_app(
        {
            "issuer": issuer_url,
            "issuer_public_key": material["issuer_pk"],
            "issuer_secret_key": material["issuer_sk"],
            "clients": {client_id: {"redirect_uris": [redirect_uri]}},
            "demo_user": "alice",
        },
        stores={"client_registry": InMemoryClientRegistry({client_id: {"redirect_uris": [redirect_uri]}})},
    )
    resource_app = create_resource_server_app(
        {
            "issuer": issuer_url,
            "issuer_public_key": material["issuer_pk"],
            "resource_audience": client_id,
        }
    )

    auth_server = KEMTLSQUICServer(
        app=auth_app,
        server_identity="auth-server",
        server_lt_sk=material["auth_lt_sk"],
        cert=material["auth_cert"],
        pdk_key_id=material["auth_pdk_key_id"],
        host="127.0.0.1",
        port=auth_port,
    )
    resource_server = KEMTLSQUICServer(
        app=resource_app,
        server_identity="resource-server",
        server_lt_sk=material["resource_lt_sk"],
        cert=material["resource_cert"],
        pdk_key_id=material["resource_pdk_key_id"],
        host="127.0.0.1",
        port=resource_port,
    )

    auth_thread = threading.Thread(target=auth_server.start, daemon=True)
    resource_thread = threading.Thread(target=resource_server.start, daemon=True)
    auth_thread.start()
    resource_thread.start()
    time.sleep(0.2)

    auth_http_client = KEMTLSHttpClient(
        ca_pk=material["ca_pk"],
        pdk_store=material["pdk_store"],
        expected_identity="auth-server",
        mode="baseline",
        transport="quic",
        keep_alive=True,
    )
    resource_http_client = KEMTLSHttpClient(
        ca_pk=material["ca_pk"],
        pdk_store=material["pdk_store"],
        expected_identity="resource-server",
        mode="baseline",
        transport="quic",
        keep_alive=True,
    )

    try:
        public_key, secret_key = auth_http_client.get_binding_keypair()
        resource_http_client.set_binding_keypair(public_key, secret_key)

        oidc_client = OIDCClient(
            http_client=auth_http_client,
            client_id=client_id,
            issuer_url=issuer_url,
            redirect_uri=redirect_uri,
        )

        verifier = "quic-verifier"
        oidc_client.code_verifier = verifier
        oidc_client.code_challenge = _challenge(verifier)

        auth_url = (
            f"{issuer_url}/authorize?"
            f"client_id={client_id}&response_type=code&scope=openid%20profile%20email"
            f"&redirect_uri={redirect_uri}&code_challenge={oidc_client.code_challenge}"
            f"&code_challenge_method=S256&state=state-1"
        )
        auth_resp = auth_http_client.get(auth_url)
        assert auth_resp["status"] == 200
        code = auth_resp["body"]["code"]

        token_resp = oidc_client.exchange_code(code)
        assert oidc_client.access_token
        assert token_resp["token_type"] == "Bearer"

        access_resp = resource_http_client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {oidc_client.access_token}"},
        )
        assert access_resp["status"] == 200
        assert access_resp["body"]["sub"] == "alice"

        attacker_http_client = KEMTLSHttpClient(
            ca_pk=material["ca_pk"],
            pdk_store=material["pdk_store"],
            expected_identity="resource-server",
            mode="baseline",
            transport="quic",
            keep_alive=True,
        )
        try:
            replay_resp = attacker_http_client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {oidc_client.access_token}"},
            )
            assert replay_resp["status"] == 401
            assert replay_resp["body"]["error"] == "binding_mismatch"
        finally:
            attacker_http_client.close()

        assert oidc_client.telemetry["handshakes"]
        assert oidc_client.telemetry["handshakes"][-1]["transport"] == "quic"
    finally:
        auth_http_client.close()
        resource_http_client.close()
        auth_server.stop()
        resource_server.stop()
