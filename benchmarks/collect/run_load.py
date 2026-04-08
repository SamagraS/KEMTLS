from __future__ import annotations

import argparse
import concurrent.futures
import csv
import statistics
import json
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from client.kemtls_http_client import KEMTLSHttpClient
from client.oidc_client import OIDCClient
from telemetry.collector import KEMTLSHandshakeCollector

from runtime_support import (
    BENCH_CLIENT_ID,
    BENCH_REDIRECT_URI,
    BENCH_SCOPE,
    BenchmarkStack,
)


def _protocol_modes(protocols: Iterable[str]) -> List[str]:
    normalized = {str(item).lower() for item in protocols}
    modes: List[str] = []
    if "kemtls" in normalized or "baseline" in normalized:
        modes.append("baseline")
    if "kemtls_pdk" in normalized or "pdk" in normalized:
        modes.append("pdk")
    return modes or ["baseline", "pdk"]


def _build_http_client(stack: BenchmarkStack, *, expected_identity: str, mode: str, keep_alive: bool) -> KEMTLSHttpClient:
    client = KEMTLSHttpClient(
        ca_pk=stack.keys["ca_pk"],
        pdk_store=stack.keys["pdk_store"],
        expected_identity=expected_identity,
        mode=mode,
        transport="tcp",
        keep_alive=keep_alive,
    )
    client.client.collector = KEMTLSHandshakeCollector()
    return client


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * p)))
    return float(ordered[idx])


def _single_request(mode: str, stack: BenchmarkStack) -> Dict[str, Any]:
    start_ns = time.perf_counter_ns()
    try:
        auth_http = _build_http_client(stack, expected_identity="auth-server", mode=mode, keep_alive=True)
        oidc_client = OIDCClient(
            http_client=auth_http,
            client_id=BENCH_CLIENT_ID,
            issuer_url=stack.auth_url,
            redirect_uri=BENCH_REDIRECT_URI,
        )
        auth_http.get(f"{stack.auth_url}/.well-known/openid-configuration")
        authorize_resp = auth_http.get(oidc_client.start_auth(scope=BENCH_SCOPE))
        code = authorize_resp.get("body", {}).get("code")
        if authorize_resp.get("status") != 200 or not code:
            raise ValueError("authorize_error")
        token_result = oidc_client.exchange_code(code)
        token = token_result.get("access_token")
        if not token:
            raise ValueError("token_error")

        resource_http = _build_http_client(stack, expected_identity="resource-server", mode=mode, keep_alive=False)
        resource_http.set_binding_keypair(*auth_http.get_binding_keypair())
        userinfo_resp = resource_http.get(
            f"{stack.resource_url}/benchmark/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
        if userinfo_resp.get("status") != 200:
            raise ValueError("userinfo_error")

        refreshed = oidc_client.refresh()
        if "access_token" not in refreshed:
            raise ValueError("refresh_error")

        end_ns = time.perf_counter_ns()
        result = {
            "ok": True,
            "latency_ms": (end_ns - start_ns) / 1_000_000,
            "t_auth_total_ms": (end_ns - start_ns) / 1_000_000,
            "t_token_ms": float(token_result.get("_telemetry", {}).get("t_token_request_ms", 0.0)),
            "t_userinfo_ms": float(userinfo_resp.get("body", {}).get("_telemetry", {}).get("t_userinfo_request_ms", 0.0)),
            "t_tls_hs_ms": float(auth_http.client.collector.get_metrics()["hct_ms"]) + float(resource_http.client.collector.get_metrics()["hct_ms"]),
            "error_type": "",
        }
        auth_http.close()
        resource_http.close()
        return result
    except Exception as exc:
        end_ns = time.perf_counter_ns()
        return {
            "ok": False,
            "latency_ms": (end_ns - start_ns) / 1_000_000,
            "t_auth_total_ms": 0.0,
            "t_token_ms": 0.0,
            "t_userinfo_ms": 0.0,
            "t_tls_hs_ms": 0.0,
            "error_type": exc.__class__.__name__,
        }


def _run_level(mode: str, stack: BenchmarkStack, total_requests: int, concurrency: int) -> Dict[str, Any]:
    started = time.perf_counter()
    results: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_single_request, mode, stack) for _ in range(total_requests)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    duration = max(time.perf_counter() - started, 1e-9)

    successes = [entry for entry in results if entry["ok"]]
    failures = [entry for entry in results if not entry["ok"]]
    latencies = [float(entry["latency_ms"]) for entry in successes]
    error_counter = Counter(entry["error_type"] for entry in failures)

    def _mean(field: str) -> float:
        if not successes:
            return 0.0
        return statistics.mean(float(entry[field]) for entry in successes)

    success_count = len(successes)
    failure_count = len(failures)
    error_rate = (failure_count / total_requests) * 100.0 if total_requests else 0.0

    return {
        "mode": mode,
        "concurrency": concurrency,
        "total_requests": total_requests,
        "successes": success_count,
        "failures": failure_count,
        "error_rate_pct": error_rate,
        "throughput_req_sec": total_requests / duration,
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0.0,
        "p50_latency_ms": _percentile(latencies, 0.50),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "p99_latency_ms": _percentile(latencies, 0.99),
        "min_latency_ms": min(latencies) if latencies else 0.0,
        "max_latency_ms": max(latencies) if latencies else 0.0,
        "t_auth_total_ms_avg": _mean("t_auth_total_ms"),
        "t_token_ms_avg": _mean("t_token_ms"),
        "t_userinfo_ms_avg": _mean("t_userinfo_ms"),
        "t_tls_hs_ms_avg": _mean("t_tls_hs_ms"),
        "errors": dict(error_counter),
    }


