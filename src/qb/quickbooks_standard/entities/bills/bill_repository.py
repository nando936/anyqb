"""
Bill Repository - Standard QuickBooks bill operations using QBFC SDK
NO custom business logic - only pure QB operations
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pywintypes
from shared_utilities.fast_qb_connection import fast_qb_connection

logger = logging.getLogger(__name__)

class BillRepository:
    """Handles standard QuickBooks bill operations using QBFC SDK"""
    
    def __init__(self):
        """Initialize bill repository"""
        pass  # Using singleton fast_qb_connection
    
    def get_bill(self, txn_id: str) -> Optional[Dict]:
        """Get a bill by transaction ID using SDK"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            bill_query = request_set.AppendBillQueryRq()
            
            # Use ORBillQuery with TxnIDList for specific TxnID
            bill_query.IncludeLineItems.SetValue(True)
            bill_query.IncludeLinkedTxns.SetValue(True)  # Include payment information
            # The correct path for TxnID filtering
            bill_query.ORBillQuery.TxnIDList.Add(txn_id)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                # If the first approach fails, try alternative query method
                # Sometimes older bills need a different query approach
                logger.warning(f"TxnID query failed, trying alternative method: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                
                # Alternative: Query all bills and filter
                request_set = fast_qb_connection.create_request_set()
                bill_query = request_set.AppendBillQueryRq()
                bill_query.IncludeLineItems.SetValue(True)
                bill_query.IncludeLinkedTxns.SetValue(True)  # Include payment information
                
                response_set = fast_qb_connection.process_request_set(request_set)
                response = response_set.ResponseList.GetAt(0)
                
                if response.StatusCode == 0 and response.Detail:
                    # Search through all bills for the matching TxnID
                    for i in range(response.Detail.Count):
                        bill_ret = response.Detail.GetAt(i)
                        if hasattr(bill_ret, 'TxnID') and bill_ret.TxnID.GetValue() == txn_id:
                            return self._parse_bill_from_sdk(bill_ret)
                
                logger.error(f"Bill {txn_id} not found after alternative search")
                return None
            
            if not response.Detail or response.Detail.Count == 0:
                logger.error(f"Bill {txn_id} not found")
                return None
            
            # Parse the bill
            bill_ret = response.Detail.GetAt(0)
            return self._parse_bill_from_sdk(bill_ret)
            
        except Exception as e:
            logger.error(f"Failed to get bill {txn_id}: {e}")
            return None
    
    def find_bills_by_vendor(self, vendor_name: str, include_line_items: bool = False) -> List[Dict]:
        """Find bills by vendor name using SDK"""
        try:
            logger.info(f"find_bills_by_vendor called with vendor_name={vendor_name}")
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            bill_query = request_set.AppendBillQueryRq()
            
            # Set vendor filter
            entity_filter = bill_query.ORBillQuery.BillFilter.EntityFilter
            logger.info(f"Adding vendor to filter: '{vendor_name}'")
            entity_filter.OREntityFilter.FullNameList.Add(vendor_name)
            
            bill_query.IncludeLineItems.SetValue(include_line_items)
            bill_query.IncludeLinkedTxns.SetValue(True)  # Include payment information
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            if not response.Detail or response.Detail.Count == 0:
                return []
            
            bills = []
            for i in range(response.Detail.Count):
                bill_ret = response.Detail.GetAt(i)
                bill_data = self._parse_bill_from_sdk(bill_ret)
                if bill_data:
                    bills.append(bill_data)
            
            return bills
            
        except Exception as e:
            logger.error(f"Failed to find bills for vendor {vendor_name}: {e}")
            return []
    
    def create_bill(self, bill_data: Dict) -> Dict:
        """Create a new bill in QuickBooks using SDK"""
        try:
            if not fast_qb_connection.connect():
                error_detail = "Failed to connect to QuickBooks"
                logger.error(f"[BillRepository.create_bill] {error_detail}")
                return {'success': False, 'error': error_detail}
            
            request_set = fast_qb_connection.create_request_set()
            bill_add = request_set.AppendBillAddRq()
            
            # Set required fields
            bill_add.VendorRef.FullName.SetValue(bill_data['vendor_name'])
            
            # Set dates
            if 'txn_date' in bill_data:
                bill_add.TxnDate.SetValue(pywintypes.Time(bill_data['txn_date']))
            if 'due_date' in bill_data:
                bill_add.DueDate.SetValue(pywintypes.Time(bill_data['due_date']))
            
            # Set optional fields
            if 'ref_number' in bill_data:
                bill_add.RefNumber.SetValue(bill_data['ref_number'])
            if 'memo' in bill_data:
                bill_add.Memo.SetValue(bill_data['memo'])
            
            # Add line items if provided
            if 'line_items' in bill_data:
                for line_item in bill_data['line_items']:
                    if line_item.get('item_name'):
                        # Item line
                        item_line = bill_add.ORItemLineAddList.Append()
                        item_line.ItemLineAdd.ItemRef.FullName.SetValue(line_item['item_name'])
                        if 'description' in line_item:
                            item_line.ItemLineAdd.Desc.SetValue(line_item['description'])
                        if 'quantity' in line_item:
                            item_line.ItemLineAdd.Quantity.SetValue(float(line_item['quantity']))
                        if 'cost' in line_item:
                            item_line.ItemLineAdd.Cost.SetValue(float(line_item['cost']))
                        if 'customer' in line_item:
                            item_line.ItemLineAdd.CustomerRef.FullName.SetValue(line_item['customer'])
                        # Set billable status if provided
                        if 'billable_status' in line_item:
                            # BillableStatus values: 0 = Billable, 1 = Not Billable, 2 = Has Been Billed
                            item_line.ItemLineAdd.BillableStatus.SetValue(int(line_item['billable_status']))
                    else:
                        # Expense line
                        expense_line = bill_add.ORExpenseLineAddList.Append()
                        expense_line.ExpenseLineAdd.AccountRef.FullName.SetValue(
                            line_item.get('account', 'Expenses')
                        )
                        expense_line.ExpenseLineAdd.Amount.SetValue(float(line_item['amount']))
                        if 'memo' in line_item:
                            expense_line.ExpenseLineAdd.Memo.SetValue(line_item['memo'])
                        if 'customer' in line_item:
                            expense_line.ExpenseLineAdd.CustomerRef.FullName.SetValue(line_item['customer'])
                        # Set billable status for expense lines too
                        if 'billable_status' in line_item:
                            expense_line.ExpenseLineAdd.BillableStatus.SetValue(int(line_item['billable_status']))
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info("Bill created successfully")
                return {'success': True, 'message': 'Bill created successfully'}
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'
                error_code = response.StatusCode if hasattr(response, 'StatusCode') else 'Unknown'
                
                # Log detailed error with context
                logger.error(f"[BillRepository.create_bill] QuickBooks rejected bill creation:")
                logger.error(f"  - Vendor: {bill_data.get('vendor_name')}")
                logger.error(f"  - Error Code: {error_code}")
                logger.error(f"  - Error Message: {error_msg}")
                logger.error(f"  - Line items: {len(bill_data.get('line_items', []))}")
                
                # Build explanation
                explanation = ""
                if error_code == 3140:
                    explanation = "Invalid item reference. Check if all items exist in QuickBooks."
                elif error_code == 3210:
                    explanation = "Billable status issue. Item may not be reimbursable."
                elif error_code == 3000:
                    explanation = "Invalid object ID. Check if vendor/items/customers exist."
                elif error_code == 3180:
                    explanation = "Required field missing. Check all required fields are provided."
                
                if explanation:
                    logger.error(f"  - EXPLANATION: {explanation}")
                
                # Return detailed error information
                error_detail = f"QuickBooks Error {error_code}: {error_msg}"
                if explanation:
                    error_detail += f"\nExplanation: {explanation}"
                    
                return {
                    'success': False,
                    'error': error_detail,
                    'error_code': error_code,
                    'error_message': error_msg,
                    'explanation': explanation
                }
                
        except Exception as e:
            error_detail = f"Exception in create_bill: {str(e)}"
            logger.error(f"[BillRepository.create_bill] {error_detail}")
            return {'success': False, 'error': error_detail}

    def find_bills_by_date_range(self, start_date: str, end_date: str, include_line_items: bool = True) -> List[Dict]:
        """Find bills within a date range using SDK

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            include_line_items: Whether to include line item details

        Returns:
            List of bill dictionaries
        """
        try:
            logger.info(f"find_bills_by_date_range called with dates {start_date} to {end_date}")
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []

            request_set = fast_qb_connection.create_request_set()
            bill_query = request_set.AppendBillQueryRq()

            # Set date range filter - convert string dates to datetime objects
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            # Convert to pywintypes datetime
            import pywintypes
            start_pywin = pywintypes.Time(start_dt)
            end_pywin = pywintypes.Time(end_dt)

            bill_query.ORBillQuery.BillFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter.FromTxnDate.SetValue(start_pywin)
            bill_query.ORBillQuery.BillFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter.ToTxnDate.SetValue(end_pywin)

            if include_line_items:
                bill_query.IncludeLineItems.SetValue(True)

            bill_query.IncludeLinkedTxns.SetValue(True)  # Include payment info

            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)

            bills = []
            if response.StatusCode == 0:
                bill_list = response.Detail
                if bill_list is not None:
                    for i in range(bill_list.Count):
                        bill = bill_list.GetAt(i)
                        # Use _parse_bill_from_sdk to get complete bill data including payment info
                        bill_dict = self._parse_bill_from_sdk(bill)
                        # Only append if bill_dict is not None
                        if bill_dict is not None:
                            bills.append(bill_dict)

                logger.info(f"Found {len(bills)} bills in date range")
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Query failed: {error_msg}")

            return bills

        except Exception as e:
            logger.error(f"Error finding bills by date range: {e}")
            return []

    def update_bill(self, bill_data: Dict) -> bool:
        """Update an existing bill in QuickBooks using SDK"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            # First get the bill to get EditSequence
            existing_bill = self.get_bill(bill_data['txn_id'])
            if not existing_bill:
                logger.error(f"Bill {bill_data['txn_id']} not found")
                return False
            
            edit_sequence = existing_bill['edit_sequence']
            
            # Now update the bill
            request_set = fast_qb_connection.create_request_set()
            bill_mod = request_set.AppendBillModRq()
            
            bill_mod.TxnID.SetValue(bill_data['txn_id'])
            bill_mod.EditSequence.SetValue(edit_sequence)
            
            # Update fields as needed
            if 'memo' in bill_data:
                bill_mod.Memo.SetValue(bill_data['memo'])
            if 'ref_number' in bill_data:
                bill_mod.RefNumber.SetValue(bill_data['ref_number'])
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Bill {bill_data['txn_id']} updated successfully")
                return True
            else:
                logger.error(f"Failed to update bill: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating bill: {e}")
            return False
    
    def update_bill_with_line_items(self, bill_data: Dict) -> bool:
        """
        Update a bill including line item modifications
        Supports adding new line items with TxnLineID = "-1"
        
        Args:
            bill_data: Dictionary with update details:
                {
                    'txn_id': str (required),
                    'edit_sequence': str (optional - will fetch if not provided),
                    'memo': str (optional),
                    'ref_number': str (optional),
                    'due_date': datetime (optional),
                    'line_items_to_add': [  # New line items to add
                        {
                            'item_name': str,
                            'description': str,
                            'quantity': float,
                            'cost': float,
                            'customer': str (optional),
                            'billable_status': int (optional, 0=billable, 1=not billable, 2=has been billed)
                        }
                    ],
                    'line_items_to_modify': [  # Existing items to modify
                        {
                            'txn_line_id': str (required),
                            'item_name': str (optional),
                            'description': str (optional),
                            'quantity': float (optional),
                            'cost': float (optional)
                        }
                    ]
                }
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            # Get EditSequence if not provided
            edit_sequence = bill_data.get('edit_sequence')
            if not edit_sequence:
                existing_bill = self.get_bill(bill_data['txn_id'])
                if not existing_bill:
                    logger.error(f"Bill {bill_data['txn_id']} not found")
                    return False
                edit_sequence = existing_bill['edit_sequence']
            
            # Build update request
            request_set = fast_qb_connection.create_request_set()
            bill_mod = request_set.AppendBillModRq()
            
            bill_mod.TxnID.SetValue(bill_data['txn_id'])
            bill_mod.EditSequence.SetValue(edit_sequence)
            
            # Update header fields if provided
            if 'memo' in bill_data:
                bill_mod.Memo.SetValue(bill_data['memo'])
            if 'ref_number' in bill_data:
                bill_mod.RefNumber.SetValue(bill_data['ref_number'])
            if 'due_date' in bill_data:
                bill_mod.DueDate.SetValue(pywintypes.Time(bill_data['due_date']))
            
            # Add new line items (TxnLineID = "-1")
            if 'line_items_to_add' in bill_data:
                for new_item in bill_data['line_items_to_add']:
                    item_line_mod = bill_mod.ORItemLineModList.Append()
                    item_line = item_line_mod.ItemLineMod
                    
                    # CRITICAL: Set TxnLineID to "-1" for new items
                    item_line.TxnLineID.SetValue("-1")
                    
                    # Set item reference
                    item_line.ItemRef.FullName.SetValue(new_item['item_name'])
                    
                    # Set description
                    if 'description' in new_item:
                        item_line.Desc.SetValue(new_item['description'])
                    
                    # Set quantity
                    if 'quantity' in new_item:
                        item_line.Quantity.SetValue(float(new_item['quantity']))
                    
                    # Set cost (rate per unit)
                    if 'cost' in new_item:
                        item_line.Cost.SetValue(float(new_item['cost']))
                    
                    # Set customer/job if provided
                    if 'customer' in new_item:
                        item_line.CustomerRef.FullName.SetValue(new_item['customer'])
                    
                    # Set billable status if explicitly provided
                    if 'billable_status' in new_item:
                        # BillableStatus values in QuickBooks:
                        # 0 = Billable, 1 = Not Billable, 2 = Has Been Billed
                        status = int(new_item['billable_status'])
                        logger.info(f"[BILL_REPO] Setting BillableStatus={status} for new line item")
                        logger.info(f"[DEBUG] Full new_item data: {new_item}")
                        item_line.BillableStatus.SetValue(status)
                    else:
                        logger.warning(f"[BILL_REPO] No billable_status in new_item: {new_item.get('description', 'no desc')}")
            
            # Handle line item deletions
            # In QuickBooks, to delete line items, we must:
            # 1. Include ALL line items we want to keep (even unchanged ones)
            # 2. Exclude the ones we want to delete
            # The items to keep are already in line_items_to_modify (set by work_bill_service)
            
            # Modify existing line items
            if 'line_items_to_modify' in bill_data:
                # CRITICAL: DO NOT SORT! QuickBooks requires line items in their ORIGINAL order
                # QuickBooks error 3290 occurs when line items are sent out of their original sequence
                # The order items were returned from QuickBooks must be preserved exactly
                
                # Use items in the order they were provided (which should be original order)
                items_to_process = bill_data['line_items_to_modify']
                
                # Debug logging to understand the order
                logger.info(f"Processing line items in original order:")
                for item in items_to_process:
                    txn_id = item.get('txn_line_id', 'none')
                    desc = item.get('description', 'no desc')
                    logger.info(f"  TxnLineID: {txn_id} - {desc[:20]}")
                
                for mod_item in items_to_process:
                    item_line_mod = bill_mod.ORItemLineModList.Append()
                    item_line = item_line_mod.ItemLineMod
                    
                    # Use existing TxnLineID
                    item_line.TxnLineID.SetValue(mod_item['txn_line_id'])
                    
                    # Update fields as needed
                    if 'item_name' in mod_item:
                        item_line.ItemRef.FullName.SetValue(mod_item['item_name'])
                    if 'description' in mod_item:
                        item_line.Desc.SetValue(mod_item['description'])
                    if 'quantity' in mod_item:
                        item_line.Quantity.SetValue(float(mod_item['quantity']))
                    if 'cost' in mod_item:
                        item_line.Cost.SetValue(float(mod_item['cost']))
                    if 'customer' in mod_item:
                        item_line.CustomerRef.FullName.SetValue(mod_item['customer'])
                    
                    # Set billable status if explicitly provided
                    if 'billable_status' in mod_item:
                        # BillableStatus values in QuickBooks:
                        # 0 = Billable, 1 = Not Billable, 2 = Has Been Billed
                        logger.info(f"[BILL_REPO] Setting BillableStatus={mod_item['billable_status']} for TxnLineID {mod_item['txn_line_id']}")
                        item_line.BillableStatus.SetValue(mod_item['billable_status'])
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Bill {bill_data['txn_id']} updated successfully with line items")
                return True
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'
                error_code = response.StatusCode if hasattr(response, 'StatusCode') else 'Unknown'
                
                # Build detailed error context
                error_context = {
                    'operation': 'update_bill_with_line_items',
                    'txn_id': bill_data.get('txn_id'),
                    'error_code': error_code,
                    'error_message': error_msg,
                    'items_to_add': len(bill_data.get('line_items_to_add', [])),
                    'items_to_modify': len(bill_data.get('line_items_to_modify', [])),
                    'items_to_delete': len(bill_data.get('line_items_to_delete', []))
                }
                
                # Build complete error message for passing up
                full_error = f"[BillRepository.update_bill_with_line_items] QuickBooks rejected update:\n"
                full_error += f"  - Bill TxnID: {bill_data.get('txn_id')}\n"
                full_error += f"  - Error Code: {error_code}\n"
                full_error += f"  - Error Message: {error_msg}\n"
                full_error += f"  - Operations attempted: Add={error_context['items_to_add']}, Modify={error_context['items_to_modify']}, Delete={error_context['items_to_delete']}"
                
                # Add explanations
                if error_code == 3140:
                    full_error += f"\n  - EXPLANATION: Invalid item reference. Check if item exists in QuickBooks."
                elif error_code == 3210:
                    full_error += f"\n  - EXPLANATION: Billable status issue. Item may not be reimbursable."
                elif error_code == 3290:
                    full_error += f"\n  - EXPLANATION: Line items are out of order. Items must be sent in TxnLineID sequence."
                elif error_code == 3000:
                    full_error += f"\n  - EXPLANATION: Invalid object ID. Check if all referenced items/customers exist."
                
                # Log it
                logger.error(full_error)
                
                # Store for caller to retrieve
                self.last_error = full_error
                
                return False
                
        except Exception as e:
            logger.error(f"Error updating bill with line items: {e}")
            return False
    
    def delete_bill(self, txn_id: str) -> bool:
        """
        Delete a bill from QuickBooks using QBFC SDK with proper method
        
        Args:
            txn_id: The transaction ID of the bill to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            # Create delete request
            request_set = fast_qb_connection.create_request_set()
            bill_del = request_set.AppendTxnDelRq()
            
            # CRITICAL: Use SetAsString for TxnDelType - NOT SetValue!
            # This is the key discovery from our testing
            bill_del.TxnDelType.SetAsString("Bill")  # Must use string value!
            bill_del.TxnID.SetValue(txn_id)
            
            # Execute delete
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Successfully deleted bill {txn_id}")
                return True
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else "Unknown error"
                logger.error(f"Failed to delete bill {txn_id}: {error_msg}")
                
                # Log common error reasons
                if "3200" in str(error_msg):
                    logger.info("Bill may have payments applied. Void payments first.")
                elif "Cannot be deleted" in str(error_msg):
                    logger.info("Bill may be in closed period or have linked transactions.")
                
                return False
                
        except Exception as e:
            logger.error(f"Error deleting bill {txn_id}: {e}")
            return False
    
    def _parse_bill_from_sdk(self, bill_ret) -> Optional[Dict]:
        """Parse a bill object from SDK response"""
        try:
            amount_value = float(bill_ret.AmountDue.GetValue()) if bill_ret.AmountDue else 0.0
            is_paid_value = bill_ret.IsPaid.GetValue() if bill_ret.IsPaid else False
            
            bill_data = {
                'txn_id': bill_ret.TxnID.GetValue() if bill_ret.TxnID else None,
                'vendor_name': bill_ret.VendorRef.FullName.GetValue() if bill_ret.VendorRef and bill_ret.VendorRef.FullName else None,
                'txn_date': str(bill_ret.TxnDate.GetValue()) if bill_ret.TxnDate else None,
                'due_date': str(bill_ret.DueDate.GetValue()) if bill_ret.DueDate else None,
                'ref_number': bill_ret.RefNumber.GetValue() if bill_ret.RefNumber else None,
                'memo': bill_ret.Memo.GetValue() if bill_ret.Memo else None,
                'amount_due': amount_value,
                'amount': amount_value,  # Include both for compatibility
                'is_paid': is_paid_value,
                'IsPaid': is_paid_value,  # Include both for compatibility
                'open_amount': float(bill_ret.OpenAmount.GetValue()) if hasattr(bill_ret, 'OpenAmount') and bill_ret.OpenAmount else None,
                'edit_sequence': bill_ret.EditSequence.GetValue() if bill_ret.EditSequence else None,
                'line_items': [],
                'payment_info': {}  # Will be populated below
            }
            
            # Parse line items if present
            if hasattr(bill_ret, 'ORItemLineRetList') and bill_ret.ORItemLineRetList:
                for i in range(bill_ret.ORItemLineRetList.Count):
                    line_ret = bill_ret.ORItemLineRetList.GetAt(i)
                    if hasattr(line_ret, 'ItemLineRet'):
                        item_line = line_ret.ItemLineRet
                        line_data = {
                            'txn_line_id': item_line.TxnLineID.GetValue() if item_line.TxnLineID else None,
                            'item_name': item_line.ItemRef.FullName.GetValue() if item_line.ItemRef and item_line.ItemRef.FullName else None,
                            'description': item_line.Desc.GetValue() if item_line.Desc else None,
                            'quantity': float(item_line.Quantity.GetValue()) if item_line.Quantity else 1.0,
                            'cost': float(item_line.Cost.GetValue()) if item_line.Cost else 0.0,
                            'amount': float(item_line.Amount.GetValue()) if item_line.Amount else 0.0,
                            'customer_name': item_line.CustomerRef.FullName.GetValue() if item_line.CustomerRef and item_line.CustomerRef.FullName else None,
                            'billable': item_line.BillableStatus.GetValue() if hasattr(item_line, 'BillableStatus') and item_line.BillableStatus else None
                        }
                        bill_data['line_items'].append(line_data)
            
            # Parse expense lines if present
            if hasattr(bill_ret, 'ORExpenseLineRetList') and bill_ret.ORExpenseLineRetList:
                for i in range(bill_ret.ORExpenseLineRetList.Count):
                    line_ret = bill_ret.ORExpenseLineRetList.GetAt(i)
                    if hasattr(line_ret, 'ExpenseLineRet'):
                        expense_line = line_ret.ExpenseLineRet
                        line_data = {
                            'txn_line_id': expense_line.TxnLineID.GetValue() if expense_line.TxnLineID else None,
                            'account_name': expense_line.AccountRef.FullName.GetValue() if expense_line.AccountRef and expense_line.AccountRef.FullName else None,
                            'amount': float(expense_line.Amount.GetValue()) if expense_line.Amount else 0.0,
                            'memo': expense_line.Memo.GetValue() if expense_line.Memo else None,
                            'customer_name': expense_line.CustomerRef.FullName.GetValue() if expense_line.CustomerRef and expense_line.CustomerRef.FullName else None
                        }
                        bill_data['line_items'].append(line_data)
            
            # Parse LinkedTxn data for payment information
            payment_txn_ids = []
            if hasattr(bill_ret, 'LinkedTxnList') and bill_ret.LinkedTxnList:
                logger.debug(f"Bill {bill_data['txn_id']} has {bill_ret.LinkedTxnList.Count} linked transactions")
                for i in range(bill_ret.LinkedTxnList.Count):
                    linked_txn = bill_ret.LinkedTxnList.GetAt(i)
                    if linked_txn:
                        # Get transaction ID and type
                        linked_txn_id = linked_txn.TxnID.GetValue() if hasattr(linked_txn, 'TxnID') and linked_txn.TxnID else None
                        linked_type = linked_txn.TxnType.GetValue() if hasattr(linked_txn, 'TxnType') and linked_txn.TxnType else None
                        
                        logger.debug(f"  LinkedTxn {i}: Type={linked_type}, ID={linked_txn_id}")
                        
                        # TxnType for payments: BillPaymentCheck (may come as different values)
                        # The SDK might return numeric codes or string names
                        # Type 2 appears to be BillPaymentCheck in some versions
                        if linked_type and (str(linked_type) in ['BillPaymentCheck', 'BillPaymentCreditCard', '54', '55', '2']):
                            if linked_txn_id:
                                logger.debug(f"    Found payment transaction: {linked_txn_id}")
                                payment_txn_ids.append(linked_txn_id)
                        
                        # Also check the amount for this linked transaction
                        linked_amount = float(linked_txn.LinkAmount.GetValue()) if hasattr(linked_txn, 'LinkAmount') and linked_txn.LinkAmount else 0.0
            else:
                logger.debug(f"Bill {bill_data['txn_id']} has no LinkedTxnList or LinkedTxnList is empty")
            
            # If we have payment transactions, get their details
            if payment_txn_ids:
                logger.debug(f"Getting payment details for {len(payment_txn_ids)} payment(s)")
                payment_details = self._get_payment_details(payment_txn_ids)
                if payment_details:
                    logger.debug(f"Got payment details: {payment_details}")
                    bill_data['payment_info'] = payment_details
                else:
                    logger.debug("No payment details retrieved")
            else:
                logger.debug("No payment transactions found for this bill")
            
            return bill_data
            
        except Exception as e:
            logger.error(f"Failed to parse bill from SDK: {e}")
            return None
    
    def get_bill_edit_sequence(self, txn_id: str) -> Optional[str]:
        """Get current EditSequence for a bill - REQUIRED before any update"""
        try:
            bill = self.get_bill(txn_id)
            if bill:
                return bill.get('edit_sequence')
            return None
        except Exception as e:
            logger.error(f"Failed to get bill edit sequence: {e}")
            return None
    
    def find_bill_by_ref_number(self, vendor_name: str, ref_number: str, include_line_items: bool = True) -> Optional[Dict]:
        """Find a bill by vendor and reference number"""
        try:
            # Get all bills for vendor
            bills = self.find_bills_by_vendor(vendor_name, include_line_items=include_line_items)
            
            if not bills:
                return None
            
            # Find bill with matching ref_number
            for bill in bills:
                if bill.get('ref_number') == ref_number:
                    return bill
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find bill by ref number: {e}")
            return None
    
    def search_by_ref_number(self, ref_number: str, include_line_items: bool = True) -> List[Dict]:
        """Search for bills by reference number only (any vendor)"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            bill_query = request_set.AppendBillQueryRq()
            
            # Set ref number filter (use RefNumberList for bills)
            bill_query.RefNumberList.Add(ref_number)
            
            # Include line items if requested
            if include_line_items:
                bill_query.IncludeLineItems.SetValue(True)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                # Log error and return empty list
                logger.error(f"Failed to search bills by ref number {ref_number}: Status {response.StatusCode}")
                return []
            
            bills = []
            for i in range(response.Detail.Count):
                bill_ret = response.Detail.GetAt(i)
                bill = self._parse_bill_from_ret(bill_ret, include_line_items)
                if bill:
                    bills.append(bill)
            
            return bills
            
        except Exception as e:
            logger.error(f"Failed to search bills by ref number: {e}")
            return []
    
    def _get_payment_details(self, payment_txn_ids: List[str]) -> Dict:
        """Get payment details for linked payment transactions"""
        try:
            if not payment_txn_ids:
                return {}
            
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks for payment details")
                return {}
            
            payments = []
            total_paid = 0.0
            
            for payment_id in payment_txn_ids:
                try:
                    # Create request for bill payment check
                    request_set = fast_qb_connection.create_request_set()
                    payment_query = request_set.AppendBillPaymentCheckQueryRq()
                    payment_query.ORTxnQuery.TxnIDList.Add(payment_id)
                    payment_query.IncludeLineItems.SetValue(True)
                    
                    # Process request
                    response_set = fast_qb_connection.process_request_set(request_set)
                    response = response_set.ResponseList.GetAt(0)
                    
                    if response.StatusCode == 0 and response.Detail:
                        payment_list = response.Detail
                        if payment_list.Count > 0:
                            payment_ret = payment_list.GetAt(0)
                            
                            # Extract payment details
                            payment_data = {
                                'payment_txn_id': payment_ret.TxnID.GetValue() if payment_ret.TxnID else payment_id,
                                'payment_date': payment_ret.TxnDate.GetValue().strftime('%m-%d-%Y') if payment_ret.TxnDate else None,
                                'amount_paid': float(payment_ret.Amount.GetValue()) if payment_ret.Amount else 0.0,
                                'bank_account': payment_ret.BankAccountRef.FullName.GetValue() if hasattr(payment_ret, 'BankAccountRef') and payment_ret.BankAccountRef and payment_ret.BankAccountRef.FullName else 'Unknown Account',
                                'check_number': payment_ret.RefNumber.GetValue() if payment_ret.RefNumber else None
                            }
                            
                            payments.append(payment_data)
                            total_paid += payment_data['amount_paid']
                    else:
                        # Try credit card payment if check payment failed
                        request_set = fast_qb_connection.create_request_set()
                        cc_payment_query = request_set.AppendBillPaymentCreditCardQueryRq()
                        cc_payment_query.ORTxnQuery.TxnIDList.Add(payment_id)
                        cc_payment_query.IncludeLineItems.SetValue(True)
                        
                        response_set = fast_qb_connection.process_request(request_set)
                        response = response_set.ResponseList.GetAt(0)
                        
                        if response.StatusCode == 0 and response.Detail:
                            payment_list = response.Detail
                            if payment_list.Count > 0:
                                payment_ret = payment_list.GetAt(0)
                                
                                payment_data = {
                                    'payment_txn_id': payment_ret.TxnID.GetValue() if payment_ret.TxnID else payment_id,
                                    'payment_date': payment_ret.TxnDate.GetValue().strftime('%m-%d-%Y') if payment_ret.TxnDate else None,
                                    'amount_paid': float(payment_ret.Amount.GetValue()) if payment_ret.Amount else 0.0,
                                    'bank_account': payment_ret.CreditCardAccountRef.FullName.GetValue() if hasattr(payment_ret, 'CreditCardAccountRef') and payment_ret.CreditCardAccountRef and payment_ret.CreditCardAccountRef.FullName else 'Credit Card',
                                    'check_number': None  # Credit card payments don't have check numbers
                                }
                                
                                payments.append(payment_data)
                                total_paid += payment_data['amount_paid']
                        
                except Exception as e:
                    logger.warning(f"Failed to get details for payment {payment_id}: {e}")
                    continue
            
            # Return payment info structure
            return {
                'payments': payments,
                'amount_paid': total_paid,
                'payment_txn_ids': payment_txn_ids  # Keep for backward compatibility
            }
            
        except Exception as e:
            logger.error(f"Failed to get payment details: {e}")
            return {}
    
    def clear_and_readd_line_items(self, txn_id: str, edit_sequence: str, items_to_keep: List[Dict]) -> bool:
        """Clear all line items and re-add specific ones - for removing items"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            # Create modification request
            request_set = fast_qb_connection.create_request_set()
            bill_mod = request_set.AppendBillModRq()
            bill_mod.TxnID.SetValue(txn_id)
            bill_mod.EditSequence.SetValue(edit_sequence)
            
            # Clear all line items
            bill_mod.ClearItemLines.SetValue(True)
            
            # Re-add items to keep
            for item in items_to_keep:
                # Add each item back (except the ones being removed)
                item_line = bill_mod.ORItemLineModList.Append()
                item_line_mod = item_line.ItemLineMod
                
                # Use "-1" for re-adding (treat as new)
                item_line_mod.TxnLineID.SetValue("-1")
                
                # Set item details
                if item.get('item_name'):
                    item_line_mod.ItemRef.FullName.SetValue(item['item_name'])
                
                if item.get('description'):
                    item_line_mod.Desc.SetValue(item['description'])
                
                if item.get('quantity') is not None:
                    item_line_mod.Quantity.SetValue(float(item['quantity']))
                
                if item.get('cost') is not None:
                    item_line_mod.Cost.SetValue(float(item['cost']))
                
                if item.get('customer'):
                    item_line_mod.CustomerRef.FullName.SetValue(item['customer'])
                
                if item.get('billable_status') is not None:
                    item_line_mod.BillableStatus.SetValue(int(item['billable_status']))
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Failed to clear and re-add line items: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return False
            
            logger.info(f"Successfully cleared and re-added line items for bill {txn_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear and re-add line items: {e}")
            return False