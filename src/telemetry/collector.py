"""
Structured metric collectors for KEMTLS handshake and OIDC flows.

All collectors use time.perf_counter_ns() for timing and track actual byte sizes.
No protocol behavior is modified; collectors are optional parameters only.
"""

import time
from typing import Any, Dict, Optional


class BaseCollector:
    """Base collector for common timing and size tracking."""

    def __init__(self):
        """Initialize collector with default fields."""
        self.t_total_ns = 0
        self.t_start_ns: Optional[int] = None
        self.t_end_ns: Optional[int] = None

    def start(self):
        """Mark the start of an operation."""
        self.t_start_ns = time.perf_counter_ns()

    def end(self):
        """Mark the end of an operation and compute total time."""
        self.t_end_ns = time.perf_counter_ns()
        if self.t_start_ns is not None:
            self.t_total_ns = self.t_end_ns - self.t_start_ns

    def get_metrics(self) -> Dict[str, Any]:
        """Return metrics as a structured dictionary. Override in subclasses."""
        return {"t_total_ns": self.t_total_ns}


class KEMTLSHandshakeCollector(BaseCollector):
    """Collects metrics for KEMTLS handshake (client and server, baseline and PDK)."""

    def __init__(self):
        """Initialize handshake collector."""
        super().__init__()
        # Message sizes
        self.client_hello_size: int = 0
        self.server_hello_size: int = 0
        self.client_key_exchange_size: int = 0
        self.server_finished_size: int = 0
        self.client_finish_size: int = 0
        
        # Mode and timing
        self.mode: str = "unknown"  # "baseline" or "pdk"
        self.cert_verify_ns: int = 0  # Baseline mode: certificate verification time
        self.pdk_lookup_ns: int = 0  # PDK mode: key store lookup time
        
        # Session
        self.session_id: Optional[str] = None
        self.peer_identity: Optional[str] = None

    def start_hct(self):
        """Start handshake timing (called from server)."""
        self.start()

    def end_hct(self):
        """End handshake timing and compute total (called from server)."""
        self.end()

    def get_metrics(self) -> Dict[str, Any]:
        """Return all handshake metrics as a dict."""
        return {
            "mode": self.mode,
            "hct_total_ns": self.t_total_ns,
            "hct_ms": self.t_total_ns / 1_000_000 if self.t_total_ns > 0 else 0,
            "client_hello_size": self.client_hello_size,
            "server_hello_size": self.server_hello_size,
            "client_key_exchange_size": self.client_key_exchange_size,
            "server_finished_size": self.server_finished_size,
            "client_finish_size": self.client_finish_size,
            "total_handshake_bytes": (
                self.client_hello_size
                + self.server_hello_size
                + self.client_key_exchange_size
                + self.server_finished_size
                + self.client_finish_size
            ),
            "cert_verify_ns": self.cert_verify_ns,
            "cert_verify_ms": self.cert_verify_ns / 1_000_000 if self.cert_verify_ns > 0 else 0,
            "pdk_lookup_ns": self.pdk_lookup_ns,
            "pdk_lookup_ms": self.pdk_lookup_ns / 1_000_000 if self.pdk_lookup_ns > 0 else 0,
            "session_id": self.session_id,
            "peer_identity": self.peer_identity,
        }


class OIDCTokenCollector(BaseCollector):
    """Collects metrics for OIDC token endpoint (authorization code grant and refresh grant)."""

    def __init__(self):
        """Initialize token endpoint collector."""
        super().__init__()
        # Operation timing
        self.t_token_request_ns: int = 0  # Total time for token request
        self.t_jwt_sign_ns: int = 0  # JWT signing time
        self.t_code_validation_ns: int = 0  # Code validation time
        
        # Token sizes (will be tracked by jwt_handler)
        self.token_sizes: Dict[str, int] = {
            "id_token": 0,  # ID token size
            "access_token": 0,  # Access token size
            "refresh_token": 0,  # Refresh token size
            "header": 0,  # JWT header size
            "payload": 0,  # JWT payload size
            "signature": 0,  # JWT signature size
        }
        
        # Grant information
        self.grant_type: str = "unknown"
        self.error: Optional[str] = None

    def start_token_request(self):
        """Start token request timing."""
        self.start()

    def end_token_request(self):
        """End token request timing."""
        self.end()
        self.t_token_request_ns = self.t_total_ns

    def get_metrics(self) -> Dict[str, Any]:
        """Return all token metrics as a dict."""
        return {
            "grant_type": self.grant_type,
            "t_token_request_ns": self.t_token_request_ns,
            "t_token_request_ms": self.t_token_request_ns / 1_000_000
            if self.t_token_request_ns > 0
            else 0,
            "t_jwt_sign_ns": self.t_jwt_sign_ns,
            "t_jwt_sign_ms": self.t_jwt_sign_ns / 1_000_000
            if self.t_jwt_sign_ns > 0
            else 0,
            "t_code_validation_ns": self.t_code_validation_ns,
            "t_code_validation_ms": self.t_code_validation_ns / 1_000_000
            if self.t_code_validation_ns > 0
            else 0,
            "token_sizes": self.token_sizes,
            "error": self.error,
        }


