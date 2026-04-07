#!/bin/bash
set -e

echo "======================================"
echo " Starting Research Benchmark Suite"
echo "======================================"

cd "$(dirname "$0")"

# Remove old results
rm -f *.csv *.json
rm -f ../analyze/plots/*.png

echo "[*] Collecting System Snapshot..."
python env_snapshot.py

echo "[*] Running Tier 1 (Crypto)..."
python run_crypto.py

echo "[*] Running Tier 2 (Handshake)..."
python run_handshake.py

echo "[*] Running Tier 3 (OIDC)..."
python run_oidc.py

echo "[*] Running Load Test..."
python run_load.py

echo ""
echo "======================================"
echo " Analyzing Results"
echo "======================================"

cd ../analyze

echo "[*] Calculating Statistics..."
python stats.py

echo "[*] Generating Plots..."
python plots.py

echo ""
echo "======================================"
echo " ALL BENCHMARKS COMPLETED!"
echo " Results available in:"
echo " - benchmarks/collect/*.csv"
echo " - benchmarks/analyze/plots/*.png"
echo "======================================"
