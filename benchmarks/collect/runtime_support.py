from __future__ import annotations

import json
import queue
import socket
import sys
import threading
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

from flask import Flask, jsonify


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from kemtls.pdk import PDKTrustStore
from kemtls.tcp_server import KEMTLSTCPServer
from oidc.auth_endpoints import InMemoryClientRegistry
from servers.auth_server_app import create_auth_server_app
from servers.resource_server_app import create_resource_server_app
from telemetry.collector import (
    KEMTLSHandshakeCollector,
    OIDCTokenCollector,
    OIDCUserinfoCollector,
)
from utils.encoding import base64url_decode


BENCH_CLIENT_ID = "bench-client"
BENCH_REDIRECT_URI = "kemtls://127.0.0.1:50001/callback"
BENCH_SCOPE = "openid profile email"


def load_keys() -> Dict[str, Any]:
    base_dir = ROOT_DIR / "keys"
    with (base_dir / "ca" / "ca_keys.json").open("r", encoding="utf-8") as file_handle:
        ca_config = json.load(file_handle)
    with (base_dir / "auth_server" / "as_config.json").open("r", encoding="utf-8") as file_handle:
        as_config = json.load(file_handle)
    with (base_dir / "resource_server" / "rs_config.json").open("r", encoding="utf-8") as file_handle:
        rs_config = json.load(file_handle)
    with (base_dir / "pdk" / "pdk_manifest.json").open("r", encoding="utf-8") as file_handle:
        pdk_manifest = json.load(file_handle)

    pdk_store = PDKTrustStore()
    for entry in pdk_manifest:
        pdk_store.add_entry(
            entry["key_id"],
            entry["identity"],
            base64url_decode(entry["ml_kem_public_key"]),
            metadata=entry.get("metadata"),
        )

    return {
        "ca_pk": base64url_decode(ca_config["public_key"]),
        "auth_jwt_pk": base64url_decode(as_config["jwt_signing_pk"]),
        "auth_jwt_sk": base64url_decode(as_config["jwt_signing_sk"]),
        "auth_sk": base64url_decode(as_config["longterm_sk"]),
        "auth_cert": as_config["certificate"],
        "auth_pdk_key_id": as_config.get("pdk_key_id", "as-key-1"),
        "resource_sk": base64url_decode(rs_config["longterm_sk"]),
        "resource_cert": rs_config["certificate"],
        "resource_pdk_key_id": rs_config.get("pdk_key_id", "rs-key-1"),
        "pdk_store": pdk_store,
    }


def find_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def wait_for_port(host: str, port: int, *, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    last_error: Optional[Exception] = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
    raise RuntimeError(f"Timed out waiting for {host}:{port} ({last_error})")


@dataclass
class ServerHandle:
    name: str
    host: str
    port: int
    server: KEMTLSTCPServer
    thread: threading.Thread
    handshake_metrics: "queue.SimpleQueue[Dict[str, Any]]"

    def stop(self) -> None:
        self.server.stop()
        self.thread.join(timeout=3.0)


def _start_server(
    *,
    name: str,
    app: Flask,
    host: str,
    port: int,
    server_identity: str,
    server_lt_sk: bytes,
    cert: Optional[Dict[str, Any]],
    pdk_key_id: Optional[str],
) -> ServerHandle:
    metrics_queue: "queue.SimpleQueue[Dict[str, Any]]" = queue.SimpleQueue()
    server = KEMTLSTCPServer(
        app=app,
        server_identity=server_identity,
        server_lt_sk=server_lt_sk,
        cert=cert,
        pdk_key_id=pdk_key_id,
        host=host,
        port=port,
    )
    server.get_collector = KEMTLSHandshakeCollector  # type: ignore[attr-defined]
    server.on_handshake_complete = metrics_queue.put  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.start, name=f"bench-{name}", daemon=True)
    thread.start()
    wait_for_port(host, port)
    return ServerHandle(
        name=name,
        host=host,
        port=port,
        server=server,
        thread=thread,
        handshake_metrics=metrics_queue,
    )


def create_probe_app(name: str) -> Flask:
    app = Flask(name)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "server": name})

    return app


