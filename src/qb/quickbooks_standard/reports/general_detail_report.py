"""
General Detail Report Repository
Flexible transaction reporting with multiple filter options
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import logging
from shared_utilities.fast_qb_connection import fast_qb_connection

logger = logging.getLogger(__name__)

class GeneralDetailReportRepository:
    """Repository for generating general detail reports with flexible filtering"""
    
    def __init__(self):
        self.connection = fast_qb_connection
    
    def generate_report(self,
                       account_filter: Optional[str] = None,
                       account_type_filter: Optional[str] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None,
                       amount_min: Optional[float] = None,
                       amount_max: Optional[float] = None,
                       entity_filter: Optional[str] = None,
                       memo_contains: Optional[str] = None,
                       txn_type_filter: Optional[str] = None,
                       include_subaccounts: bool = True,
                       max_returned: int = 100) -> List[Dict]:
        """
        Generate a general detail report with flexible filtering
        
        Args:
            account_filter: Specific account name to filter by
            account_type_filter: Account type (Expense, Income, Bank, etc.)
            date_from: Start date MM-DD-YYYY or MM/DD/YYYY
            date_to: End date MM-DD-YYYY or MM/DD/YYYY
            amount_min: Minimum transaction amount
            amount_max: Maximum transaction amount
            entity_filter: Filter by entity (vendor, customer, employee)
            memo_contains: Filter by memo text
            txn_type_filter: Transaction type (Check, Bill, Invoice, etc.)
            include_subaccounts: Include subaccounts in account filter
            max_returned: Maximum number of transactions to return
            
        Returns:
            List of transaction dictionaries
        """
        try:
            if not self.connection.connect():
                logger.error("[GeneralDetailReport] Failed to connect to QuickBooks")
                return []
            
            request_set = self.connection.create_request_set()
            report_query = request_set.AppendGeneralDetailReportQueryRq()
            
            # Set report type to Transaction Detail by Account
            report_query.GeneralDetailReportType.SetValue(27)  # Transaction Detail by Account
            
            # Apply date filter
            if date_from or date_to:
                report_period = report_query.ORReportPeriod.ReportPeriod
                if date_from:
                    from_date = self._parse_date(date_from)
                    report_period.FromReportDate.SetValue(from_date)
                if date_to:
                    to_date = self._parse_date(date_to)
                    report_period.ToReportDate.SetValue(to_date)
            else:
                # Default to last 90 days if no date specified
                from datetime import timedelta
                report_period = report_query.ORReportPeriod.ReportPeriod
                report_period.ToReportDate.SetValue(datetime.now())
                report_period.FromReportDate.SetValue(datetime.now() - timedelta(days=90))
            
            # Filter by specific account name if provided
            # Note: For Transaction Detail by Account report, account filtering
            # is better done client-side after getting the data since the
            # ReportAccountFilter may not work as expected
            if account_type_filter:
                # Filter by account type (this might work)
                try:
                    account_type_list = report_query.ReportAccountFilter.AccountTypeList
                    account_type_list.Add(account_type_filter)
                except:
                    # If this fails, we'll filter client-side
                    pass
            
            # Filter by entity if provided  
            if entity_filter:
                entity_ref_list = report_query.ReportEntityFilter.EntityRefList
                entity_ref_list.Add(entity_filter)
            
            # Filter by transaction type if provided
            if txn_type_filter:
                txn_type_list = report_query.ReportTxnTypeFilter.TxnTypeList
                txn_type_list.Add(txn_type_filter)
            
            # Note: IncludeSubcolumns not available for GeneralDetailReport
            # report_query.IncludeSubcolumns.SetValue(True)
            
            # Process the request
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"[GeneralDetailReport] QB Error {response.StatusCode}: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            transactions = []
            
            # Parse the report response
            if hasattr(response, 'Detail') and response.Detail:
                report = response.Detail
                transactions = self._parse_report_response(report)
                
                # Apply client-side filters
                filtered = []
                for txn in transactions:
                    if self._apply_filters(txn, account_filter, amount_min, amount_max, 
                                          memo_contains, txn_type_filter):
                        filtered.append(txn)
                        if len(filtered) >= max_returned:
                            break
                
                return filtered
            
            logger.warning("[GeneralDetailReport] No report data returned")
            return []
            
        except Exception as e:
            logger.error(f"[GeneralDetailReport] Exception: {str(e)}", exc_info=True)
            return []
    
    def _parse_report_response(self, report) -> List[Dict]:
        """Parse the entire report response into transactions"""
        transactions = []
        
        try:
            # Check for ReportData
            if not hasattr(report, 'ReportData'):
                logger.warning("[GeneralDetailReport] No ReportData in response")
                return []
            
            report_data = report.ReportData
            current_account = None
            
            # Transaction Detail by Account has special structure:
            # TextRows contain account names
            # DataRows contain transactions for that account
            if hasattr(report_data, 'ORReportDataList'):
                data_list = report_data.ORReportDataList
                
                for i in range(data_list.Count):
                    data_item = data_list.GetAt(i)
                    
                    # Check if this is a TextRow (account name)
                    if hasattr(data_item, 'TextRow') and data_item.TextRow:
                        text_row = data_item.TextRow
                        if hasattr(text_row, 'value') and text_row.value:
                            # This is an account name
                            current_account = text_row.value.GetValue()
                            logger.debug(f"[GeneralDetailReport] Found account: {current_account}")
                    
                    # Check if this is a DataRow (transaction)
                    elif hasattr(data_item, 'DataRow') and data_item.DataRow:
                        txn = self._parse_data_row(data_item.DataRow, current_account)
                        if txn and txn.get('date'):  # Valid transaction
                            # Add the current account if not already in transaction
                            if current_account and not txn.get('account'):
                                txn['account'] = current_account
                            transactions.append(txn)
                    
                    # Check for SubtotalRow or TotalRow (skip these)
                    elif hasattr(data_item, 'SubtotalRow') or hasattr(data_item, 'TotalRow'):
                        # Skip subtotal and total rows
                        continue
            
            logger.info(f"[GeneralDetailReport] Parsed {len(transactions)} transactions")
            
        except Exception as e:
            logger.error(f"[GeneralDetailReport] Error parsing report: {str(e)}", exc_info=True)
        
        return transactions
    
    def _parse_data_row(self, data_row, current_account=None) -> Dict:
        """Parse a DataRow into a transaction dictionary"""
        txn = {
            'date': None,
            'ref_number': None,
            'name': None,
            'memo': None,
            'account': current_account,  # Use the current account from TextRow
            'amount': 0.0,
            'txn_type': None
        }
        
        try:
            # Check for ColDataList
            if hasattr(data_row, 'ColDataList'):
                col_list = data_row.ColDataList
                
                # Parse each column - for Transaction Detail by Account report
                # The columns are: Type, Date, Name, Clr, Split, Debit, Credit/Balance
                for col_idx in range(col_list.Count):
                    col = col_list.GetAt(col_idx)
                    
                    if hasattr(col, 'value') and col.value:
                        value = col.value.GetValue()
                        
                        # Map columns for Transaction Detail by Account format
                        if col_idx == 0:  # Transaction Type
                            txn['txn_type'] = str(value) if value else None
                        elif col_idx == 1:  # Date
                            txn['date'] = str(value) if value else None
                        elif col_idx == 2:  # Name/Payee
                            txn['name'] = str(value) if value else None
                        elif col_idx == 3:  # Cleared Status
                            txn['cleared'] = str(value) if value else None
                        elif col_idx == 4:  # Split/Account (the other side of the transaction)
                            if value:
                                txn['split_account'] = str(value)
                        elif col_idx == 5:  # Debit Amount
                            if value:
                                try:
                                    amount_str = str(value).replace('$', '').replace(',', '')
                                    amount = float(amount_str)
                                    if amount != 0:
                                        txn['debit'] = amount
                                        txn['amount'] = amount
                                except:
                                    pass
                        elif col_idx == 6:  # Credit/Balance (or running balance)
                            if value:
                                try:
                                    amount_str = str(value).replace('$', '').replace(',', '')
                                    amount = float(amount_str)
                                    # This might be a credit amount or a running balance
                                    # If we don't have a debit, this is likely the transaction amount
                                    if txn.get('debit') is None or txn.get('debit') == 0:
                                        txn['amount'] = amount
                                    txn['balance'] = amount
                                except:
                                    pass
            
        except Exception as e:
            logger.debug(f"[GeneralDetailReport] Error parsing data row: {str(e)}")
        
        return txn
    
    def _parse_text_row(self, text_row) -> Dict:
        """Parse a TextRow into a transaction dictionary"""
        txn = {
            'date': None,
            'ref_number': None,
            'name': None,
            'memo': None,
            'account': None,
            'amount': 0.0,
            'txn_type': None
        }
        
        try:
            if hasattr(text_row, 'value') and text_row.value:
                text = text_row.value.GetValue()
                
                # Parse tab or space delimited text
                parts = text.split('\t') if '\t' in text else text.split('    ')
                
                if len(parts) >= 3:
                    txn['date'] = parts[0].strip()
                    if len(parts) > 1:
                        txn['ref_number'] = parts[1].strip()
                    if len(parts) > 2:
                        txn['name'] = parts[2].strip()
                    if len(parts) > 3:
                        txn['memo'] = parts[3].strip()
                    if len(parts) > 4:
                        txn['account'] = parts[4].strip()
                    if len(parts) > 5:
                        try:
                            amount_str = parts[5].strip().replace('$', '').replace(',', '')
                            txn['amount'] = float(amount_str)
                        except:
                            txn['amount'] = 0.0
        
        except Exception as e:
            logger.debug(f"[GeneralDetailReport] Error parsing text row: {str(e)}")
        
        return txn
    
    def _apply_filters(self, txn: Dict, 
                       account_filter: Optional[str],
                       amount_min: Optional[float],
                       amount_max: Optional[float],
                       memo_contains: Optional[str],
                       txn_type_filter: Optional[str]) -> bool:
        """Apply additional filters to a transaction"""
        
        # Account filter
        if account_filter and txn.get('account'):
            if account_filter.lower() not in txn['account'].lower():
                return False
        
        # Amount range
        amount = txn.get('amount', 0.0)
        if amount_min is not None and amount < amount_min:
            return False
        if amount_max is not None and amount > amount_max:
            return False
        
        # Memo filter
        if memo_contains and txn.get('memo'):
            if memo_contains.lower() not in txn['memo'].lower():
                return False
        
        # Transaction type filter
        if txn_type_filter and txn.get('txn_type'):
            if txn_type_filter.lower() not in txn['txn_type'].lower():
                return False
        
        return True
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime"""
        if not date_str:
            return datetime.now()
        
        # Try different formats
        for fmt in ['%m-%d-%Y', '%m/%d/%Y', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        # Default to today if parsing fails
        logger.warning(f"[GeneralDetailReport] Could not parse date: {date_str}")
        return datetime.now()