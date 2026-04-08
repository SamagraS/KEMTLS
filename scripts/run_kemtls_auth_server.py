"""Authorization server launcher for the real KEMTLS OIDC stack."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

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


def create_auth_app(host: str, port: int, transport: str, config: dict | None = None):
    base_dir = Path(__file__).parent.parent / "keys"
    with open(base_dir / "auth_server" / "as_config.json", "r", encoding="utf-8") as file_handle:
        as_config = json.load(file_handle)

    client_config = _load_runtime_client_config()
    issuer_url = f"kemtls://{host}:{port}"
    clients = {
        client_config["client_id"]: {
            "redirect_uris": [client_config["redirect_uri"]],
        },
        "bench-client": {
            "redirect_uris": ["kemtls://127.0.0.1:50001/callback"],
        },
    }
    merged_config = {
        "issuer": issuer_url,
        "issuer_public_key": base64url_decode(as_config["jwt_signing_pk"]),
        "issuer_secret_key": base64url_decode(as_config["jwt_signing_sk"]),
        "signing_kid": "signing-key-1",
        "clients": clients,
        "demo_user": "user-1",
        "introspection_endpoint": f"{issuer_url}/introspect",
        "kemtls_modes_supported": ["baseline", "pdk", "auto"],
        "kemtls_transports_supported": [transport],
        "kemtls_default_transport": transport,
    }
    if config:
        merged_config.update(config)
        if "clients" in config and isinstance(config["clients"], dict):
            merged_config["clients"].update(config["clients"])

    return create_auth_server_app(
        merged_config,
        stores={"client_registry": InMemoryClientRegistry(merged_config["clients"])},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the KEMTLS authorization server")
    parser.add_argument("--transport", choices=["tcp", "quic"], default="tcp")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4433)
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / "keys"
    config_path = base_dir / "auth_server" / "as_config.json"
    if not os.path.exists(config_path):
        print("Config not found. Run bootstrap_ca.py first.")
        return

    with open(config_path, "r", encoding="utf-8") as file_handle:
        config = json.load(file_handle)

    app = create_auth_app(args.host, args.port, args.transport)
    server_class = KEMTLSTCPServer if args.transport == "tcp" else KEMTLSQUICServer
    server = server_class(
        app=app,
        server_identity="auth-server",
        server_lt_sk=base64url_decode(config["longterm_sk"]),
        cert=config["certificate"],
        pdk_key_id=load_pdk_key_id(base_dir, "auth-server"),
        host=args.host,
        port=args.port,
    )
    print(f"Starting Auth Server on {args.host}:{args.port} using {args.transport.upper()} transport...")
    server.start()


if __name__ == "__main__":
    main()
