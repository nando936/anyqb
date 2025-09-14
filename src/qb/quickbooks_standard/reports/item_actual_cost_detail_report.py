"""Item Actual Cost Detail Report - Shows actual transaction details for items
This queries bills, checks, and other expense transactions to show actual costs
"""
from typing import Dict, List, Optional
import logging
from datetime import datetime
from shared_utilities.fast_qb_connection import fast_qb_connection

logger = logging.getLogger(__name__)

class ItemActualCostDetailReport:
    """Get actual cost transaction details for items"""
    
    def __init__(self):
        self.connection = fast_qb_connection
    
    def get_item_cost_details(self, item_name: str, job_name: Optional[str] = None, 
                              date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict:
        """
        Get all cost transactions for an item with details using Purchases by Item Detail report
        
        Args:
            item_name: Item name (e.g., "21 Doors")
            job_name: Optional job filter (e.g., "raised panel door:3408")
            date_from: Optional start date (MM-DD-YYYY)
            date_to: Optional end date (MM-DD-YYYY)
            
        Returns:
            Dictionary with detailed cost transactions
        """
        try:
            if not self.connection.connect():
                logger.error("[ItemActualCostDetail] Failed to connect to QuickBooks")
                return {'status': 'error', 'message': 'Failed to connect'}
            
            result = {
                'item_name': item_name,
                'job_name': job_name,
                'status': 'success',
                'transactions': [],
                'total_cost': 0.0,
                'total_quantity': 0.0
            }
            
            # Use Purchases by Item Detail report (GeneralDetailReportType = 22)
            transactions = self._query_purchases_by_item_detail(item_name, job_name, date_from, date_to)
            result['transactions'] = transactions
            
            # Calculate totals
            for txn in result['transactions']:
                result['total_cost'] += txn.get('amount', 0)
                result['total_quantity'] += txn.get('quantity', 0)
            
            return result
            
        except Exception as e:
            logger.error(f"[ItemActualCostDetail] Error: {str(e)}")
            return {'status': 'error', 'message': str(e)}
        finally:
            self.connection.disconnect()
    
    def _query_purchases_by_item_detail(self, item_name: str, job_name: Optional[str],
                                         date_from: Optional[str], date_to: Optional[str]) -> List[Dict]:
        """Query purchases using Purchases by Item Detail report (GeneralDetailReportType = 22)"""
        transactions = []
        try:
            request_set = self.connection.create_request_set()
            report_query = request_set.AppendGeneralDetailReportQueryRq()
            
            # Type 22 = Purchases by Item Detail
            report_query.GeneralDetailReportType.SetValue(22)
            
            # Add date filter if specified
            if date_from or date_to:
                date_filter = report_query.ORReportPeriod.ReportDateMacro.SetValue("Custom")
                if date_from:
                    report_query.ORReportPeriod.ReportDateMacro.FromReportDate.SetValue(date_from)
                if date_to:
                    report_query.ORReportPeriod.ReportDateMacro.ToReportDate.SetValue(date_to)
            
            # Add job filter if specified
            if job_name:
                try:
                    entity_filter = report_query.ReportEntityFilter.ORReportEntityFilter
                    entity_filter.FullNameList.Add(job_name)
                except Exception as e:
                    logger.warning(f"[ItemActualCostDetail] Could not add job filter: {e}")
            
            # Add item filter if specified
            if item_name:
                try:
                    item_filter = report_query.ReportItemFilter.ORReportItemFilter
                    item_filter.FullNameList.Add(item_name)
                except Exception as e:
                    logger.warning(f"[ItemActualCostDetail] Could not add item filter: {e}")
            
            report_query.DisplayReport.SetValue(False)
            
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail:
                report = response.Detail
                
                # Parse report data
                if hasattr(report, 'ReportData') and report.ReportData:
                    if hasattr(report.ReportData, 'ORReportDataList'):
                        current_item = None
                        
                        for i in range(report.ReportData.ORReportDataList.Count):
                            row = report.ReportData.ORReportDataList.GetAt(i)
                            
                            # Track current item from TextRow
                            if hasattr(row, 'TextRow') and row.TextRow:
                                if hasattr(row.TextRow, 'value'):
                                    current_item = row.TextRow.value.GetValue()
                            
                            # Process DataRow (actual transactions)
                            elif hasattr(row, 'DataRow') and row.DataRow:
                                dr = row.DataRow
                                
                                if hasattr(dr, 'ColDataList') and dr.ColDataList:
                                    cols = []
                                    for j in range(dr.ColDataList.Count):
                                        col = dr.ColDataList.GetAt(j)
                                        if hasattr(col, 'value'):
                                            cols.append(col.value.GetValue())
                                    
                                    if cols and len(cols) >= 8:
                                        # Column structure: Type | Date | Num | Vendor | Job | Qty | Rate | Amount
                                        txn_type = cols[0] if len(cols) > 0 else ""
                                        date = cols[1] if len(cols) > 1 else ""
                                        ref_number = cols[2] if len(cols) > 2 else ""
                                        vendor = cols[3] if len(cols) > 3 else ""
                                        job = cols[4] if len(cols) > 4 else ""
                                        qty = cols[5] if len(cols) > 5 else ""
                                        rate = cols[6] if len(cols) > 6 else ""
                                        amount = cols[7] if len(cols) > 7 else ""
                                        
                                        # Only include rows with actual transaction data
                                        if txn_type and (amount or qty):
                                            try:
                                                qty_float = float(qty) if qty else 0.0
                                                rate_float = float(rate) if rate else 0.0
                                                amount_float = float(amount) if amount else 0.0
                                            except:
                                                qty_float = rate_float = amount_float = 0.0
                                            
                                            txn = {
                                                'type': txn_type,
                                                'date': date,
                                                'ref_number': ref_number,
                                                'vendor': vendor,
                                                'job': job,
                                                'item': current_item,
                                                'quantity': qty_float,
                                                'rate': rate_float,
                                                'amount': amount_float,
                                                'description': f"{current_item} - {txn_type} {ref_number}"
                                            }
                                            transactions.append(txn)
            
        except Exception as e:
            logger.error(f"[ItemActualCostDetail] Error in purchases by item detail report: {e}")
        
        return transactions