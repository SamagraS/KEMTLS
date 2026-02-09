"""
Quick Start - Demo with Frontend
Role: Easy launcher for demo + frontend

Starts both demo server and frontend in one command.
"""

import os
import sys
import subprocess
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def print_banner():
    print("=" * 60)
    print("KEMTLS + OIDC Demo Launcher")
    print("=" * 60)
    print()

def check_keys():
    """Check if keys exist"""
    keys_dir = os.path.join(ROOT_DIR, "keys")
    kyber_pk = os.path.join(keys_dir, "auth_server_kyber_pk.bin")
    
    if not os.path.exists(kyber_pk):
        print("❌ Keys not found!")
        print("   Run: python scripts/generate_keys.py")
        print()
        sys.exit(1)
    
    print("✓ Keys found")

def check_frontend():
    """Check if frontend is set up"""
    frontend_dir = os.path.join(ROOT_DIR, "frontend")
    node_modules = os.path.join(frontend_dir, "node_modules")
    
    if not os.path.exists(node_modules):
        print("❌ Frontend dependencies not installed!")
        print("   Run: cd frontend && npm install")
        print()
        sys.exit(1)
    
    print("✓ Frontend dependencies installed")

def main():
    print_banner()
    
    print("1. Checking prerequisites...")
    check_keys()
    check_frontend()
    print()
    
    print("2. Starting services...")
    print()
    
    # Start demo server
    print("Starting Demo WebSocket Server (Port 5002)...")
    demo_server_script = os.path.join(ROOT_DIR, "scripts", "demo_server.py")
    
    print("✓ Demo server starting in background")
    print()
    
    print("=" * 60)
    print("SERVICES READY")
    print("=" * 60)
    print()
    print("Demo Server:  http://localhost:5002")
    print("               ws://localhost:5002")
    print()
    print("To start frontend:")
    print("  cd frontend")
    print("  npm run dev")
    print()
    print("Then open: http://localhost:5173/")
    print()
    print("=" * 60)
    print()
    print("Starting demo server now...")
    print("(Press Ctrl+C to stop)")
    print()
    
    # Run demo server
    subprocess.run([sys.executable, demo_server_script])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped")
        sys.exit(0)
