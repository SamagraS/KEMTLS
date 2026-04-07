"""Session-bound userinfo handlers for the resource server side."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from flask import g, jsonify, request

from oidc.claims import ClaimsProcessor
from oidc.jwt_handler import PQJWT
from oidc.session_binding import verify_access_token_binding_claim
from utils.telemetry import OIDCUserinfoCollector


class UserInfoEndpoint:
    """Validates access tokens locally and enforces active KEMTLS session binding."""

    def __init__(
        self,
        issuer_pk: bytes,
        *,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        claims_processor: Optional[ClaimsProcessor] = None,
        jwt_handler: Optional[PQJWT] = None,
    ):
        self.issuer_pk = issuer_pk
        self.issuer = issuer
        self.audience = audience
        self.claims_processor = claims_processor or ClaimsProcessor()
        self.jwt_handler = jwt_handler or PQJWT()

    def handle_userinfo_request(
        self,
        access_token: str,
        session=None,
    ) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
        telemetry = OIDCUserinfoCollector()
        telemetry.total_request_timer.start()
        
        if not isinstance(access_token, str) or not access_token:
            telemetry.error_status = "invalid_token"
            telemetry.total_request_timer.stop()
            return {"error": "invalid_token"}, 401, telemetry.get_metrics()
        if session is None:
            telemetry.error_status = "missing_session_context"
            telemetry.total_request_timer.stop()
            return {"error": "missing_session_context"}, 401, telemetry.get_metrics()

        try:
            telemetry.jwt_verification_timer.start()
            claims = self.jwt_handler.validate_access_token(
                access_token,
                self.issuer_pk,
                issuer=self.issuer,
                audience=self.audience,
            )
            telemetry.jwt_verification_timer.stop()
        except Exception:
            telemetry.jwt_verification_timer.stop()
            telemetry.error_status = "invalid_token"
            telemetry.total_request_timer.stop()
            return {"error": "invalid_token"}, 401, telemetry.get_metrics()

        telemetry.session_binding_timer.start()
        valid_binding = verify_access_token_binding_claim(claims, session)
        telemetry.session_binding_timer.stop()
        
        telemetry.binding_validation_success = valid_binding
        if not valid_binding:
            telemetry.error_status = "binding_mismatch"
            telemetry.total_request_timer.stop()
            return {"error": "binding_mismatch"}, 401, telemetry.get_metrics()

        scopes = str(claims.get("scope", "")).split()
        response = self.claims_processor.get_user_claims(str(claims["sub"]), scopes)
        if "email_verified" in claims:
            response["email_verified"] = claims["email_verified"]
            
        telemetry.total_request_timer.stop()
        return response, 200, telemetry.get_metrics()

    def register_routes(self, app, get_session=None) -> None:
        def _resolve_session():
            if callable(get_session):
                return get_session()
            session = request.environ.get("kemtls.session")
            if session is None:
                session = request.environ.get("active_kemtls_session")
            if session is None:
                session = getattr(g, "active_kemtls_session", None)
            return session

        def _extract_bearer_token() -> Optional[str]:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return None
            return auth_header[7:]

        @app.route("/userinfo", methods=["GET"])
        @app.route("/api/userinfo", methods=["GET"])
        def userinfo_route():
            token = _extract_bearer_token()
            if token is None:
                return jsonify({"error": "invalid_token"}), 401

            response, status, telemetry_dict = self.handle_userinfo_request(
                token,
                session=_resolve_session(),
            )
            response["_telemetry"] = telemetry_dict
            return jsonify(response), status


__all__ = ["UserInfoEndpoint"]
