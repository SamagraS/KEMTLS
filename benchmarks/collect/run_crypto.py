import os
import sys
import time
import uuid
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from crypto.ml_kem import MLKEM768
from crypto.ml_dsa import MLDSA65
from crypto.aead import seal, open_

def measure(fn, *args):
    start = time.perf_counter_ns()
    res = fn(*args)
    return (time.perf_counter_ns() - start) / 1000.0, res # us

def run():
    run_id = str(uuid.uuid4())[:8]
    
    out_path = os.path.join(os.path.dirname(__file__), 'crypto_results.csv')
    with open(out_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['run_id', 'primitive', 'operation', 'latency_us'])
        
        print("[*] Running crypto warmups (50 iterations)...")
        # Warmup
        for _ in range(50):
            pk_k, sk_k = MLKEM768.generate_keypair()
            ct, ss = MLKEM768.encapsulate(pk_k)
            MLKEM768.decapsulate(sk_k, ct)
            pk_s, sk_s = MLDSA65.generate_keypair()
            MLDSA65.verify(pk_s, b'msg', MLDSA65.sign(sk_s, b'msg'))
        
        print("[*] Running crypto measurements (1000 iterations)...")
        
        # ML-KEM-768
        for _ in range(1000):
            lat, (pk_k, sk_k) = measure(MLKEM768.generate_keypair)
            w.writerow([run_id, 'ML-KEM-768', 'keygen', lat])
            lat, (ct, ss) = measure(MLKEM768.encapsulate, pk_k)
            w.writerow([run_id, 'ML-KEM-768', 'encap', lat])
            lat, _ = measure(MLKEM768.decapsulate, sk_k, ct)
            w.writerow([run_id, 'ML-KEM-768', 'decap', lat])
            
        # ML-DSA-65
        for _ in range(1000):
            lat, (pk_s, sk_s) = measure(MLDSA65.generate_keypair)
            w.writerow([run_id, 'ML-DSA-65', 'keygen', lat])
            msg = b'test message payload'
            lat, sig = measure(MLDSA65.sign, sk_s, msg)
            w.writerow([run_id, 'ML-DSA-65', 'sign', lat])
            lat, _ = measure(MLDSA65.verify, pk_s, msg, sig)
            w.writerow([run_id, 'ML-DSA-65', 'verify', lat])
            
        # ChaCha20-Poly1305
        for _ in range(1000):
            key, nonce, ad, pt = os.urandom(32), os.urandom(12), b'aad', b'plaintext'*64
            lat, ct2 = measure(seal, key, nonce, pt, ad)
            w.writerow([run_id, 'ChaCha20-Poly1305', 'seal_1k', lat])
            lat, _ = measure(open_, key, nonce, ct2, ad)
            w.writerow([run_id, 'ChaCha20-Poly1305', 'open_1k', lat])
            
    print(f"[*] Crypto benchmarks saved to {out_path}")

if __name__ == "__main__":
    run()
