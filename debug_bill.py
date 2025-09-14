#!/usr/bin/env python
"""
Debug bill data
"""
import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qb.connector import QBConnector

def debug_bills():
    """Debug Adrian's bills"""
    qb = QBConnector()
    
    if not qb.connected:
        print("[ERROR] QuickBooks not connected")
        return
    
    vendor_name = qb.resolve_vendor("Adrian")
    print(f"Resolved vendor: {vendor_name}")
    
    # Use the bill_repo directly
    bills = qb.bill_repo.find_bills_by_vendor(vendor_name)
    print(f"\nFound {len(bills)} bills")
    
    # Look for the current week's bill
    for bill in bills:
        if 'zp_09/08-09/14/25' in str(bill.get('ref_number', '')):
            print("\n=== CURRENT WEEK BILL FOUND ===")
            print(f"TxnID: {bill.get('txn_id')}")
            print(f"Ref: {bill.get('ref_number')}")
            print(f"Amount Due: ${bill.get('amount_due', 0):.2f}")
            print(f"Balance: ${bill.get('balance', 0):.2f}")
            print(f"Open Amount: ${bill.get('open_amount', 0):.2f}")
            print(f"Is Paid: {bill.get('is_paid')}")
            for key in bill.keys():
                if 'balance' in key.lower() or 'amount' in key.lower() or 'paid' in key.lower():
                    print(f"  {key}: {bill[key]}")
            break
    else:
        print("\nCurrent week bill not found in list")
    
    print("\n=== First 3 bills ===")
    for i, bill in enumerate(bills[:3]):  # Show first 3
        print(f"\n=== Bill #{i+1} ===")
        print(f"TxnID: {bill.get('txn_id')}")
        print(f"Ref: {bill.get('ref_number')}")
        print(f"Amount Due: ${bill.get('amount_due', 0):.2f}")
        print(f"Balance: ${bill.get('balance', 0):.2f}")
        print(f"Open Amount: ${bill.get('open_amount', 0):.2f}")
        print(f"Is Paid: {bill.get('is_paid')}")
        print(f"Payment Status: {bill.get('payment_status')}")
        
        # Check all balance fields
        print(f"All balance fields:")
        for key in bill.keys():
            if 'balance' in key.lower() or 'amount' in key.lower() or 'paid' in key.lower():
                print(f"  {key}: {bill[key]}")

if __name__ == "__main__":
    debug_bills()