"""
Test suite for telemetry collectors.

Tests basic initialization, metric capture, and output formats for all collector types.
"""

import time
import pytest
from telemetry.collector import (
    BaseCollector,
    KEMTLSHandshakeCollector,
    OIDCTokenCollector,
    OIDCUserinfoCollector,
    OIDCClientFlowCollector,
)


class TestBaseCollector:
    """Tests for BaseCollector base class."""

    def test_base_collector_initialization(self):
        """Test that BaseCollector initializes with default values."""
        collector = BaseCollector()
        assert collector.t_total_ns == 0
        assert collector.t_start_ns is None
        assert collector.t_end_ns is None

    def test_base_collector_timing(self):
        """Test that BaseCollector accurately measures elapsed time."""
        collector = BaseCollector()
        collector.start()
        assert collector.t_start_ns is not None
        
        time.sleep(0.01)  # 10ms
        collector.end()
        
        assert collector.t_end_ns is not None
        assert collector.t_total_ns > 9_000_000  # > 9ms in nanoseconds
        assert collector.t_total_ns < 50_000_000  # < 50ms (some overhead)

    def test_base_collector_get_metrics(self):
        """Test that get_metrics returns expected structure."""
        collector = BaseCollector()
        metrics = collector.get_metrics()
        
        assert isinstance(metrics, dict)
        assert "t_total_ns" in metrics
        assert metrics["t_total_ns"] == 0


class TestKEMTLSHandshakeCollector:
    """Tests for KEMTLSHandshakeCollector."""

    def test_kemtls_handshake_collector_initialization(self):
        """Test KEMTLSHandshakeCollector initializes with correct defaults."""
        collector = KEMTLSHandshakeCollector()
        
        assert collector.client_hello_size == 0
        assert collector.server_hello_size == 0
        assert collector.client_key_exchange_size == 0
        assert collector.server_finished_size == 0
        assert collector.client_finish_size == 0
        assert collector.mode == "unknown"
        assert collector.cert_verify_ns == 0
        assert collector.pdk_lookup_ns == 0

    def test_kemtls_handshake_collector_timing(self):
        """Test handshake timing capture."""
        collector = KEMTLSHandshakeCollector()
        
        collector.start_hct()
        time.sleep(0.01)  # 10ms
        collector.end_hct()
        
        assert collector.t_total_ns > 9_000_000

    def test_kemtls_handshake_collector_message_sizes(self):
        """Test message size tracking."""
        collector = KEMTLSHandshakeCollector()
        
        collector.client_hello_size = 512
        collector.server_hello_size = 1024
        collector.client_key_exchange_size = 2048
        collector.server_finished_size = 256
        collector.client_finish_size = 256
        
        metrics = collector.get_metrics()
        
        assert metrics["client_hello_size"] == 512
        assert metrics["server_hello_size"] == 1024
        assert metrics["total_handshake_bytes"] == 512 + 1024 + 2048 + 256 + 256

    def test_kemtls_handshake_collector_baseline_mode(self):
        """Test baseline mode metric capture."""
        collector = KEMTLSHandshakeCollector()
        collector.mode = "baseline"
        collector.cert_verify_ns = 5_000_000  # 5ms
        
        metrics = collector.get_metrics()
        
        assert metrics["mode"] == "baseline"
        assert metrics["cert_verify_ms"] == pytest.approx(5.0)

    def test_kemtls_handshake_collector_pdk_mode(self):
        """Test PDK mode metric capture."""
        collector = KEMTLSHandshakeCollector()
        collector.mode = "pdk"
        collector.pdk_lookup_ns = 2_000_000  # 2ms
        
        metrics = collector.get_metrics()
        
        assert metrics["mode"] == "pdk"
        assert metrics["pdk_lookup_ms"] == pytest.approx(2.0)

    def test_kemtls_handshake_collector_get_metrics_format(self):
        """Test that get_metrics returns all required fields."""
        collector = KEMTLSHandshakeCollector()
        collector.mode = "baseline"
        collector.client_hello_size = 100
        collector.server_hello_size = 200
        
        metrics = collector.get_metrics()
        
        required_fields = [
            "mode", "hct_total_ns", "hct_ms",
            "client_hello_size", "server_hello_size",
            "total_handshake_bytes"
        ]
        for field in required_fields:
            assert field in metrics


