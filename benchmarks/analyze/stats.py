import pandas as pd
import numpy as np
import os

def bootstrap_ci(data, stat_func=np.mean, n_boot=1000):
    if len(data) == 0:
        return 0, 0
    boot_stats = []
    for _ in range(n_boot):
        sample = np.random.choice(data, size=len(data), replace=True)
        boot_stats.append(stat_func(sample))
    return np.percentile(boot_stats, 2.5), np.percentile(boot_stats, 97.5)

def analyze_crypto(filepath):
    if not os.path.exists(filepath): return
    df = pd.read_csv(filepath)
    print("\n" + "="*40 + "\n--- Crypto Results ---\n" + "="*40)
    for (prim, op), group in df.groupby(['primitive', 'operation']):
        vals = group['latency_us'].values
        m = np.mean(vals)
        median = np.median(vals)
        std = np.std(vals)
        p95 = np.percentile(vals, 95)
        p99 = np.percentile(vals, 99)
        ci_low, ci_high = bootstrap_ci(vals)
        print(f"{prim} {op}:")
        print(f"  Mean: {m:.2f}us, Median: {median:.2f}us, Std: {std:.2f}us")
        print(f"  P95: {p95:.2f}us, P99: {p99:.2f}us")
        print(f"  95% CI (BCa): [{ci_low:.2f}us, {ci_high:.2f}us]")

def analyze_handshake(filepath):
    if not os.path.exists(filepath): return
    df = pd.read_csv(filepath)
    print("\n" + "="*40 + "\n--- Handshake Results ---\n" + "="*40)
    for (proto, scen), group in df.groupby(['protocol', 'scenario']):
        vals = group['ttfb_ms'].values
        ttfb = np.mean(vals)
        median = np.median(vals)
        p95 = np.percentile(vals, 95)
        p99 = np.percentile(vals, 99)
        ci_low, ci_high = bootstrap_ci(vals)
        print(f"{proto} {scen}:")
        print(f"  TTFB Mean: {ttfb:.2f}ms, Median: {median:.2f}ms")
        print(f"  P95: {p95:.2f}ms, P99: {p99:.2f}ms")
        print(f"  95% CI (BCa): [{ci_low:.2f}ms, {ci_high:.2f}ms]")

def analyze_oidc(filepath):
    if not os.path.exists(filepath): return
    df = pd.read_csv(filepath)
    print("\n" + "="*40 + "\n--- OIDC Results ---\n" + "="*40)
    for (proto, scen), group in df.groupby(['protocol', 'scenario']):
        vals = group['t_auth_total_ms'].values
        t_auth = np.mean(vals)
        median = np.median(vals)
        p99 = np.percentile(vals, 99)
        ci_low, ci_high = bootstrap_ci(vals)
        print(f"{proto} {scen}:")
        print(f"  Total Auth Flow Mean: {t_auth:.2f}ms, Median: {median:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  95% CI (BCa): [{ci_low:.2f}ms, {ci_high:.2f}ms]")

def run():
    base = os.path.join(os.path.dirname(__file__), '../collect')
    analyze_crypto(os.path.join(base, 'crypto_results.csv'))
    analyze_handshake(os.path.join(base, 'handshake_results.csv'))
    analyze_oidc(os.path.join(base, 'oidc_results.csv'))

if __name__ == "__main__":
    run()
