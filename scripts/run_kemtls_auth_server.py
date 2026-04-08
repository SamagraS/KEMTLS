"""Authorization server launcher for the real KEMTLS OIDC stack."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure src in path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kemtls.tcp_server import KEMTLSTCPServer
from kemtls.quic_server import KEMTLSQUICServer
from oidc.auth_endpoints import InMemoryClientRegistry
from servers.auth_server_app import create_auth_server_app
from utils.encoding import base64url_decode


def load_pdk_key_id(base_dir: Path, identity: str) -> str | None:
    manifest_path = base_dir / "pdk" / "pdk_manifest.json"
    if not os.path.exists(manifest_path):
        return None

    with open(manifest_path, "r", encoding="utf-8") as file_handle:
        manifest = json.load(file_handle)

    for entry in manifest:
        if entry.get("identity") == identity:
            return entry.get("key_id")

    return None


def _load_runtime_client_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "client_config.json"
    with open(config_path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def _build_app_config() -> dict:
    base_dir = Path(__file__).parent.parent / "keys"
    with open(base_dir / "auth_server" / "as_config.json", "r", encoding="utf-8") as file_handle:
        as_config = json.load(file_handle)

    client_config = _load_runtime_client_config()
    issuer_url = "kemtls://127.0.0.1:4433"
    clients = {
        client_config["client_id"]: {
            "redirect_uris": [client_config["redirect_uri"]],
        },
        "bench-client": {
            "redirect_uris": ["kemtls://127.0.0.1:50001/callback"],
        },
    }

    return {
        "issuer": issuer_url,
        "issuer_public_key": base64url_decode(as_config["jwt_signing_pk"]),
        "issuer_secret_key": base64url_decode(as_config["jwt_signing_sk"]),
        "signing_kid": "signing-key-1",
        "clients": clients,
        "demo_user": "user-1",
        "introspection_endpoint": f"{issuer_url}/introspect",
    }


def create_auth_app(config: dict | None = None):
    merged_config = _build_app_config()
    if config:
        merged_config.update(config)
        if "clients" in config and isinstance(config["clients"], dict):
            merged_config["clients"].update(config["clients"])
    return create_auth_server_app(
        merged_config,
        stores={"client_registry": InMemoryClientRegistry(merged_config["clients"])}
    )


def main():
    base_dir = Path(__file__).parent.parent / "keys"
    config_path = base_dir / "auth_server" / "as_config.json"
    if not os.path.exists(config_path):
        print("Config not found. Run bootstrap_ca.py first.")
        return

    with open(config_path, "r", encoding="utf-8") as file_handle:
        config = json.load(file_handle)

    as_lt_sk = base64url_decode(config["longterm_sk"])
    as_cert = config["certificate"]
    as_pdk_key_id = load_pdk_key_id(base_dir, "auth-server")
    print(f"Auth server PDK key id: {as_pdk_key_id}")

    app = create_auth_app()
    server = KEMTLSQUICServer(
        app=app,
        server_identity="auth-server",
        server_lt_sk=as_lt_sk,
        cert=as_cert,
        pdk_key_id=as_pdk_key_id,
        host="127.0.0.1",
        port=4433,
    )

    print("Starting Auth Server on port 4433 using QUIC transport...")
    server.start()


if __name__ == "__main__":
    main()
