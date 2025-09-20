"""Test if item receipts show in different report types"""

import sys
sys.path.insert(0, 'src')

from qb.shared_utilities.fast_qb_connection import FastQBConnection

def test_receipts_in_reports():
    """Test different report types to see if receipts are included"""
    conn = FastQBConnection()

    if not conn.connect():
        print("[ERROR] Failed to connect to QuickBooks")
        return

    try:
        job_name = "jeck:Jeff trailer"

        # Test different report types
        report_types = [
            (1, "Item Profitability"),
            (4, "Job Profitability Detail"),
            (5, "Job Profitability Summary"),
            (6, "Job Estimates vs Actuals Detail"),
            (7, "Job Estimates vs Actuals Summary"),
            (8, "Job Progress Invoices vs Estimates")
        ]

        for report_type, report_name in report_types:
            print(f"\n{'='*60}")
            print(f"Testing Report Type {report_type}: {report_name}")
            print('='*60)

            request_set = conn.create_request_set()
            report_query = request_set.AppendJobReportQueryRq()

            # Set report type
            try:
                report_query.JobReportType.SetValue(report_type)
                print(f"  [OK] Set report type to {report_type}")
            except Exception as e:
                print(f"  [ERROR] Failed to set report type: {e}")
                continue

            # Set ReportPostingStatusFilter to include all
            if hasattr(report_query, 'ReportPostingStatusFilter'):
                try:
                    report_query.ReportPostingStatusFilter.SetValue(0)  # All transactions
                    print(f"  [OK] Set ReportPostingStatusFilter to 0 (All)")
                except:
                    pass

            # Set job filter
            report_query.ReportEntityFilter.ORReportEntityFilter.FullNameList.Add(job_name)
            report_query.DisplayReport.SetValue(False)

            # Execute query
            response_set = conn.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)

            if response.StatusCode == 0:
                print(f"  [SUCCESS] Report generated")

                if response.Detail:
                    report = response.Detail

                    # Check report basis
                    if hasattr(report, 'ReportBasis') and report.ReportBasis:
                        basis = report.ReportBasis.GetValue()
                        basis_names = {0: "Cash", 1: "Accrual", 2: "None"}
                        print(f"  Report Basis: {basis} ({basis_names.get(basis, 'Unknown')})")

                    # Look for totals and key values
                    if hasattr(report, 'ReportData') and report.ReportData:
                        if hasattr(report.ReportData, 'ORReportDataList'):

                            # Track what we find
                            found_income = False
                            found_cogs = False
                            income_total = 0
                            cogs_total = 0
                            materials_amount = 0

                            for i in range(report.ReportData.ORReportDataList.Count):
                                data = report.ReportData.ORReportDataList.GetAt(i)

                                # Check TextRows for headers
                                if hasattr(data, 'TextRow') and data.TextRow:
                                    if hasattr(data.TextRow, 'value') and data.TextRow.value:
                                        text = data.TextRow.value.GetValue()
                                        if 'Income' in text or 'Revenue' in text:
                                            found_income = True
                                        elif 'Cost' in text or 'Expense' in text or 'COGS' in text:
                                            found_cogs = True

                                # Check DataRows for values
                                if hasattr(data, 'DataRow') and data.DataRow:
                                    if hasattr(data.DataRow, 'RowData'):
                                        row_data = data.DataRow.RowData
                                        if hasattr(row_data, 'value') and row_data.value:
                                            desc = row_data.value.GetValue()

                                            # Look for job materials
                                            if 'job materials' in str(desc).lower():
                                                # Get amount from columns
                                                if hasattr(data.DataRow, 'ColDataList'):
                                                    for j in range(data.DataRow.ColDataList.Count):
                                                        col = data.DataRow.ColDataList.GetAt(j)
                                                        if hasattr(col, 'value') and col.value:
                                                            val_str = col.value.GetValue()
                                                            try:
                                                                # Try to parse as amount
                                                                amount = float(val_str.replace('$','').replace(',','').replace('(','').replace(')',''))
                                                                if amount > 0:
                                                                    materials_amount = amount
                                                                    break
                                                            except:
                                                                pass

                                # Check for total rows
                                if hasattr(data, 'TotalRow') and data.TotalRow:
                                    if hasattr(data.TotalRow, 'ColDataList'):
                                        for j in range(data.TotalRow.ColDataList.Count):
                                            col = data.TotalRow.ColDataList.GetAt(j)
                                            if hasattr(col, 'value') and col.value:
                                                val_str = col.value.GetValue()
                                                try:
                                                    amount = float(val_str.replace('$','').replace(',',''))
                                                    if found_income and income_total == 0:
                                                        income_total = amount
                                                    elif found_cogs and cogs_total == 0:
                                                        cogs_total = amount
                                                except:
                                                    pass

                            # Report findings
                            if materials_amount > 0:
                                print(f"  Job Materials COGS: ${materials_amount:.2f}")
                            if income_total > 0:
                                print(f"  Total Income: ${income_total:.2f}")
                            if cogs_total > 0:
                                print(f"  Total COGS: ${cogs_total:.2f}")

                            # Expected values
                            print(f"\n  Expected with receipts:")
                            print(f"    Checks: $481.94")
                            print(f"    Receipts: $450.00 (TEST_VENDOR)")
                            print(f"    Total: $931.94")

            else:
                print(f"  [ERROR] {response.StatusMessage}")

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    test_receipts_in_reports()