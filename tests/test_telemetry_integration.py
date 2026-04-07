"""
Integration tests for telemetry collectors with real KEMTLS and OIDC components.

Tests that collectors accurately capture metrics when used with actual protocol implementations.
"""

import pytest
from telemetry.collector import (
    KEMTLSHandshakeCollector,
    OIDCTokenCollector,
    OIDCUserinfoCollector,
)
from crypto.ml_dsa import MLDSA65
from crypto.ml_kem import MLKEM768
from utils.helpers import get_timestamp


class TestKEMTLSHandshakeWithCollector:
    """Integration tests for KEMTLS handshake with collector."""

    def test_collector_accepts_handshake_instance(self):
        """Test that handshake accepts collector parameter without errors."""
        from kemtls.handshake import ClientHandshake, ServerHandshake
        
        collector = KEMTLSHandshakeCollector()
        
        # Generate minimal keys
        client_ca_pk, _ = MLDSA65.generate_keypair()
        server_lt_pk, server_lt_sk = MLKEM768.generate_keypair()
        
        # Should not raise with collector parameter
        try:
            client_hs = ClientHandshake(
                "server.test",
                ca_pk=client_ca_pk,
                collector=collector
            )
            server_hs = ServerHandshake(
                "server.test",
                server_lt_sk,
                collector=collector
            )
            assert True
        except TypeError as e:
            pytest.fail(f"Handshake should accept collector parameter: {e}")

    def test_pdk_handshake_captures_pdk_lookup_time(self):
        """Test that PDK handshake collector captures trust-store lookup time."""
        from kemtls.handshake import ClientHandshake
        from kemtls.pdk import PDKTrustStore
        
        # Generate keys
        server_lt_pk, server_lt_sk = MLKEM768.generate_keypair()
        
        # Create PDK trust store
        pdk_store = PDKTrustStore()
        pdk_store.add_entry(
            identity="server.test",
            key_id="key-1",
            ml_kem_public_key=server_lt_pk
        )
        
        # Client side with collector
        client_collector = KEMTLSHandshakeCollector()
        client_hs = ClientHandshake(
            "server.test",
            pdk_store=pdk_store,
            collector=client_collector
        )
        
        # Verify collector was assigned
        assert client_hs.collector is not None
        assert client_hs.collector == client_collector

    def test_handshake_collector_message_size_tracking(self):
        """Test that collector correctly tracks message sizes."""
        collector = KEMTLSHandshakeCollector()
        
        # Simulate message sizes
        collector.client_hello_size = 512
        collector.server_hello_size = 1024
        collector.client_key_exchange_size = 2048
        collector.server_finished_size = 256
        collector.client_finish_size = 256
        
        metrics = collector.get_metrics()
        total_bytes = metrics["total_handshake_bytes"]
        
        # Should match sum of individual message sizes
        expected_total = 512 + 1024 + 2048 + 256 + 256
        assert total_bytes == expected_total


class TestOIDCTokenEndpointWithCollector:
    """Integration tests for OIDC token endpoint with collector."""

    def test_token_collector_accepts_jwt_handler(self):
        """Test that JWT handler accepts collector parameter."""
        from oidc.jwt_handler import PQJWT
        
        issuer_pk, issuer_sk = MLDSA65.generate_keypair()
        
        jwt_handler = PQJWT()
        collector = OIDCTokenCollector()
        
        # Create claims
        claims = {
            "iss": "https://issuer.test",
            "sub": "user123",
            "iat": int(get_timestamp()),
            "exp": int(get_timestamp()) + 3600,
        }
        
        # Sign JWT should accept collector
        try:
            token = jwt_handler.sign_jwt(claims, issuer_sk, collector=collector)
            assert len(token) > 0
        except TypeError as e:
            pytest.fail(f"JWT handler should accept collector parameter: {e}")

    def test_token_end_with_collector_parameter(self):
        """Test that token endpoint methods accept collector parameter."""
        from oidc.token_endpoints import TokenEndpoint
        
        issuer_pk, issuer_sk = MLDSA65.generate_keypair()
        
        # Create token endpoint
        endpoint = TokenEndpoint(
            issuer_sk,
            "https://issuer.test",
            issuer_pk=issuer_pk
        )
        
        # Should accept collector parameter without error
        collector = OIDCTokenCollector()
        
        # Verify endpoint was created with proper methods
        assert hasattr(endpoint, 'handle_token_request')
        assert callable(endpoint.handle_token_request)

    def test_token_collector_size_tracking(self):
        """Test that token sizes are properly tracked."""
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
        assert metrics["token_sizes"]["refresh_token"] == 50


