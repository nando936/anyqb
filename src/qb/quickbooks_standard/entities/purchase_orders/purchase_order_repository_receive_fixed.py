"""Fixed receive_purchase_order method using QBFC for partial receipt support"""

def receive_purchase_order(
    self,
    po_ref_number: Optional[str] = None,
    po_txn_id: Optional[str] = None,
    line_items: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an Item Receipt from a Purchase Order with support for partial receipts
    
    Args:
        po_ref_number: PO reference number
        po_txn_id: PO transaction ID (alternative to ref_number)
        line_items: Optional list of items to receive with quantities
                   If not provided, receives all items in full
                   Format: [{'item': 'Item Name', 'quantity': 50}]
    
    Returns:
        Receipt details or error
        
    Note: Uses QBFC connection with line-level LinkToTxn for partial receipt support
    """
    try:
        # Use QBFC connection for proper partial receipt support
        from shared_utilities.fast_qb_connection import FastQBConnection
        fast_conn = FastQBConnection()
        
        if not fast_conn.connect():
            return {'error': 'Failed to connect to QuickBooks'}
        
        # First, get the PO details using a query
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
        
        # Get PO line details
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
                    'received': float(po_line.ReceivedQuantity.GetValue()) if po_line.ReceivedQuantity else 0
                }
                if line_info['item']:
                    po_lines.append(line_info)
        
        # Create Item Receipt using QBFC
        from datetime import datetime
        receipt_request = fast_conn.create_request_set()
        item_receipt_add = receipt_request.AppendItemReceiptAddRq()
        
        # Set vendor and date
        item_receipt_add.VendorRef.FullName.SetValue(vendor_name)
        item_receipt_add.TxnDate.SetValue(datetime.now())
        item_receipt_add.RefNumber.SetValue(f"Receipt-{po_ref_num}")
        item_receipt_add.Memo.SetValue(f"Receipt for PO #{po_ref_num}")
        
        # IMPORTANT: Do NOT use LinkToTxnIDList for partial receipts
        # Instead, use line-level LinkToTxn
        
        if line_items:
            # User specified which items to receive - partial receipt
            for receive_item in line_items:
                item_name = receive_item.get('item', '')
                quantity = receive_item.get('quantity', 0)
                
                # Fuzzy match the item name
                from quickbooks_standard.entities.items.item_repository import ItemRepository
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
                
                # Add line with LinkToTxn for partial receipt
                line_add = item_receipt_add.ORItemLineAddList.Append()
                # IMPORTANT: Do NOT set ItemRef when using LinkToTxn
                # The item info is pulled from the PO line
                line_add.ItemLineAdd.Quantity.SetValue(float(quantity))
                line_add.ItemLineAdd.LinkToTxn.TxnID.SetValue(po_txn_id_actual)
                line_add.ItemLineAdd.LinkToTxn.TxnLineID.SetValue(matching_po_line['txn_line_id'])
        else:
            # Receive all items from PO in full - use header-level link
            # This is simpler for full receipt
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
            
            # Get received quantities
            received_items = []
            line_count = receipt_ret.ORItemLineRetList.Count if receipt_ret.ORItemLineRetList else 0
            
            for i in range(line_count):
                line_ret = receipt_ret.ORItemLineRetList.GetAt(i)
                if hasattr(line_ret, 'ItemLineRet'):
                    item_line = line_ret.ItemLineRet
                    if item_line.ItemRef and item_line.Quantity:
                        received_items.append({
                            'item': item_line.ItemRef.FullName.GetValue(),
                            'quantity': float(item_line.Quantity.GetValue())
                        })
            
            result['received_items'] = received_items
            return result
        
        return {'error': 'No receipt details returned'}
        
    except Exception as e:
        return {'error': f'Exception during receipt: {str(e)}'}