class TestOIDCTokenCollector:
    """Tests for OIDCTokenCollector."""

    def test_oidc_token_collector_initialization(self):
        """Test OIDCTokenCollector initializes with correct defaults."""
        collector = OIDCTokenCollector()
        
        assert collector.t_token_request_ns == 0
        assert collector.t_jwt_sign_ns == 0
        assert collector.t_code_validation_ns == 0
        assert collector.grant_type == "unknown"
        assert collector.error is None
        assert isinstance(collector.token_sizes, dict)
        assert collector.token_sizes["id_token"] == 0
        assert collector.token_sizes["access_token"] == 0

    def test_oidc_token_collector_timing(self):
        """Test token request timing capture."""
        collector = OIDCTokenCollector()
        
        collector.start_token_request()
        time.sleep(0.01)  # 10ms
        collector.end_token_request()
        
        assert collector.t_token_request_ns > 9_000_000

    def test_oidc_token_collector_jwt_signing(self):
        """Test JWT signing timing accumulation."""
        collector = OIDCTokenCollector()
        
        collector.t_jwt_sign_ns = 3_000_000  # 3ms
        
        metrics = collector.get_metrics()
        
        assert metrics["t_jwt_sign_ms"] == pytest.approx(3.0)

    def test_oidc_token_collector_token_sizes(self):
        """Test token size tracking."""
        collector = OIDCTokenCollector()
        
        collector.token_sizes = {
            "id_token": 1200,
            "access_token": 800,
            "refresh_token": 50,
            "header": 100,
            "payload": 900,
            "signature": 200,
        }
        
        metrics = collector.get_metrics()
        
        assert metrics["token_sizes"]["id_token"] == 1200
        assert metrics["token_sizes"]["access_token"] == 800

    def test_oidc_token_collector_grant_type(self):
        """Test grant type tracking."""
        collector = OIDCTokenCollector()
        collector.grant_type = "authorization_code"
        
        metrics = collector.get_metrics()
        
        assert metrics["grant_type"] == "authorization_code"

    def test_oidc_token_collector_error_capture(self):
        """Test error status capture."""
        collector = OIDCTokenCollector()
        collector.error = "invalid_grant"
        
        metrics = collector.get_metrics()
        
        assert metrics["error"] == "invalid_grant"

    def test_oidc_token_collector_get_metrics_format(self):
        """Test that get_metrics returns all required fields."""
        collector = OIDCTokenCollector()
        
        metrics = collector.get_metrics()
        
        required_fields = [
            "grant_type", "t_token_request_ns", "t_token_request_ms",
            "t_jwt_sign_ns", "t_jwt_sign_ms",
            "token_sizes", "error"
        ]
        for field in required_fields:
            assert field in metrics


class TestOIDCUserinfoCollector:
    """Tests for OIDCUserinfoCollector."""

    def test_oidc_userinfo_collector_initialization(self):
        """Test OIDCUserinfoCollector initializes with correct defaults."""
        collector = OIDCUserinfoCollector()
        
        assert collector.t_userinfo_request_ns == 0
        assert collector.t_verify_ns == 0
        assert collector.t_binding_verify_ns == 0
        assert collector.error is None
        assert collector.binding_valid is False

    def test_oidc_userinfo_collector_timing(self):
        """Test userinfo request timing capture."""
        collector = OIDCUserinfoCollector()
        
        collector.start_userinfo_request()
        time.sleep(0.01)  # 10ms
        collector.end_userinfo_request()
        
        assert collector.t_userinfo_request_ns > 9_000_000

    def test_oidc_userinfo_collector_verification_timing(self):
        """Test verification timing tracking."""
        collector = OIDCUserinfoCollector()
        
        collector.t_verify_ns = 2_000_000  # 2ms
        collector.t_binding_verify_ns = 1_000_000  # 1ms
        
        metrics = collector.get_metrics()
        
        assert metrics["t_verify_ms"] == pytest.approx(2.0)
        assert metrics["t_binding_verify_ms"] == pytest.approx(1.0)

    def test_oidc_userinfo_collector_binding_status(self):
        """Test binding verification status."""
        collector = OIDCUserinfoCollector()
        collector.binding_valid = True
        
        metrics = collector.get_metrics()
        
        assert metrics["binding_valid"] is True

    def test_oidc_userinfo_collector_error_capture(self):
        """Test error status capture."""
        collector = OIDCUserinfoCollector()
        collector.error = "binding_mismatch"
        
        metrics = collector.get_metrics()
        
        assert metrics["error"] == "binding_mismatch"

    def test_oidc_userinfo_collector_get_metrics_format(self):
        """Test that get_metrics returns all required fields."""
        collector = OIDCUserinfoCollector()
        
        metrics = collector.get_metrics()
        
        required_fields = [
            "t_userinfo_request_ns", "t_userinfo_request_ms",
            "t_verify_ns", "t_verify_ms",
            "t_binding_verify_ns", "t_binding_verify_ms",
            "binding_valid", "error"
        ]
        for field in required_fields:
            assert field in metrics


