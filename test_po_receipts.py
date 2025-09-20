"""Test script to investigate PO and Receipt linking"""

import xml.etree.ElementTree as ET
from src.qb.shared_utilities.xml_qb_connection import XMLQBConnection

def test_po_details():
    """Get full details of PO #269070 including received quantities"""
    connection = XMLQBConnection()

    if not connection.connect():
        print("[ERROR] Failed to connect to QuickBooks")
        return

    try:
        # Query PO #269070 with all details
        request_xml = """<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <PurchaseOrderQueryRq requestID="1">
            <RefNumber>269070</RefNumber>
            <IncludeLineItems>true</IncludeLineItems>
            <IncludeLinkedTxns>true</IncludeLinkedTxns>
        </PurchaseOrderQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""

        response_xml = connection.session_manager.ProcessRequest(
            connection.ticket, request_xml
        )

        # Save raw XML for inspection
        with open("po_269070_raw.xml", "w") as f:
            f.write(response_xml)

        # Parse response
        root = ET.fromstring(response_xml)
        po_elem = root.find('.//PurchaseOrderRet')

        if po_elem:
            print("\n=== PO #269070 Details ===")
            print(f"RefNumber: {po_elem.find('RefNumber').text if po_elem.find('RefNumber') is not None else 'N/A'}")
            print(f"IsFullyReceived: {po_elem.find('IsFullyReceived').text if po_elem.find('IsFullyReceived') is not None else 'N/A'}")
            print(f"IsManuallyClosed: {po_elem.find('IsManuallyClosed').text if po_elem.find('IsManuallyClosed') is not None else 'N/A'}")

            print("\nLine Items:")
            for line in po_elem.findall('.//PurchaseOrderLineRet'):
                item_name = line.find('.//ItemRef/FullName').text if line.find('.//ItemRef/FullName') is not None else 'N/A'
                qty = line.find('Quantity').text if line.find('Quantity') is not None else '0'
                received = line.find('ReceivedQuantity').text if line.find('ReceivedQuantity') is not None else '0'
                print(f"  - {item_name}: Ordered={qty}, Received={received}")

            print("\nLinked Transactions:")
            for linked in po_elem.findall('.//LinkedTxn'):
                txn_type = linked.find('TxnType').text if linked.find('TxnType') is not None else 'N/A'
                txn_id = linked.find('TxnID').text if linked.find('TxnID') is not None else 'N/A'
                ref_num = linked.find('RefNumber').text if linked.find('RefNumber') is not None else 'N/A'
                print(f"  - {txn_type}: {ref_num} (ID: {txn_id})")
        else:
            print("[ERROR] PO not found")

    except Exception as e:
        print(f"[ERROR] {str(e)}")
    finally:
        connection.disconnect()

def test_receipt_details():
    """Get details of receipts to see if they show linked PO"""
    connection = XMLQBConnection()

    if not connection.connect():
        print("[ERROR] Failed to connect to QuickBooks")
        return

    try:
        # Query receipts for TEST_VENDOR_RECEIPT
        request_xml = """<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <ItemReceiptQueryRq requestID="1">
            <IncludeLineItems>true</IncludeLineItems>
            <IncludeLinkedTxns>true</IncludeLinkedTxns>
        </ItemReceiptQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""

        response_xml = connection.session_manager.ProcessRequest(
            connection.ticket, request_xml
        )

        # Save raw XML for inspection
        with open("receipts_raw.xml", "w") as f:
            f.write(response_xml)

        # Parse response
        root = ET.fromstring(response_xml)

        print("\n=== Item Receipts ===")
        for receipt_elem in root.findall('.//ItemReceiptRet'):
            ref_num = receipt_elem.find('RefNumber').text if receipt_elem.find('RefNumber') is not None else 'N/A'
            vendor = receipt_elem.find('.//VendorRef/FullName').text if receipt_elem.find('.//VendorRef/FullName') is not None else 'N/A'

            if 'TEST' in vendor:
                print(f"\nReceipt: {ref_num}")
                print(f"  Vendor: {vendor}")

                # Check for linked PO
                linked_po = receipt_elem.find('.//LinkToTxnID')
                if linked_po is not None:
                    print(f"  Linked to PO TxnID: {linked_po.text}")
                else:
                    print("  No linked PO found")

                # Show LinkedTxn elements
                for linked in receipt_elem.findall('.//LinkedTxn'):
                    txn_type = linked.find('TxnType').text if linked.find('TxnType') is not None else 'N/A'
                    txn_id = linked.find('TxnID').text if linked.find('TxnID') is not None else 'N/A'
                    ref_num_linked = linked.find('RefNumber').text if linked.find('RefNumber') is not None else 'N/A'
                    print(f"  LinkedTxn: {txn_type} #{ref_num_linked} (ID: {txn_id})")

                # Show items
                for line in receipt_elem.findall('.//ItemLineRet'):
                    item_name = line.find('.//ItemRef/FullName').text if line.find('.//ItemRef/FullName') is not None else 'N/A'
                    qty = line.find('Quantity').text if line.find('Quantity') is not None else '0'
                    print(f"    - {item_name}: {qty} units")

                    # Check for LinkToTxn in line items
                    line_link = line.find('LinkToTxn')
                    if line_link is not None:
                        link_type = line_link.find('TxnType').text if line_link.find('TxnType') is not None else 'N/A'
                        link_id = line_link.find('TxnID').text if line_link.find('TxnID') is not None else 'N/A'
                        print(f"      Linked to: {link_type} (ID: {link_id})")

    except Exception as e:
        print(f"[ERROR] {str(e)}")
    finally:
        connection.disconnect()

if __name__ == "__main__":
    print("Testing PO and Receipt linking...")
    test_po_details()
    test_receipt_details()
    print("\nCheck po_269070_raw.xml and receipts_raw.xml for full XML details")