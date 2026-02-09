"""
Demo WebSocket Server
Role: Real-time demo execution with WebSocket streaming

Runs demo_full_flow.py and streams progress to frontend via WebSocket.
Provides real-time phase updates, logs, and completion status.
"""

import os
import sys
import threading
import subprocess
import json
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import time

# Add src to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

app = Flask(__name__)
CORS(app)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25
)

# Import demo functions
sys.path.insert(0, SCRIPT_DIR)

demo_running = False


class EventEmitter:
    """Event emitter for demo progress"""
    
    def __init__(self, socketio_instance):
        self.socketio = socketio_instance
    
    def phase_start(self, phase: int, name: str, details: dict = None):
        """Emit phase start event"""
        self.socketio.emit('phase_start', {
            'phase': phase,
            'name': name,
            'details': details or {},
            'timestamp': time.time()
        })
    
    def phase_complete(self, phase: int, duration: float):
        """Emit phase complete event"""
        self.socketio.emit('phase_complete', {
            'phase': phase,
            'duration': duration,
            'timestamp': time.time()
        })
    
    def log(self, message: str, level: str = 'info'):
        """Emit log message"""
        self.socketio.emit('log', {
            'message': message,
            'level': level,
            'timestamp': time.time()
        })
    
    def error(self, message: str, error: str):
        """Emit error event"""
        self.socketio.emit('error', {
            'message': message,
            'error': str(error),
            'timestamp': time.time()
        })
    
    def complete(self, success: bool, total_time: float, summary: dict):
        """Emit demo complete event"""
        self.socketio.emit('demo_complete', {
            'success': success,
            'total_time': total_time,
            'summary': summary,
            'timestamp': time.time()
        })
    
    def benchmark_start(self):
        """Emit benchmark start event"""
        self.socketio.emit('benchmark_start', {
            'timestamp': time.time()
        })
    
    def benchmark_progress(self, current: int, total: int, operation: str):
        """Emit benchmark progress event"""
        self.socketio.emit('benchmark_progress', {
            'current': current,
            'total': total,
            'operation': operation,
            'timestamp': time.time()
        })
    
    def benchmark_complete(self, results: dict):
        """Emit benchmark complete event with results"""
        self.socketio.emit('benchmark_complete', {
            'results': results,
            'timestamp': time.time()
        })


def run_benchmarks_with_events(emitter: EventEmitter):
    """Run benchmarks and emit results"""
    try:
        emitter.benchmark_start()
        emitter.log("🔬 Running performance benchmarks...", "info")
        
        results_dir = os.path.join(ROOT_DIR, "results_benchmarks")
        protocol_results_file = os.path.join(results_dir, "protocol_benchmark_results.json")
        e2e_results_file = os.path.join(results_dir, "end_to_end_benchmark_results.json")
        
        # Run protocol benchmarks
        emitter.benchmark_progress(1, 2, "Protocol benchmarks")
        try:
            subprocess.run(
                [sys.executable, os.path.join(ROOT_DIR, "benchmarks", "protocol_benchmarks.py"), 
                 "--iterations", "50", "--output", protocol_results_file],
                cwd=ROOT_DIR,
                capture_output=True,
                timeout=60
            )
        except Exception as e:
            emitter.log(f"⚠️ Protocol benchmark warning: {str(e)}", "warning")
        
        time.sleep(0.3)
        
        # Run end-to-end benchmarks
        emitter.benchmark_progress(2, 2, "End-to-end benchmarks")
        try:
            subprocess.run(
                [sys.executable, os.path.join(ROOT_DIR, "benchmarks", "end_to_end_benchmark.py"),
                 "--iterations", "50", "--output", e2e_results_file],
                cwd=ROOT_DIR,
                capture_output=True,
                timeout=60
            )
        except Exception as e:
            emitter.log(f"⚠️ E2E benchmark warning: {str(e)}", "warning")
        
        time.sleep(0.3)
        
        # Read results from JSON files
        results = {}
        
        # Parse protocol benchmarks
        if os.path.exists(protocol_results_file):
            with open(protocol_results_file, 'r') as f:
                protocol_data = json.load(f)
                results['kemtls_handshake'] = protocol_data['kemtls']['operations']['full_handshake']['avg_ms']
                results['token_creation'] = protocol_data['jwt']['operations']['create_token']['avg_ms']
                results['token_verification'] = protocol_data['jwt']['operations']['verify_token']['avg_ms']
                results['pop_proof_creation'] = protocol_data['pop']['operations']['generate_proof']['avg_ms']
                results['pop_verification'] = protocol_data['pop']['operations']['verify_proof']['avg_ms']
        
        # Parse end-to-end benchmarks
        if os.path.exists(e2e_results_file):
            with open(e2e_results_file, 'r') as f:
                e2e_data = json.load(f)
                results['end_to_end'] = e2e_data['statistics']['total']['avg_ms']
        
        # If we got results, emit them
        if results:
            emitter.log("✅ Benchmarks complete!", "success")
            emitter.benchmark_complete(results)
            return results
        else:
            raise Exception("No benchmark results found")
        
    except Exception as e:
        emitter.log(f"⚠️ Benchmark failed: {str(e)}", "warning")
        emitter.log("Continuing with demo using default values...", "info")
        # Return default values if benchmarks fail
        return {
            'kemtls_handshake': 1.5,
            'token_creation': 0.55,
            'token_verification': 0.20,
            'pop_proof_creation': 0.50,
            'pop_verification': 0.15,
            'end_to_end': 3.0
        }


