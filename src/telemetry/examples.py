"""
Example usage of telemetry collectors for KEMTLS handshake and OIDC flows.

This module demonstrates how to instrument code with collectors to gather
timing and size metrics without modifying protocol behavior.
"""

from telemetry.collector import (
    KEMTLSHandshakeCollector,
    OIDCTokenCollector,
    OIDCUserinfoCollector,
    OIDCClientFlowCollector,
)


# ============================================================================
# Example 1: KEMTLS Client Handshake (Baseline Mode)
# ============================================================================
def example_kemtls_client_handshake():
    """
    Demonstrates collecting metrics from a client-side KEMTLS handshake.
    
    Usage:
        from kemtls.handshake import ClientHandshake
        from telemetry.collector import KEMTLSHandshakeCollector
        
        collector = KEMTLSHandshakeCollector()
        
        # Create handshake with collector
        client_handshake = ClientHandshake(
            "client.example.com",
            server_pk,
            ca_pk,
            collector=collector
        )
        
        # Perform handshake
        client_hello = client_handshake.client_hello()
        # ... send and receive messages ...
        session = client_handshake.process_server_finished(server_finished)
        
        # Get metrics
        metrics = collector.get_metrics()
        print(f"Handshake completed in {metrics['hct_ms']:.2f}ms")
        print(f"Total handshake bytes: {metrics['total_handshake_bytes']}")
        print(f"Mode: {metrics['mode']}")
    """
    pass


# ============================================================================
# Example 2: KEMTLS Server Handshake (PDK Mode)
# ============================================================================
def example_kemtls_server_handshake():
    """
    Demonstrates collecting metrics from server-side KEMTLS handshake.
    
    The server typically creates collectors via get_collector() hook:
    
        class MyTCPServer(KEMTLSTCPServer):
            def get_collector(self):
                return KEMTLSHandshakeCollector()
            
            def on_handshake_complete(self, metrics):
                print(f"Server handshake metrics: {metrics}")
    
    The tcp_server module will:
    1. Call collector.start_hct() before handshake
    2. Pass collector to ServerHandshake constructor
    3. ServerHandshake sets message sizes and timings
    4. Call collector.end_hct() after handshake
    5. Call on_handshake_complete(collector.get_metrics())
    """
    pass


# ============================================================================
# Example 3: OIDC Token Endpoint (Authorization Code Grant)
# ============================================================================
def example_oidc_token_endpoint():
    """
    Demonstrates collecting metrics from OIDC token endpoint.
    
    Usage:
        from oidc.token_endpoints import TokenEndpoint
        from telemetry.collector import OIDCTokenCollector
        
        collector = OIDCTokenCollector()
        collector.grant_type = "authorization_code"
        
        token_endpoint = TokenEndpoint(...)
        
        # Make token request - token endpoint will use collector
        result = token_endpoint.handle_token_request(
            grant_type="authorization_code",
            client_id="client-1",
            code="auth_code_xyz",
            code_verifier="verifier_xyz",
            session=active_session,
            collector=collector
        )
        
        if "error" not in result:
            metrics = collector.get_metrics()
            print(f"Token request completed in {metrics['t_token_request_ms']:.2f}ms")
            print(f"ID token size: {metrics['token_sizes']['id_token']} bytes")
            print(f"JWT signing took {metrics['t_jwt_sign_ms']:.2f}ms")
        else:
            collector.error = result.get("error")
    """
    pass


# ============================================================================
# Example 4: OIDC Userinfo Endpoint (Token Validation + Binding Check)
# ============================================================================
def example_oidc_userinfo_endpoint():
    """
    Demonstrates collecting metrics from OIDC userinfo endpoint.
    
    Usage:
        from oidc.userinfo_endpoints import UserInfoEndpoint
        from telemetry.collector import OIDCUserinfoCollector
        
        collector = OIDCUserinfoCollector()
        
        userinfo_endpoint = UserInfoEndpoint(issuer_pk)
        
        # Make userinfo request
        result, status = userinfo_endpoint.handle_userinfo_request(
            access_token="eyJhbGc...",
            session=active_session,
            collector=collector
        )
        
        if status == 200:
            metrics = collector.get_metrics()
            print(f"Userinfo request completed in {metrics['t_userinfo_request_ms']:.2f}ms")
            print(f"JWT verification took {metrics['t_verify_ms']:.2f}ms")
            print(f"Binding validation took {metrics['t_binding_verify_ms']:.2f}ms")
            print(f"Binding valid: {metrics['binding_valid']}")
        else:
            collector.error = result.get("error")
    """
    pass


