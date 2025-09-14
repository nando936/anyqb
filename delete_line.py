#!/usr/bin/env python
"""
Delete a line item from a vendor's bill
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qb.connector import QBConnector

def delete_line_item(vendor_name, day_to_remove):
    """Delete a line item from vendor's bill"""
    qb = QBConnector()
    
    if not qb.connected:
        print("[ERROR] QuickBooks not connected")
        return
    
    # Use UPDATE_WORK_BILL with remove_days parameter
    result = qb.execute_command("UPDATE_WORK_BILL", {
        "vendor_name": vendor_name,
        "remove_days": [day_to_remove]
    })
    
    if result['success']:
        print(result['output'])
    else:
        print(f"[ERROR] {result.get('error', 'Failed to delete line')}")

if __name__ == "__main__":
    # Delete Friday's line from Adrian's bill
    delete_line_item("Adrian", "friday")