"""
Check Demo Setup Status
Role: Verify all prerequisites for demo

Checks:
- Keys exist
- Python dependencies
- Frontend dependencies
- Port availability
"""

import os
import sys
import subprocess
import socket

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def check_symbol(status):
    return "✓" if status else "❌"

def check_keys():
    """Check if keys are generated"""
    keys_dir = os.path.join(ROOT_DIR, "keys")
    kyber_pk = os.path.join(keys_dir, "auth_server_kyber_pk.bin")
    kyber_sk = os.path.join(keys_dir, "auth_server_kyber_sk.bin")
    dilithium_pk = os.path.join(keys_dir, "auth_server_dilithium_pk.bin")
    dilithium_sk = os.path.join(keys_dir, "auth_server_dilithium_sk.bin")
    
    all_exist = all(os.path.exists(f) for f in [kyber_pk, kyber_sk, dilithium_pk, dilithium_sk])
    
    print(f"{check_symbol(all_exist)} Keys generated")
    if not all_exist:
        print("   Fix: python scripts/generate_keys.py")
    
    return all_exist

def check_python_deps():
    """Check if Python dependencies are installed"""
    try:
        import flask
        import flask_socketio
        import flask_cors
        has_deps = True
    except ImportError:
        has_deps = False
    
    print(f"{check_symbol(has_deps)} Python dependencies")
    if not has_deps:
        print("   Fix: pip install -r requirements.txt")
    
    return has_deps

def check_frontend_deps():
    """Check if frontend dependencies are installed"""
    frontend_dir = os.path.join(ROOT_DIR, "frontend")
    node_modules = os.path.join(frontend_dir, "node_modules")
    
    exists = os.path.exists(node_modules)
    
    print(f"{check_symbol(exists)} Frontend dependencies")
    if not exists:
        print("   Fix: cd frontend && npm install")
    
    return exists

def check_port(port, name):
    """Check if port is available"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    is_available = result != 0
    
    if is_available:
        print(f"✓ Port {port} available ({name})")
    else:
        print(f"⚠️  Port {port} in use ({name})")
        print(f"   Note: This is OK if {name} is running")
    
    return is_available

def main():
    print("=" * 60)
    print("KEMTLS Demo - Setup Status Check")
    print("=" * 60)
    print()
    
    print("Prerequisites:")
    print("-" * 60)
    
    keys_ok = check_keys()
    python_deps_ok = check_python_deps()
    frontend_deps_ok = check_frontend_deps()
    
    print()
    print("Ports:")
    print("-" * 60)
    
    port_5002 = check_port(5002, "Demo WebSocket Server")
    port_5173 = check_port(5173, "Frontend Dev Server")
    
    print()
    print("=" * 60)
    
    all_ok = keys_ok and python_deps_ok and frontend_deps_ok
    
    if all_ok:
        print("✅ ALL PREREQUISITES MET")
        print()
        print("Ready to run demo!")
        print()
        print("Next steps:")
        print("  1. python scripts/demo_server.py")
        print("  2. cd frontend && npm run dev")
        print("  3. Open http://localhost:5173/")
    else:
        print("⚠️  PREREQUISITES MISSING")
        print()
        print("Fix the issues above, then re-run this script.")
    
    print("=" * 60)
    print()
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
