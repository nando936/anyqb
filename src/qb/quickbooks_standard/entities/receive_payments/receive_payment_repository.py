"""
Repository for managing receive payment (invoice payment) operations in QuickBooks
Handles CRUD operations for invoice payments using QBFC SDK
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import pywintypes
from shared_utilities.fast_qb_connection import fast_qb_connection

logger = logging.getLogger(__name__)

class ReceivePaymentRepository:
    """Repository for managing invoice payments in QuickBooks"""
    
    def __init__(self):
        """Initialize receive payment repository"""
        self.connection = fast_qb_connection
    
    def create_payment(self, payment_data: Dict) -> Optional[Dict]:
        """
        Create a new payment for an invoice
        
        Args:
            payment_data: Dictionary containing:
                - customer_name: Name of the customer
                - amount: Payment amount
                - invoice_ref_number: Invoice reference number (optional)
                - payment_method: Payment method (Check, Cash, Credit Card, etc.)
                - check_number: Check number if applicable
                - deposit_account: Account to deposit payment
                - memo: Payment memo
                - date: Payment date
        
        Returns:
            Created payment details or None if failed
        """
        try:
            if not self.connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = self.connection.create_request_set()
            payment_add = request_set.AppendReceivePaymentAddRq()
            
            # Set customer
            payment_add.CustomerRef.FullName.SetValue(payment_data.get('customer_name'))
            
            # Set payment date
            payment_date = payment_data.get('date', datetime.now())
            if isinstance(payment_date, str):
                # Parse date string
                for fmt in ['%m-%d-%Y', '%m/%d/%Y', '%Y-%m-%d']:
                    try:
                        payment_date = datetime.strptime(payment_date, fmt)
                        break
                    except:
                        continue
            payment_add.TxnDate.SetValue(pywintypes.Time(payment_date))
            
            # Set amount
            payment_add.TotalAmount.SetValue(payment_data.get('amount', 0.0))
            
            # Set payment method if provided
            if payment_data.get('payment_method'):
                payment_add.PaymentMethodRef.FullName.SetValue(payment_data['payment_method'])
            
            # Set check number if provided
            if payment_data.get('check_number'):
                payment_add.RefNumber.SetValue(str(payment_data['check_number']))
            
            # Set deposit account if provided
            if payment_data.get('deposit_account'):
                payment_add.DepositToAccountRef.FullName.SetValue(payment_data['deposit_account'])
            
            # Set memo if provided
            if payment_data.get('memo'):
                payment_add.Memo.SetValue(payment_data['memo'])
            
            # Apply to specific invoice if provided
            if payment_data.get('invoice_ref_number') or payment_data.get('invoice_txn_id'):
                # Apply to specific invoice
                invoice_txn_id = payment_data.get('invoice_txn_id')
                
                # If we have ref number but no txn_id, look it up
                if not invoice_txn_id and payment_data.get('invoice_ref_number'):
                    # Find invoice by ref number to get TxnID
                    from quickbooks_standard.entities.invoices.invoice_repository import InvoiceRepository
                    invoice_repo = InvoiceRepository()
                    
                    # Get invoice by ref number directly
                    inv = invoice_repo.get_invoice(ref_number=payment_data['invoice_ref_number'])
                    
                    if inv:
                        invoice_txn_id = inv.get('txn_id')
                        balance = inv.get('balance', 0)
                        logger.info(f"Found invoice TxnID {invoice_txn_id} for ref number {payment_data['invoice_ref_number']}, Balance: ${balance}")
                        
                        # Check if invoice is already paid
                        if balance <= 0:
                            logger.error(f"Invoice {payment_data['invoice_ref_number']} is already fully paid (Balance: ${balance})")
                            return None  # FAIL - cannot apply payment to paid invoice
                    
                    if not invoice_txn_id and payment_data.get('invoice_ref_number'):
                        # Invoice not found
                        logger.error(f"Invoice {payment_data['invoice_ref_number']} not found for customer {customer_name}")
                        return None  # FAIL - invoice not found
                
                if invoice_txn_id:
                    # Use ORApplyPayment structure discovered by SDK explorer
                    try:
                        logger.info(f"Applying payment to invoice TxnID: {invoice_txn_id}")
                        
                        # Method 1: Try AppliedToTxnAddList
                        if hasattr(payment_add, 'ORApplyPayment'):
                            or_apply = payment_add.ORApplyPayment
                            
                            # Check if we can use AppliedToTxnAddList
                            if hasattr(or_apply, 'AppliedToTxnAddList'):
                                applied_list = or_apply.AppliedToTxnAddList
                                applied_to = applied_list.Append()
                                applied_to.TxnID.SetValue(invoice_txn_id)
                                applied_to.PaymentAmount.SetValue(payment_data.get('amount', 0.0))
                                logger.info(f"Applied payment to invoice using AppliedToTxnAddList")
                            # Method 2: Try IsAutoApply
                            elif hasattr(or_apply, 'IsAutoApply'):
                                or_apply.IsAutoApply.SetValue(True)
                                logger.info("Set IsAutoApply=True to auto-apply to open invoices")
                            else:
                                logger.warning("ORApplyPayment structure doesn't have expected fields")
                        else:
                            logger.warning("ORApplyPayment not available in SDK")
                            
                    except Exception as e:
                        logger.error(f"Failed to apply payment to invoice: {e}")
                        logger.info("Payment will be created as unapplied credit")
            else:
                # No invoice specified - set IsAutoApply to false for unapplied credit
                logger.info("Creating unapplied payment (no invoice specified)")
                if hasattr(payment_add, 'ORApplyPayment'):
                    or_apply = payment_add.ORApplyPayment
                    if hasattr(or_apply, 'IsAutoApply'):
                        or_apply.IsAutoApply.SetValue(False)
                        logger.info("Set IsAutoApply=False for unapplied credit")
            
            # Process the request
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Failed to create payment: {response.StatusMessage}")
                return None
            
            # Parse the created payment
            payment_ret = response.Detail
            return self._parse_payment(payment_ret)
            
        except Exception as e:
            logger.error(f"Failed to create invoice payment: {e}")
            return None
    
    def get_payment(self, txn_id: str) -> Optional[Dict]:
        """
        Get a specific payment by transaction ID
        
        Args:
            txn_id: Transaction ID of the payment
        
        Returns:
            Payment details or None if not found
        """
        try:
            if not self.connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = self.connection.create_request_set()
            payment_query = request_set.AppendReceivePaymentQueryRq()
            
            # Query by TxnID
            payment_query.ORTxnQuery.TxnIDList.Add(txn_id)
            payment_query.IncludeLineItems.SetValue(True)
            
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Query failed: {response.StatusMessage}")
                return None
            
            if not response.Detail or response.Detail.Count == 0:
                logger.error(f"Payment {txn_id} not found")
                return None
            
            # Parse the payment
            payment_ret = response.Detail.GetAt(0)
            return self._parse_payment(payment_ret)
            
        except Exception as e:
            logger.error(f"Failed to get payment {txn_id}: {e}")
            return None
    
    def find_payments_by_customer(self, customer_name: str) -> List[Dict]:
        """
        Find all payments for a customer
        
        Args:
            customer_name: Name of the customer
        
        Returns:
            List of payment details
        """
        try:
            if not self.connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = self.connection.create_request_set()
            payment_query = request_set.AppendReceivePaymentQueryRq()
            
            # Filter by customer
            entity_filter = payment_query.ORTxnQuery.TxnFilter.EntityFilter
            entity_filter.OREntityFilter.FullNameList.Add(customer_name)
            
            payment_query.IncludeLineItems.SetValue(True)
            
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Query failed: {response.StatusMessage}")
                return []
            
            if not response.Detail:
                return []
            
            payments = []
            for i in range(response.Detail.Count):
                payment_ret = response.Detail.GetAt(i)
                payment_data = self._parse_payment(payment_ret)
                if payment_data:
                    payments.append(payment_data)
            
            return payments
            
        except Exception as e:
            logger.error(f"Failed to find payments for customer {customer_name}: {e}")
            return []
    
    def update_payment(self, txn_id: str, updates: Dict) -> Optional[Dict]:
        """
        Update an existing payment
        
        Args:
            txn_id: Transaction ID of the payment to update
            updates: Dictionary of fields to update
        
        Returns:
            Updated payment details or None if failed
        """
        try:
            # Get existing payment first for edit sequence
            existing = self.get_payment(txn_id)
            if not existing:
                logger.error(f"Payment {txn_id} not found for update")
                return None
            
            if not self.connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = self.connection.create_request_set()
            payment_mod = request_set.AppendReceivePaymentModRq()
            
            # Set the transaction ID and edit sequence
            payment_mod.TxnID.SetValue(txn_id)
            payment_mod.EditSequence.SetValue(existing['edit_sequence'])
            
            # Update fields
            if 'amount' in updates:
                payment_mod.TotalAmount.SetValue(updates['amount'])
            
            if 'payment_method' in updates:
                payment_mod.PaymentMethodRef.FullName.SetValue(updates['payment_method'])
            
            if 'check_number' in updates:
                payment_mod.RefNumber.SetValue(str(updates['check_number']))
            
            if 'memo' in updates:
                payment_mod.Memo.SetValue(updates['memo'])
            
            if 'date' in updates:
                payment_date = updates['date']
                if isinstance(payment_date, str):
                    for fmt in ['%m-%d-%Y', '%m/%d/%Y', '%Y-%m-%d']:
                        try:
                            payment_date = datetime.strptime(payment_date, fmt)
                            break
                        except:
                            continue
                payment_mod.TxnDate.SetValue(pywintypes.Time(payment_date))
            
            # Process the request
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Failed to update payment: {response.StatusMessage}")
                return None
            
            # Return the updated payment
            return self.get_payment(txn_id)
            
        except Exception as e:
            logger.error(f"Failed to update payment {txn_id}: {e}")
            return None
    
    def delete_payment(self, txn_id: str) -> bool:
        """
        Delete a payment from QuickBooks
        
        Args:
            txn_id: Transaction ID of the payment to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing payment first for edit sequence
            existing = self.get_payment(txn_id)
            if not existing:
                logger.error(f"Payment {txn_id} not found for deletion")
                return False
            
            if not self.connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            request_set = self.connection.create_request_set()
            
            # Create delete request
            delete_req = request_set.AppendTxnDelRq()
            delete_req.TxnDelType.SetValue(18)  # ReceivePayment type
            delete_req.TxnID.SetValue(txn_id)
            
            # Process the request
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Failed to delete payment: {response.StatusMessage}")
                return False
            
            logger.info(f"Successfully deleted payment {txn_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete payment {txn_id}: {e}")
            return False
    
    def _parse_payment(self, payment_ret) -> Optional[Dict]:
        """
        Parse payment data from SDK response
        
        Args:
            payment_ret: ReceivePaymentRet object from SDK
        
        Returns:
            Parsed payment dictionary
        """
        try:
            payment_data = {
                'txn_id': None,
                'edit_sequence': None,
                'txn_date': None,
                'ref_number': None,
                'customer_name': None,
                'amount': 0.0,
                'payment_method': None,
                'deposit_account': None,
                'memo': None,
                'unapplied_amount': 0.0,
                'applied_to_txns': []
            }
            
            # Safely get each value
            if hasattr(payment_ret, 'TxnID') and payment_ret.TxnID:
                try:
                    payment_data['txn_id'] = payment_ret.TxnID.GetValue()
                except:
                    pass
            
            if hasattr(payment_ret, 'EditSequence') and payment_ret.EditSequence:
                try:
                    payment_data['edit_sequence'] = payment_ret.EditSequence.GetValue()
                except:
                    pass
            
            if hasattr(payment_ret, 'TxnDate') and payment_ret.TxnDate:
                try:
                    payment_data['txn_date'] = payment_ret.TxnDate.GetValue()
                except:
                    pass
            
            if hasattr(payment_ret, 'RefNumber') and payment_ret.RefNumber:
                try:
                    payment_data['ref_number'] = payment_ret.RefNumber.GetValue()
                except:
                    pass
            
            if hasattr(payment_ret, 'TotalAmount') and payment_ret.TotalAmount:
                try:
                    payment_data['amount'] = payment_ret.TotalAmount.GetValue()
                except:
                    pass
            
            if hasattr(payment_ret, 'Memo') and payment_ret.Memo:
                try:
                    payment_data['memo'] = payment_ret.Memo.GetValue()
                except:
                    pass
            
            if hasattr(payment_ret, 'UnusedPayment') and payment_ret.UnusedPayment:
                try:
                    payment_data['unapplied_amount'] = payment_ret.UnusedPayment.GetValue()
                except:
                    pass
            
            # Get customer name
            if hasattr(payment_ret, 'CustomerRef') and payment_ret.CustomerRef:
                try:
                    payment_data['customer_name'] = payment_ret.CustomerRef.FullName.GetValue()
                except:
                    pass
            
            # Get payment method
            if hasattr(payment_ret, 'PaymentMethodRef') and payment_ret.PaymentMethodRef:
                try:
                    payment_data['payment_method'] = payment_ret.PaymentMethodRef.FullName.GetValue()
                except:
                    pass
            
            # Get deposit account
            if hasattr(payment_ret, 'DepositToAccountRef') and payment_ret.DepositToAccountRef:
                try:
                    payment_data['deposit_account'] = payment_ret.DepositToAccountRef.FullName.GetValue()
                except:
                    pass
            
            # Get applied transactions
            if hasattr(payment_ret, 'AppliedToTxnRetList') and payment_ret.AppliedToTxnRetList:
                try:
                    for i in range(payment_ret.AppliedToTxnRetList.Count):
                        applied = payment_ret.AppliedToTxnRetList.GetAt(i)
                        applied_data = {
                            'txn_id': applied.TxnID.GetValue() if hasattr(applied, 'TxnID') else None,
                            'txn_type': applied.TxnType.GetValue() if hasattr(applied, 'TxnType') else None,
                            'txn_date': applied.TxnDate.GetValue() if hasattr(applied, 'TxnDate') else None,
                            'ref_number': applied.RefNumber.GetValue() if hasattr(applied, 'RefNumber') else None,
                            'amount': applied.Amount.GetValue() if hasattr(applied, 'Amount') else 0.0
                        }
                        payment_data['applied_to_txns'].append(applied_data)
                except Exception as e:
                    logger.debug(f"No applied transactions or error parsing: {e}")
            
            return payment_data
            
        except Exception as e:
            logger.error(f"Failed to parse payment: {e}")
            return None