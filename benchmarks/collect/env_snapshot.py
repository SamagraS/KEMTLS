import os
import sys
import platform
import json

def collect_snapshot():
    oqs_version = "Unknown"
    try:
        import oqs
        oqs_version = oqs.oqs_version()
    except Exception:
        pass
    
    data = {
        "os": platform.system(),
        "kernel": platform.release(),
        "python_version": sys.version,
        "liboqs_version": oqs_version,
        "cpu_info": platform.processor(),
        "architecture": platform.machine()
    }
    
    out_path = os.path.join(os.path.dirname(__file__), 'env_snapshot.json')
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[*] Environment snapshot saved to {out_path}")

if __name__ == "__main__":
    collect_snapshot()