# ============================================================================
# Example 5: OIDC Client-Side Complete Flow
# ============================================================================
def example_oidc_client_flow():
    """
    Demonstrates collecting metrics for complete OIDC client flow.
    
    Usage:
        from client.oidc_client import OIDCClient
        from telemetry.collector import OIDCClientFlowCollector
        
        collector = OIDCClientFlowCollector()
        collector.start_flow()
        
        client = OIDCClient(http_client, "client-1", "https://auth.example.com", redirect_uri)
        client.scopes = "openid profile email"
        
        try:
            # Step 1: Discovery (timing captured in collector)
            start_discovery = time.perf_counter_ns()
            metadata = client.discover()  # Calls .well-known/openid-configuration
            collector.t_discovery_ns = time.perf_counter_ns() - start_discovery
            
            # Step 2: Start auth (PKCE generation - local, no network)
            start_auth = time.perf_counter_ns()
            auth_url = client.start_auth(scope=client.scopes)
            collector.t_authorize_ns = time.perf_counter_ns() - start_auth
            
            # Step 3: User authorizes and we get code (simulated)
            auth_code = "auth_code_abc"
            
            # Step 4: Exchange code for tokens (network call)
            start_token = time.perf_counter_ns()
            token_result = client.exchange_code(auth_code)
            collector.t_token_exchange_ns = time.perf_counter_ns() - start_token
            collector.t_tls_handshake_ns = token_result.get("tls_handshake_ns", 0)
            collector.access_token_size = len(token_result.get("access_token", ""))
            collector.id_token_size = len(token_result.get("id_token", ""))
            
            # Step 5: Call userinfo (network call)
            start_userinfo = time.perf_counter_ns()
            userinfo = client.call_api("https://auth.example.com/userinfo")
            collector.t_userinfo_ns = time.perf_counter_ns() - start_userinfo
            
            collector.end_flow()
            
            # Print summary
            metrics = collector.get_metrics()
            print(f"Complete OAuth flow took {metrics['t_total_flow_ms']:.2f}ms")
            print(f"  Discovery:     {metrics['t_discovery_ms']:.2f}ms")
            print(f"  Authorization: {metrics['t_authorize_ms']:.2f}ms")
            print(f"  Token exchange: {metrics['t_token_exchange_ms']:.2f}ms")
            print(f"    TLS handshake: {metrics['t_tls_handshake_ms']:.2f}ms")
            print(f"  Userinfo call: {metrics['t_userinfo_ms']:.2f}ms")
            print(f"Tokens: id={metrics['id_token_size']}B, access={metrics['access_token_size']}B")
        
        except Exception as e:
            collector.error = str(e)
            collector.end_flow()
            raise
    """
    pass


# ============================================================================
# Example 6: Aggregating Results for End-to-End Benchmarking
# ============================================================================
def example_aggregating_results():
    """
    Demonstrates how to collect and aggregate metrics from multiple operations.
    
    This is useful for benchmarking scripts:
    
        results = []
        
        for iteration in range(n_iterations):
            # Handshake
            hs_collector = KEMTLSHandshakeCollector()
            session = perform_kemtls_handshake(collector=hs_collector)
            results.append({
                'iteration': iteration,
                'type': 'handshake',
                'metrics': hs_collector.get_metrics()
            })
            
            # Token endpoint
            token_collector = OIDCTokenCollector()
            token_collector.grant_type = "authorization_code"
            tokens = get_tokens(session, collector=token_collector)
            results.append({
                'iteration': iteration,
                'type': 'token',
                'metrics': token_collector.get_metrics()
            })
            
            # Userinfo endpoint
            ui_collector = OIDCUserinfoCollector()
            userinfo = get_userinfo(tokens['access_token'], session, collector=ui_collector)
            results.append({
                'iteration': iteration,
                'type': 'userinfo',
                'metrics': ui_collector.get_metrics()
            })
        
        # Aggregate
        import statistics
        hs_times = [r['metrics']['hct_ms'] for r in results if r['type'] == 'handshake']
        print(f"Handshake - mean: {statistics.mean(hs_times):.2f}ms, "
              f"median: {statistics.median(hs_times):.2f}ms, "
              f"stdev: {statistics.stdev(hs_times):.2f}ms")
    """
    pass


if __name__ == "__main__":
    print(__doc__)