def run_demo_with_events(emitter: EventEmitter):
    """Run demo with event emissions"""
    global demo_running
    
    try:
        demo_running = True
        
        # Run benchmarks first
        benchmark_results = run_benchmarks_with_events(emitter)
        time.sleep(1.0)
        
        start_time = time.time()
        
        # Import demo functions
        from crypto.kyber_kem import KyberKEM
        from crypto.dilithium_sig import DilithiumSignature
        from kemtls.handshake import KEMTLSHandshake
        from client.oidc_client import OIDCClient
        from oidc.jwt_handler import PQJWT
        from pop.client import PoPClient
        from pop.server import ProofOfPossession
        from utils.helpers import get_timestamp
        
        emitter.log("=" * 70, "info")
        emitter.log("POST-QUANTUM OIDC + KEMTLS", "info")
        emitter.log("Complete End-to-End Demonstration", "info")
        emitter.log("=" * 70, "info")
        emitter.log("", "info")
        
        # Verify keys exist
        keys_dir = os.path.join(ROOT_DIR, "keys")
        if not os.path.exists(os.path.join(keys_dir, "auth_server_kyber_pk.bin")):
            emitter.error("Server keys not found", "Please run: python scripts/generate_keys.py")
            return
        
        # Phase 1: KEMTLS Handshake
        phase1_start = time.time()
        emitter.phase_start(1, "KEMTLS Handshake", {
            "protocol": "KEMTLS with Kyber768",
            "security_level": "NIST Level 3"
        })
        
        emitter.log("[1/5] KEMTLS HANDSHAKE", "info")
        emitter.log("Loading server long-term keys...", "info")
        
        with open(os.path.join(keys_dir, "auth_server_kyber_pk.bin"), "rb") as f:
            server_lt_pk = f.read()
        with open(os.path.join(keys_dir, "auth_server_kyber_sk.bin"), "rb") as f:
            server_lt_sk = f.read()
        
        emitter.log(f"✓ Server public key: {len(server_lt_pk)} bytes", "success")
        emitter.log(f"✓ Server secret key: {len(server_lt_sk)} bytes", "success")
        time.sleep(1.0)
        
        emitter.log("Initializing KEMTLS endpoints...", "info")
        client = KEMTLSHandshake(is_server=False)
        server = KEMTLSHandshake(is_server=True)
        emitter.log("✓ Client initialized", "success")
        emitter.log("✓ Server initialized", "success")
        time.sleep(1.0)
        
        emitter.log("[Server → Client] Sending Server Hello...", "info")
        server_hello = server.server_init_handshake(server_lt_sk, server_lt_pk)
        emitter.log(f"✓ Server Hello: {len(server_hello)} bytes", "success")
        time.sleep(1.2)
        
        emitter.log("[Client → Server] Processing Server Hello...", "info")
        client_kex, _ = client.client_process_server_hello(
            server_hello,
            trusted_longterm_pk=server_lt_pk
        )
        emitter.log(f"✓ Client Key Exchange: {len(client_kex)} bytes", "success")
        time.sleep(1.2)
        
        emitter.log("[Server] Processing Client Key Exchange...", "info")
        server_keys = server.server_process_client_key_exchange(client_kex)
        client_keys = client.get_session_keys()
        
        if server_keys == client_keys:
            emitter.log("✅ KEY AGREEMENT SUCCESSFUL", "success")
            emitter.log(f"   Session key: {len(server_keys['session_key'])} bytes", "success")
            emitter.log(f"   Session ID: {server.get_session_id()}", "success")
        else:
            emitter.error("Key agreement failed", "Keys do not match")
            return
        
        emitter.phase_complete(1, time.time() - phase1_start)
        time.sleep(2.0)
        
        # Phase 2: Client Credentials & Authentication
        phase2_start = time.time()
        emitter.phase_start(2, "User Authentication", {
            "protocol": "OpenID Connect",
            "client_id": "demo_client"
        })
        
        emitter.log("[2/5] USER AUTHENTICATION (OIDC)", "info")
        emitter.log("Generating client ephemeral keypair for PoP...", "info")
        sig = DilithiumSignature()
        client_eph_pk, client_eph_sk = sig.generate_keypair()
        emitter.log(f"✓ Public key: {len(client_eph_pk)} bytes", "success")
        emitter.log(f"✓ Secret key: {len(client_eph_sk)} bytes", "success")
        time.sleep(1.0)
        
        emitter.log("Initializing OIDC client...", "info")
        oidc_client = OIDCClient(
            client_id="demo_client",
            redirect_uri="http://localhost:8080/callback",
            auth_server_url="http://localhost:5000",
            client_ephemeral_sk=client_eph_sk
        )
        emitter.log("✓ OIDC client configured", "success")
        time.sleep(1.0)
        
        emitter.log("[Client → Auth Server] Authorization Request...", "info")
        auth_url = oidc_client.create_authorization_url(
            scope="openid profile email",
            nonce="demo_nonce_12345"
        )
        emitter.log("✓ Authorization URL generated", "success")
        time.sleep(1.0)
        
        emitter.log("[User] Login and consent...", "info")
        emitter.log("   👤 Username: alice@example.com", "info")
        emitter.log("   ✓ User grants permissions", "success")
        time.sleep(1.0)
        
        auth_code = "AUTH_CODE_" + "X" * 32
        emitter.log("[Auth Server → Client] Authorization Response...", "success")
        emitter.log(f"✓ Authorization code: {auth_code[:20]}...", "success")
        
        emitter.phase_complete(2, time.time() - phase2_start)
        time.sleep(2.0)
        
        # Phase 3: Token Issuance
        phase3_start = time.time()
        emitter.phase_start(3, "Token Issuance", {
            "algorithm": "ML-DSA-65 (Dilithium3)",
            "token_type": "JWT with PoP binding"
        })
        
        emitter.log("[3/5] TOKEN ISSUANCE", "info")
        emitter.log("[Auth Server] Loading signing keys...", "info")
        
        with open(os.path.join(keys_dir, "auth_server_dilithium_pk.bin"), "rb") as f:
            issuer_pk = f.read()
        with open(os.path.join(keys_dir, "auth_server_dilithium_sk.bin"), "rb") as f:
            issuer_sk = f.read()
        
        emitter.log(f"✓ Dilithium public key: {len(issuer_pk)} bytes", "success")
        emitter.log(f"✓ Dilithium secret key: {len(issuer_sk)} bytes", "success")
        time.sleep(1.0)
        
        emitter.log("[Auth Server] Creating tokens...", "info")
        jwt = PQJWT()
        
        claims = {
            "iss": "http://localhost:5000",
            "sub": "alice@example.com",
            "aud": "demo_client",
            "exp": get_timestamp() + 3600,
            "iat": get_timestamp(),
            "nonce": "demo_nonce_12345",
            "email": "alice@example.com",
            "name": "Alice Smith"
        }
        
        id_token = jwt.create_id_token(
            claims=claims,
            issuer_sk=issuer_sk,
            issuer_pk=issuer_pk,
            client_ephemeral_pk=client_eph_pk,
            session_id="session_" + "Y" * 20
        )
        
        access_token = "ACCESS_TOKEN_" + "Z" * 40
        
        emitter.log(f"✓ ID Token created: {len(id_token)} bytes", "success")
        emitter.log("   - Algorithm: DILITHIUM3", "success")
        emitter.log("   - PoP Binding: Client ephemeral key embedded", "success")
        time.sleep(1.2)
        
        emitter.log(f"✓ Access Token created: {len(access_token)} chars", "success")
        
        emitter.phase_complete(3, time.time() - phase3_start)
        time.sleep(2.0)
        
        # Phase 4: Resource Access
        phase4_start = time.time()
        emitter.phase_start(4, "Resource Access", {
            "resource": "/api/userinfo",
            "pop_method": "Dilithium3 signature"
        })
        
        emitter.log("[4/5] RESOURCE ACCESS (PoP)", "info")
        emitter.log("[Client] Initializing PoP client...", "info")
        pop_client = PoPClient(client_eph_sk)
        emitter.log("✓ PoP client ready", "success")
        time.sleep(1.0)
        
        emitter.log("[Client → Resource Server] GET /api/userinfo...", "info")
        time.sleep(1.0)
        
        emitter.log("[Resource Server → Client] PoP Challenge...", "info")
        pop_server = ProofOfPossession()
        challenge = pop_server.generate_challenge(session_id="session_Y" * 4)
        emitter.log(f"✓ Challenge nonce: {challenge['nonce'][:30]}...", "success")
        time.sleep(1.2)
        
        emitter.log("[Client] Generating PoP proof...", "info")
        proof = pop_client.create_pop_proof(
            challenge=challenge,
            token=access_token
        )
        emitter.log(f"✓ Proof generated: {len(proof)} chars", "success")
        time.sleep(1.2)
        
        emitter.log("[Resource Server] Verifying PoP proof...", "info")
        is_valid = pop_server.verify_pop_response(
            challenge=challenge,
            proof=proof,
            client_eph_pk=client_eph_pk,
            token=access_token
        )
        
        if is_valid:
            emitter.log("✅ PoP VERIFICATION SUCCESSFUL", "success")
            emitter.log("   - Client possesses correct ephemeral key", "success")
            emitter.log("   - Token is valid and not replayed", "success")
            time.sleep(1.2)
            
            emitter.log("[Resource Server → Client] User Info Response...", "success")
            emitter.log('✓ Protected resource accessed:', "success")
            emitter.log('   {"sub": "alice@example.com", "email": "alice@example.com"}', "success")
        else:
            emitter.error("PoP verification failed", "Invalid proof")
            return
        
        emitter.phase_complete(4, time.time() - phase4_start)
        time.sleep(2.0)
        
        # Complete
        total_time = time.time() - start_time
        
        emitter.log("=" * 70, "info")
        emitter.log("✅ DEMONSTRATION COMPLETE", "success")
        emitter.log("", "info")
        emitter.log("Protocol Summary:", "info")
        emitter.log("  1. KEMTLS Handshake      ✓ Kyber768", "success")
        emitter.log("  2. User Authentication   ✓ OIDC Flow", "success")
        emitter.log("  3. Token Issuance        ✓ Dilithium3 JWT", "success")
        emitter.log("  4. Resource Access       ✓ PoP Verified", "success")
        emitter.log("", "info")
        emitter.log("🎉 POST-QUANTUM OIDC + KEMTLS COMPLETE!", "success")
        
        emitter.complete(True, total_time, {
            "phases_completed": 4,
            "security_level": "NIST Level 3",
            "algorithms": ["Kyber768", "ML-DSA-65/Dilithium3"]
        })
        
    except Exception as e:
        emitter.error("Demo execution failed", str(e))
        import traceback
        emitter.log(traceback.format_exc(), "error")
    finally:
        demo_running = False


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connected', {'status': 'ready'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')


@socketio.on('start_demo')
def handle_start_demo():
    """Handle demo start request"""
    global demo_running
    
    if demo_running:
        emit('error', {'message': 'Demo is already running'})
        return
    
    print('Starting demo...')
    emit('demo_started', {'timestamp': time.time()})
    
    # Run demo in background thread
    emitter = EventEmitter(socketio)
    thread = threading.Thread(target=run_demo_with_events, args=(emitter,))
    thread.daemon = True
    thread.start()


@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'demo_running': demo_running}


def main():
    """Start the demo server"""
    print("=" * 60)
    print("KEMTLS Demo WebSocket Server")
    print("=" * 60)
    print("\n✓ WebSocket server starting on http://localhost:5002")
    print("✓ CORS enabled for frontend connections")
    print("\nEndpoints:")
    print("  • WebSocket: ws://localhost:5002")
    print("  • Health:    http://localhost:5002/health")
    print("\nEvents:")
    print("  Client → Server: 'start_demo'")
    print("  Server → Client: 'phase_start', 'phase_complete', 'log', 'demo_complete'")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=5002, 
            debug=False, 
            use_reloader=False,
            log_output=False
        )
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
    except Exception as e:
        print(f"\n✗ Server error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
