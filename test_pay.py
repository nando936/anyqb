#!/usr/bin/env python
"""
Test bill payment functionality
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qb.connector import QBConnector

def test_payment():
    """Test paying Adrian's bill"""
    qb = QBConnector()
    
    if not qb.connected:
        print("[ERROR] QuickBooks not connected")
        return
    
    # First check the bill
    print("\n=== Checking Adrian's Bill ===")
    bill_result = qb.execute_command("GET_WORK_BILL", {"vendor_name": "Adrian"})
    if bill_result['success']:
        print(bill_result['output'])
    
    # Now try to pay it
    print("\n=== Attempting Payment ===")
    payment_result = qb.execute_command("PAY_BILLS", {
        "vendor_name": "Adrian",
        "amount": 1000,
        "bank_account": "1887 b",
        "check_number": "DEBIT-" + str(Path(__file__).parent).split('\\')[-1]
    })
    
    print(payment_result.get('output', payment_result.get('error')))

if __name__ == "__main__":
    test_payment()