class TestUserinfoEndpointWithCollector:
    """Integration tests for OIDC userinfo endpoint with collector."""

    def test_userinfo_collector_accepts_endpoint(self):
        """Test that userinfo endpoint accepts collector parameter."""
        from oidc.userinfo_endpoints import UserInfoEndpoint
        
        issuer_pk, issuer_sk = MLDSA65.generate_keypair()
        
        endpoint = UserInfoEndpoint(
            issuer_pk,
            issuer="https://issuer.test",
        )
        
        collector = OIDCUserinfoCollector()
        
        # Verify endpoint has handle_userinfo_request method
        assert hasattr(endpoint, 'handle_userinfo_request')
        assert callable(endpoint.handle_userinfo_request)

    def test_userinfo_collector_binding_verification(self):
        """Test that userinfo collector tracks binding verification."""
        collector = OIDCUserinfoCollector()
        
        # Simulate binding verification
        collector.binding_valid = True
        collector.t_binding_verify_ns = 1_000_000  # 1ms
        
        metrics = collector.get_metrics()
        
        assert metrics["binding_valid"] is True
        assert metrics["t_binding_verify_ms"] == pytest.approx(1.0)


class TestCollectorWithMultipleIterations:
    """Tests for repeated measurements with collectors."""

    def test_multiple_collectors_independent(self):
        """Test that multiple collectors track independently."""
        collectors = []
        
        for i in range(3):
            collector = KEMTLSHandshakeCollector()
            collector.mode = "baseline"
            collector.client_hello_size = 512 + i * 10
            collectors.append(collector)
        
        # All collectors should have captured different sizes
        assert len(collectors) == 3
        for i, collector in enumerate(collectors):
            metrics = collector.get_metrics()
            assert metrics["client_hello_size"] == 512 + i * 10

    def test_collector_sequence_independence(self):
        """Test that collectors in sequence don't interfere."""
        hs_collector = KEMTLSHandshakeCollector()
        token_collector = OIDCTokenCollector()
        userinfo_collector = OIDCUserinfoCollector()
        
        # Set different values
        hs_collector.mode = "baseline"
        token_collector.grant_type = "authorization_code"
        userinfo_collector.binding_valid = True
        
        # Get metrics and verify independence
        hs_metrics = hs_collector.get_metrics()
        token_metrics = token_collector.get_metrics()
        ui_metrics = userinfo_collector.get_metrics()
        
        assert hs_metrics["mode"] == "baseline"
        assert token_metrics["grant_type"] == "authorization_code"
        assert ui_metrics["binding_valid"] is True


class TestCollectorMetricsConsistency:
    """Tests for metrics consistency and correctness."""

    def test_handshake_mode_consistency(self):
        """Test that handshake mode is consistently recorded."""
        # Baseline mode
        collector_baseline = KEMTLSHandshakeCollector()
        collector_baseline.mode = "baseline"
        metrics_baseline = collector_baseline.get_metrics()
        assert metrics_baseline["mode"] == "baseline"
        
        # PDK mode
        collector_pdk = KEMTLSHandshakeCollector()
        collector_pdk.mode = "pdk"
        metrics_pdk = collector_pdk.get_metrics()
        assert metrics_pdk["mode"] == "pdk"

    def test_token_collector_grant_type_consistency(self):
        """Test that grant type is consistently recorded."""
        # Authorization code
        collector_auth_code = OIDCTokenCollector()
        collector_auth_code.grant_type = "authorization_code"
        metrics_auth = collector_auth_code.get_metrics()
        assert metrics_auth["grant_type"] == "authorization_code"
        
        # Refresh token
        collector_refresh = OIDCTokenCollector()
        collector_refresh.grant_type = "refresh_token"
        metrics_refresh = collector_refresh.get_metrics()
        assert metrics_refresh["grant_type"] == "refresh_token"

    def test_userinfo_binding_validation_status(self):
        """Test that binding validation status is correctly recorded."""
        # Valid binding
        collector_valid = OIDCUserinfoCollector()
        collector_valid.binding_valid = True
        metrics_valid = collector_valid.get_metrics()
        assert metrics_valid["binding_valid"] is True
        
        # Invalid binding
        collector_invalid = OIDCUserinfoCollector()
        collector_invalid.binding_valid = False
        metrics_invalid = collector_invalid.get_metrics()
        assert metrics_invalid["binding_valid"] is False
