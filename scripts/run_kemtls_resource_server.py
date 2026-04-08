"""Resource server launcher for the real KEMTLS OIDC stack."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kemtls.tcp_server import KEMTLSTCPServer
from kemtls.quic_server import KEMTLSQUICServer
from servers.resource_server_app import create_resource_server_app
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


def create_rs_app(host: str, auth_port: int, config: dict | None = None):
    base_dir = Path(__file__).parent.parent / "keys"
    with open(base_dir / "auth_server" / "as_config.json", "r", encoding="utf-8") as file_handle:
        as_config = json.load(file_handle)

    merged_config = {
        "issuer": f"kemtls://{host}:{auth_port}",
        "issuer_public_key": base64url_decode(as_config["jwt_signing_pk"]),
        "resource_audience": None,
    }
    if config:
        merged_config.update(config)
    return create_resource_server_app(merged_config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the KEMTLS resource server")
    parser.add_argument("--transport", choices=["tcp", "quic"], default="quic")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4434)
    parser.add_argument("--auth-port", type=int, default=4433)
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / "keys"
    rs_config_path = base_dir / "resource_server" / "rs_config.json"
    if not os.path.exists(rs_config_path):
        print("Required config not found. Run bootstrap_ca.py first.")
        return

    with open(rs_config_path, "r", encoding="utf-8") as file_handle:
        rs_config = json.load(file_handle)

    app = create_rs_app(args.host, args.auth_port)
    server_class = KEMTLSTCPServer if args.transport == "tcp" else KEMTLSQUICServer
    server = server_class(
        app=app,
        server_identity="resource-server",
        server_lt_sk=base64url_decode(rs_config["longterm_sk"]),
        cert=rs_config["certificate"],
        pdk_key_id=load_pdk_key_id(base_dir, "resource-server"),
        host=args.host,
        port=args.port,
    )
    print(f"Starting Resource Server on {args.host}:{args.port} using {args.transport.upper()} transport...")
    server.start()


if __name__ == "__main__":
    main()
