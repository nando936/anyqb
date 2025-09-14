#!/usr/bin/env python
"""
Test QuickBooks Connector
Verify QB integration is working
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qb.connector import QBConnector

def test_qb_connection():
    """Test basic QB functionality"""
    print("\n=== Testing QuickBooks Connector ===\n")
    
    # Initialize connector
    qb = QBConnector()
    
    if not qb.connected:
        print("[ERROR] QuickBooks not connected")
        print("[INFO] This is normal if QB is not installed")
        print("[INFO] The app will work with simulated data")
        return
    
    print("[OK] QuickBooks connected successfully\n")
    
    # Test commands
    tests = [
        ("SEARCH_VENDORS", {"search_term": "martinez"}),
        ("GET_WORK_WEEK_SUMMARY", {}),
        ("SEARCH_CUSTOMERS", {"active_only": True}),
    ]
    
    for command, params in tests:
        print(f"Testing: {command}")
        result = qb.execute_command(command, params)
        
        if result['success']:
            print("[OK] Command executed")
            # Show first 200 chars of output
            output = result['output'][:200]
            if len(result['output']) > 200:
                output += "..."
            print(f"Output: {output}\n")
        else:
            print(f"[ERROR] {result['error']}\n")

if __name__ == "__main__":
    test_qb_connection()