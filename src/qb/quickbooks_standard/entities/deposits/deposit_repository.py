"""Repository for QuickBooks Deposit operations"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from shared_utilities.fast_qb_connection import fast_qb_connection

logger = logging.getLogger(__name__)

class DepositRepository:
    """Repository for deposit operations"""
    
    def search_deposits(self,
                       date_from: Optional[datetime] = None,
                       date_to: Optional[datetime] = None,
                       bank_account: Optional[str] = None,
                       amount: Optional[float] = None,
                       max_returned: int = 100) -> List[Dict]:
        """Search for deposits with various filters
        
        This includes both:
        1. Regular Deposit transactions (DepositAdd)
        2. Direct ReceivePayments that go straight to bank accounts
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            deposit_query = request_set.AppendDepositQueryRq()
            
            # Note: DepositQuery doesn't support filters in the same way as other queries
            # We'll have to get all deposits and filter in memory
            # Apply date filter if provided - NOT SUPPORTED BY SDK
            # Apply account filter if provided - NOT SUPPORTED BY SDK
            
            # Set max returned only if no filters are applied
            if not (date_from or date_to or bank_account):
                deposit_query.MaxReturned.SetValue(max_returned)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to search deposits: {error_msg}")
                return []
            
            if not response.Detail:
                return []
            
            deposits = []
            for i in range(response.Detail.Count):
                deposit_ret = response.Detail.GetAt(i)
                deposit_data = self._parse_deposit_from_sdk(deposit_ret)
                if deposit_data:
                    # Apply filters in memory
                    include = True
                    
                    # Filter by date if specified
                    if date_from or date_to:
                        deposit_date_str = deposit_data.get('txn_date')
                        if deposit_date_str:
                            # Parse the date string
                            from datetime import datetime
                            try:
                                # Handle various date formats
                                if '+' in deposit_date_str:
                                    deposit_date_str = deposit_date_str.split('+')[0]
                                if 'T' in deposit_date_str:
                                    deposit_date = datetime.fromisoformat(deposit_date_str)
                                else:
                                    deposit_date = datetime.strptime(deposit_date_str, '%Y-%m-%d')
                                
                                if date_from and deposit_date < date_from:
                                    include = False
                                if date_to and deposit_date > date_to:
                                    include = False
                            except:
                                pass
                    
                    # Filter by bank account if specified
                    if include and bank_account:
                        deposit_account = deposit_data.get('deposit_to_account', '')
                        if bank_account.lower() not in deposit_account.lower():
                            include = False
                    
                    # Filter by amount if specified
                    if include and amount is not None:
                        if abs(deposit_data.get('total', 0) - amount) > 0.01:
                            include = False
                    
                    if include:
                        deposits.append(deposit_data)
            
            # Also search for direct ReceivePayments that go to bank accounts
            logger.info("Searching for direct payments to bank accounts...")
            direct_payments = self._search_direct_payments(date_from, date_to, bank_account, amount, max_returned)
            deposits.extend(direct_payments)
            
            # Sort by date (newest first)
            deposits.sort(key=lambda x: x.get('txn_date', ''), reverse=True)
            
            return deposits
            
        except Exception as e:
            logger.error(f"Failed to search deposits: {e}")
            return []
    
    def get_deposit(self, txn_id: str) -> Optional[Dict]:
        """Get a specific deposit by transaction ID"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            deposit_query = request_set.AppendDepositQueryRq()
            
            # Query by TxnID
            deposit_query.ORTxnQuery.TxnIDList.Add(txn_id)
            deposit_query.IncludeLineItems.SetValue(True)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to get deposit {txn_id}: {error_msg}")
                return None
            
            if not response.Detail or response.Detail.Count == 0:
                logger.info(f"Deposit {txn_id} not found")
                return None
            
            deposit_ret = response.Detail.GetAt(0)
            return self._parse_deposit_from_sdk(deposit_ret)
            
        except Exception as e:
            logger.error(f"Failed to get deposit {txn_id}: {e}")
            return None
    
    def _parse_deposit_from_sdk(self, deposit_ret) -> Optional[Dict]:
        """Parse deposit data from SDK response"""
        try:
            deposit_data = {
                'txn_id': deposit_ret.TxnID.GetValue() if hasattr(deposit_ret, 'TxnID') and deposit_ret.TxnID else None,
                'txn_number': deposit_ret.TxnNumber.GetValue() if hasattr(deposit_ret, 'TxnNumber') and deposit_ret.TxnNumber else None,
                'txn_date': deposit_ret.TxnDate.GetValue() if hasattr(deposit_ret, 'TxnDate') and deposit_ret.TxnDate else None,
                'total': 0.0,
                'memo': None,
                'deposit_to_account': None,
                'deposit_lines': []
            }
            
            # Get total
            if hasattr(deposit_ret, 'DepositTotal') and deposit_ret.DepositTotal:
                deposit_data['total'] = float(deposit_ret.DepositTotal.GetValue())
            
            # Get memo
            if hasattr(deposit_ret, 'Memo') and deposit_ret.Memo:
                deposit_data['memo'] = deposit_ret.Memo.GetValue()
            
            # Get deposit to account
            if hasattr(deposit_ret, 'DepositToAccountRef') and deposit_ret.DepositToAccountRef:
                deposit_data['deposit_to_account'] = deposit_ret.DepositToAccountRef.FullName.GetValue()
            
            # Parse deposit lines
            if hasattr(deposit_ret, 'DepositLineList') and deposit_ret.DepositLineList:
                for i in range(deposit_ret.DepositLineList.Count):
                    line = deposit_ret.DepositLineList.GetAt(i)
                    line_data = {
                        'txn_line_id': line.TxnLineID.GetValue() if hasattr(line, 'TxnLineID') and line.TxnLineID else None,
                        'amount': float(line.Amount.GetValue()) if hasattr(line, 'Amount') and line.Amount else 0.0,
                        'memo': line.Memo.GetValue() if hasattr(line, 'Memo') and line.Memo else None,
                    }
                    
                    # Get entity (customer/vendor/etc)
                    if hasattr(line, 'EntityRef') and line.EntityRef:
                        line_data['entity'] = line.EntityRef.FullName.GetValue()
                    
                    # Get account
                    if hasattr(line, 'AccountRef') and line.AccountRef:
                        line_data['account'] = line.AccountRef.FullName.GetValue()
                    
                    # Get check number if this is a check deposit
                    if hasattr(line, 'CheckNumber') and line.CheckNumber:
                        line_data['check_number'] = line.CheckNumber.GetValue()
                    
                    # Get payment method
                    if hasattr(line, 'PaymentMethodRef') and line.PaymentMethodRef:
                        line_data['payment_method'] = line.PaymentMethodRef.FullName.GetValue()
                    
                    deposit_data['deposit_lines'].append(line_data)
            
            # Time created and modified
            if hasattr(deposit_ret, 'TimeCreated') and deposit_ret.TimeCreated:
                deposit_data['time_created'] = deposit_ret.TimeCreated.GetValue()
            
            if hasattr(deposit_ret, 'TimeModified') and deposit_ret.TimeModified:
                deposit_data['time_modified'] = deposit_ret.TimeModified.GetValue()
            
            return deposit_data
            
        except Exception as e:
            logger.error(f"Failed to parse deposit: {e}")
            return None
    
    def create_customer_payment_deposit(self,
                                       deposit_to_account: str,
                                       payment_txn_id: str,
                                       payment_txn_line_id: Optional[str] = None,
                                       txn_date: Optional[str] = None,
                                       memo: Optional[str] = None) -> Optional[Dict]:
        """Create a deposit to move customer payment from Undeposited Funds to bank account
        
        Args:
            deposit_to_account: Target bank account (e.g., "1887 b")
            payment_txn_id: Transaction ID of the payment to deposit
            payment_txn_line_id: Optional line ID (will query if not provided)
            txn_date: Optional deposit date (MM-DD-YYYY)
            memo: Optional memo
            
        Returns:
            Created deposit details or None if failed
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            # If payment_txn_line_id not provided, query for it
            if not payment_txn_line_id:
                payment_txn_line_id = self._get_payment_line_id(payment_txn_id)
                if not payment_txn_line_id:
                    logger.error(f"Could not find line ID for payment {payment_txn_id}")
                    return None
            
            request_set = fast_qb_connection.create_request_set()
            deposit_add = request_set.AppendDepositAddRq()
            
            # Set target bank account
            deposit_add.DepositToAccountRef.FullName.SetValue(deposit_to_account)
            
            # Set date if provided
            if txn_date:
                deposit_add.TxnDate.SetValue(txn_date)
            
            # Set memo if provided  
            if memo:
                deposit_add.Memo.SetValue(memo)
            
            # Add the payment line
            deposit_line = deposit_add.DepositLineAddList.Append()
            
            # Reference the payment transaction and line
            if payment_txn_id and payment_txn_line_id:
                # Use the ORDepositLineAdd choice for payment reference
                deposit_line.ORDepositLineAdd.PaymentLine.PaymentTxnID.SetValue(payment_txn_id)
                deposit_line.ORDepositLineAdd.PaymentLine.PaymentTxnLineID.SetValue(payment_txn_line_id)
            else:
                logger.error(f"Missing payment reference: TxnID={payment_txn_id}, LineID={payment_txn_line_id}")
                return None
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to create deposit: {error_msg}")
                return None
            
            if not response.Detail:
                logger.error("No deposit details returned")
                return None
            
            deposit_ret = response.Detail.GetAt(0)
            return self._parse_deposit_from_sdk(deposit_ret)
            
        except Exception as e:
            logger.error(f"Failed to create customer payment deposit: {e}")
            return None
    
    def _get_payment_line_id(self, payment_txn_id: str) -> Optional[str]:
        """Query for payment line ID using ReceivePaymentToDepositQuery
        
        Args:
            payment_txn_id: Transaction ID of the payment
            
        Returns:
            Payment line ID or None if not found
        """
        try:
            if not fast_qb_connection.connect():
                return None
            
            request_set = fast_qb_connection.create_request_set()
            query = request_set.AppendReceivePaymentToDepositQueryRq()
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to query payments to deposit: {error_msg}")
                # Payment might not be in Undeposited Funds - check if already deposited
                logger.info(f"Payment {payment_txn_id} may already be deposited or not in Undeposited Funds")
                return None
            
            if not response.Detail:
                logger.info("No payments found in Undeposited Funds")
                return None
            
            # Search through payments to find matching TxnID
            logger.info(f"Searching {response.Detail.Count} payments for TxnID {payment_txn_id}")
            for i in range(response.Detail.Count):
                payment = response.Detail.GetAt(i)
                if hasattr(payment, 'TxnID') and payment.TxnID:
                    txn_id = payment.TxnID.GetValue()
                    logger.debug(f"Found payment TxnID: {txn_id}")
                    if txn_id == payment_txn_id:
                        # Found the payment, get its line ID
                        if hasattr(payment, 'TxnLineID') and payment.TxnLineID:
                            line_id = payment.TxnLineID.GetValue()
                            logger.info(f"Found payment {payment_txn_id} with line ID: {line_id}")
                            return line_id
                        else:
                            # Payment found but no line ID - use default
                            logger.info(f"Found payment {payment_txn_id} but no line ID, using default -1")
                            return "-1"
            
            logger.warning(f"Payment {payment_txn_id} not found in Undeposited Funds")
            logger.info("This payment may have already been deposited or applied differently")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get payment line ID: {e}")
            return None
    
    def _search_direct_payments(self,
                               date_from: Optional[datetime] = None,
                               date_to: Optional[datetime] = None,
                               bank_account: Optional[str] = None,
                               amount: Optional[float] = None,
                               max_returned: int = 100) -> List[Dict]:
        """Search for ReceivePayments that went directly to bank accounts
        
        These are payments that bypassed Undeposited Funds and went straight to a bank account
        """
        direct_payments = []
        
        try:
            if not fast_qb_connection.connect():
                return []
            
            request_set = fast_qb_connection.create_request_set()
            payment_query = request_set.AppendReceivePaymentQueryRq()
            
            # Apply date filters if provided (use TxnDateRangeFilter for payments)
            if date_from or date_to:
                if date_from:
                    payment_query.TxnDateRangeFilter.FromTxnDate.SetValue(date_from)
                if date_to:
                    payment_query.TxnDateRangeFilter.ToTxnDate.SetValue(date_to)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.warning(f"Failed to search payments: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            if not response.Detail:
                return []
            
            # Process each payment
            for i in range(response.Detail.Count):
                payment = response.Detail.GetAt(i)
                
                # Check if this payment went directly to a bank account
                if hasattr(payment, 'DepositToAccountRef') and payment.DepositToAccountRef:
                    deposit_account = payment.DepositToAccountRef.FullName.GetValue()
                    
                    # Skip if it's Undeposited Funds (not a direct deposit)
                    if "undeposited" in deposit_account.lower():
                        continue
                    
                    # Apply filters
                    include = True
                    
                    # Filter by bank account if specified
                    if bank_account and bank_account.lower() not in deposit_account.lower():
                        include = False
                    
                    # Filter by amount if specified
                    if include and amount is not None:
                        payment_amount = float(payment.TotalAmount.GetValue()) if hasattr(payment, 'TotalAmount') and payment.TotalAmount else 0.0
                        if abs(payment_amount - amount) > 0.01:
                            include = False
                    
                    # Filter by date if specified
                    if include and (date_from or date_to):
                        payment_date_str = payment.TxnDate.GetValue() if hasattr(payment, 'TxnDate') and payment.TxnDate else None
                        if payment_date_str:
                            try:
                                # Handle timezone in date string
                                if '+' in payment_date_str:
                                    payment_date_str = payment_date_str.split('+')[0]
                                if 'T' in payment_date_str:
                                    payment_date = datetime.fromisoformat(payment_date_str)
                                else:
                                    payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d')
                                
                                if date_from and payment_date < date_from:
                                    include = False
                                if date_to and payment_date > date_to:
                                    include = False
                            except:
                                pass
                    
                    if include:
                        # Create deposit-like record for this direct payment
                        payment_data = {
                            'txn_id': payment.TxnID.GetValue() if hasattr(payment, 'TxnID') and payment.TxnID else None,
                            'txn_number': payment.RefNumber.GetValue() if hasattr(payment, 'RefNumber') and payment.RefNumber else None,
                            'txn_date': payment.TxnDate.GetValue() if hasattr(payment, 'TxnDate') and payment.TxnDate else None,
                            'total': float(payment.TotalAmount.GetValue()) if hasattr(payment, 'TotalAmount') and payment.TotalAmount else 0.0,
                            'memo': payment.Memo.GetValue() if hasattr(payment, 'Memo') and payment.Memo else None,
                            'deposit_to_account': deposit_account,
                            'deposit_type': 'Direct Payment',  # Mark as direct payment
                            'customer': payment.CustomerRef.FullName.GetValue() if hasattr(payment, 'CustomerRef') and payment.CustomerRef else None,
                            'check_number': payment.RefNumber.GetValue() if hasattr(payment, 'RefNumber') and payment.RefNumber else None
                        }
                        
                        # Add time created/modified
                        if hasattr(payment, 'TimeCreated') and payment.TimeCreated:
                            payment_data['time_created'] = payment.TimeCreated.GetValue()
                        if hasattr(payment, 'TimeModified') and payment.TimeModified:
                            payment_data['time_modified'] = payment.TimeModified.GetValue()
                        
                        direct_payments.append(payment_data)
                        
                        # Stop if we've reached max_returned
                        if len(direct_payments) >= max_returned:
                            break
            
            logger.info(f"Found {len(direct_payments)} direct payments to bank accounts")
            return direct_payments
            
        except Exception as e:
            logger.error(f"Failed to search direct payments: {e}")
            return []