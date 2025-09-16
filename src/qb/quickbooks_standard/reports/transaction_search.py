"""
Transaction search across all types - optimized with GeneralDetailReport
"""
from typing import Dict, List, Optional
from shared_utilities.fast_qb_connection import fast_qb_connection
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TransactionSearch:
    """Search all transaction types - optimized version"""

    def search_by_amount(self, amount: float, date_from: Optional[str] = None,
                         date_to: Optional[str] = None, tolerance: float = 0.01) -> Dict:
        """
        Search for transactions by amount - tries optimized method first
        """
        # Try the fast method first
        result = self.search_by_amount_optimized(amount, date_from, date_to, tolerance)
        if result.get('success'):
            return result

        # Fall back to the thorough but slow method
        logger.info("Falling back to multi-query search method")
        return self.search_by_amount_slow(amount, date_from, date_to, tolerance)

    def search_by_amount_optimized(self, amount: float, date_from: Optional[str] = None,
                                   date_to: Optional[str] = None, tolerance: float = 0.01) -> Dict:
        """
        FAST: Search using GeneralDetailReport - ONE query for all transaction types
        """
        try:
            if not fast_qb_connection.connect():
                return {"success": False, "error": "Failed to connect to QuickBooks"}

            logger.info(f"[OPTIMIZED] Searching for ${amount:.2f} using GeneralDetailReport")

            # Default to current year if no date range specified
            if not date_from:
                date_from = f"01-01-{datetime.now().year}"
            if not date_to:
                date_to = datetime.now().strftime('%m-%d-%Y')

            # Create report request
            request_set = fast_qb_connection.create_request_set()
            report_query = request_set.AppendGeneralDetailReportQueryRq()

            # Set report type to Transaction Detail by Account (type 27)
            report_query.GeneralDetailReportType.SetValue(27)

            # Set date range
            report_period = report_query.ORReportPeriod.ReportPeriod
            from_date = self._parse_date_for_report(date_from)
            to_date = self._parse_date_for_report(date_to)
            report_period.FromReportDate.SetValue(from_date)
            report_period.ToReportDate.SetValue(to_date)

            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)

            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'
                logger.error(f"Report query failed: {error_msg}")
                return {"success": False, "error": error_msg}

            # Parse report and filter by amount
            transactions = []
            if hasattr(response, 'Detail') and response.Detail:
                report = response.Detail
                all_txns = self._parse_general_report(report)

                # Filter by amount
                for txn in all_txns:
                    txn_amount = abs(float(txn.get('amount', 0)))
                    if abs(txn_amount - abs(amount)) <= tolerance:
                        transactions.append({
                            'type': txn.get('txn_type', 'Unknown'),
                            'date': txn.get('date', 'N/A'),
                            'amount': txn_amount,
                            'name': txn.get('name', 'N/A'),
                            'ref_number': txn.get('ref_number', ''),
                            'memo': txn.get('memo', ''),
                            'account': txn.get('account', 'N/A'),
                            'txn_id': txn.get('txn_id', 'N/A')
                        })

            # Sort by date (newest first)
            transactions.sort(key=lambda x: x.get('date', ''), reverse=True)

            logger.info(f"[OPTIMIZED] Found {len(transactions)} matching transactions")

            return {
                "success": True,
                "transactions": transactions,
                "count": len(transactions),
                "search_amount": amount,
                "method": "optimized_report"
            }

        except Exception as e:
            logger.error(f"Optimized search failed: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            fast_qb_connection.disconnect()

    def _parse_general_report(self, report) -> List[Dict]:
        """Parse GeneralDetailReport response into transactions"""
        transactions = []
        current_account = None

        try:
            if not hasattr(report, 'ReportData'):
                return []

            report_data = report.ReportData

            # Transaction Detail by Account structure:
            # TextRows = account names, DataRows = transactions
            if hasattr(report_data, 'ORReportDataList'):
                data_list = report_data.ORReportDataList

                for i in range(data_list.Count):
                    data_item = data_list.GetAt(i)

                    # Check for account name (TextRow)
                    if hasattr(data_item, 'TextRow') and data_item.TextRow:
                        text_row = data_item.TextRow
                        if hasattr(text_row, 'value') and text_row.value:
                            current_account = text_row.value.GetValue()

                    # Check for transaction (DataRow)
                    elif hasattr(data_item, 'DataRow') and data_item.DataRow:
                        txn = self._parse_report_data_row(data_item.DataRow, current_account)
                        if txn and txn.get('date'):
                            transactions.append(txn)

        except Exception as e:
            logger.error(f"Error parsing report: {str(e)}")

        return transactions

    def _parse_report_data_row(self, data_row, current_account=None) -> Dict:
        """Parse a DataRow from GeneralDetailReport"""
        txn = {
            'account': current_account,
            'amount': 0.0
        }

        try:
            if hasattr(data_row, 'ColDataList'):
                col_list = data_row.ColDataList

                # Columns: Type, Date, Name, Clr, Split, Debit, Credit
                for col_idx in range(col_list.Count):
                    col = col_list.GetAt(col_idx)

                    if hasattr(col, 'value') and col.value:
                        value = col.value.GetValue()

                        if col_idx == 0:  # Transaction Type
                            txn['txn_type'] = str(value) if value else None
                        elif col_idx == 1:  # Date
                            txn['date'] = str(value) if value else None
                        elif col_idx == 2:  # Name/Payee
                            txn['name'] = str(value) if value else None
                        elif col_idx == 3:  # Ref Number (sometimes)
                            # This might be cleared status or ref number
                            if value and str(value).isdigit():
                                txn['ref_number'] = str(value)
                        elif col_idx == 4:  # Split/Memo
                            if value:
                                txn['memo'] = str(value)
                        elif col_idx == 5:  # Debit Amount
                            if value:
                                try:
                                    amount_str = str(value).replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                                    amount = float(amount_str)
                                    if amount != 0:
                                        txn['amount'] = abs(amount)
                                except:
                                    pass
                        elif col_idx == 6:  # Credit Amount
                            if value and txn.get('amount', 0) == 0:
                                try:
                                    amount_str = str(value).replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                                    amount = float(amount_str)
                                    if amount != 0:
                                        txn['amount'] = abs(amount)
                                except:
                                    pass

        except Exception as e:
            logger.debug(f"Error parsing data row: {str(e)}")

        return txn if txn.get('date') else None

    def _parse_date_for_report(self, date_str: str):
        """Convert date string to datetime for report query"""
        try:
            # Handle MM-DD-YYYY or MM/DD/YYYY
            date_str = date_str.replace('/', '-')
            parts = date_str.split('-')
            if len(parts) == 3:
                if len(parts[0]) == 2:  # MM-DD-YYYY
                    return datetime(int(parts[2]), int(parts[0]), int(parts[1]))
                else:  # YYYY-MM-DD
                    return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
        except:
            pass
        return datetime.now()

    def search_by_amount_slow(self, amount: float, date_from: Optional[str] = None,
                              date_to: Optional[str] = None, tolerance: float = 0.01) -> Dict:
        """
        SLOW: Original method - searches 5 transaction types separately

        Args:
            amount: Amount to search for
            date_from: Start date (MM-DD-YYYY or MM/DD/YYYY)
            date_to: End date (MM-DD-YYYY or MM/DD/YYYY)
            tolerance: Amount tolerance for matching (default 0.01)

        Returns:
            Dictionary with found transactions
        """
        try:
            if not fast_qb_connection.connect():
                return {"success": False, "error": "Failed to connect to QuickBooks"}

            logger.info(f"[SLOW METHOD] Searching 5 transaction types for ${amount:.2f}")
            transactions = []

            # Search Checks first
            logger.info("Searching checks...")
            transactions.extend(self._search_checks(amount, date_from, date_to, tolerance))
            
            # Search Bills
            logger.info("Searching bills...")
            transactions.extend(self._search_bills(amount, date_from, date_to, tolerance))

            # Search Bill Payments
            logger.info("Searching bill payments...")
            transactions.extend(self._search_bill_payments(amount, date_from, date_to, tolerance))

            # Search Invoices
            logger.info("Searching invoices...")
            transactions.extend(self._search_invoices(amount, date_from, date_to, tolerance))

            # Search Deposits
            logger.info("Searching deposits...")
            transactions.extend(self._search_deposits(amount, date_from, date_to, tolerance))
            
            # Sort by date
            transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            return {
                "success": True,
                "transactions": transactions,
                "count": len(transactions),
                "search_amount": amount
            }
            
        except Exception as e:
            logger.error(f"Error searching transactions by amount: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            fast_qb_connection.disconnect()
    
    def _search_checks(self, amount: float, date_from: Optional[str], date_to: Optional[str], tolerance: float) -> List[Dict]:
        """Search check transactions"""
        transactions = []
        try:
            request_set = fast_qb_connection.create_request_set()
            check_query = request_set.AppendCheckQueryRq()
            
            # Simplified - just query all checks, filter in Python
            # Date filters cause issues with complex filter paths
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    check = response.Detail.GetAt(i)
                    check_amount = check.Amount.GetValue() if hasattr(check, 'Amount') and check.Amount else 0
                    
                    if abs(abs(check_amount) - amount) <= tolerance:
                        transactions.append({
                            'type': 'Check',
                            'date': str(check.TxnDate.GetValue())[:10] if hasattr(check, 'TxnDate') else 'N/A',
                            'amount': check_amount,
                            'name': check.PayeeEntityRef.FullName.GetValue() if hasattr(check, 'PayeeEntityRef') and check.PayeeEntityRef and hasattr(check.PayeeEntityRef, 'FullName') else 'N/A',
                            'ref_number': check.RefNumber.GetValue() if hasattr(check, 'RefNumber') and check.RefNumber else '',
                            'memo': check.Memo.GetValue() if hasattr(check, 'Memo') and check.Memo else '',
                            'account': check.AccountRef.FullName.GetValue() if hasattr(check, 'AccountRef') and check.AccountRef and hasattr(check.AccountRef, 'FullName') else 'N/A',
                            'txn_id': check.TxnID.GetValue() if hasattr(check, 'TxnID') else 'N/A'
                        })
        except Exception as e:
            logger.debug(f"Error searching checks: {e}")
        
        return transactions
    
    def _search_bills(self, amount: float, date_from: Optional[str], date_to: Optional[str], tolerance: float) -> List[Dict]:
        """Search bill transactions"""
        transactions = []
        try:
            request_set = fast_qb_connection.create_request_set()
            bill_query = request_set.AppendBillQueryRq()
            
            # Date filter
            if date_from or date_to:
                date_filter = bill_query.ORBillQuery.BillFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter
                if date_from:
                    date_filter.FromTxnDate.SetValue(self._parse_date(date_from))
                if date_to:
                    date_filter.ToTxnDate.SetValue(self._parse_date(date_to))
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    bill = response.Detail.GetAt(i)
                    bill_amount = bill.AmountDue.GetValue() if hasattr(bill, 'AmountDue') and bill.AmountDue else 0
                    
                    if abs(abs(bill_amount) - amount) <= tolerance:
                        transactions.append({
                            'type': 'Bill',
                            'date': str(bill.TxnDate.GetValue())[:10] if hasattr(bill, 'TxnDate') else 'N/A',
                            'amount': bill_amount,
                            'name': bill.VendorRef.FullName.GetValue() if hasattr(bill, 'VendorRef') and bill.VendorRef and hasattr(bill.VendorRef, 'FullName') else 'N/A',
                            'ref_number': bill.RefNumber.GetValue() if hasattr(bill, 'RefNumber') and bill.RefNumber else '',
                            'memo': bill.Memo.GetValue() if hasattr(bill, 'Memo') and bill.Memo else '',
                            'txn_id': bill.TxnID.GetValue() if hasattr(bill, 'TxnID') else 'N/A'
                        })
        except Exception as e:
            logger.debug(f"Error searching bills: {e}")
        
        return transactions
    
    def _search_bill_payments(self, amount: float, date_from: Optional[str], date_to: Optional[str], tolerance: float) -> List[Dict]:
        """Search bill payment transactions"""
        transactions = []
        try:
            request_set = fast_qb_connection.create_request_set()
            payment_query = request_set.AppendBillPaymentCheckQueryRq()
            
            # Date filter
            if date_from or date_to:
                date_filter = payment_query.ORTxnQuery.TxnFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter
                if date_from:
                    date_filter.FromTxnDate.SetValue(self._parse_date(date_from))
                if date_to:
                    date_filter.ToTxnDate.SetValue(self._parse_date(date_to))
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    payment = response.Detail.GetAt(i)
                    payment_amount = payment.Amount.GetValue() if hasattr(payment, 'Amount') and payment.Amount else 0
                    
                    if abs(abs(payment_amount) - amount) <= tolerance:
                        transactions.append({
                            'type': 'Bill Payment',
                            'date': str(payment.TxnDate.GetValue())[:10] if hasattr(payment, 'TxnDate') else 'N/A',
                            'amount': payment_amount,
                            'name': payment.PayeeEntityRef.FullName.GetValue() if hasattr(payment, 'PayeeEntityRef') and payment.PayeeEntityRef and hasattr(payment.PayeeEntityRef, 'FullName') else 'N/A',
                            'ref_number': payment.RefNumber.GetValue() if hasattr(payment, 'RefNumber') and payment.RefNumber else '',
                            'memo': payment.Memo.GetValue() if hasattr(payment, 'Memo') and payment.Memo else '',
                            'account': payment.BankAccountRef.FullName.GetValue() if hasattr(payment, 'BankAccountRef') and payment.BankAccountRef and hasattr(payment.BankAccountRef, 'FullName') else 'N/A',
                            'txn_id': payment.TxnID.GetValue() if hasattr(payment, 'TxnID') else 'N/A'
                        })
        except Exception as e:
            logger.debug(f"Error searching bill payments: {e}")
        
        return transactions
    
    def _search_invoices(self, amount: float, date_from: Optional[str], date_to: Optional[str], tolerance: float) -> List[Dict]:
        """Search invoice transactions"""
        transactions = []
        try:
            request_set = fast_qb_connection.create_request_set()
            invoice_query = request_set.AppendInvoiceQueryRq()
            
            # Date filter
            if date_from or date_to:
                date_filter = invoice_query.ORInvoiceQuery.InvoiceFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter
                if date_from:
                    date_filter.FromTxnDate.SetValue(self._parse_date(date_from))
                if date_to:
                    date_filter.ToTxnDate.SetValue(self._parse_date(date_to))
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    invoice = response.Detail.GetAt(i)
                    invoice_amount = invoice.TotalAmount.GetValue() if hasattr(invoice, 'TotalAmount') and invoice.TotalAmount else 0
                    
                    if abs(abs(invoice_amount) - amount) <= tolerance:
                        transactions.append({
                            'type': 'Invoice',
                            'date': str(invoice.TxnDate.GetValue())[:10] if hasattr(invoice, 'TxnDate') else 'N/A',
                            'amount': invoice_amount,
                            'name': invoice.CustomerRef.FullName.GetValue() if hasattr(invoice, 'CustomerRef') and invoice.CustomerRef and hasattr(invoice.CustomerRef, 'FullName') else 'N/A',
                            'ref_number': invoice.RefNumber.GetValue() if hasattr(invoice, 'RefNumber') and invoice.RefNumber else '',
                            'memo': invoice.Memo.GetValue() if hasattr(invoice, 'Memo') and invoice.Memo else '',
                            'txn_id': invoice.TxnID.GetValue() if hasattr(invoice, 'TxnID') else 'N/A'
                        })
        except Exception as e:
            logger.debug(f"Error searching invoices: {e}")
        
        return transactions
    
    def _search_deposits(self, amount: float, date_from: Optional[str], date_to: Optional[str], tolerance: float) -> List[Dict]:
        """Search deposit transactions"""
        transactions = []
        try:
            request_set = fast_qb_connection.create_request_set()
            deposit_query = request_set.AppendDepositQueryRq()
            
            # Date filter
            if date_from or date_to:
                date_filter = deposit_query.ORTxnQuery.TxnFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter
                if date_from:
                    date_filter.FromTxnDate.SetValue(self._parse_date(date_from))
                if date_to:
                    date_filter.ToTxnDate.SetValue(self._parse_date(date_to))
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    deposit = response.Detail.GetAt(i)
                    deposit_amount = deposit.DepositTotal.GetValue() if hasattr(deposit, 'DepositTotal') and deposit.DepositTotal else 0
                    
                    if abs(abs(deposit_amount) - amount) <= tolerance:
                        transactions.append({
                            'type': 'Deposit',
                            'date': str(deposit.TxnDate.GetValue())[:10] if hasattr(deposit, 'TxnDate') else 'N/A',
                            'amount': deposit_amount,
                            'name': 'Deposit',
                            'memo': deposit.Memo.GetValue() if hasattr(deposit, 'Memo') and deposit.Memo else '',
                            'account': deposit.DepositToAccountRef.FullName.GetValue() if hasattr(deposit, 'DepositToAccountRef') and deposit.DepositToAccountRef and hasattr(deposit.DepositToAccountRef, 'FullName') else 'N/A',
                            'txn_id': deposit.TxnID.GetValue() if hasattr(deposit, 'TxnID') else 'N/A'
                        })
        except Exception as e:
            logger.debug(f"Error searching deposits: {e}")
        
        return transactions
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to YYYY-MM-DD format"""
        # Handle MM-DD-YYYY or MM/DD/YYYY
        date_str = date_str.replace('/', '-')
        parts = date_str.split('-')
        if len(parts) == 3:
            if len(parts[0]) == 2:  # MM-DD-YYYY
                return f"{parts[2]}-{parts[0]}-{parts[1]}"
            else:  # YYYY-MM-DD
                return date_str
        return date_str
    
    def _parse_report_row(self, row) -> Optional[Dict]:
        """Parse a report row into transaction data"""
        try:
            txn_data = {}
            
            # Extract data from row columns
            if hasattr(row, 'ColData'):
                for i, col in enumerate(row.ColData):
                    value = col.GetValue() if hasattr(col, 'GetValue') else str(col)
                    
                    # Map column index to field name
                    if i == 0:
                        txn_data['type'] = value
                    elif i == 1:
                        txn_data['date'] = value
                    elif i == 2:
                        txn_data['ref_number'] = value
                    elif i == 3:
                        txn_data['name'] = value
                    elif i == 4:
                        txn_data['memo'] = value
                    elif i == 5:
                        txn_data['account'] = value
                    elif i == 6:
                        txn_data['amount'] = value
            
            return txn_data if txn_data else None
            
        except Exception as e:
            logger.debug(f"Error parsing report row: {e}")
            return None