class TestOIDCClientFlowCollector:
    """Tests for OIDCClientFlowCollector."""

    def test_oidc_client_flow_collector_initialization(self):
        """Test OIDCClientFlowCollector initializes with correct defaults."""
        collector = OIDCClientFlowCollector()
        
        assert collector.t_discovery_ns == 0
        assert collector.t_authorize_ns == 0
        assert collector.t_token_exchange_ns == 0
        assert collector.t_userinfo_ns == 0
        assert collector.t_total_flow_ns == 0
        assert collector.t_tls_handshake_ns == 0
        assert collector.error is None

    def test_oidc_client_flow_collector_full_timing(self):
        """Test complete flow timing capture."""
        collector = OIDCClientFlowCollector()
        
        collector.start_flow()
        time.sleep(0.05)  # 50ms
        collector.end_flow()
        
        assert collector.t_total_flow_ns > 49_000_000

    def test_oidc_client_flow_collector_step_timings(self):
        """Test individual step timing tracking."""
        collector = OIDCClientFlowCollector()
        
        collector.t_discovery_ns = 10_000_000  # 10ms
        collector.t_authorize_ns = 5_000_000  # 5ms
        collector.t_token_exchange_ns = 50_000_000  # 50ms
        collector.t_userinfo_ns = 20_000_000  # 20ms
        
        metrics = collector.get_metrics()
        
        assert metrics["t_discovery_ms"] == pytest.approx(10.0)
        assert metrics["t_authorize_ms"] == pytest.approx(5.0)
        assert metrics["t_token_exchange_ms"] == pytest.approx(50.0)
        assert metrics["t_userinfo_ms"] == pytest.approx(20.0)

    def test_oidc_client_flow_collector_tls_timing(self):
        """Test TLS handshake timing capture."""
        collector = OIDCClientFlowCollector()
        
        collector.t_tls_handshake_ns = 15_000_000  # 15ms
        
        metrics = collector.get_metrics()
        
        assert metrics["t_tls_handshake_ms"] == pytest.approx(15.0)

    def test_oidc_client_flow_collector_token_sizes(self):
        """Test token size tracking."""
        collector = OIDCClientFlowCollector()
        
        collector.id_token_size = 1200
        collector.access_token_size = 800
        collector.refresh_token_size = 50
        
        metrics = collector.get_metrics()
        
        assert metrics["id_token_size"] == 1200
        assert metrics["access_token_size"] == 800
        assert metrics["refresh_token_size"] == 50

    def test_oidc_client_flow_collector_scopes(self):
        """Test scope tracking."""
        collector = OIDCClientFlowCollector()
        collector.scopes = "openid profile email"
        
        metrics = collector.get_metrics()
        
        assert metrics["scopes"] == "openid profile email"

    def test_oidc_client_flow_collector_error_capture(self):
        """Test error status capture."""
        collector = OIDCClientFlowCollector()
        collector.error = "token_expired"
        
        metrics = collector.get_metrics()
        
        assert metrics["error"] == "token_expired"

    def test_oidc_client_flow_collector_get_metrics_format(self):
        """Test that get_metrics returns all required fields."""
        collector = OIDCClientFlowCollector()
        
        metrics = collector.get_metrics()
        
        required_fields = [
            "t_discovery_ns", "t_discovery_ms",
            "t_authorize_ns", "t_authorize_ms",
            "t_token_exchange_ns", "t_token_exchange_ms",
            "t_userinfo_ns", "t_userinfo_ms",
            "t_tls_handshake_ns", "t_tls_handshake_ms",
            "t_total_flow_ns", "t_total_flow_ms",
            "id_token_size", "access_token_size", "refresh_token_size",
            "scopes", "error"
        ]
        for field in required_fields:
            assert field in metrics


class TestCollectorPrecision:
    """Tests for timing precision and units."""

    def test_nanosecond_precision(self):
        """Test that nanosecond timing is accurate."""
        collector = BaseCollector()
        
        collector.start()
        time.sleep(0.001)  # 1ms
        collector.end()
        
        # Should be approximately 1ms (1_000_000 ns)
        assert 900_000 < collector.t_total_ns < 5_000_000

    def test_millisecond_conversion(self):
        """Test that ns to ms conversion is correct."""
        collector = KEMTLSHandshakeCollector()
        
        collector.t_total_ns = 5_000_000  # 5ms in ns
        metrics = collector.get_metrics()
        
        assert metrics["hct_ms"] == pytest.approx(5.0)

    def test_zero_timing_handling(self):
        """Test that zero timing doesn't cause errors."""
        collector = OIDCTokenCollector()
        
        # Don't set any timing, leave as 0
        metrics = collector.get_metrics()
        
        assert metrics["t_token_request_ms"] == 0
        assert metrics["t_jwt_sign_ms"] == 0


class TestCollectorIntegration:
    """Tests for multiple collectors used together."""

    def test_multiple_collectors_independent(self):
        """Test that multiple collectors don't interfere with each other."""
        collector1 = KEMTLSHandshakeCollector()
        collector2 = OIDCTokenCollector()
        
        collector1.mode = "baseline"
        collector2.grant_type = "authorization_code"
        
        metrics1 = collector1.get_metrics()
        metrics2 = collector2.get_metrics()
        
        assert metrics1["mode"] == "baseline"
        assert metrics2["grant_type"] == "authorization_code"

    def test_collector_sequence(self):
        """Test sequential use of collectors."""
        collectors = [
            KEMTLSHandshakeCollector(),
            OIDCTokenCollector(),
            OIDCUserinfoCollector(),
        ]
        
        collectors[0].mode = "baseline"
        collectors[1].grant_type = "authorization_code"
        collectors[2].binding_valid = True
        
        metrics = [c.get_metrics() for c in collectors]
        
        assert metrics[0]["mode"] == "baseline"
        assert metrics[1]["grant_type"] == "authorization_code"
        assert metrics[2]["binding_valid"] is True
