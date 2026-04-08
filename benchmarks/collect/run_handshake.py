from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from kemtls.client import KEMTLSClient
from telemetry.collector import KEMTLSHandshakeCollector

from runtime_support import BenchmarkStack, latest_metric


def _stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    return {
        "avg": statistics.mean(values),
        "median": statistics.median(values),
        "p95": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))],
    }


def _protocol_modes(protocols: Iterable[str]) -> List[str]:
    normalized = {str(item).lower() for item in protocols}
    modes: List[str] = []
    if "kemtls" in normalized or "baseline" in normalized:
        modes.append("baseline")
    if "kemtls_pdk" in normalized or "pdk" in normalized:
        modes.append("pdk")
    return modes or ["baseline", "pdk"]


def _run_handshake(
    *,
    mode: str,
    stack: BenchmarkStack,
    port: int,
    server_metrics_queue,
) -> Dict[str, Any]:
    collector = KEMTLSHandshakeCollector()
    client = KEMTLSClient(
        expected_identity="auth-server",
        ca_pk=stack.keys["ca_pk"],
        pdk_store=stack.keys["pdk_store"],
        mode=mode,
        collector=collector,
        transport="tcp",
    )
    start_ns = time.perf_counter_ns()
    response, session = client.request(
        host=stack.host,
        port=port,
        method="GET",
        path="/health",
        headers={"Accept": "application/json"},
    )
    total_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
    client.close()

    server_metrics = None
    deadline = time.time() + 1.0
    while server_metrics is None and time.time() < deadline:
        server_metrics = latest_metric(server_metrics_queue)
        if server_metrics is None:
            time.sleep(0.01)

    client_metrics = collector.get_metrics()
    return {
        "mode": session.handshake_mode,
        "hct_client_ms": float(client_metrics["hct_ms"]),
        "hct_server_ms": float((server_metrics or {}).get("hct_ms", 0.0)),
        "ttfb_ms": total_ms,
        "bytes_client_hello": int(client_metrics["client_hello_size"]),
        "bytes_server_hello": int(client_metrics["server_hello_size"]),
        "bytes_client_key_exchange": int(client_metrics["client_key_exchange_size"]),
        "bytes_server_finished": int(client_metrics["server_finished_size"]),
        "bytes_client_finished": int(client_metrics["client_finished_size"]),
        "bytes_total": int(client_metrics["total_handshake_bytes"]),
        "tcp_segments": max(1, (int(client_metrics["total_handshake_bytes"]) + 1439) // 1440),
        "cert_verify_ms": float(client_metrics["cert_verify_ms"]),
        "pdk_lookup_ms": float(client_metrics["pdk_lookup_ms"]),
        "cpu_cycles": 0,
        "rss_delta": int((server_metrics or {}).get("rss_delta", 0)),
        "response_bytes": len(response),
    }


def run_benchmark(config: Dict[str, Any]) -> Path:
    run_id = str(config.get("run_id") or uuid.uuid4().hex[:8])
    environment_profile = str(config.get("environment_profile", "wsl2_loopback"))
    scenario = str((config.get("scenarios") or ["loopback"])[0])
    warmup = int(config.get("warmup", 50))
    repeat = int(config.get("repeat", 1000))
    protocols = list(config.get("protocols", ["kemtls", "kemtls_pdk"]))
    results_dir = Path(config.get("results_dir", "benchmarks/results"))
    raw_dir = results_dir / "raw" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)

    csv_path = raw_dir / "handshake_results.csv"
    summary_path = raw_dir / "handshake_summary.json"

    print("Running handshake benchmark suite...")
    print(f"[*] run_id={run_id}")
    print(f"[*] environment_profile={environment_profile}")
    print(f"[*] scenario={scenario}")
    print(f"[*] warmup={warmup} repeat={repeat}")

    rows: List[Dict[str, Any]] = []
    summaries: Dict[str, Dict[str, Any]] = {}

    with BenchmarkStack(transport="tcp") as stack:
        probe_handle = stack.start_probe_server()
        modes = _protocol_modes(protocols)

        for mode in modes:
            for _ in range(warmup):
                _run_handshake(
                    mode=mode,
                    stack=stack,
                    port=probe_handle.port,
                    server_metrics_queue=probe_handle.handshake_metrics,
                )

            hct_client_values: List[float] = []
            hct_server_values: List[float] = []
            ttfb_values: List[float] = []
            total_bytes_values: List[float] = []

            for iteration in range(repeat):
                result = _run_handshake(
                    mode=mode,
                    stack=stack,
                    port=probe_handle.port,
                    server_metrics_queue=probe_handle.handshake_metrics,
                )
                hct_client_values.append(float(result["hct_client_ms"]))
                hct_server_values.append(float(result["hct_server_ms"]))
                ttfb_values.append(float(result["ttfb_ms"]))
                total_bytes_values.append(float(result["bytes_total"]))
                rows.append(
                    {
                        "run_id": run_id,
                        "protocol": "KEMTLS",
                        "scenario": scenario,
                        "handshake_mode": mode,
                        "hct_client_ms": round(float(result["hct_client_ms"]), 3),
                        "hct_server_ms": round(float(result["hct_server_ms"]), 3),
                        "ttfb_ms": round(float(result["ttfb_ms"]), 3),
                        "bytes_client_hello": int(result["bytes_client_hello"]),
                        "bytes_server_hello": int(result["bytes_server_hello"]),
                        "bytes_client_key_exchange": int(result["bytes_client_key_exchange"]),
                        "bytes_server_finished": int(result["bytes_server_finished"]),
                        "bytes_client_finished": int(result["bytes_client_finished"]),
                        "bytes_total": int(result["bytes_total"]),
                        "tcp_segments": int(result["tcp_segments"]),
                        "cert_verify_ms": round(float(result["cert_verify_ms"]), 3),
                        "pdk_lookup_ms": round(float(result["pdk_lookup_ms"]), 3),
                        "cpu_cycles": int(result["cpu_cycles"]),
                        "rss_delta": int(result["rss_delta"]),
                        "iteration": iteration,
                        "environment_profile": environment_profile,
                    }
                )

            summaries[mode] = {
                "hct_client": _stats(hct_client_values),
                "hct_server": _stats(hct_server_values),
                "ttfb": _stats(ttfb_values),
                "bytes_total": _stats(total_bytes_values),
            }

    with csv_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "run_id",
                "protocol",
                "scenario",
                "handshake_mode",
                "hct_client_ms",
                "hct_server_ms",
                "ttfb_ms",
                "bytes_client_hello",
                "bytes_server_hello",
                "bytes_client_key_exchange",
                "bytes_server_finished",
                "bytes_client_finished",
                "bytes_total",
                "tcp_segments",
                "cert_verify_ms",
                "pdk_lookup_ms",
                "cpu_cycles",
                "rss_delta",
                "iteration",
                "environment_profile",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"[*] Handshake benchmarks saved to {csv_path}")
    print(f"[*] Handshake summary saved to {summary_path}")
    return csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real socket-backed handshake benchmarks")
    parser.add_argument("--config", default="../config.json")
    parser.add_argument("--results-dir", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--repeat", type=int, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--environment-profile", default=None)
    args = parser.parse_args()

    config_path = (SCRIPT_DIR / args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    if args.results_dir is not None:
        config["results_dir"] = args.results_dir
    if args.run_id is not None:
        config["run_id"] = args.run_id
    if args.repeat is not None:
        config["repeat"] = args.repeat
    if args.warmup is not None:
        config["warmup"] = args.warmup
    if args.environment_profile is not None:
        config["environment_profile"] = args.environment_profile

    run_benchmark(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBenchmark stopped")
