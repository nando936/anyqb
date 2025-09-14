"""Job Profitability Report Repository
Uses QuickBooks native JobReportQueryRq with proper parsing
"""
from typing import Dict, List, Optional
import logging
from shared_utilities.fast_qb_connection import fast_qb_connection

logger = logging.getLogger(__name__)

class JobProfitabilityReportRepository:
    """Repository for generating job profitability reports"""
    
    def __init__(self):
        self.connection = fast_qb_connection
    
    def generate_job_report(self, job_name: str) -> Dict:
        """
        Generate a profitability report using JobReportQueryRq
        
        IMPORTANT SDK LIMITATION: JobReportType 5 (JobProfitabilityDetail) returns
        only summary data, not transaction-level details. This is a QuickBooks SDK
        limitation - the "Detail" report doesn't actually provide transaction details.
        
        Args:
            job_name: Customer:Job name (e.g., "raised panel door:3408")
            
        Returns:
            Dictionary with job profitability summary data
        """
        try:
            if not self.connection.connect():
                logger.error("[JobProfitabilityReport] Failed to connect to QuickBooks")
                return self._empty_report(job_name)
            
            request_set = self.connection.create_request_set()
            report_query = request_set.AppendJobReportQueryRq()
            
            # JobReportType enumeration:
            # 1 = Item Profitability 
            # 4 = Job Profitability Detail (shows revenue/cost by item)
            # 5 = Job Profitability Summary (shows total revenue/cost)
            report_query.JobReportType.SetValue(4)  # JobProfitabilityDetail - shows by item
            
            # Set ReportDetailLevel to get full transaction details
            # rdlfAll = 0, rdlfAllExceptSummary = 1, rdlfSummaryOnly = 2
            if hasattr(report_query, 'ReportDetailLevel'):
                logger.info("[JobProfitabilityReport] Setting ReportDetailLevel to rdlfAll (0)")
                report_query.ReportDetailLevel.SetValue(0)  # rdlfAll - include all details
            
            # Alternative: try ReportDetailLevelFilter if ReportDetailLevel doesn't exist
            elif hasattr(report_query, 'ReportDetailLevelFilter'):
                logger.info("[JobProfitabilityReport] Setting ReportDetailLevelFilter to 0 (All)")
                report_query.ReportDetailLevelFilter.SetValue(0)  # All details
            
            # Include subcolumns for more info
            if hasattr(report_query, 'IncludeSubcolumns'):
                report_query.IncludeSubcolumns.SetValue(True)
            
            # Set ActiveOnly to false to include all data
            if hasattr(report_query, 'ActiveOnly'):
                logger.info("[JobProfitabilityReport] Setting ActiveOnly to False")
                report_query.ActiveOnly.SetValue(False)
            
            # Filter for specific job using ReportEntityFilter
            report_query.ReportEntityFilter.ORReportEntityFilter.FullNameList.Add(job_name)
            
            # Don't display the report UI
            report_query.DisplayReport.SetValue(False)
            
            response_set = self.connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                # Extract and parse the report data
                return self._parse_job_report(response, job_name)
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"[JobProfitabilityReport] QB Error {response.StatusCode}: {error_msg}")
                return {
                    'job_name': job_name,
                    'status': 'error',
                    'error_code': response.StatusCode,
                    'error_message': error_msg
                }
                
        except Exception as e:
            logger.error(f"[JobProfitabilityReport] Exception: {str(e)}")
            return {
                'job_name': job_name,
                'status': 'error',
                'error_message': str(e)
            }
    
    def _parse_job_report(self, response, job_name: str) -> Dict:
        """Parse the QB JobReport response to extract actual data"""
        try:
            if not hasattr(response, 'Detail') or not response.Detail:
                return {
                    'job_name': job_name,
                    'status': 'error',
                    'error_message': 'No report data in response'
                }
            
            report = response.Detail
            
            # Initialize result structure
            result = {
                'job_name': job_name,
                'status': 'success',
                'income': {'total': 0.0, 'items': []},
                'expenses': {'total': 0.0, 'items': []},
                'report_structure': {}
            }
            
            # Log what we have for debugging
            logger.info(f"[JobProfitabilityReport] Report object attributes: {dir(report)}")
            
            # Check for ReportTitle
            if hasattr(report, 'ReportTitle') and report.ReportTitle:
                result['report_title'] = report.ReportTitle.GetValue()
                logger.info(f"Report Title: {result['report_title']}")
            
            # Check for ReportSubtitle
            if hasattr(report, 'ReportSubtitle') and report.ReportSubtitle:
                result['report_subtitle'] = report.ReportSubtitle.GetValue()
            
            # Check for column descriptions
            if hasattr(report, 'ColDescList') and report.ColDescList:
                columns = []
                for i in range(report.ColDescList.Count):
                    col_desc = report.ColDescList.GetAt(i)
                    col_info = {}
                    if hasattr(col_desc, 'ColTitle') and col_desc.ColTitle:
                        if hasattr(col_desc.ColTitle, 'value'):
                            col_info['title'] = col_desc.ColTitle.value.GetValue()
                    if hasattr(col_desc, 'ColType') and col_desc.ColType:
                        col_info['type'] = col_desc.ColType.GetValue()
                    columns.append(col_info)
                result['columns'] = columns
                logger.info(f"Columns: {columns}")
            
            # Parse the actual report data
            if hasattr(report, 'ReportData') and report.ReportData:
                logger.info("Found ReportData")
                
                # Check what type of report data we have - it's ORReportDataList not ORReportData
                if hasattr(report.ReportData, 'ORReportDataList'):
                    logger.info(f"ORReportDataList Count: {report.ReportData.ORReportDataList.Count}")
                    
                    for i in range(report.ReportData.ORReportDataList.Count):
                        data = report.ReportData.ORReportDataList.GetAt(i)
                        
                        # Check for DataRow
                        if hasattr(data, 'DataRow') and data.DataRow:
                            row_info = self._parse_report_row(data.DataRow)
                            if row_info and row_info.get('description'):
                                # This is an item row with revenue/cost data
                                cols = row_info.get('columns', [])
                                if len(cols) >= 4:  # Columns: [0]=item_code, [1]=cost, [2]=revenue, [3]=net
                                    item_name = row_info['description']
                                    
                                    # Column 1 is COST, Column 2 is REVENUE (I had them backwards!)
                                    try:
                                        cost = float(cols[1].replace('$', '').replace(',', '').strip() or '0')
                                        if cost > 0:
                                            result['expenses']['items'].append({
                                                'item': item_name,
                                                'amount': cost
                                            })
                                            result['expenses']['total'] += cost
                                    except:
                                        pass
                                    
                                    try:
                                        revenue = float(cols[2].replace('$', '').replace(',', '').strip() or '0')
                                        if revenue > 0:
                                            result['income']['items'].append({
                                                'item': item_name,
                                                'amount': revenue
                                            })
                                            result['income']['total'] += revenue
                                    except:
                                        pass
                        
                        # Check for TextRow (headers/subtotals)
                        elif hasattr(data, 'TextRow') and data.TextRow:
                            if hasattr(data.TextRow, 'value'):
                                text = data.TextRow.value.GetValue()
                                logger.info(f"TextRow: {text}")
                
                # Alternative structure
                elif hasattr(report.ReportData, 'DataRow'):
                    logger.info("Found direct DataRow")
                    # Handle single row or different structure
            
            # Calculate profit/loss
            result['profit_loss'] = result['income']['total'] - result['expenses']['total']
            if result['income']['total'] > 0:
                result['profit_margin'] = (result['profit_loss'] / result['income']['total']) * 100
            else:
                result['profit_margin'] = 0
            
            # Log summary
            logger.info(f"Income Total: ${result['income']['total']:.2f}")
            logger.info(f"Expense Total: ${result['expenses']['total']:.2f}")
            logger.info(f"Profit/Loss: ${result['profit_loss']:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"[JobProfitabilityReport] Error parsing report: {str(e)}", exc_info=True)
            return {
                'job_name': job_name,
                'status': 'error',
                'error_message': f'Error parsing report: {str(e)}'
            }
    
    def _parse_report_row(self, row) -> Optional[Dict]:
        """Parse a single DataRow from the report"""
        try:
            row_data = {}
            
            # Get row data/description
            if hasattr(row, 'RowData') and row.RowData:
                if hasattr(row.RowData, 'value'):
                    row_data['description'] = row.RowData.value.GetValue()
            
            # Get column data - use ColDataList not ColData
            if hasattr(row, 'ColDataList') and row.ColDataList:
                cols = []
                for i in range(row.ColDataList.Count):
                    col = row.ColDataList.GetAt(i)
                    if hasattr(col, 'value'):
                        val = col.value.GetValue()
                        cols.append(val)
                        
                
                row_data['columns'] = cols
            
            
            return row_data if row_data.get('description') or row_data.get('columns') else None
            
        except Exception as e:
            logger.error(f"Error parsing row: {e}")
            return None
    
    def _empty_report(self, job_name: str) -> Dict:
        """Return an error report structure"""
        return {
            'job_name': job_name,
            'status': 'error',
            'error_message': 'Failed to connect to QuickBooks'
        }