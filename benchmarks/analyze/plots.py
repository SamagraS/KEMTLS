import pandas as pd
import matplotlib.pyplot as plt
import os

def run():
    base = os.path.join(os.path.dirname(__file__), '../collect')
    out_dir = os.path.join(os.path.dirname(__file__), 'plots')
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Handshake Boxplots
    hs_file = os.path.join(base, 'handshake_results.csv')
    if os.path.exists(hs_file):
        df = pd.read_csv(hs_file)
        plt.figure(figsize=(10, 6))
        df.boxplot(column='ttfb_ms', by='scenario', showfliers=False)
        plt.title('Handshake Latency (TTFB) by Scenario (No Outliers)')
        plt.suptitle('')
        plt.ylabel('TTFB (ms)')
        plt.savefig(os.path.join(out_dir, 'handshake_latency_boxplot.png'))
        plt.close()
        
    # 2. Token Size breakdown
    oidc_file = os.path.join(base, 'oidc_results.csv')
    if os.path.exists(oidc_file):
        df = pd.read_csv(oidc_file)
        if not df.empty:
            s_id = df['s_id_token_bytes'].iloc[0]
            s_sig = df['s_id_token_sig'].iloc[0]
            s_payload = s_id - s_sig
            
            plt.figure(figsize=(6, 6))
            plt.bar(['ID Token'], [s_payload], label='Payload + Headers')
            plt.bar(['ID Token'], [s_sig], bottom=[s_payload], label='ML-DSA-65 Signature')
            plt.ylabel('Bytes')
            plt.title('Token Size Breakdown')
            plt.legend()
            plt.savefig(os.path.join(out_dir, 'token_size.png'))
            plt.close()

    # 3. Throughput vs Concurrency
    load_file = os.path.join(base, 'load_results.csv')
    if os.path.exists(load_file):
        df = pd.read_csv(load_file)
        plt.figure(figsize=(10, 6))
        plt.plot(df['concurrency'], df['throughput_req_sec'], marker='o', label='Throughput')
        plt.xlabel('Concurrency (Users)')
        plt.ylabel('Throughput (req/s)')
        plt.title('Throughput vs Concurrency')
        plt.grid(True)
        plt.savefig(os.path.join(out_dir, 'throughput.png'))
        plt.close()
        
        plt.figure(figsize=(10, 6))
        plt.plot(df['concurrency'], df['avg_latency_ms'], marker='s', color='orange')
        plt.xlabel('Concurrency (Users)')
        plt.ylabel('Latency (ms)')
        plt.title('Latency vs Concurrency')
        plt.grid(True)
        plt.savefig(os.path.join(out_dir, 'latency_concurrency.png'))
        plt.close()
            
    print(f"[*] Analysis plots generated in {out_dir}")

if __name__ == "__main__":
    run()
