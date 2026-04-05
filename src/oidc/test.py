"""Standalone smoke test for the current OIDC package shape."""

from __future__ import annotations

import hashlib
import os
import sys


CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.dirname(CURRENT_DIR)
if sys.path and sys.path[0] == CURRENT_DIR:
    sys.path.pop(0)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from dataclasses import dataclass

from oidc.auth_endpoints import AuthorizationEndpoint, InMemoryClientRegistry
from crypto.ml_dsa import MLDSA65
from oidc.discovery import DiscoveryEndpoint
from oidc.introspection_endpoints import IntrospectionEndpoint
from oidc.jwks import JWKSEndpoint
from oidc.refresh_store import RefreshTokenStore
from oidc.token_endpoints import TokenEndpoint
from oidc.userinfo_endpoints import UserInfoEndpoint
from utils.encoding import base64url_encode


@dataclass
class _Session:
    session_binding_id: bytes
    refresh_binding_id: bytes
    handshake_mode: str = "baseline"


def _pkce_challenge(verifier: str) -> str:
    return base64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_sandbox() -> None:
    print("[sandbox] patching ML-DSA backend")
    from oidc import jwt_handler as jwt_handler_module

    original_sign = jwt_handler_module.MLDSA65.sign
    original_verify = jwt_handler_module.MLDSA65.verify
    jwt_handler_module.MLDSA65.sign = classmethod(
        lambda cls, _sk, message: hashlib.sha256(message).digest()
    )
    jwt_handler_module.MLDSA65.verify = classmethod(
        lambda cls, _pk, message, signature: signature == hashlib.sha256(message).digest()
    )

    try:
        registry = InMemoryClientRegistry(
            {"client123": {"redirect_uris": ["https://client.example/cb"]}}
        )
        auth = AuthorizationEndpoint(client_registry=registry)
        token = TokenEndpoint(
            issuer_url="https://issuer.example",
            issuer_sk=b"issuer-secret-key",
            issuer_pk=b"P" * MLDSA65.PUBLIC_KEY_SIZE,
            authorization_code_store=auth.code_store,
            refresh_token_store=RefreshTokenStore(),
            signing_kid="signing-key-1",
        )
        discovery = DiscoveryEndpoint(
            "https://issuer.example",
            introspection_endpoint="https://issuer.example/introspect",
        )
        jwks = JWKSEndpoint({"signing-key-1": b"P" * MLDSA65.PUBLIC_KEY_SIZE})
        introspection = IntrospectionEndpoint(
            b"P" * MLDSA65.PUBLIC_KEY_SIZE,
            issuer="https://issuer.example",
            audience="client123",
        )
        userinfo = UserInfoEndpoint(
            b"P" * MLDSA65.PUBLIC_KEY_SIZE,
            issuer="https://issuer.example",
            audience="client123",
        )

        verifier = "sandbox-verifier"
        session = _Session(b"a" * 32, b"b" * 32)

        print("[authorization] issuing code")
        auth_result = auth.handle_authorize_request(
            client_id="client123",
            redirect_uri="https://client.example/cb",
            scope="openid profile email",
            state="state123",
            nonce="nonce123",
            user_id="alice",
            code_challenge=_pkce_challenge(verifier),
        )
        _assert("code" in auth_result, "authorization code missing")

        print("[token] issuing tokens")
        token_response = token.handle_token_request(
            grant_type="authorization_code",
            client_id="client123",
            redirect_uri="https://client.example/cb",
            code=auth_result["code"],
            code_verifier=verifier,
            session=session,
        )
        _assert("access_token" in token_response, "access_token missing")
        _assert("id_token" in token_response, "id_token missing")
        _assert("refresh_token" in token_response, "refresh_token missing")

        print("[discovery] checking metadata")
        metadata = discovery.get_configuration()
        _assert(metadata["issuer"] == "https://issuer.example", "issuer mismatch")
        _assert(metadata["jwks_uri"].endswith("/jwks"), "jwks_uri missing")

        print("[jwks] checking published key")
        jwks_doc = jwks.get_jwks()
        _assert(any(key["kid"] == "signing-key-1" for key in jwks_doc["keys"]), "kid missing from jwks")

        print("[userinfo] validating same-session access")
        userinfo_payload, userinfo_status = userinfo.handle_userinfo_request(
            token_response["access_token"],
            session=session,
        )
        _assert(userinfo_status == 200, "userinfo should succeed on same session")
        _assert(userinfo_payload["sub"] == "alice", "userinfo sub mismatch")

        print("[introspection] validating replay rejection on different session")
        introspection_payload = introspection.introspect(
            token_response["access_token"],
            session=_Session(b"z" * 32, b"b" * 32, "pdk"),
        )
        _assert(introspection_payload["active"] is False, "replayed token should be inactive")
        _assert(introspection_payload["binding_status"] is False, "binding_status should be false")

        print("[refresh] rotating refresh token")
        refreshed = token.handle_token_request(
            grant_type="refresh_token",
            client_id="client123",
            refresh_token=token_response["refresh_token"],
            session=session,
        )
        _assert("refresh_token" in refreshed, "refresh rotation failed")

        print("OIDC sandbox checks passed")
    finally:
        jwt_handler_module.MLDSA65.sign = original_sign
        jwt_handler_module.MLDSA65.verify = original_verify


if __name__ == "__main__":
    run_sandbox()
