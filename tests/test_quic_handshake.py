import json
import threading
import time
from pathlib import Path

from client.kemtls_http_client import KEMTLSHttpClient
from kemtls.pdk import PDKTrustStore
from kemtls.quic_server import KEMTLSQUICServer
from oidc.auth_endpoints import InMemoryClientRegistry
from servers.auth_server_app import create_auth_server_app
from utils.encoding import base64url_decode


def _load_material():
    base_dir = Path(__file__).parent.parent / "keys"
    with open(base_dir / "ca" / "ca_keys.json", "r", encoding="utf-8") as file_handle:
        ca_cfg = json.load(file_handle)
    with open(base_dir / "auth_server" / "as_config.json", "r", encoding="utf-8") as file_handle:
        as_cfg = json.load(file_handle)
    with open(base_dir / "pdk" / "pdk_manifest.json", "r", encoding="utf-8") as file_handle:
        pdk_manifest = json.load(file_handle)

    pdk_store = PDKTrustStore()
    auth_pdk_key_id = None
    for entry in pdk_manifest:
        pdk_store.add_entry(
            entry["key_id"],
            entry["identity"],
            base64url_decode(entry["ml_kem_public_key"]),
        )
        if entry.get("identity") == "auth-server":
            auth_pdk_key_id = entry["key_id"]

    return {
        "ca_pk": base64url_decode(ca_cfg["public_key"]),
        "issuer_pk": base64url_decode(as_cfg["jwt_signing_pk"]),
        "issuer_sk": base64url_decode(as_cfg["jwt_signing_sk"]),
        "auth_lt_sk": base64url_decode(as_cfg["longterm_sk"]),
        "auth_cert": as_cfg["certificate"],
        "auth_pdk_key_id": auth_pdk_key_id,
        "pdk_store": pdk_store,
    }


def test_quic_handshake_and_discovery_metadata():
    material = _load_material()
    auth_port = 45433
    issuer_url = f"kemtls://127.0.0.1:{auth_port}"

    app = create_auth_server_app(
        {
            "issuer": issuer_url,
            "issuer_public_key": material["issuer_pk"],
            "issuer_secret_key": material["issuer_sk"],
            "clients": {
                "quic-client": {
                    "redirect_uris": [f"{issuer_url}/callback"],
                }
            },
            "demo_user": "alice",
            "kemtls_transports_supported": ["tcp", "quic"],
            "kemtls_default_transport": "quic",
        },
        stores={"client_registry": InMemoryClientRegistry({"quic-client": {"redirect_uris": [f"{issuer_url}/callback"]}})},
    )

    server = KEMTLSQUICServer(
        app=app,
        server_identity="auth-server",
        server_lt_sk=material["auth_lt_sk"],
        cert=material["auth_cert"],
        pdk_key_id=material["auth_pdk_key_id"],
        host="127.0.0.1",
        port=auth_port,
    )
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    time.sleep(0.2)

    client = KEMTLSHttpClient(
        ca_pk=material["ca_pk"],
        pdk_store=material["pdk_store"],
        expected_identity="auth-server",
        mode="baseline",
        transport="quic",
    )

    try:
        response = client.get(f"{issuer_url}/.well-known/openid-configuration")
        assert response["status"] == 200
        metadata = response["body"]
        assert metadata["kemtls_supported"] is True
        assert metadata["kemtls_default_transport"] == "quic"
        assert "quic" in metadata["kemtls_transports_supported"]
        assert response["kemtls_metadata"]["transport"] == "quic"
    finally:
        client.close()
        server.stop()
