"""
Benchmark: Protocol Flow Sizes
Compares KEMTLS vs KEMTLS-PDK vs PQ-TLS handshake sizes.
"""

import os
import sys
import json
from pathlib import Path

def run_benchmark(config: dict):
    print("Computing Protocol Handshake Sizes...")
    
    # We load the raw_kemtls data to get the exact bytes for kemtls and kemtls-pdk
    raw_path = Path('results/raw_kemtls.json')
    if not raw_path.exists():
        print("Required raw_kemtls.json not found. Run bench_kemtls.py first.")
        return
        
    with open(raw_path) as f:
        kemtls_data = json.load(f)
        
    kemtls_runs = kemtls_data['runs']['kemtls']
    pdk_runs = kemtls_data['runs']['kemtls_pdk']
    pqtls_runs = kemtls_data['runs']['pqtls_simulated']
    
    # We just need one sample since sizes are deterministic
    kemtls_size = kemtls_runs[0]['total_bytes']
    pdk_size = pdk_runs[0]['total_bytes']
    pqtls_size = pqtls_runs[0]['total_bytes']

    diff_kemtls = ((pqtls_size - kemtls_size) / pqtls_size) * 100
    diff_pdk = ((pqtls_size - pdk_size) / pqtls_size) * 100

    results = {
        'pqtls_bytes': pqtls_size,
        'kemtls_bytes': kemtls_size,
        'kemtls_pdk_bytes': pdk_size,
        'savings_kemtls_vs_pqtls_percent': round(diff_kemtls, 2),
        'savings_kemtls_pdk_vs_pqtls_percent': round(diff_pdk, 2)
    }

    os.makedirs('results', exist_ok=True)
    with open('results/raw_protocol_sizes.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Saved raw_protocol_sizes.json")

if __name__ == "__main__":
    with open('config.json') as f:
        config = json.load(f)
    run_benchmark(config)
