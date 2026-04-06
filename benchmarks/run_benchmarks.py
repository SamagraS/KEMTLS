"""
Benchmark Orchestrator

Runs all benchmark scripts sequentially and generates aggregated stats.
"""

import os
import subprocess
import json
import sys
from pathlib import Path

def main():
    benchmarks_dir = Path(__file__).parent
    python_executable = sys.executable
    
    # 1. Load Config
    config_path = benchmarks_dir / 'config.json'
    if not config_path.exists():
        print("config.json missing!")
        return
        
    with open(config_path) as f:
        config = json.load(f)
        
    print(f"Starting Benchmarking Suite ({config['runs']} runs per mode)")
    print("=" * 50)
    
    scripts = [
        "bench_kemtls.py",
        "bench_oidc_flow.py",
        "bench_token_crypto.py",
        "bench_token_sizes.py",
        "bench_protocol_sizes.py", # Needs raw_kemtls.json
        "aggregate_results.py"     # Runs last
    ]
    
    # Ensure keys are bootstrapped
    keys_dir = benchmarks_dir.parent / 'keys'
    if not keys_dir.exists():
        print("Bootstrapping CA and keys...")
        subprocess.run([python_executable, str(benchmarks_dir.parent / "scripts" / "bootstrap_ca.py")], check=True)
    
    for script_name in scripts:
        script_path = benchmarks_dir / script_name
        print(f"\n--- Running {script_name} ---")
        try:
            # We run as a separate process to start fresh and avoid module leaks
            subprocess.run([python_executable, str(script_path)], check=True, cwd=str(benchmarks_dir))
        except subprocess.CalledProcessError as e:
            print(f"Error executing {script_name}: {e}")
            break
            
    print("\n" + "=" * 50)
    print("Benchmarking Complete.")
    print("Results are available in benchmarks/results/aggregated_results.json")

if __name__ == "__main__":
    main()
