"""Resource server Flask app factory for the updated architecture."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import Flask, g, jsonify, request

from oidc.claims import ClaimsProcessor
from oidc.jwt_handler import PQJWT
from oidc.session_binding import extract_binding_proof_from_headers
from oidc.userinfo_endpoints import UserInfoEndpoint


def create_resource_server_app(
    config: Dict[str, Any],
    stores: Optional[Dict[str, Any]] = None,
) -> Flask:
    stores = stores or {}
    app = Flask(__name__)

    issuer_pk = config["issuer_public_key"]
    userinfo_endpoint = UserInfoEndpoint(
        issuer_pk,
        issuer=config.get("issuer"),
        audience=config.get("resource_audience"),
        claims_processor=stores.get("claims_processor") or ClaimsProcessor(),
        jwt_handler=stores.get("jwt_handler") or PQJWT(),
    )

    app.extensions["userinfo_endpoint"] = userinfo_endpoint

    def _resolve_session():
        session = request.environ.get("kemtls.session")
        if session is None:
            session = request.environ.get("active_kemtls_session")
        if session is None:
            session = getattr(g, "active_kemtls_session", None)
        return session

    benchmark_userinfo_collector_factory = stores.get("benchmark_userinfo_collector_factory")
    if benchmark_userinfo_collector_factory:
        app.extensions["benchmark_userinfo_collector_factory"] = benchmark_userinfo_collector_factory

    def _register_benchmark_route() -> None:
        @app.route("/benchmark/userinfo", methods=["GET"])
        def benchmark_userinfo_route():
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "invalid_token"}), 401
            collector = None
            collector_factory = app.extensions.get("benchmark_userinfo_collector_factory")
            if callable(collector_factory):
                collector = collector_factory()
            response, status = userinfo_endpoint.handle_userinfo_request(
                auth_header[7:],
                session=_resolve_session(),
                binding_proof=extract_binding_proof_from_headers(request.headers),
                method=request.method,
                path=request.path,
                collector=collector,
            )
            payload = dict(response)
            if collector is not None:
                payload["_telemetry"] = collector.get_metrics()
            return jsonify(payload), status

    userinfo_endpoint.register_routes(app, get_session=_resolve_session)
    _register_benchmark_route()
    return app


__all__ = ["create_resource_server_app"]