class OIDCUserinfoCollector(BaseCollector):
    """Collects metrics for OIDC userinfo endpoint (JWT verification and binding validation)."""

    def __init__(self):
        """Initialize userinfo endpoint collector."""
        super().__init__()
        # Operation timing
        self.t_userinfo_request_ns: int = 0  # Total time for userinfo request
        self.t_verify_ns: int = 0  # JWT verification time
        self.t_binding_verify_ns: int = 0  # Session binding verification time
        
        # Status
        self.error: Optional[str] = None
        self.binding_valid: bool = False

    def start_userinfo_request(self):
        """Start userinfo request timing."""
        self.start()

    def end_userinfo_request(self):
        """End userinfo request timing."""
        self.end()
        self.t_userinfo_request_ns = self.t_total_ns

    def get_metrics(self) -> Dict[str, Any]:
        """Return all userinfo metrics as a dict."""
        return {
            "t_userinfo_request_ns": self.t_userinfo_request_ns,
            "t_userinfo_request_ms": self.t_userinfo_request_ns / 1_000_000
            if self.t_userinfo_request_ns > 0
            else 0,
            "t_verify_ns": self.t_verify_ns,
            "t_verify_ms": self.t_verify_ns / 1_000_000 if self.t_verify_ns > 0 else 0,
            "t_binding_verify_ns": self.t_binding_verify_ns,
            "t_binding_verify_ms": self.t_binding_verify_ns / 1_000_000
            if self.t_binding_verify_ns > 0
            else 0,
            "binding_valid": self.binding_valid,
            "error": self.error,
        }


class OIDCClientFlowCollector(BaseCollector):
    """Collects metrics for OIDC client-side Authorization Code flow."""

    def __init__(self):
        """Initialize client flow collector."""
        super().__init__()
        # Overall flow timing
        self.t_discovery_ns: int = 0  # Discovery time
        self.t_authorize_ns: int = 0  # Authorization redirect time (no network, just PKCE)
        self.t_token_exchange_ns: int = 0  # Token endpoint roundtrip time
        self.t_userinfo_ns: int = 0  # Userinfo endpoint roundtrip time
        self.t_total_flow_ns: int = 0  # Total flow time
        
        # TLS handshake timing (from KEMTLS handshake)
        self.t_tls_handshake_ns: int = 0
        
        # Token information
        self.id_token_size: int = 0
        self.access_token_size: int = 0
        self.refresh_token_size: int = 0
        
        # Flow state
        self.scopes: str = ""
        self.error: Optional[str] = None

    def start_flow(self):
        """Start overall flow timing."""
        self.start()

    def end_flow(self):
        """End overall flow timing."""
        self.end()
        self.t_total_flow_ns = self.t_total_ns

    def get_metrics(self) -> Dict[str, Any]:
        """Return all client flow metrics as a dict."""
        return {
            "t_discovery_ns": self.t_discovery_ns,
            "t_discovery_ms": self.t_discovery_ns / 1_000_000
            if self.t_discovery_ns > 0
            else 0,
            "t_authorize_ns": self.t_authorize_ns,
            "t_authorize_ms": self.t_authorize_ns / 1_000_000
            if self.t_authorize_ns > 0
            else 0,
            "t_token_exchange_ns": self.t_token_exchange_ns,
            "t_token_exchange_ms": self.t_token_exchange_ns / 1_000_000
            if self.t_token_exchange_ns > 0
            else 0,
            "t_userinfo_ns": self.t_userinfo_ns,
            "t_userinfo_ms": self.t_userinfo_ns / 1_000_000
            if self.t_userinfo_ns > 0
            else 0,
            "t_tls_handshake_ns": self.t_tls_handshake_ns,
            "t_tls_handshake_ms": self.t_tls_handshake_ns / 1_000_000
            if self.t_tls_handshake_ns > 0
            else 0,
            "t_total_flow_ns": self.t_total_flow_ns,
            "t_total_flow_ms": self.t_total_flow_ns / 1_000_000
            if self.t_total_flow_ns > 0
            else 0,
            "id_token_size": self.id_token_size,
            "access_token_size": self.access_token_size,
            "refresh_token_size": self.refresh_token_size,
            "scopes": self.scopes,
            "error": self.error,
        }
