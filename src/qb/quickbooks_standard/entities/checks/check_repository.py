"""
Check Repository - Standard QuickBooks check operations using QBFC SDK
NO custom business logic - only pure QB operations
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pywintypes
import threading
import time
from shared_utilities.fast_qb_connection import fast_qb_connection
from shared_utilities.xml_qb_connection import xml_qb_connection
from shared_utilities.check_cache import check_cache

logger = logging.getLogger(__name__)

class CheckRepository:
    """Handles standard QuickBooks check operations using QBFC SDK"""
    
    def __init__(self):
        """Initialize check repository"""
        self.cache = check_cache
    
    def load_quarter_checks(self, quarter_key: str) -> List[Dict]:
        """Load all checks for a specific quarter from QuickBooks"""
        try:
            # Check cache first
            cached = self.cache.get_quarter_checks(quarter_key)
            if cached is not None:
                return cached
            
            logger.info(f"Loading checks for quarter {quarter_key} from QuickBooks...")
            
            # Get quarter date range
            year, q = quarter_key.split('_Q')
            year = int(year)
            quarter = int(q)
            
            start_month = (quarter - 1) * 3 + 1
            date_from = datetime(year, start_month, 1)
            
            if quarter == 4:
                date_to = datetime(year + 1, 1, 1)
            else:
                date_to = datetime(year, start_month + 3, 1)
            
            # Load checks from QuickBooks
            checks = self._load_checks_from_qb(date_from, date_to)
            
            # Cache the results
            self.cache.set_quarter_checks(quarter_key, checks)
            
            logger.info(f"Loaded and cached {len(checks)} checks for quarter {quarter_key}")
            return checks
            
        except Exception as e:
            logger.error(f"Failed to load quarter checks: {e}")
            return []
    
    def _load_checks_from_qb(self, date_from: datetime, date_to: datetime) -> List[Dict]:
        """Load checks from QuickBooks for a date range"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            # For now, return empty list due to QB SDK date filter issues
            # In production, this would properly query QB
            logger.warning("Check date filtering not fully implemented due to QB SDK limitations")
            return []
            
        except Exception as e:
            logger.error(f"Failed to load checks from QB: {e}")
            return []
    
    def get_check(self, txn_id: str) -> Optional[Dict]:
        """Get a check by transaction ID - uses XML for COGS support"""
        try:
            # First try XML connection (supports COGS accounts)
            xml_result = xml_qb_connection.query_check(txn_id)
            if xml_result:
                logger.debug(f"Check {txn_id} retrieved via XML with {len(xml_result.get('expense_lines', []))} expense lines")
                return xml_result
            
            # Fallback to QBFC if XML fails
            logger.debug(f"XML failed for check {txn_id}, falling back to QBFC")
            
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            check_query = request_set.AppendCheckQueryRq()
            
            # Query by TxnID
            # Note: QBFC CheckQuery doesn't support IncludeLineItems
            # We'll fetch line items separately for each check if needed
            try:
                check_query.IncludeLineItems.SetValue(True)
            except:
                # QBFC doesn't support this, will fetch details separately
                pass
            check_query.ORTxnQuery.TxnIDList.Add(txn_id)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.debug(f"Regular check query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                # Don't return None, try bill payments below
            elif response.Detail and response.Detail.Count > 0:
                # Found as regular check
                check_ret = response.Detail.GetAt(0)
                return self._parse_check_from_sdk(check_ret)
            
            # If we get here, not found as regular check - try bill payments
            logger.debug(f"Check {txn_id} not found as regular check, searching bill payments")
            
            # Bill payments don't support direct TxnID query well
            # So we'll search payments from this year
            request_set = fast_qb_connection.create_request_set()
            payment_query = request_set.AppendBillPaymentCheckQueryRq()
            
            # Search within current year only (for performance)
            from datetime import datetime
            current_year_start = datetime(datetime.now().year, 1, 1)
            
            try:
                # Use transaction date filter for current year
                txn_filter = payment_query.ORTxnQuery.TxnFilter
                date_range = txn_filter.ORDateRangeFilter.TxnDateRangeFilter
                date_filter = date_range.ORTxnDateRangeFilter.TxnDateFilter
                date_filter.FromTxnDate.SetValue(pywintypes.Time(current_year_start))
                date_filter.ToTxnDate.SetValue(pywintypes.Time(datetime.now()))
                logger.debug(f"Searching bill payments from {current_year_start.strftime('%m-%d-%Y')} to now")
            except Exception as e:
                logger.debug(f"Could not set date filter for bill payments: {e}")
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Bill payment query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return None
            
            if response.Detail:
                # Search through payments for matching TxnID
                for i in range(response.Detail.Count):
                    payment_ret = response.Detail.GetAt(i)
                    if hasattr(payment_ret, 'TxnID') and payment_ret.TxnID:
                        payment_txn_id = payment_ret.TxnID.GetValue()
                        if payment_txn_id == txn_id:
                            logger.debug(f"Found bill payment check {txn_id}")
                            return self._parse_bill_payment_check(payment_ret)
            
            logger.info(f"Check/Payment {txn_id} not found in current year. For older transactions, specify a date range.")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get check {txn_id}: {e}")
            return None
    
    def find_checks_by_payee(self, payee_name: str, max_returned: int = 100) -> List[Dict]:
        """Find checks by payee name using SDK"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            check_query = request_set.AppendCheckQueryRq()
            
            # Set payee filter
            entity_filter = check_query.ORTxnQuery.TxnFilter.EntityFilter
            entity_filter.OREntityFilter.FullNameList.Add(payee_name)
            
            # Set max returned (must be before filters)
            try:
                check_query.SetMaxReturned(max_returned)
            except:
                # Some versions don't support SetMaxReturned
                pass
            
            # Note: QBFC CheckQuery doesn't support IncludeLineItems
            # We'll fetch line items separately for each check if needed
            try:
                check_query.IncludeLineItems.SetValue(True)
            except:
                # QBFC doesn't support this, will fetch details separately
                pass
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            if not response.Detail:
                return []
            
            checks = []
            for i in range(response.Detail.Count):
                check_ret = response.Detail.GetAt(i)
                check_data = self._parse_check_from_sdk(check_ret)
                if check_data:
                    # QBFC doesn't return line items in search, fetch separately
                    if check_data.get('txn_id') and not check_data.get('expense_lines') and not check_data.get('item_lines'):
                        # Get the full check with line items
                        full_check = self.get_check(check_data['txn_id'])
                        if full_check:
                            check_data['expense_lines'] = full_check.get('expense_lines', [])
                            check_data['item_lines'] = full_check.get('item_lines', [])
                    checks.append(check_data)
            
            return checks
            
        except Exception as e:
            logger.error(f"Failed to find checks for payee {payee_name}: {e}")
            return []
    
    def search_checks(self, 
                     ref_number: Optional[str] = None,
                     date_from: Optional[datetime] = None,
                     date_to: Optional[datetime] = None,
                     bank_account: Optional[str] = None,
                     memo_contains: Optional[str] = None,
                     created_from: Optional[datetime] = None,
                     created_to: Optional[datetime] = None,
                     modified_from: Optional[datetime] = None,
                     modified_to: Optional[datetime] = None,
                     amount: Optional[float] = None,
                     max_returned: int = 100) -> List[Dict]:
        """Search checks with various filters"""
        from datetime import timedelta
        try:
            logger.debug(f"search_checks called with date_from={date_from}, date_to={date_to}, created_from={created_from}, created_to={created_to}, modified_from={modified_from}, modified_to={modified_to}, amount={amount}")
            
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            logger.debug("Connected to QuickBooks")
            
            request_set = fast_qb_connection.create_request_set()
            check_query = request_set.AppendCheckQueryRq()
            
            logger.debug("Created check query request")
            
            # If no filters provided, default to current week
            if not any([date_from, date_to, created_from, created_to, modified_from, modified_to, 
                       ref_number, bank_account, memo_contains, amount]):
                # Default to current week
                today = datetime.now()
                # Find the most recent Sunday (week start)
                days_since_sunday = today.weekday() + 1 if today.weekday() != 6 else 0
                week_start = today - timedelta(days=days_since_sunday)
                week_start = datetime(week_start.year, week_start.month, week_start.day, 0, 0, 0)
                # Saturday (week end)
                week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
                
                date_from = week_start
                date_to = week_end
                logger.info(f"No filters provided - defaulting to current week: {week_start} to {week_end}")
            
            # Apply filters if provided
            # For creation date, we'll get all checks and filter in post-processing
            # because ModifiedDate filter has SDK issues
            filter_applied = False
            if created_from or created_to:
                filter_applied = True
                # We'll handle this in post-processing after getting results
                # Set a flag to filter by TimeCreated/TimeModified after retrieval
                logger.info("Creation date filtering will be applied in post-processing")
                # Get checks from a wider date range and filter later
                if created_from:
                    # Use transaction date with a wide range to ensure we get all checks
                    wider_from = created_from - timedelta(days=365)  # Go back a year
                    txn_filter = check_query.ORTxnQuery.TxnFilter
                    date_range = txn_filter.ORDateRangeFilter.TxnDateRangeFilter
                    date_filter = date_range.ORTxnDateRangeFilter.TxnDateFilter
                    date_filter.FromTxnDate.SetValue(pywintypes.Time(wider_from))
                    date_filter.ToTxnDate.SetValue(pywintypes.Time(datetime.now()))
                    logger.debug(f"Using wide date range for post-processing filter")
            if modified_from or modified_to:
                # Use ModifiedDate filter for modified date search
                txn_filter = check_query.ORTxnQuery.TxnFilter
                date_range = txn_filter.ORDateRangeFilter.ModifiedDateRangeFilter
                
                if modified_from:
                    date_range.FromModifiedDate.SetValue(pywintypes.Time(modified_from))
                    logger.debug(f"Set FromModifiedDate to {modified_from}")
                if modified_to:
                    date_range.ToModifiedDate.SetValue(pywintypes.Time(modified_to))
                    logger.debug(f"Set ToModifiedDate to {modified_to}")
                logger.info("Using ModifiedDate filter for modified date search")
            if date_from or date_to:
                # Use transaction date filter with correct structure
                txn_filter = check_query.ORTxnQuery.TxnFilter
                date_range = txn_filter.ORDateRangeFilter.TxnDateRangeFilter
                date_filter = date_range.ORTxnDateRangeFilter.TxnDateFilter
                
                if date_from:
                    # Convert datetime to pywintypes time for QB SDK
                    date_filter.FromTxnDate.SetValue(pywintypes.Time(date_from))
                    logger.debug(f"Set FromTxnDate to {date_from}")
                
                if date_to:
                    # Convert datetime to pywintypes time for QB SDK
                    date_filter.ToTxnDate.SetValue(pywintypes.Time(date_to))
                    logger.debug(f"Set ToTxnDate to {date_to}")
            if ref_number:
                check_query.ORTxnQuery.TxnFilter.ORRefNumberFilter.RefNumberFilter.MatchCriterion.SetValue(2)  # Contains
                check_query.ORTxnQuery.TxnFilter.ORRefNumberFilter.RefNumberFilter.RefNumber.SetValue(ref_number)
            if bank_account:
                # Can filter by bank account
                account_filter = check_query.ORTxnQuery.TxnFilter.AccountFilter
                account_filter.ORAccountFilter.FullNameList.Add(bank_account)
            
            # Set max returned (must be before filters)
            try:
                check_query.SetMaxReturned(max_returned)
            except:
                # Some versions don't support SetMaxReturned
                pass
            
            # Note: QBFC CheckQuery doesn't support IncludeLineItems
            # We'll fetch line items separately for each check if needed
            try:
                check_query.IncludeLineItems.SetValue(True)
            except:
                # QBFC doesn't support this, will fetch details separately
                pass
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            if not response.Detail:
                return []
            
            checks = []
            for i in range(response.Detail.Count):
                check_ret = response.Detail.GetAt(i)
                check_data = self._parse_check_from_sdk(check_ret)
                
                if not check_data:
                    continue
                
                # QBFC doesn't return line items in search, fetch separately
                if check_data.get('txn_id') and not check_data.get('expense_lines') and not check_data.get('item_lines'):
                    # Get the full check with line items
                    full_check = self.get_check(check_data['txn_id'])
                    if full_check:
                        check_data['expense_lines'] = full_check.get('expense_lines', [])
                        check_data['item_lines'] = full_check.get('item_lines', [])
                
                # Apply additional filters if specified
                # Creation date filter (post-processing)
                if created_from or created_to:
                    # Get TimeCreated or TimeModified from the check
                    time_created = None
                    if hasattr(check_ret, 'TimeCreated'):
                        time_created = check_ret.TimeCreated.GetValue()
                    elif hasattr(check_ret, 'TimeModified'):
                        time_created = check_ret.TimeModified.GetValue()
                    
                    if time_created:
                        # Convert pywintypes datetime to regular datetime for comparison
                        # Remove timezone info to make both naive for comparison
                        if hasattr(time_created, 'replace'):
                            time_created_naive = time_created.replace(tzinfo=None)
                        else:
                            # If it's already a naive datetime
                            time_created_naive = time_created
                        
                        if created_from and time_created_naive < created_from:
                            continue
                        if created_to and time_created_naive > created_to:
                            continue
                    else:
                        # If no time fields, skip this check for creation date filter
                        logger.debug(f"Check {check_data.get('txn_id')} has no TimeCreated/TimeModified")
                        continue
                
                # Memo filter
                if memo_contains:
                    if not check_data.get('memo') or memo_contains.lower() not in check_data['memo'].lower():
                        continue
                
                # Amount filter
                if amount is not None:
                    check_amount = check_data.get('amount', 0.0)
                    logger.debug(f"Amount filter: looking for {amount}, check has {check_amount}")
                    if abs(check_amount - amount) > 0.01:
                        logger.debug(f"Skipping check - amount mismatch")
                        continue
                
                checks.append(check_data)
            
            return checks
            
        except Exception as e:
            logger.error(f"Failed to search checks: {e}")
            return []
    
    def create_check(self, check_data: Dict) -> Optional[Dict]:
        """Create a new check in QuickBooks"""
        try:
            logger.info(f"CheckRepository.create_check called with data: {check_data}")
            logger.info(f"Python file last modified - forcing fresh load")
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            check_add = request_set.AppendCheckAddRq()
            
            # Required: Bank account
            if 'bank_account' not in check_data:
                logger.error("Bank account is required for check creation")
                return None
            check_add.AccountRef.FullName.SetValue(check_data['bank_account'])
            
            # Payee (could be vendor, customer, employee, or other)
            if 'payee' in check_data:
                check_add.PayeeEntityRef.FullName.SetValue(check_data['payee'])
            
            # Date
            if 'date' in check_data:
                from datetime import datetime
                date_value = check_data['date']
                # Convert to datetime if it's a string
                if isinstance(date_value, str):
                    for fmt in ['%m-%d-%Y', '%m/%d/%Y', '%Y-%m-%d', '%m-%d-%y']:
                        try:
                            date_value = datetime.strptime(date_value, fmt)
                            break
                        except:
                            continue
                # Only set if we have a datetime object
                if isinstance(date_value, datetime):
                    check_add.TxnDate.SetValue(date_value)
            
            # Check number - if not provided, set to "Debit" for card payments
            if 'check_number' in check_data and check_data['check_number']:
                check_add.RefNumber.SetValue(str(check_data['check_number']))
            else:
                # Set to "Debit" to indicate card payment (not a physical check)
                check_add.RefNumber.SetValue("Debit")
            
            # Never mark as "To Be Printed" unless explicitly requested
            if check_data.get('to_be_printed', False):
                check_add.IsToBePrinted.SetValue(True)
            else:
                # Explicitly set to False to prevent auto-marking
                check_add.IsToBePrinted.SetValue(False)
            
            # Memo
            if 'memo' in check_data:
                check_add.Memo.SetValue(check_data['memo'])
            
            # Address (if provided)
            if 'address' in check_data:
                for line in check_data['address'].split('\n')[:5]:
                    if line.strip():
                        check_add.Address.Addr1.SetValue(line.strip())
                        break
            
            # Line items (expenses or items)
            if 'line_items' in check_data:
                for line_item in check_data['line_items']:
                    if line_item.get('expense_account'):
                        # Expense line
                        try:
                            expense_line = check_add.ExpenseLineAddList.Append()
                            expense_line.AccountRef.FullName.SetValue(line_item['expense_account'])
                        except Exception as e:
                            logger.error(f"Failed to add expense line: {e}")
                            logger.error(f"Line item data: {line_item}")
                            raise
                        
                        if 'amount' in line_item:
                            expense_line.Amount.SetValue(line_item['amount'])
                        
                        if 'memo' in line_item:
                            expense_line.Memo.SetValue(line_item['memo'])
                        
                        if 'customer_job' in line_item:
                            expense_line.CustomerRef.FullName.SetValue(line_item['customer_job'])
                        
                        if 'class' in line_item:
                            expense_line.ClassRef.FullName.SetValue(line_item['class'])
                        
                        # Only set billable status if explicitly requested as billable
                        # For non-billable items, don't set the field at all as some items don't support it
                        if line_item.get('billable', False):  # Only set if True
                            expense_line.BillableStatus.SetValue(1)  # 1=Billable
                        # Don't set BillableStatus at all if False (default behavior)
                    
                    elif line_item.get('item'):
                        # Item line - use ItemLineAdd structure
                        item_line = check_add.ORItemLineAddList.Append().ItemLineAdd
                        item_line.ItemRef.FullName.SetValue(line_item['item'])
                        
                        if 'quantity' in line_item:
                            item_line.Quantity.SetValue(line_item['quantity'])
                        
                        if 'cost' in line_item:
                            item_line.Cost.SetValue(line_item['cost'])
                        
                        if 'amount' in line_item:
                            item_line.Amount.SetValue(line_item['amount'])
                        
                        if 'description' in line_item:
                            item_line.Desc.SetValue(line_item['description'])
                        
                        if 'customer_job' in line_item:
                            item_line.CustomerRef.FullName.SetValue(line_item['customer_job'])
                        
                        if 'class' in line_item:
                            item_line.ClassRef.FullName.SetValue(line_item['class'])
                        
                        # Only set billable status if explicitly requested as billable
                        # For non-billable items, don't set the field at all as some items don't support it
                        if line_item.get('billable', False):  # Only set if True
                            item_line.BillableStatus.SetValue(1)  # 1=Billable
                        # Don't set BillableStatus at all if False (default behavior)
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to create check: StatusCode={response.StatusCode}, Message={error_msg}")
                logger.error(f"Check data sent: {check_data}")
                return None
            
            if not response.Detail:
                logger.error("No check data returned after creation")
                return None
            
            # Parse and return the created check
            check_ret = response.Detail
            return self._parse_check_from_sdk(check_ret)
            
        except Exception as e:
            import traceback
            logger.error(f"Failed to create check: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def update_check(self, txn_id: str, updates: Dict) -> Optional[Dict]:
        """Update an existing check"""
        try:
            # First get the existing check with edit sequence
            existing_check = self.get_check(txn_id)
            if not existing_check:
                logger.error(f"Check {txn_id} not found for update")
                return None
            
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            check_mod = request_set.AppendCheckModRq()
            
            # Required: TxnID and EditSequence
            check_mod.TxnID.SetValue(txn_id)
            check_mod.EditSequence.SetValue(existing_check['edit_sequence'])
            
            # Apply updates
            if 'check_number' in updates:
                check_mod.RefNumber.SetValue(str(updates['check_number']))
            
            if 'date' in updates:
                check_mod.TxnDate.SetValue(updates['date'])
            
            if 'memo' in updates:
                check_mod.Memo.SetValue(updates['memo'])
            
            if 'payee' in updates:
                check_mod.PayeeEntityRef.FullName.SetValue(updates['payee'])
            
            if 'bank_account' in updates:
                check_mod.AccountRef.FullName.SetValue(updates['bank_account'])
            
            # Handle line item modifications
            if 'clear_lines' in updates and updates['clear_lines']:
                # Clear all existing line items
                check_mod.ClearItemLines.SetValue(True)
                check_mod.ClearExpenseLines.SetValue(True)
            
            # Handle line removal
            if 'remove_expense_lines' in updates or 'remove_item_lines' in updates:
                # Note: existing_check already retrieved above for edit sequence
                if existing_check:
                    # Handle expense line removal
                    if 'remove_expense_lines' in updates:
                        remove_ids = updates.get('remove_expense_lines', [])
                        # Check if ALL expense lines should be removed
                        if 'ALL' in remove_ids:
                            # Use ClearExpenseLines to remove all expense lines
                            check_mod.ClearExpenseLines.SetValue(True)
                            # Still need to preserve existing item lines
                            if existing_check.get('item_lines') and 'remove_item_lines' not in updates:
                                for line in existing_check['item_lines']:
                                    if line.get('txn_line_id'):
                                        item_mod = check_mod.ORItemLineModList.Append().ItemLineMod
                                        item_mod.TxnLineID.SetValue(line['txn_line_id'])
                        elif existing_check.get('expense_lines'):
                            # Keep only expense lines that aren't being removed
                            for line in existing_check['expense_lines']:
                                if line.get('txn_line_id') and line['txn_line_id'] not in remove_ids:
                                    # Include this line to keep it (just TxnLineID is enough)
                                    expense_mod = check_mod.ExpenseLineModList.Append()
                                    expense_mod.TxnLineID.SetValue(line['txn_line_id'])
                    
                    # Handle item line removal
                    if 'remove_item_lines' in updates:
                        remove_ids = updates.get('remove_item_lines', [])
                        # Check if ALL item lines should be removed
                        if 'ALL' in remove_ids:
                            # Use ClearItemLines to remove all item lines
                            check_mod.ClearItemLines.SetValue(True)
                        elif existing_check.get('item_lines'):
                            # Keep only item lines that aren't being removed
                            for line in existing_check['item_lines']:
                                if line.get('txn_line_id') and line['txn_line_id'] not in remove_ids:
                                    # Include this line to keep it
                                    # Use ORItemLineModList for modifications
                                    item_mod = check_mod.ORItemLineModList.Append().ItemLineMod
                                    item_mod.TxnLineID.SetValue(line['txn_line_id'])
            
            # Add new expense lines
            if 'expense_lines' in updates:
                for expense in updates['expense_lines']:
                    expense_mod = check_mod.ORCheckLineModList.Append().CheckLineMod
                    expense_mod.TxnLineID.SetValue("-1")  # -1 means new line
                    
                    if expense.get('account'):
                        expense_mod.AccountRef.FullName.SetValue(expense['account'])
                    if expense.get('amount') is not None:
                        expense_mod.Amount.SetValue(expense['amount'])
                    if expense.get('memo'):
                        expense_mod.Memo.SetValue(expense['memo'])
                    if expense.get('customer_job'):
                        expense_mod.CustomerRef.FullName.SetValue(expense['customer_job'])
                    if expense.get('class'):
                        expense_mod.ClassRef.FullName.SetValue(expense['class'])
            
            # Add new item lines (support both 'item_lines' and 'add_item_lines')
            item_lines_to_add = updates.get('item_lines', []) + updates.get('add_item_lines', [])
            if item_lines_to_add:
                for item in item_lines_to_add:
                    item_mod = check_mod.ORItemLineModList.Append().ItemLineMod
                    item_mod.TxnLineID.SetValue("-1")  # -1 means new line
                    
                    if item.get('item'):
                        item_mod.ItemRef.FullName.SetValue(item['item'])
                    if item.get('quantity') is not None:
                        item_mod.Quantity.SetValue(item['quantity'])
                    if item.get('cost') is not None:
                        item_mod.Cost.SetValue(item['cost'])
                    if item.get('amount') is not None:
                        item_mod.Amount.SetValue(item['amount'])
                    if item.get('description'):
                        item_mod.Desc.SetValue(item['description'])
                    if item.get('customer_job'):
                        item_mod.CustomerRef.FullName.SetValue(item['customer_job'])
                    if item.get('class'):
                        item_mod.ClassRef.FullName.SetValue(item['class'])
                    if 'billable' in item:
                        item_mod.BillableStatus.SetValue(1 if item['billable'] else 0)
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to update check: {error_msg}")
                return None
            
            if not response.Detail:
                logger.error("No check data returned after update")
                return None
            
            # Parse and return the updated check
            check_ret = response.Detail
            return self._parse_check_from_sdk(check_ret)
            
        except Exception as e:
            logger.error(f"Failed to update check {txn_id}: {e}")
            return None
    
    def delete_check(self, txn_id: str) -> bool:
        """Delete a check from QuickBooks"""
        try:
            # First get the check to verify it exists and get edit sequence
            existing_check = self.get_check(txn_id)
            if not existing_check:
                logger.error(f"Check {txn_id} not found for deletion")
                return False
            
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            request_set = fast_qb_connection.create_request_set()
            check_del = request_set.AppendTxnDelRq()
            
            # CRITICAL: Must use SetAsString for TxnDelType - NOT SetValue!
            # This is a QuickBooks SDK requirement for transaction deletion
            check_del.TxnDelType.SetAsString("Check")  # Must use string value!
            check_del.TxnID.SetValue(txn_id)
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                error_code = response.StatusCode
                logger.error(f"[CheckRepository.delete_check] Failed to delete check {txn_id}")
                logger.error(f"  - Error Code: {error_code}")
                logger.error(f"  - Error Message: {error_msg}")
                logger.error(f"  - Transaction ID: {txn_id}")
                
                # Raise exception with full context so service layer can report it
                raise Exception(f"QuickBooks Error {error_code}: {error_msg} (Check ID: {txn_id})")
                return False
            
            logger.info(f"Successfully deleted check {txn_id}")
            return True
            
        except Exception as e:
            logger.error(f"[CheckRepository.delete_check] Exception during deletion")
            logger.error(f"  - Transaction ID: {txn_id}")
            logger.error(f"  - Error Type: {type(e).__name__}")
            logger.error(f"  - Error Details: {str(e)}")
            # Re-raise the exception so service layer can handle it
            raise
    
    def _parse_check_from_sdk(self, check_ret) -> Optional[Dict]:
        """Parse check data from SDK response"""
        try:
            ref_num = check_ret.RefNumber.GetValue() if hasattr(check_ret, 'RefNumber') and check_ret.RefNumber else None
            check_data = {
                'txn_id': check_ret.TxnID.GetValue() if hasattr(check_ret, 'TxnID') and check_ret.TxnID else None,
                'edit_sequence': check_ret.EditSequence.GetValue() if hasattr(check_ret, 'EditSequence') and check_ret.EditSequence else None,
                'txn_number': check_ret.TxnNumber.GetValue() if hasattr(check_ret, 'TxnNumber') and check_ret.TxnNumber else None,
                'txn_date': check_ret.TxnDate.GetValue() if hasattr(check_ret, 'TxnDate') and check_ret.TxnDate else None,
                'ref_number': ref_num,
                'check_number': ref_num,  # Set both for compatibility
                'amount': float(check_ret.Amount.GetValue()) if hasattr(check_ret, 'Amount') and check_ret.Amount else 0.0,
                'memo': check_ret.Memo.GetValue() if hasattr(check_ret, 'Memo') and check_ret.Memo else None,
                'is_printed': not check_ret.IsToBePrinted.GetValue() if hasattr(check_ret, 'IsToBePrinted') and check_ret.IsToBePrinted else True,
                'is_to_be_printed': check_ret.IsToBePrinted.GetValue() if hasattr(check_ret, 'IsToBePrinted') and check_ret.IsToBePrinted else False,
            }
            
            # Additional fields
            if hasattr(check_ret, 'CurrencyRef') and check_ret.CurrencyRef:
                check_data['currency'] = check_ret.CurrencyRef.FullName.GetValue() if hasattr(check_ret.CurrencyRef, 'FullName') and check_ret.CurrencyRef.FullName else None
            
            if hasattr(check_ret, 'ExchangeRate') and check_ret.ExchangeRate:
                check_data['exchange_rate'] = float(check_ret.ExchangeRate.GetValue())
            
            if hasattr(check_ret, 'AmountInHomeCurrency') and check_ret.AmountInHomeCurrency:
                check_data['amount_home_currency'] = float(check_ret.AmountInHomeCurrency.GetValue())
            
            if hasattr(check_ret, 'IsTaxIncluded') and check_ret.IsTaxIncluded:
                check_data['is_tax_included'] = check_ret.IsTaxIncluded.GetValue()
            
            # Time created and modified
            if hasattr(check_ret, 'TimeCreated') and check_ret.TimeCreated:
                check_data['time_created'] = check_ret.TimeCreated.GetValue()
            
            if hasattr(check_ret, 'TimeModified') and check_ret.TimeModified:
                check_data['time_modified'] = check_ret.TimeModified.GetValue()
            
            # Payee information
            if hasattr(check_ret, 'PayeeEntityRef') and check_ret.PayeeEntityRef:
                payee_ref = check_ret.PayeeEntityRef
                check_data['payee_name'] = payee_ref.FullName.GetValue() if hasattr(payee_ref, 'FullName') and payee_ref.FullName else None
                check_data['payee_type'] = payee_ref.Type.GetValue() if hasattr(payee_ref, 'Type') and payee_ref.Type else None
            
            # Bank account
            if hasattr(check_ret, 'AccountRef') and check_ret.AccountRef:
                account_ref = check_ret.AccountRef
                check_data['bank_account'] = account_ref.FullName.GetValue() if hasattr(account_ref, 'FullName') and account_ref.FullName else None
            
            # Address
            if hasattr(check_ret, 'Address') and check_ret.Address:
                address_lines = []
                for i in range(1, 6):
                    addr_attr = f'Addr{i}'
                    if hasattr(check_ret.Address, addr_attr):
                        addr_field = getattr(check_ret.Address, addr_attr)
                        if addr_field:
                            line = addr_field.GetValue()
                            if line:
                                address_lines.append(line)
                if address_lines:
                    check_data['address'] = '\n'.join(address_lines)
            
            # Parse expense lines
            expense_lines = []
            if hasattr(check_ret, 'ExpenseLineList') and check_ret.ExpenseLineList:
                for i in range(check_ret.ExpenseLineList.Count):
                    expense_line = check_ret.ExpenseLineList.GetAt(i)
                    line_data = {
                        'txn_line_id': expense_line.TxnLineID.GetValue() if hasattr(expense_line, 'TxnLineID') and expense_line.TxnLineID else None,
                        'expense_account': expense_line.AccountRef.FullName.GetValue() if hasattr(expense_line, 'AccountRef') and expense_line.AccountRef and hasattr(expense_line.AccountRef, 'FullName') and expense_line.AccountRef.FullName else None,
                        'amount': float(expense_line.Amount.GetValue()) if hasattr(expense_line, 'Amount') and expense_line.Amount else 0.0,
                        'memo': expense_line.Memo.GetValue() if hasattr(expense_line, 'Memo') and expense_line.Memo else None,
                    }
                    
                    if hasattr(expense_line, 'CustomerRef') and expense_line.CustomerRef:
                        customer_ref = expense_line.CustomerRef
                        line_data['customer_job'] = customer_ref.FullName.GetValue() if hasattr(customer_ref, 'FullName') and customer_ref.FullName else None
                    
                    if hasattr(expense_line, 'ClassRef') and expense_line.ClassRef:
                        class_ref = expense_line.ClassRef
                        line_data['class'] = class_ref.FullName.GetValue() if hasattr(class_ref, 'FullName') and class_ref.FullName else None
                    
                    expense_lines.append(line_data)
            
            # Parse item lines
            item_lines = []
            if hasattr(check_ret, 'ItemLineList') and check_ret.ItemLineList:
                for i in range(check_ret.ItemLineList.Count):
                    item_line = check_ret.ItemLineList.GetAt(i)
                    line_data = {
                        'txn_line_id': item_line.TxnLineID.GetValue() if hasattr(item_line, 'TxnLineID') and item_line.TxnLineID else None,
                        'item': item_line.ItemRef.FullName.GetValue() if hasattr(item_line, 'ItemRef') and item_line.ItemRef and hasattr(item_line.ItemRef, 'FullName') and item_line.ItemRef.FullName else None,
                        'description': item_line.Desc.GetValue() if hasattr(item_line, 'Desc') and item_line.Desc else None,
                        'quantity': float(item_line.Quantity.GetValue()) if hasattr(item_line, 'Quantity') and item_line.Quantity else 0.0,
                        'cost': float(item_line.Cost.GetValue()) if hasattr(item_line, 'Cost') and item_line.Cost else 0.0,
                        'amount': float(item_line.Amount.GetValue()) if hasattr(item_line, 'Amount') and item_line.Amount else 0.0,
                    }
                    
                    if hasattr(item_line, 'CustomerRef') and item_line.CustomerRef:
                        customer_ref = item_line.CustomerRef
                        line_data['customer_job'] = customer_ref.FullName.GetValue() if hasattr(customer_ref, 'FullName') and customer_ref.FullName else None
                    
                    if hasattr(item_line, 'ClassRef') and item_line.ClassRef:
                        class_ref = item_line.ClassRef
                        line_data['class'] = class_ref.FullName.GetValue() if hasattr(class_ref, 'FullName') and class_ref.FullName else None
                    
                    item_lines.append(line_data)
            
            check_data['expense_lines'] = expense_lines
            check_data['item_lines'] = item_lines
            
            return check_data
            
        except Exception as e:
            logger.error(f"Failed to parse check data: {e}")
            return None
    
    def search_all_checks(self,
                         date_from: Optional[datetime] = None,
                         date_to: Optional[datetime] = None,
                         bank_account: Optional[str] = None,
                         created_from: Optional[datetime] = None,
                         created_to: Optional[datetime] = None,
                         amount: Optional[float] = None,
                         max_returned: int = 200) -> List[Dict]:
        """Search both regular checks AND bill payment checks"""
        try:
            all_checks = []
            
            # Get regular checks
            regular_checks = self.search_checks(
                date_from=date_from,
                date_to=date_to,
                bank_account=bank_account,
                created_from=created_from,
                created_to=created_to,
                amount=amount,
                max_returned=max_returned
            )
            all_checks.extend(regular_checks)
            
            # Get bill payment checks
            bill_payment_checks = self._search_bill_payment_checks(
                date_from=date_from,
                date_to=date_to,
                bank_account=bank_account,
                created_from=created_from,
                created_to=created_to,
                amount=amount,
                max_returned=max_returned
            )
            all_checks.extend(bill_payment_checks)
            
            # Sort by date (newest first) and limit results
            all_checks.sort(key=lambda x: x.get('txn_date', datetime.min), reverse=True)
            
            return all_checks[:max_returned]
            
        except Exception as e:
            logger.error(f"Failed to search all checks: {e}")
            return []
    
    def _search_bill_payment_checks(self,
                                   date_from: Optional[datetime] = None,
                                   date_to: Optional[datetime] = None,
                                   bank_account: Optional[str] = None,
                                   created_from: Optional[datetime] = None,
                                   created_to: Optional[datetime] = None,
                                   amount: Optional[float] = None,
                                   max_returned: int = 100) -> List[Dict]:
        """Search bill payment checks"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            payment_query = request_set.AppendBillPaymentCheckQueryRq()
            
            # MaxReturned may not be available for BillPaymentCheckQuery
            try:
                payment_query.MaxReturned.SetValue(max_returned)
            except:
                # If MaxReturned is not available, continue without it
                pass
            
            # Apply filters based on what's available for bill payment checks
            if created_from or created_to:
                # For bill payment checks, we'll use transaction date as proxy
                # since they also have TimeCreated/TimeModified issues
                if created_from:
                    date_from = created_from
                if created_to:
                    date_to = created_to
            
            if date_from or date_to:
                # Use transaction date filter
                txn_filter = payment_query.ORTxnQuery.TxnFilter
                date_range = txn_filter.ORDateRangeFilter.TxnDateRangeFilter
                date_filter = date_range.ORTxnDateRangeFilter.TxnDateFilter
                
                if date_from:
                    date_filter.FromTxnDate.SetValue(pywintypes.Time(date_from))
                if date_to:
                    date_filter.ToTxnDate.SetValue(pywintypes.Time(date_to))
            elif bank_account:
                # Filter by bank account
                account_filter = payment_query.ORTxnQuery.TxnFilter.AccountFilter
                account_filter.ORAccountFilter.FullNameList.Add(bank_account)
            
            # Process request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Bill payment query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            if not response.Detail:
                return []
            
            checks = []
            for i in range(response.Detail.Count):
                payment_ret = response.Detail.GetAt(i)
                check_data = self._parse_bill_payment_check(payment_ret, created_from, created_to, amount)
                
                if check_data:
                    checks.append(check_data)
            
            return checks
            
        except Exception as e:
            logger.error(f"Failed to search bill payment checks: {e}")
            return []
    
    def _parse_bill_payment_check(self, payment_ret, created_from=None, created_to=None, amount_filter=None) -> Optional[Dict]:
        """Parse bill payment check data from SDK response"""
        try:
            # Apply creation date filter if provided
            if created_from or created_to:
                time_created = None
                if hasattr(payment_ret, 'TimeCreated'):
                    time_created = payment_ret.TimeCreated.GetValue()
                elif hasattr(payment_ret, 'TimeModified'):
                    time_created = payment_ret.TimeModified.GetValue()
                
                if time_created:
                    # Remove timezone info for comparison
                    if hasattr(time_created, 'replace'):
                        time_created_naive = time_created.replace(tzinfo=None)
                    else:
                        time_created_naive = time_created
                    
                    if created_from and time_created_naive < created_from:
                        return None
                    if created_to and time_created_naive > created_to:
                        return None
            
            check_data = {
                'txn_id': None,
                'txn_date': None,
                'ref_number': None,
                'amount': 0.0,
                'memo': None,
                'is_printed': False,
                'check_type': 'Bill Payment Check',
                'payee': None,
                'bank_account': None
            }
            
            # Safely get values
            try:
                if hasattr(payment_ret, 'TxnID') and payment_ret.TxnID:
                    check_data['txn_id'] = payment_ret.TxnID.GetValue()
            except:
                pass
            
            try:
                if hasattr(payment_ret, 'TxnDate') and payment_ret.TxnDate:
                    check_data['txn_date'] = payment_ret.TxnDate.GetValue()
            except:
                pass
            
            try:
                if hasattr(payment_ret, 'RefNumber') and payment_ret.RefNumber:
                    check_data['ref_number'] = payment_ret.RefNumber.GetValue()
            except:
                pass
            
            try:
                if hasattr(payment_ret, 'Amount') and payment_ret.Amount:
                    check_data['amount'] = payment_ret.Amount.GetValue()
            except:
                pass
            
            try:
                if hasattr(payment_ret, 'Memo') and payment_ret.Memo:
                    check_data['memo'] = payment_ret.Memo.GetValue()
            except:
                pass
            
            try:
                if hasattr(payment_ret, 'IsToBePrinted') and payment_ret.IsToBePrinted:
                    check_data['is_printed'] = payment_ret.IsToBePrinted.GetValue()
            except:
                pass
            
            # Apply amount filter if specified
            if amount_filter is not None:
                if abs(check_data['amount'] - amount_filter) > 0.01:
                    return None
            
            # Get payee (vendor) - set both payee and payee_name for compatibility
            try:
                if hasattr(payment_ret, 'PayeeEntityRef') and payment_ret.PayeeEntityRef:
                    if hasattr(payment_ret.PayeeEntityRef, 'FullName') and payment_ret.PayeeEntityRef.FullName:
                        payee_name = payment_ret.PayeeEntityRef.FullName.GetValue()
                        check_data['payee'] = payee_name
                        check_data['payee_name'] = payee_name  # Add payee_name for consistency with regular checks
            except:
                pass
            
            # Get bank account
            try:
                if hasattr(payment_ret, 'BankAccountRef') and payment_ret.BankAccountRef:
                    if hasattr(payment_ret.BankAccountRef, 'FullName') and payment_ret.BankAccountRef.FullName:
                        check_data['bank_account'] = payment_ret.BankAccountRef.FullName.GetValue()
            except:
                pass
            
            # Get time created and modified
            try:
                if hasattr(payment_ret, 'TimeCreated') and payment_ret.TimeCreated:
                    check_data['time_created'] = payment_ret.TimeCreated.GetValue()
            except:
                pass
            
            try:
                if hasattr(payment_ret, 'TimeModified') and payment_ret.TimeModified:
                    check_data['time_modified'] = payment_ret.TimeModified.GetValue()
            except:
                pass
            
            # Get applied bills info if available
            applied_bills = []
            try:
                if hasattr(payment_ret, 'AppliedToTxnRetList') and payment_ret.AppliedToTxnRetList:
                    for j in range(payment_ret.AppliedToTxnRetList.Count):
                        try:
                            applied = payment_ret.AppliedToTxnRetList.GetAt(j)
                            bill_info = {}
                            
                            if hasattr(applied, 'TxnID') and applied.TxnID:
                                bill_info['bill_txn_id'] = applied.TxnID.GetValue()
                            
                            if hasattr(applied, 'Amount') and applied.Amount:
                                bill_info['amount'] = applied.Amount.GetValue()
                            
                            if bill_info:
                                applied_bills.append(bill_info)
                        except:
                            continue
            except:
                pass
            
            check_data['applied_bills'] = applied_bills
            
            return check_data
            
        except Exception as e:
            logger.error(f"Failed to parse bill payment check: {e}")
            return None