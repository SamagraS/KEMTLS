import time
from typing import Dict, Any, Optional

class TelemetryTimer:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_ns = 0

    def start(self):
        self.start_time = time.perf_counter_ns()

    def stop(self):
        if self.start_time is not None:
            self.total_ns += (time.perf_counter_ns() - self.start_time)
            self.start_time = None

    @property
    def ms(self) -> float:
        return self.total_ns / 1_000_000.0

class KEMTLSHandshakeCollector:
    def __init__(self):
        self.handshake_timer = TelemetryTimer()
        self.cert_verification_timer = TelemetryTimer()
        self.pdk_lookup_timer = TelemetryTimer()
        self.message_sizes = {
            "ClientHello": 0,
            "ServerHello": 0,
            "ClientKeyExchange": 0,
            "ServerFinished": 0,
            "ClientFinished": 0,
            "total_bytes": 0
        }
        self.mode = "unknown"
        self.session_id = None
        self.peer_identity = None

    def record_message_size(self, msg_type: str, size: int):
        self.message_sizes[msg_type] = size
        self.message_sizes["total_bytes"] += size

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "handshake_timing_ns": self.handshake_timer.total_ns,
            "handshake_timing_ms": self.handshake_timer.ms,
            "message_sizes": self.message_sizes,
            "mode": self.mode,
            "cert_verification_timing_ns": self.cert_verification_timer.total_ns,
            "cert_verification_timing_ms": self.cert_verification_timer.ms,
            "pdk_lookup_timing_ns": self.pdk_lookup_timer.total_ns,
            "pdk_lookup_timing_ms": self.pdk_lookup_timer.ms,
            "session_id": self.session_id,
            "peer_identity": self.peer_identity
        }

class OIDCTokenCollector:
    def __init__(self):
        self.total_request_timer = TelemetryTimer()
        self.jwt_signing_timer = TelemetryTimer()
        self.code_validation_timer = TelemetryTimer()
        self.token_sizes = {
            "id_token": 0,
            "access_token": 0,
            "refresh_token": 0,
            "header": 0,
            "payload": 0,
            "signature": 0
        }
        self.grant_type = None
        self.error_status = None

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_request_timing_ns": self.total_request_timer.total_ns,
            "total_request_timing_ms": self.total_request_timer.ms,
            "jwt_signing_timing_ns": self.jwt_signing_timer.total_ns,
            "jwt_signing_timing_ms": self.jwt_signing_timer.ms,
            "code_validation_timing_ns": self.code_validation_timer.total_ns,
            "code_validation_timing_ms": self.code_validation_timer.ms,
            "token_sizes": self.token_sizes,
            "grant_type": self.grant_type,
            "error_status": self.error_status
        }

class OIDCUserinfoCollector:
    def __init__(self):
        self.total_request_timer = TelemetryTimer()
        self.jwt_verification_timer = TelemetryTimer()
        self.session_binding_timer = TelemetryTimer()
        self.binding_validation_success = False
        self.error_status = None

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_request_timing_ns": self.total_request_timer.total_ns,
            "total_request_timing_ms": self.total_request_timer.ms,
            "jwt_verification_timing_ns": self.jwt_verification_timer.total_ns,
            "jwt_verification_timing_ms": self.jwt_verification_timer.ms,
            "session_binding_timing_ns": self.session_binding_timer.total_ns,
            "session_binding_timing_ms": self.session_binding_timer.ms,
            "binding_validation_success": self.binding_validation_success,
            "error_status": self.error_status
        }

class OIDCClientFlowCollector:
    def __init__(self):
        self.discovery_timer = TelemetryTimer()
        self.authorization_timer = TelemetryTimer()
        self.token_exchange_timer = TelemetryTimer()
        self.userinfo_timer = TelemetryTimer()
        self.tls_handshake_timer = TelemetryTimer()
        self.total_flow_timer = TelemetryTimer()
        self.token_sizes = {
            "id_token": 0,
            "access_token": 0,
            "refresh_token": 0
        }
        self.scopes_requested = []
        self.error_status = None

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "discovery_timing_ns": self.discovery_timer.total_ns,
            "discovery_timing_ms": self.discovery_timer.ms,
            "authorization_timing_ns": self.authorization_timer.total_ns,
            "authorization_timing_ms": self.authorization_timer.ms,
            "token_exchange_timing_ns": self.token_exchange_timer.total_ns,
            "token_exchange_timing_ms": self.token_exchange_timer.ms,
            "userinfo_timing_ns": self.userinfo_timer.total_ns,
            "userinfo_timing_ms": self.userinfo_timer.ms,
            "tls_handshake_timing_ns": self.tls_handshake_timer.total_ns,
            "tls_handshake_timing_ms": self.tls_handshake_timer.ms,
            "total_flow_timing_ns": self.total_flow_timer.total_ns,
            "total_flow_timing_ms": self.total_flow_timer.ms,
            "token_sizes": self.token_sizes,
            "scopes_requested": self.scopes_requested,
            "error_status": self.error_status
        }