def create_auth_app(
    *,
    keys: Dict[str, Any],
    host: str,
    port: int,
    transport: str = "tcp",
    clients: Optional[Dict[str, Dict[str, Any]]] = None,
    benchmark_token_collector_factory: Optional[Callable[[], Any]] = None,
) -> Flask:
    issuer = f"kemtls://{host}:{port}"
    client_registry = clients or {
        BENCH_CLIENT_ID: {"redirect_uris": [BENCH_REDIRECT_URI]},
    }
    app = create_auth_server_app(
        {
            "issuer": issuer,
            "issuer_public_key": keys["auth_jwt_pk"],
            "issuer_secret_key": keys["auth_jwt_sk"],
            "clients": client_registry,
            "demo_user": "alice",
            "introspection_endpoint": f"{issuer}/introspect",
            "kemtls_modes_supported": ["baseline", "pdk", "auto"],
            "kemtls_transports_supported": [transport],
            "kemtls_default_transport": transport,
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/token",
            "jwks_uri": f"{issuer}/jwks",
        },
        stores={"client_registry": InMemoryClientRegistry(client_registry)},
    )
    if benchmark_token_collector_factory is not None:
        app.extensions["benchmark_token_collector_factory"] = benchmark_token_collector_factory
    return app


def create_resource_app(
    *,
    keys: Dict[str, Any],
    issuer_url: str,
    audience: str = BENCH_CLIENT_ID,
    benchmark_userinfo_collector_factory: Optional[Callable[[], Any]] = None,
) -> Flask:
    stores: Dict[str, Any] = {}
    if benchmark_userinfo_collector_factory is not None:
        stores["benchmark_userinfo_collector_factory"] = benchmark_userinfo_collector_factory
    return create_resource_server_app(
        {
            "issuer": issuer_url,
            "issuer_public_key": keys["auth_jwt_pk"],
            "resource_audience": audience,
        },
        stores=stores,
    )


class BenchmarkStack:
    def __init__(self, *, transport: str = "tcp", host: str = "127.0.0.1"):
        self.transport = transport
        self.host = host
        self.keys = load_keys()
        self._exit_stack = ExitStack()
        self.auth_handle: Optional[ServerHandle] = None
        self.resource_handle: Optional[ServerHandle] = None

    @property
    def auth_url(self) -> str:
        if self.auth_handle is None:
            raise RuntimeError("auth server not started")
        return f"kemtls://{self.auth_handle.host}:{self.auth_handle.port}"

    @property
    def resource_url(self) -> str:
        if self.resource_handle is None:
            raise RuntimeError("resource server not started")
        return f"kemtls://{self.resource_handle.host}:{self.resource_handle.port}"

    def start_probe_server(self) -> ServerHandle:
        port = find_free_port(self.host)
        app = create_probe_app("probe")
        handle = _start_server(
            name="probe",
            app=app,
            host=self.host,
            port=port,
            server_identity="auth-server",
            server_lt_sk=self.keys["auth_sk"],
            cert=self.keys["auth_cert"],
            pdk_key_id=self.keys["auth_pdk_key_id"],
        )
        self._exit_stack.callback(handle.stop)
        return handle

    def start_oidc_servers(self) -> tuple[ServerHandle, ServerHandle]:
        auth_port = find_free_port(self.host)
        issuer_url = f"kemtls://{self.host}:{auth_port}"
        auth_app = create_auth_app(
            keys=self.keys,
            host=self.host,
            port=auth_port,
            transport=self.transport,
            benchmark_token_collector_factory=OIDCTokenCollector,
        )
        resource_port = find_free_port(self.host)
        resource_app = create_resource_app(
            keys=self.keys,
            issuer_url=issuer_url,
            benchmark_userinfo_collector_factory=OIDCUserinfoCollector,
        )

        self.auth_handle = _start_server(
            name="auth",
            app=auth_app,
            host=self.host,
            port=auth_port,
            server_identity="auth-server",
            server_lt_sk=self.keys["auth_sk"],
            cert=self.keys["auth_cert"],
            pdk_key_id=self.keys["auth_pdk_key_id"],
        )
        self._exit_stack.callback(self.auth_handle.stop)

        self.resource_handle = _start_server(
            name="resource",
            app=resource_app,
            host=self.host,
            port=resource_port,
            server_identity="resource-server",
            server_lt_sk=self.keys["resource_sk"],
            cert=self.keys["resource_cert"],
            pdk_key_id=self.keys["resource_pdk_key_id"],
        )
        self._exit_stack.callback(self.resource_handle.stop)
        return self.auth_handle, self.resource_handle

    def close(self) -> None:
        self._exit_stack.close()

    def __enter__(self) -> "BenchmarkStack":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def drain_queue_values(metric_queue: "queue.SimpleQueue[Dict[str, Any]]") -> list[Dict[str, Any]]:
    values: list[Dict[str, Any]] = []
    while True:
        try:
            values.append(metric_queue.get_nowait())
        except queue.Empty:
            return values


def latest_metric(metric_queue: "queue.SimpleQueue[Dict[str, Any]]") -> Optional[Dict[str, Any]]:
    values = drain_queue_values(metric_queue)
    if not values:
        return None
    return values[-1]
