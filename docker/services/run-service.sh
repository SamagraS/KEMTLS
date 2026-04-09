#!/bin/sh
set -eu

name="${SERVICE_NAME:-unknown}"
role="${SERVICE_ROLE:-unspecified role}"
desc="${SERVICE_DESC:-no description provided}"

echo "============================================================"
echo "All docker services running"
echo "service: ${name}"
echo "role: ${role}"
echo "details: ${desc}"
echo "status: RUNNING"
echo ""
echo "============================================================"

count=0
while true; do
  count=$((count + 1))
  echo "[${name}] heartbeat ${count}: container alive"
  sleep 30
done