def run_benchmark(config: Dict[str, Any]) -> Path:
    run_id = str(config.get("run_id") or uuid.uuid4().hex[:8])
    environment_profile = str(config.get("environment_profile", "wsl2_loopback"))
    scenario = str((config.get("scenarios") or ["loopback"])[0])
    repeat = int(config.get("repeat", 1000))
    warmup = int(config.get("warmup", 50))
    protocols = list(config.get("protocols", ["kemtls", "kemtls_pdk"]))
    concurrency_levels = [int(v) for v in config.get("load_concurrency_levels", [1, 5, 10, 25, 50, 100])]
    results_dir = Path(config.get("results_dir", "benchmarks/results"))
    raw_dir = results_dir / "raw" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)

    csv_path = raw_dir / "load_results.csv"
    summary_path = raw_dir / "load_summary.json"

    print("Running load benchmark suite...")
    print(f"[*] run_id={run_id}")
    print(f"[*] environment_profile={environment_profile}")
    print(f"[*] scenario={scenario}")
    print(f"[*] warmup_requests={warmup} measured_requests={repeat}")

    rows: List[Dict[str, Any]] = []
    summaries: Dict[str, Dict[str, Any]] = {}

    with BenchmarkStack(transport="tcp") as stack:
        stack.start_oidc_servers()
        for mode in _protocol_modes(protocols):
            summaries[mode] = {}
            for concurrency in concurrency_levels:
                if warmup > 0:
                    _run_level(mode, stack, warmup, concurrency)
                result = _run_level(mode, stack, repeat, concurrency)
                row = {
                    "run_id": run_id,
                    "protocol": "OIDC_LOAD",
                    "scenario": scenario,
                    "handshake_mode": mode,
                    "concurrency": concurrency,
                    "total_requests": result["total_requests"],
                    "successes": result["successes"],
                    "failures": result["failures"],
                    "error_rate_pct": round(float(result["error_rate_pct"]), 3),
                    "throughput_req_sec": round(float(result["throughput_req_sec"]), 3),
                    "avg_latency_ms": round(float(result["avg_latency_ms"]), 3),
                    "p50_latency_ms": round(float(result["p50_latency_ms"]), 3),
                    "p95_latency_ms": round(float(result["p95_latency_ms"]), 3),
                    "p99_latency_ms": round(float(result["p99_latency_ms"]), 3),
                    "min_latency_ms": round(float(result["min_latency_ms"]), 3),
                    "max_latency_ms": round(float(result["max_latency_ms"]), 3),
                    "t_auth_total_ms_avg": round(float(result["t_auth_total_ms_avg"]), 3),
                    "t_token_ms_avg": round(float(result["t_token_ms_avg"]), 3),
                    "t_userinfo_ms_avg": round(float(result["t_userinfo_ms_avg"]), 3),
                    "t_tls_hs_ms_avg": round(float(result["t_tls_hs_ms_avg"]), 3),
                    "warmup_requests": warmup,
                    "environment_profile": environment_profile,
                }
                rows.append(row)
                summaries[mode][str(concurrency)] = {**row, "errors": result["errors"]}

    with csv_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "run_id",
                "protocol",
                "scenario",
                "handshake_mode",
                "concurrency",
                "total_requests",
                "successes",
                "failures",
                "error_rate_pct",
                "throughput_req_sec",
                "avg_latency_ms",
                "p50_latency_ms",
                "p95_latency_ms",
                "p99_latency_ms",
                "min_latency_ms",
                "max_latency_ms",
                "t_auth_total_ms_avg",
                "t_token_ms_avg",
                "t_userinfo_ms_avg",
                "t_tls_hs_ms_avg",
                "warmup_requests",
                "environment_profile",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"[*] Load benchmarks saved to {csv_path}")
    print(f"[*] Load summary saved to {summary_path}")
    return csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real socket-backed OIDC/KEMTLS load benchmarks")
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
