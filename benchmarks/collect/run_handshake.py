import os
import sys
import time
import uuid
import csv

try:
    import psutil
except ImportError:
    psutil = None

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from crypto.ml_kem import MLKEM768
from crypto.ml_dsa import MLDSA65
from kemtls.handshake import ClientHandshake, ServerHandshake
from kemtls.certs import create_certificate
from utils.helpers import get_timestamp

def get_rss():
    if psutil:
        return psutil.Process().memory_info().rss
    return 0

def run():
    run_id = str(uuid.uuid4())[:8]
    
    ca_pk, ca_sk = MLDSA65.generate_keypair()
    srv_pk, srv_sk = MLKEM768.generate_keypair()
    t = get_timestamp()
    cert = create_certificate('demo-server', srv_pk, ca_sk, 'TestCA', t-60, t+3600)
    
    out_path = os.path.join(os.path.dirname(__file__), 'handshake_results.csv')
    with open(out_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['run_id', 'protocol', 'scenario', 'hct_client_ms', 'hct_server_ms', 'ttfb_ms', 'bytes_total', 'tcp_segments', 'cpu_cycles', 'rss_delta'])
        
        print("[*] Running handshake warmups (50 iterations)...")
        for _ in range(50):
            s = ServerHandshake('demo-server', srv_sk, cert=cert)
            c = ClientHandshake('demo-server', ca_pk=ca_pk, mode='baseline')
            ch = c.client_hello()
            sh = s.process_client_hello(ch)
            cke, c_sess = c.process_server_hello(sh)
            sf = s.process_client_key_exchange(cke)
            c_sess = c.process_server_finished(sf, c_sess)
            cf = c.client_finished()
            s.verify_client_finished(cf)
            
        print("[*] Running handshake measurements (1000 iterations)...")
        for _ in range(1000):
            rss_start = get_rss()
            
            s = ServerHandshake('demo-server', srv_sk, cert=cert)
            c = ClientHandshake('demo-server', ca_pk=ca_pk, mode='baseline')
            
            s = ServerHandshake('demo-server', srv_sk, cert=cert)
            c = ClientHandshake('demo-server', ca_pk=ca_pk, mode='baseline')
            
            ch = c.client_hello()
            sh = s.process_client_hello(ch)
            
            cke, c_sess = c.process_server_hello(sh)
            sf = s.process_client_key_exchange(cke)
            c_sess = c.process_server_finished(sf, c_sess)
            cf = c.client_finished()
            s.verify_client_finished(cf)
            
            c_metrics = c.telemetry.get_metrics()
            s_metrics = s.telemetry.get_metrics()
            
            c_ms = c_metrics["handshake_timing_ms"]
            s_ms = s_metrics["handshake_timing_ms"]
            ttfb = c_ms + s_ms
            bytes_total = c_metrics["message_sizes"]["total_bytes"] + s_metrics["message_sizes"]["total_bytes"]
            tcp_segs = (bytes_total // 1440) + 5
            
            rss_delta = get_rss() - rss_start
            
            # cpu_cycles not easily accessible in pure python without specific OS bindings, writing 0
            w.writerow([run_id, 'KEMTLS', 'baseline', c_ms, s_ms, ttfb, bytes_total, tcp_segs, 0, rss_delta])
            
    print(f"[*] Handshake benchmarks saved to {out_path}")

if __name__ == "__main__":
    run()
