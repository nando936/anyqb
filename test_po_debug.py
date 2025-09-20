"""Debug PO parsing issue"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'qb'))

from quickbooks_standard.entities.purchase_orders.purchase_order_repository import PurchaseOrderRepository

def test_po_parsing():
    """Test if PO repository correctly parses quantities"""
    po_repo = PurchaseOrderRepository()

    # Get PO #269070
    pos = po_repo.get_purchase_orders(
        open_only=True,
        include_line_items=True
    )

    for po in pos:
        if po.get('ref_number') == '269070':
            print(f"\n=== PO #269070 from Repository ===")
            print(f"RefNumber: {po.get('ref_number')}")
            print(f"Total: ${po.get('total', 0):.2f}")
            print(f"IsFullyReceived: {po.get('is_fully_received')}")

            print("\nLine Items:")
            for item in po.get('line_items', []):
                print(f"  Item: {item.get('item')}")
                print(f"    Quantity: {item.get('quantity')}")
                print(f"    Received: {item.get('received', 0)}")
                print(f"    Rate: ${item.get('rate', 0):.2f}")
                print(f"    Amount: ${item.get('amount', 0):.2f}")
                print(f"    Customer/Job: {item.get('customer_job', 'N/A')}")

                remaining = item['quantity'] - item.get('received', 0)
                print(f"    Remaining/Backordered: {remaining}")

            print("\n=== Raw Line Items Dict ===")
            import json
            print(json.dumps(po.get('line_items', []), indent=2))

            return po

    print("PO #269070 not found")
    return None

if __name__ == "__main__":
    print("Testing PO repository parsing...")
    po = test_po_parsing()

    if po:
        print("\n=== Summary ===")
        print("The repository is returning:")
        for item in po.get('line_items', []):
            print(f"  {item.get('item')}: Qty={item.get('quantity')}, Received={item.get('received', 0)}")