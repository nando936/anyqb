#!/usr/bin/env python
"""
Direct QB bill retrieval script
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qb.connector import QBConnector

def get_bill(vendor_name):
    """Get bill for specified vendor"""
    qb = QBConnector()
    
    if not qb.connected:
        print("[ERROR] QuickBooks not connected")
        return
    
    result = qb.execute_command("GET_WORK_BILL", {"vendor_name": vendor_name})
    
    if result['success']:
        print(result['output'])
    else:
        print(f"[ERROR] {result.get('error', 'Failed to get bill')}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        vendor = sys.argv[1]
        get_bill(vendor)
    else:
        print("Usage: python get_bill.py <vendor_name>")