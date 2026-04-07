import os
import sys
import time
import uuid
import csv
import hashlib
import concurrent.futures

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from crypto.ml_dsa import MLDSA65
from utils.encoding import base64url_encode
from servers.auth_server_app import create_auth_server_app

def _challenge(verifier: str) -> str:
    return base64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())

def run():
    run_id = str(uuid.uuid4())[:8]
    issuer_public_key, issuer_secret_key = MLDSA65.generate_keypair()
    auth_app = create_auth_server_app({
        "issuer": "https://issuer.example", 
        "issuer_public_key": issuer_public_key, 
        "issuer_secret_key": issuer_secret_key, 
        "clients": {"client123": {"redirect_uris": ["https://client.example/cb"]}}, 
        "demo_user": "alice"
    })
    
    out_path = os.path.join(os.path.dirname(__file__), 'load_results.csv')
    concurrency_levels = [1, 5, 10, 25, 50, 100]
    
    with open(out_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['run_id', 'concurrency', 'throughput_req_sec', 'avg_latency_ms'])
        
        for c in concurrency_levels:
            print(f"[*] Running load test with {c} concurrent users...")
            
            def single_request():
                client = auth_app.test_client()
                verifier = "bench-verifier"
                url = f"/authorize?response_type=code&client_id=client123&redirect_uri=https://client.example/cb&scope=openid profile&state=1&code_challenge={_challenge(verifier)}&code_challenge_method=S256"
                start = time.perf_counter()
                client.get(url)
                return time.perf_counter() - start
                
            tasks = 1000
            if c > 25:
                tasks = 500
                
            latencies = []
            start_total = time.perf_counter()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=c) as executor:
                futures = [executor.submit(single_request) for _ in range(tasks)]
                for future in concurrent.futures.as_completed(futures):
                    latencies.append(future.result())
            
            end_total = time.perf_counter()
            
            duration = end_total - start_total
            throughput = len(latencies) / duration
            avg_lat = (sum(latencies) / len(latencies)) * 1000
            
            w.writerow([run_id, c, throughput, avg_lat])
            print(f"    Throughput: {throughput:.2f} req/s, Avg Latency: {avg_lat:.2f} ms")
            
    print(f"[*] Load test benchmarks saved to {out_path}")

if __name__ == "__main__":
    run()
