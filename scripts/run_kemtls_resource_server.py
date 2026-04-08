"""Resource server launcher for the real KEMTLS OIDC stack."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure src in path
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


def create_rs_app(config: dict | None = None):
    base_dir = Path(__file__).parent.parent / "keys"
    with open(base_dir / "auth_server" / "as_config.json", "r", encoding="utf-8") as file_handle:
        as_config = json.load(file_handle)

    merged_config = {
        "issuer": "kemtls://127.0.0.1:4433",
        "issuer_public_key": base64url_decode(as_config["jwt_signing_pk"]),
        "resource_audience": None,
    }
    if config:
        merged_config.update(config)

    return create_resource_server_app(merged_config)


def main():
    base_dir = Path(__file__).parent.parent / "keys"
    rs_config_path = base_dir / "resource_server" / "rs_config.json"

    if not os.path.exists(rs_config_path):
        print("Required config not found. Run bootstrap_ca.py first.")
        return

    with open(rs_config_path, "r", encoding="utf-8") as file_handle:
        rs_config = json.load(file_handle)

    rs_lt_sk = base64url_decode(rs_config["longterm_sk"])
    rs_cert = rs_config["certificate"]
    rs_pdk_key_id = load_pdk_key_id(base_dir, "resource-server")
    print(f"Resource server PDK key id: {rs_pdk_key_id}")

    app = create_rs_app()
    server = KEMTLSQUICServer(
        app=app,
        server_identity="resource-server",
        server_lt_sk=rs_lt_sk,
        cert=rs_cert,
        pdk_key_id=rs_pdk_key_id,
        host="127.0.0.1",
        port=4434,
    )

    print("Starting Resource Server on port 4434 using QUIC transport...")
    server.start()


if __name__ == "__main__":
    main()
