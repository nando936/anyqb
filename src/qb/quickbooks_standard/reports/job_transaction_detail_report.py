"""Job Transaction Detail Report - Gets actual transaction details for a job
Since JobReportQueryRq doesn't return transaction details, this queries transactions directly
"""
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
from shared_utilities.fast_qb_connection import fast_qb_connection

logger = logging.getLogger(__name__)

class JobTransactionDetailReport:
    """Get transaction-level details for a job by querying transactions directly"""
    
    def __init__(self):
        self.connection = fast_qb_connection
    
    def get_job_transactions(self, job_name: str, date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict:
        """
        Get all transactions for a job with full details
        
        Args:
            job_name: Customer:Job name (e.g., "raised panel door:3408")
            date_from: Optional start date (MM-DD-YYYY)
            date_to: Optional end date (MM-DD-YYYY)
            
        Returns:
            Dictionary with detailed transaction data
        """
        try:
            if not self.connection.connect():
                logger.error("[JobTransactionDetail] Failed to connect to QuickBooks")
                return {'status': 'error', 'message': 'Failed to connect'}
            
            result = {
                'job_name': job_name,
                'status': 'success',
                'income': {
                    'invoices': [],
                    'sales_receipts': [],
                    'total': 0.0
                },
                'expenses': {
                    'bills': [],
                    'checks': [],
                    'credit_cards': [],
                    'total': 0.0
                },
                'profit_loss': 0.0,
                'transaction_count': 0
            }
            
            # Query Invoices for this job
            invoices = self._query_invoices(job_name, date_from, date_to)
            result['income']['invoices'] = invoices
            for inv in invoices:
                result['income']['total'] += inv.get('amount', 0)
                result['transaction_count'] += 1
            
            # Query Bills with job line items
            bills = self._query_bills_for_job(job_name, date_from, date_to)
            result['expenses']['bills'] = bills
            for bill in bills:
                result['expenses']['total'] += bill.get('job_amount', 0)
                result['transaction_count'] += 1
            
            # Query Checks with job line items  
            checks = self._query_checks_for_job(job_name, date_from, date_to)
            result['expenses']['checks'] = checks
            for check in checks:
                result['expenses']['total'] += check.get('job_amount', 0)
                result['transaction_count'] += 1
            
            # Calculate profit/loss
            result['profit_loss'] = result['income']['total'] - result['expenses']['total']
            if result['income']['total'] > 0:
                result['profit_margin'] = (result['profit_loss'] / result['income']['total']) * 100
            else:
                result['profit_margin'] = 0
            
            return result
            
        except Exception as e:
            logger.error(f"[JobTransactionDetail] Error: {str(e)}")
            return {'status': 'error', 'message': str(e)}
        finally:
            self.connection.disconnect()
    
    def _query_invoices(self, job_name: str, date_from: Optional[str], date_to: Optional[str]) -> List[Dict]:
        """Query invoices for the job"""
        invoices = []
        try:
            request_set = self.connection.create_request_set()
            invoice_query = request_set.AppendInvoiceQueryRq()
            
            # Filter by customer/job - correct structure
            invoice_query.ORInvoiceQuery.InvoiceFilter.EntityFilter.OREntityFilter.FullNameList.Add(job_name)
            
            # Add date filter if provided
            if date_from or date_to:
                date_filter = invoice_query.ORInvoiceQuery.InvoiceFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter
                if date_from:
                    date_filter.FromTxnDate.SetValue(date_from)
                if date_to:
                    date_filter.ToTxnDate.SetValue(date_to)
            
            invoice_query.IncludeLineItems.SetValue(True)
            
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    inv = response.Detail.GetAt(i)
                    invoices.append({
                        'type': 'Invoice',
                        'txn_id': inv.TxnID.GetValue() if hasattr(inv, 'TxnID') else None,
                        'ref_number': inv.RefNumber.GetValue() if hasattr(inv, 'RefNumber') else None,
                        'date': inv.TxnDate.GetValue() if hasattr(inv, 'TxnDate') else None,
                        'amount': float(inv.Subtotal.GetValue()) if hasattr(inv, 'Subtotal') else 0,
                        'memo': inv.Memo.GetValue() if hasattr(inv, 'Memo') and inv.Memo else ''
                    })
                    
        except Exception as e:
            logger.error(f"[JobTransactionDetail] Error querying invoices: {e}")
        
        return invoices
    
    def _query_bills_for_job(self, job_name: str, date_from: Optional[str], date_to: Optional[str]) -> List[Dict]:
        """Query bills that have line items for this job"""
        bills = []
        try:
            request_set = self.connection.create_request_set()
            bill_query = request_set.AppendBillQueryRq()
            
            # Can't filter bills by job directly, need to get all and filter
            if date_from or date_to:
                if date_from:
                    bill_query.ORBillQuery.BillFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter.FromTxnDate.SetValue(date_from)
                if date_to:
                    bill_query.ORBillQuery.BillFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter.ToTxnDate.SetValue(date_to)
            
            bill_query.IncludeLineItems.SetValue(True)
            
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    bill = response.Detail.GetAt(i)
                    
                    # Check if any line items are for this job
                    job_amount = 0.0
                    has_job = False
                    
                    if hasattr(bill, 'ORItemLineRetList'):
                        for j in range(bill.ORItemLineRetList.Count):
                            line = bill.ORItemLineRetList.GetAt(j)
                            if hasattr(line, 'ItemLineRet') and line.ItemLineRet:
                                item_line = line.ItemLineRet
                                if hasattr(item_line, 'CustomerRef') and item_line.CustomerRef:
                                    if hasattr(item_line.CustomerRef, 'FullName'):
                                        if item_line.CustomerRef.FullName.GetValue() == job_name:
                                            has_job = True
                                            if hasattr(item_line, 'Amount'):
                                                job_amount += float(item_line.Amount.GetValue())
                    
                    if has_job:
                        bills.append({
                            'type': 'Bill',
                            'txn_id': bill.TxnID.GetValue() if hasattr(bill, 'TxnID') else None,
                            'ref_number': bill.RefNumber.GetValue() if hasattr(bill, 'RefNumber') else None,
                            'date': bill.TxnDate.GetValue() if hasattr(bill, 'TxnDate') else None,
                            'vendor': bill.VendorRef.FullName.GetValue() if hasattr(bill, 'VendorRef') else None,
                            'job_amount': job_amount,
                            'total_amount': float(bill.AmountDue.GetValue()) if hasattr(bill, 'AmountDue') else 0,
                            'memo': bill.Memo.GetValue() if hasattr(bill, 'Memo') and bill.Memo else ''
                        })
                    
        except Exception as e:
            logger.error(f"[JobTransactionDetail] Error querying bills: {e}")
        
        return bills
    
    def _query_checks_for_job(self, job_name: str, date_from: Optional[str], date_to: Optional[str]) -> List[Dict]:
        """Query checks that have line items for this job"""
        checks = []
        try:
            request_set = self.connection.create_request_set()
            check_query = request_set.AppendCheckQueryRq()
            
            # Can't filter checks by job directly, need to get all and filter
            if date_from or date_to:
                if date_from:
                    check_query.ORCheckQuery.CheckFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter.FromTxnDate.SetValue(date_from)
                if date_to:
                    check_query.ORCheckQuery.CheckFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.TxnDateFilter.ToTxnDate.SetValue(date_to)
            
            check_query.IncludeLineItems.SetValue(True)
            
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    check = response.Detail.GetAt(i)
                    
                    # Check if any line items are for this job
                    job_amount = 0.0
                    has_job = False
                    
                    # Check item lines
                    if hasattr(check, 'ORItemLineRetList'):
                        for j in range(check.ORItemLineRetList.Count):
                            line = check.ORItemLineRetList.GetAt(j)
                            if hasattr(line, 'ItemLineRet') and line.ItemLineRet:
                                item_line = line.ItemLineRet
                                if hasattr(item_line, 'CustomerRef') and item_line.CustomerRef:
                                    if hasattr(item_line.CustomerRef, 'FullName'):
                                        if item_line.CustomerRef.FullName.GetValue() == job_name:
                                            has_job = True
                                            if hasattr(item_line, 'Amount'):
                                                job_amount += float(item_line.Amount.GetValue())
                    
                    # Check expense lines
                    if hasattr(check, 'ExpenseLineRetList'):
                        for j in range(check.ExpenseLineRetList.Count):
                            exp_line = check.ExpenseLineRetList.GetAt(j)
                            if hasattr(exp_line, 'CustomerRef') and exp_line.CustomerRef:
                                if hasattr(exp_line.CustomerRef, 'FullName'):
                                    if exp_line.CustomerRef.FullName.GetValue() == job_name:
                                        has_job = True
                                        if hasattr(exp_line, 'Amount'):
                                            job_amount += float(exp_line.Amount.GetValue())
                    
                    if has_job:
                        checks.append({
                            'type': 'Check',
                            'txn_id': check.TxnID.GetValue() if hasattr(check, 'TxnID') else None,
                            'ref_number': check.RefNumber.GetValue() if hasattr(check, 'RefNumber') else None,
                            'date': check.TxnDate.GetValue() if hasattr(check, 'TxnDate') else None,
                            'payee': check.PayeeEntityRef.FullName.GetValue() if hasattr(check, 'PayeeEntityRef') else None,
                            'job_amount': job_amount,
                            'total_amount': float(check.Amount.GetValue()) if hasattr(check, 'Amount') else 0,
                            'memo': check.Memo.GetValue() if hasattr(check, 'Memo') and check.Memo else ''
                        })
                    
        except Exception as e:
            logger.error(f"[JobTransactionDetail] Error querying checks: {e}")
        
        return checks