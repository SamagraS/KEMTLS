"""
Aggregate Benchmark Results

Computes avg, median, and p95 for all numeric data found in raw results.
"""

import os
import json
import statistics
from pathlib import Path

def percentiles(data, p):
    if not data:
        return 0
    data = sorted(data)
    k = (len(data) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(data):
        return data[-1]
    if f == c:
        return data[f]
    d0 = data[f] * (c - k)
    d1 = data[c] * (k - f)
    return d0 + d1

def compute_stats(arr):
    if not arr:
        return {}
    return {
        'avg': sum(arr) / len(arr),
        'median': statistics.median(arr),
        'p95': percentiles(arr, 95)
    }


def trim_authorization_warmup(samples):
    """Drop the first authorization sample when multiple runs are present.

    The first auth run is typically a cold-start outlier because it includes
    initial imports, Rust backend loading, socket setup, and server warm-up.
    """
    if len(samples) <= 1:
        return samples
    return samples[1:]

def main():
    results_dir = Path('results')
    if not results_dir.exists():
        print("No results directory found.")
        return

    aggregated = {}

    # 1. Process KEMTLS Handshake
    raw_kemtls = results_dir / 'raw_kemtls.json'
    if raw_kemtls.exists():
        with open(raw_kemtls) as f:
            data = json.load(f)
            
        aggregated['kemtls_handshake'] = {
            'component_times': data.get('component_times_s', {}),
            'modes': {}
        }
        
        for mode, runs in data.get('runs', {}).items():
            latencies = [r['latency_s'] for r in runs]
            aggregated['kemtls_handshake']['modes'][mode] = {
                'latency_s': compute_stats(latencies),
                'total_bytes': runs[0]['total_bytes'] if runs else 0
            }

    # 2. Process OIDC Flow
    raw_flow = results_dir / 'raw_oidc_flow.json'
    if raw_flow.exists():
        with open(raw_flow) as f:
            data = json.load(f)
            
        aggregated['oidc_flow_s'] = {}
        
        for mode, runs in data.items():
            authorize_samples = trim_authorization_warmup([r['authorize_s'] for r in runs])
            aggregated['oidc_flow_s'][mode] = {
                'authorize': compute_stats(authorize_samples),
                'token': compute_stats([r['token_s'] for r in runs]),
                'resource': compute_stats([r['resource_s'] for r in runs]),
                'refresh': compute_stats([r['refresh_s'] for r in runs]),
                'total_login': compute_stats([r['total_login_s'] for r in runs]),
                'authorize_warmup_trimmed': len(runs) - len(authorize_samples),
            }

    # 3. Process Crypto Timings
    raw_crypto = results_dir / 'raw_token_crypto.json'
    if raw_crypto.exists():
        with open(raw_crypto) as f:
            data = json.load(f)
            
        aggregated['crypto_timings_s'] = {
            'id_token_signing': compute_stats(data.get('id_token_signing_s', [])),
            'jwt_verification': compute_stats(data.get('jwt_verification_s', [])),
            'jwks_generation': compute_stats(data.get('jwks_generation_s', []))
        }

    # 4. Sizes (Static values)
    raw_sizes = results_dir / 'raw_sizes.json'
    if raw_sizes.exists():
        with open(raw_sizes) as f:
            aggregated['sizes_bytes'] = json.load(f)

    raw_protocol_sizes = results_dir / 'raw_protocol_sizes.json'
    if raw_protocol_sizes.exists():
        with open(raw_protocol_sizes) as f:
            aggregated['protocol_sizes'] = json.load(f)

    # Output aggregated results
    with open(results_dir / 'aggregated_results.json', 'w') as f:
        json.dump(aggregated, f, indent=2)
    print("Saved aggregated_results.json")

if __name__ == "__main__":
    main()
