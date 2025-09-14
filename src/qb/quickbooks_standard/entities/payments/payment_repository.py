"""
Payment Repository - Standard QuickBooks payment operations
Part of the quickbooks_standard layer - handles all direct QB SDK interactions for payments
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, date
from shared_utilities.fast_qb_connection import fast_qb_connection

logger = logging.getLogger(__name__)

class PaymentRepository:
    """Repository for QuickBooks Payment operations"""
    
    def __init__(self):
        """Initialize payment repository"""
        pass
    
    def create_bill_payment(self, 
                           vendor_list_id: str,
                           bill_txn_id: str,
                           amount: float,
                           bank_account_list_id: str,
                           payment_method: str = "Check",
                           payment_date: Optional[date] = None,
                           check_number: Optional[str] = None,
                           memo: Optional[str] = None) -> Dict:
        """
        Create a bill payment (check) in QuickBooks
        
        Args:
            vendor_list_id: ListID of the vendor
            bill_txn_id: Transaction ID of the bill to pay
            amount: Payment amount
            bank_account_list_id: Bank account ListID
            payment_method: Payment method (Check, Cash, Credit Card)
            payment_date: Date of payment (defaults to today)
            check_number: Optional check number
            memo: Optional memo for the payment
            
        Returns:
            Payment details dictionary with txn_id and status
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return {"success": False, "error": "Failed to connect to QuickBooks"}
            
            request_set = fast_qb_connection.create_request_set()
            
            # Create BillPaymentCheck
            payment_add = request_set.AppendBillPaymentCheckAddRq()
            
            # Set vendor
            payment_add.PayeeEntityRef.ListID.SetValue(vendor_list_id)
            
            # Set payment date
            if payment_date:
                import pywintypes
                pay_datetime = datetime.combine(payment_date, datetime.min.time())
                pay_date = pywintypes.Time(pay_datetime)
                payment_add.TxnDate.SetValue(pay_date)
            
            # Set bank account
            payment_add.BankAccountRef.ListID.SetValue(bank_account_list_id)
            
            # Set check print options - must use ORCheckPrint (either RefNumber OR IsToBePrinted)
            if check_number:
                # If check number provided, use it
                payment_add.ORCheckPrint.RefNumber.SetValue(str(check_number))
            else:
                # Otherwise set IsToBePrinted based on payment method
                payment_add.ORCheckPrint.IsToBePrinted.SetValue(payment_method == "Check")
            
            # Add memo if provided
            if memo:
                payment_add.Memo.SetValue(memo)
            
            # Apply payment to bill - this is the key to linking payment to bill
            applied_to = payment_add.AppliedToTxnAddList.Append()
            applied_to.TxnID.SetValue(bill_txn_id)
            applied_to.PaymentAmount.SetValue(amount)
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                # Get the payment details from response
                payment_txn_id = None
                ref_number = None
                
                # The response.Detail might be a BillPaymentCheckRet directly or wrapped
                if response.Detail:
                    payment = None
                    
                    # Check if it's wrapped in a list-like object with Count
                    if hasattr(response.Detail, 'Count'):
                        if response.Detail.Count > 0:
                            payment = response.Detail.GetAt(0)
                    else:
                        # It might be the payment object directly
                        payment = response.Detail
                    
                    if payment:
                        # Get Transaction ID
                        if hasattr(payment, 'TxnID') and payment.TxnID:
                            payment_txn_id = payment.TxnID.GetValue()
                        
                        # Get check/reference number
                        if hasattr(payment, 'RefNumber') and payment.RefNumber:
                            ref_number = payment.RefNumber.GetValue()
                
                logger.info(f"Created bill payment: TxnID={payment_txn_id}, Amount=${amount}")
                
                return {
                    "success": True,
                    "txn_id": payment_txn_id,
                    "bill_txn_id": bill_txn_id,
                    "amount": amount,
                    "payment_date": payment_date.isoformat() if payment_date else datetime.now().date().isoformat(),
                    "payment_method": payment_method,
                    "check_number": ref_number or check_number,
                    "bank_account_list_id": bank_account_list_id
                }
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to create bill payment: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": response.StatusCode
                }
                
        except Exception as e:
            logger.error(f"Exception creating bill payment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_bank_accounts(self) -> List[Dict]:
        """
        Get all bank accounts from QuickBooks
        
        Returns:
            List of bank account dictionaries
        """
        # Use hardcoded list of known bank accounts to avoid SDK AccountType bug
        # The SDK has a critical bug with AccountType that causes "invalid literal for int()" errors
        known_bank_accounts = [
            {"list_id": "800000CA-1701549330", "name": "1887 b"},
            {"list_id": "800000C0-1699359929", "name": "3841 for 8631card"},
            {"list_id": "800000C9-1701470222", "name": "8824 b"},
            {"list_id": "80000051-1402331221", "name": "Cuenta de Cash"},
            {"list_id": "80000061-1414451245", "name": "Suarez group1 - 8824"}
        ]
        
        logger.info(f"Using known bank accounts list ({len(known_bank_accounts)} accounts)")
        return known_bank_accounts
    
    def check_bill_payment_status(self, bill_txn_id: str) -> Dict:
        """
        Check if a bill is already paid and get payment details
        
        Args:
            bill_txn_id: Transaction ID of the bill
            
        Returns:
            Dictionary with payment status and linked payment details
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return {"success": False, "error": "Failed to connect to QuickBooks"}
            
            request_set = fast_qb_connection.create_request_set()
            
            # Query the bill
            bill_query = request_set.AppendBillQueryRq()
            bill_query.ORBillQuery.TxnIDList.Add(bill_txn_id)
            bill_query.IncludeLinkedTxns.SetValue(True)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail and response.Detail.Count > 0:
                bill_ret = response.Detail.GetAt(0)
                
                # Check IsPaid status
                is_paid = False
                if hasattr(bill_ret, 'IsPaid') and bill_ret.IsPaid:
                    is_paid = bill_ret.IsPaid.GetValue()
                
                # Get balance remaining
                balance = 0.0
                if hasattr(bill_ret, 'OpenAmount') and bill_ret.OpenAmount:
                    balance = float(bill_ret.OpenAmount.GetValue())
                
                # Get amount due
                amount_due = 0.0
                if hasattr(bill_ret, 'AmountDue') and bill_ret.AmountDue:
                    amount_due = float(bill_ret.AmountDue.GetValue())
                
                # Get linked transactions (payments)
                linked_payments = []
                if hasattr(bill_ret, 'LinkedTxnList') and bill_ret.LinkedTxnList:
                    for i in range(bill_ret.LinkedTxnList.Count):
                        linked_txn = bill_ret.LinkedTxnList.GetAt(i)
                        payment_info = {}
                        
                        if hasattr(linked_txn, 'TxnID') and linked_txn.TxnID:
                            payment_info['txn_id'] = linked_txn.TxnID.GetValue()
                        
                        if hasattr(linked_txn, 'TxnType') and linked_txn.TxnType:
                            payment_info['type'] = linked_txn.TxnType.GetValue()
                        
                        if hasattr(linked_txn, 'TxnDate') and linked_txn.TxnDate:
                            payment_info['date'] = str(linked_txn.TxnDate.GetValue())
                        
                        if hasattr(linked_txn, 'LinkType') and linked_txn.LinkType:
                            payment_info['link_type'] = linked_txn.LinkType.GetValue()
                        
                        if hasattr(linked_txn, 'Amount') and linked_txn.Amount:
                            payment_info['amount'] = float(linked_txn.Amount.GetValue())
                        
                        linked_payments.append(payment_info)
                
                return {
                    "success": True,
                    "is_paid": is_paid,
                    "amount_due": amount_due,
                    "balance_remaining": balance,
                    "linked_payments": linked_payments,
                    "payment_count": len(linked_payments)
                }
            else:
                return {
                    "success": False,
                    "error": "Bill not found"
                }
                
        except Exception as e:
            logger.error(f"Error checking bill payment status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_bill_payment(self,
                           payment_txn_id: str,
                           payment_date: Optional[date] = None,
                           bank_account_list_id: Optional[str] = None,
                           check_number: Optional[str] = None,
                           memo: Optional[str] = None) -> Dict:
        """
        Update an existing bill payment in QuickBooks
        
        Args:
            payment_txn_id: Transaction ID of the payment to update
            payment_date: New payment date (optional)
            bank_account_list_id: New bank account ListID (optional)
            check_number: New check number (optional)
            memo: New memo (optional)
            
        Returns:
            Updated payment details dictionary
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return {"success": False, "error": "Failed to connect to QuickBooks"}
            
            # First, query the existing payment to get EditSequence
            request_set = fast_qb_connection.create_request_set()
            query_rq = request_set.AppendBillPaymentCheckQueryRq()
            query_rq.ORTxnQuery.TxnIDList.Add(payment_txn_id)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Payment not found'
                return {"success": False, "error": error_msg}
            
            # Get the payment details
            payment_ret = None
            if response.Detail and hasattr(response.Detail, 'Count') and response.Detail.Count > 0:
                payment_ret = response.Detail.GetAt(0)
            
            if not payment_ret:
                return {"success": False, "error": "Payment not found"}
            
            # Get EditSequence
            edit_sequence = payment_ret.EditSequence.GetValue() if payment_ret.EditSequence else None
            if not edit_sequence:
                return {"success": False, "error": "Could not get EditSequence for payment"}
            
            # Create update request
            request_set = fast_qb_connection.create_request_set()
            update_rq = request_set.AppendBillPaymentCheckModRq()
            update_rq.TxnID.SetValue(payment_txn_id)
            update_rq.EditSequence.SetValue(edit_sequence)
            
            # Update fields that were provided
            if payment_date:
                import pywintypes
                pay_datetime = datetime.combine(payment_date, datetime.min.time())
                pay_date = pywintypes.Time(pay_datetime)
                update_rq.TxnDate.SetValue(pay_date)
            
            if bank_account_list_id:
                update_rq.BankAccountRef.ListID.SetValue(bank_account_list_id)
            
            if check_number is not None:
                # Use ORCheckPrint to set check number
                update_rq.ORCheckPrint.RefNumber.SetValue(str(check_number))
            
            if memo is not None:
                update_rq.Memo.SetValue(memo)
            
            # Process the update
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                # Get updated payment details
                updated_payment = response.Detail
                if updated_payment:
                    result = {
                        "success": True,
                        "txn_id": payment_txn_id,
                        "message": "Payment updated successfully"
                    }
                    
                    # Add updated details
                    if hasattr(updated_payment, 'TxnDate') and updated_payment.TxnDate:
                        result['payment_date'] = str(updated_payment.TxnDate.GetValue())
                    if hasattr(updated_payment, 'RefNumber') and updated_payment.RefNumber:
                        result['check_number'] = updated_payment.RefNumber.GetValue()
                    if hasattr(updated_payment, 'Memo') and updated_payment.Memo:
                        result['memo'] = updated_payment.Memo.GetValue()
                    
                    logger.info(f"Successfully updated payment: {payment_txn_id}")
                    return result
                else:
                    return {
                        "success": True,
                        "txn_id": payment_txn_id,
                        "message": "Payment updated successfully"
                    }
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to update payment: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": response.StatusCode
                }
                
        except Exception as e:
            logger.error(f"Exception updating payment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_payment(self, payment_txn_id: str) -> Dict:
        """
        Delete a bill payment check from QuickBooks
        
        Args:
            payment_txn_id: Transaction ID of the payment to delete
            
        Returns:
            Dictionary with success status
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return {"success": False, "error": "Failed to connect to QuickBooks"}
            
            request_set = fast_qb_connection.create_request_set()
            
            # Delete the payment
            delete_rq = request_set.AppendTxnDelRq()
            delete_rq.TxnDelType.SetValue(13)  # 13 = BillPaymentCheck
            delete_rq.TxnID.SetValue(payment_txn_id)
            
            # Process the delete request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Successfully deleted payment: {payment_txn_id}")
                return {
                    "success": True,
                    "message": f"Payment {payment_txn_id} deleted successfully"
                }
            else:
                # Return the error without voiding fallback
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else f'Error code {response.StatusCode}'
                logger.error(f"Failed to delete payment {payment_txn_id}: {error_msg}")
                return {
                    "success": False,
                    "error": f"Failed to delete payment: {error_msg}",
                    "error_code": response.StatusCode
                }
                
        except Exception as e:
            logger.error(f"Exception deleting payment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            fast_qb_connection.disconnect()
    
    def search_payments(self, search_term: Optional[str] = None, vendor_name: Optional[str] = None, max_results: int = 100) -> List[Dict]:
        """
        Search for payments using fuzzy matching across all fields
        
        Args:
            search_term: Optional search term to match against any field
            vendor_name: Optional specific vendor name filter
            
        Returns:
            List of matching payment dictionaries
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            query_rq = request_set.AppendBillPaymentCheckQueryRq()
            
            # If vendor name specified, get vendor ListID for filtering
            vendor_list_id = None
            if vendor_name:
                from quickbooks_standard.entities.vendors.vendor_repository import VendorRepository
                vendor_repo = VendorRepository()
                vendor = vendor_repo.find_vendor_fuzzy(vendor_name)
                
                if vendor:
                    vendor_list_id = vendor['list_id']
                    logger.info(f"Will filter payments by vendor '{vendor_name}' (ListID: {vendor_list_id})")
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            all_payments = []
            if response.StatusCode == 0:
                if response.Detail and hasattr(response.Detail, 'Count'):
                    total_count = response.Detail.Count
                    logger.info(f"Found {total_count} payment(s) in QuickBooks")
                    
                    # If filtering by vendor, we need to process all payments to find the vendor's payments
                    # Otherwise limit for performance
                    if vendor_name:
                        process_count = total_count  # Process all when filtering by vendor
                    else:
                        process_count = min(total_count, max_results * 2)  # Process more to allow for filtering
                    
                    for i in range(process_count):
                        payment_ret = response.Detail.GetAt(i)
                        
                        # Extract vendor list ID for filtering
                        vendor_list_id = None
                        if hasattr(payment_ret, 'PayeeEntityRef'):
                            if hasattr(payment_ret.PayeeEntityRef, 'ListID') and payment_ret.PayeeEntityRef.ListID:
                                vendor_list_id = payment_ret.PayeeEntityRef.ListID.GetValue()
                        
                        payment_data = {
                            'txn_id': payment_ret.TxnID.GetValue() if hasattr(payment_ret, 'TxnID') and payment_ret.TxnID else None,
                            'txn_date': str(payment_ret.TxnDate.GetValue()) if hasattr(payment_ret, 'TxnDate') and payment_ret.TxnDate else None,
                            'amount': float(payment_ret.Amount.GetValue()) if hasattr(payment_ret, 'Amount') and payment_ret.Amount else 0,
                            'ref_number': payment_ret.RefNumber.GetValue() if hasattr(payment_ret, 'RefNumber') and payment_ret.RefNumber else None,
                            'memo': payment_ret.Memo.GetValue() if hasattr(payment_ret, 'Memo') and payment_ret.Memo else None,
                            'vendor_name': payment_ret.PayeeEntityRef.FullName.GetValue() if hasattr(payment_ret, 'PayeeEntityRef') and hasattr(payment_ret.PayeeEntityRef, 'FullName') and payment_ret.PayeeEntityRef.FullName else None,
                            'vendor_list_id': vendor_list_id,
                            'bank_account': payment_ret.BankAccountRef.FullName.GetValue() if hasattr(payment_ret, 'BankAccountRef') and hasattr(payment_ret.BankAccountRef, 'FullName') and payment_ret.BankAccountRef.FullName else None,
                            'is_to_be_printed': payment_ret.IsToBePrinted.GetValue() if hasattr(payment_ret, 'IsToBePrinted') and payment_ret.IsToBePrinted else False
                        }
                    
                        # Get applied bills
                        if hasattr(payment_ret, 'AppliedToTxnList'):
                            applied_bills = []
                            for j in range(payment_ret.AppliedToTxnList.Count):
                                applied = payment_ret.AppliedToTxnList.GetAt(j)
                                applied_bills.append({
                                    'bill_txn_id': applied.TxnID.GetValue() if hasattr(applied, 'TxnID') else None,
                                    'amount': float(applied.Amount.GetValue()) if hasattr(applied, 'Amount') else 0
                                })
                            payment_data['applied_bills'] = applied_bills
                        
                        all_payments.append(payment_data)
            
            # Filter out voided payments (those with VOID or VOIDED in memo)
            non_voided_payments = []
            for payment in all_payments:
                memo = payment.get('memo', '')
                if memo and ('VOID' in memo.upper()):
                    logger.debug(f"Skipping voided payment: {payment.get('txn_id')}")
                    continue
                non_voided_payments.append(payment)
            all_payments = non_voided_payments
            
            # Filter by vendor if specified
            if vendor_name and all_payments:
                # Get vendor ListID for filtering
                from quickbooks_standard.entities.vendors.vendor_repository import VendorRepository
                vendor_repo = VendorRepository()
                vendor = vendor_repo.find_vendor_fuzzy(vendor_name)
                
                if vendor:
                    vendor_list_id = vendor.get('list_id')
                    filtered_payments = []
                    
                    # Debug: Check first few payments
                    if all_payments and logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"First 3 payments vendor_list_id values: {[p.get('vendor_list_id') for p in all_payments[:3]]}")
                        logger.debug(f"Looking for vendor_list_id: {vendor_list_id}")
                    
                    for payment in all_payments:
                        if payment.get('vendor_list_id') == vendor_list_id:
                            filtered_payments.append(payment)
                    all_payments = filtered_payments
                    logger.info(f"Filtered to {len(all_payments)} payment(s) for vendor '{vendor_name}' (ListID: {vendor_list_id})")
                else:
                    logger.warning(f"Vendor '{vendor_name}' not found - cannot filter payments")
                    all_payments = []
            
            # Apply fuzzy search if search_term provided
            if search_term and all_payments:
                search_lower = search_term.lower()
                matched_payments = []
                
                for payment in all_payments:
                    # Check if search term matches any field
                    match_found = False
                    
                    # Search in all text fields
                    searchable_fields = [
                        str(payment.get('txn_id', '')),
                        str(payment.get('txn_date', '')),
                        str(payment.get('amount', '')),
                        str(payment.get('ref_number', '')),
                        str(payment.get('memo', '')),
                        str(payment.get('vendor_name', '')),
                        str(payment.get('bank_account', ''))
                    ]
                    
                    for field in searchable_fields:
                        if search_lower in field.lower():
                            match_found = True
                            break
                    
                    # Also check in applied bills
                    if not match_found and payment.get('applied_bills'):
                        for bill in payment['applied_bills']:
                            if search_lower in str(bill.get('bill_txn_id', '')).lower():
                                match_found = True
                                break
                    
                    if match_found:
                        matched_payments.append(payment)
                
                return matched_payments[:max_results]
            
            return all_payments[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching payments: {e}")
            return []
    
    def find_payments_by_vendor(self, vendor_name: str) -> List[Dict]:
        """
        Find all payments made to a vendor
        
        Args:
            vendor_name: Name of the vendor
            
        Returns:
            List of payment dictionaries
        """
        # Use the comprehensive search method with vendor filter
        return self.search_payments(vendor_name=vendor_name)