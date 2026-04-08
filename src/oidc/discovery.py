"""OIDC discovery metadata for the updated architecture."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from crypto.ml_dsa import MLDSA65


class DiscoveryEndpoint:
    def __init__(
        self,
        issuer_url: str,
        *,
        authorization_endpoint: Optional[str] = None,
        token_endpoint: Optional[str] = None,
        userinfo_endpoint: Optional[str] = None,
        jwks_uri: Optional[str] = None,
        introspection_endpoint: Optional[str] = None,
        kemtls_modes_supported: Optional[Iterable[str]] = None,
        kemtls_transports_supported: Optional[Iterable[str]] = None,
        kemtls_default_transport: str = "tcp",
        kemtls_session_binding_supported: bool = True,
        scopes_supported: Optional[Iterable[str]] = None,
    ):
        self.issuer_url = issuer_url.rstrip("/")
        self.authorization_endpoint = authorization_endpoint or f"{self.issuer_url}/authorize"
        self.token_endpoint = token_endpoint or f"{self.issuer_url}/token"
        self.userinfo_endpoint = userinfo_endpoint or f"{self.issuer_url}/userinfo"
        self.jwks_uri = jwks_uri or f"{self.issuer_url}/jwks"
        self.introspection_endpoint = introspection_endpoint
        self.kemtls_modes_supported = list(kemtls_modes_supported or ("baseline", "pdk", "auto"))
        self.kemtls_transports_supported = list(kemtls_transports_supported or ("tcp", "quic"))
        self.kemtls_default_transport = kemtls_default_transport
        self.kemtls_session_binding_supported = bool(kemtls_session_binding_supported)
        self.scopes_supported = list(scopes_supported or ("openid", "profile", "email"))

    def get_configuration(self) -> Dict[str, Any]:
        metadata = {
            "issuer": self.issuer_url,
            "authorization_endpoint": self.authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "userinfo_endpoint": self.userinfo_endpoint,
            "jwks_uri": self.jwks_uri,
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "subject_types_supported": ["public"],
            "scopes_supported": self.scopes_supported,
            "claims_supported": ["sub", "name", "email", "email_verified"],
            "id_token_signing_alg_values_supported": [MLDSA65.ALGORITHM],
            "token_endpoint_auth_methods_supported": ["none"],
            "kemtls_supported": True,
            "kemtls_session_binding_supported": self.kemtls_session_binding_supported,
            "kemtls_modes_supported": self.kemtls_modes_supported,
            "kemtls_transports_supported": self.kemtls_transports_supported,
            "kemtls_default_transport": self.kemtls_default_transport,
        }
        if self.introspection_endpoint:
            metadata["introspection_endpoint"] = self.introspection_endpoint
        return metadata


__all__ = ["DiscoveryEndpoint"]
