"""
QBFC-based receive_purchase_order implementation with CustomerRef preservation
"""

def receive_purchase_order_qbfc(
    self,
    po_ref_number: Optional[str] = None,
    po_txn_id: Optional[str] = None,
    line_items: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Receive items from a purchase order using QBFC (create Item Receipt)

    Args:
        po_ref_number: PO reference number (e.g., "269066")
        po_txn_id: PO transaction ID (alternative to ref_number)
        line_items: List of items to receive, each dict should have:
            - item: Item name (will be fuzzy matched)
            - quantity: Quantity to receive

    Returns:
        Dictionary with receipt details or error
    """
    from datetime import datetime

    # Use QBFC connection for proper job assignment handling
    fast_conn = FastQBConnection()

    if not fast_conn.connect():
        logger.error("Failed to connect to QuickBooks via QBFC")
        return {'error': 'Failed to connect to QuickBooks'}

    try:
        # First, query the PO to get details
        request_set = fast_conn.create_request_set()
        po_query = request_set.AppendPurchaseOrderQueryRq()

        if po_ref_number:
            po_query.ORTxnQuery.RefNumberList.Add(po_ref_number)
        elif po_txn_id:
            po_query.ORTxnQuery.TxnIDList.Add(po_txn_id)
        else:
            return {'error': 'Either po_ref_number or po_txn_id is required'}

        po_query.IncludeLineItems.SetValue(True)

        # Process the query
        response_set = fast_conn.process_request_set(request_set)
        response = response_set.ResponseList.GetAt(0)

        if response.StatusCode != 0:
            return {'error': f'Failed to query PO: {response.StatusMessage}'}

        if response.Detail is None or response.Detail.Count == 0:
            return {'error': f'Purchase Order not found: {po_ref_number or po_txn_id}'}

        # Get PO details
        po = response.Detail.GetAt(0)
        po_txn_id_actual = po.TxnID.GetValue()
        po_ref_num = po.RefNumber.GetValue()
        vendor_name = po.VendorRef.FullName.GetValue()

        # Get PO line details including CustomerRef
        po_lines = []
        line_count = po.ORPurchaseOrderLineRetList.Count if po.ORPurchaseOrderLineRetList else 0

        for i in range(line_count):
            line_ret = po.ORPurchaseOrderLineRetList.GetAt(i)
            if hasattr(line_ret, 'PurchaseOrderLineRet'):
                po_line = line_ret.PurchaseOrderLineRet
                line_info = {
                    'txn_line_id': po_line.TxnLineID.GetValue(),
                    'item': po_line.ItemRef.FullName.GetValue() if po_line.ItemRef else None,
                    'quantity': float(po_line.Quantity.GetValue()) if po_line.Quantity else 0,
                    'received': float(po_line.ReceivedQuantity.GetValue()) if po_line.ReceivedQuantity else 0,
                    'customer_job': po_line.CustomerRef.FullName.GetValue() if po_line.CustomerRef else None
                }
                if line_info['item']:
                    po_lines.append(line_info)

        # Create Item Receipt
        receipt_request = fast_conn.create_request_set()
        item_receipt_add = receipt_request.AppendItemReceiptAddRq()

        # Set basic receipt info
        item_receipt_add.VendorRef.FullName.SetValue(vendor_name)
        item_receipt_add.TxnDate.SetValue(datetime.now())
        item_receipt_add.RefNumber.SetValue(f"Receipt-{po_ref_num}-{datetime.now().strftime('%H%M')}")
        item_receipt_add.Memo.SetValue(f"Receipt for PO #{po_ref_num}")

        if line_items:
            # User specified which items to receive - partial receipt
            for receive_item in line_items:
                item_name = receive_item.get('item', '')
                quantity = receive_item.get('quantity', 0)

                # Fuzzy match the item name
                from qb.quickbooks_standard.entities.items.item_repository import ItemRepository
                item_repo = ItemRepository()
                all_items = item_repo.get_all_items()
                item_names = [item['name'] for item in all_items if item.get('is_active', True)]

                item_match = self.fuzzy_matcher.find_best_match(
                    item_name,
                    item_names,
                    entity_type='item'
                )

                if not item_match.found:
                    return {'error': f"Item '{item_name}' not found"}

                matched_item_name = item_match.exact_name

                # Find the corresponding PO line
                matching_po_line = None
                for po_line in po_lines:
                    if po_line['item'] == matched_item_name:
                        matching_po_line = po_line
                        break

                if not matching_po_line:
                    return {'error': f"Item '{matched_item_name}' not found in PO #{po_ref_num}"}

                # Add line item to receipt
                line_add = item_receipt_add.ORItemLineAddList.Append()
                item_line = line_add.ItemLineAdd

                # Set item and quantity
                item_line.ItemRef.FullName.SetValue(matched_item_name)
                item_line.Quantity.SetValue(float(quantity))

                # CRITICAL: Set CustomerRef to preserve job assignment
                if matching_po_line.get('customer_job'):
                    item_line.CustomerRef.FullName.SetValue(matching_po_line['customer_job'])
                    item_line.BillableStatus.SetValue('Billable')

                # Link to PO line
                item_line.LinkToTxn.TxnID.SetValue(po_txn_id_actual)
                item_line.LinkToTxn.TxnLineID.SetValue(matching_po_line['txn_line_id'])
        else:
            # Receive all items from PO in full
            # Use header-level link for simplicity
            item_receipt_add.LinkToTxnIDList.Add(po_txn_id_actual)

        # Process the Item Receipt
        receipt_response_set = fast_conn.process_request_set(receipt_request)
        receipt_response = receipt_response_set.ResponseList.GetAt(0)

        # Check for errors
        if receipt_response.StatusCode != 0:
            return {'error': f'Failed to create receipt: {receipt_response.StatusMessage}'}

        receipt_ret = receipt_response.Detail
        if receipt_ret:
            receipt_txn_id = receipt_ret.TxnID.GetValue()
            receipt_ref = receipt_ret.RefNumber.GetValue()

            result = {
                'success': True,
                'txn_id': receipt_txn_id,
                'ref_number': receipt_ref,
                'po_ref_number': po_ref_num,
                'message': f'Successfully created receipt {receipt_ref} from PO #{po_ref_num}'
            }

            # Get received items details
            received_items = []
            line_count = receipt_ret.ORItemLineRetList.Count if receipt_ret.ORItemLineRetList else 0

            for i in range(line_count):
                line_ret = receipt_ret.ORItemLineRetList.GetAt(i)
                if hasattr(line_ret, 'ItemLineRet'):
                    item_line = line_ret.ItemLineRet
                    if item_line.ItemRef and item_line.Quantity:
                        item_detail = {
                            'item': item_line.ItemRef.FullName.GetValue(),
                            'quantity': float(item_line.Quantity.GetValue())
                        }
                        # Check if CustomerRef was preserved
                        if hasattr(item_line, 'CustomerRef') and item_line.CustomerRef:
                            item_detail['customer_job'] = item_line.CustomerRef.FullName.GetValue()
                        received_items.append(item_detail)

            result['received_items'] = received_items
            return result

        return {'error': 'No receipt details returned'}

    except Exception as e:
        logger.error(f"Error receiving purchase order: {str(e)}")
        return {'error': str(e)}
    finally:
        fast_conn.disconnect()