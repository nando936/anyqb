#!/usr/bin/env python
"""
AnyQB Startup Script
Quick start for the AnyQB mobile web application
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the AnyQB server"""
    print("[OK] Starting AnyQB Server...")
    print("=" * 50)
    
    # Check for .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("[WARNING] No .env file found")
        print("[INFO] Creating .env from template...")
        
        env_example = Path(".env.example")
        if env_example.exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("[OK] Created .env file")
            print("[ACTION] Please edit .env and add your ANTHROPIC_API_KEY")
            print("")
            input("Press Enter after updating .env file...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("[ERROR] Python 3.8+ is required")
        sys.exit(1)
    
    print(f"[OK] Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Install dependencies if needed
    try:
        import fastapi
        import uvicorn
        import requests
        print("[OK] Dependencies installed")
    except ImportError:
        print("[INFO] Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("[OK] Dependencies installed")
    
    # Start the server
    print("")
    print("=" * 50)
    print("[OK] Starting FastAPI server...")
    print("[INFO] Server will be available at:")
    print("       http://localhost:8000")
    print("       http://127.0.0.1:8000")
    print("")
    print("[INFO] Mobile access (same network):")
    print("       http://[your-ip]:8000")
    print("")
    print("[INFO] Press Ctrl+C to stop the server")
    print("=" * 50)
    print("")
    
    # Run the server
    os.chdir(Path(__file__).parent)
    subprocess.run([sys.executable, "src/api/server.py"])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[OK] Server stopped")