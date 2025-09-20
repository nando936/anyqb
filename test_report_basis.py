"""Test if ReportBasis can be set on JobReport and what effect it has"""

import sys
sys.path.insert(0, 'src')

from qb.shared_utilities.fast_qb_connection import FastQBConnection

def test_report_basis():
    """Test different ReportBasis settings"""
    conn = FastQBConnection()

    if not conn.connect():
        print("[ERROR] Failed to connect to QuickBooks")
        return

    try:
        job_name = "jeck:Jeff trailer"

        # Test different ReportBasis values
        basis_values = [
            (None, "Default (not set)"),
            (0, "Cash"),
            (1, "Accrual"),
            (2, "None")
        ]

        for basis_value, basis_name in basis_values:
            print(f"\n{'='*60}")
            print(f"Testing ReportBasis: {basis_name}")
            print('='*60)

            request_set = conn.create_request_set()
            report_query = request_set.AppendJobReportQueryRq()

            # Set report type to Job Profitability Detail
            report_query.JobReportType.SetValue(4)

            # Check if ReportBasis exists
            if hasattr(report_query, 'ReportBasis'):
                print(f"  [OK] ReportBasis attribute exists")
                if basis_value is not None:
                    try:
                        report_query.ReportBasis.SetValue(basis_value)
                        print(f"  [OK] Successfully set ReportBasis to {basis_value}")
                    except Exception as e:
                        print(f"  [ERROR] Failed to set ReportBasis: {e}")
            else:
                print(f"  [WARNING] ReportBasis attribute does NOT exist")

            # Check for ReportPostingStatusFilter
            if hasattr(report_query, 'ReportPostingStatusFilter'):
                print(f"  [OK] ReportPostingStatusFilter exists")
                try:
                    report_query.ReportPostingStatusFilter.SetValue(0)  # All transactions
                    print(f"  [OK] Set ReportPostingStatusFilter to 0 (All)")
                except Exception as e:
                    print(f"  [ERROR] Failed to set ReportPostingStatusFilter: {e}")
            else:
                print(f"  [WARNING] ReportPostingStatusFilter does NOT exist")

            # Set job filter
            report_query.ReportEntityFilter.ORReportEntityFilter.FullNameList.Add(job_name)
            report_query.DisplayReport.SetValue(False)

            # Execute query
            response_set = conn.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)

            if response.StatusCode == 0:
                print(f"\n  [SUCCESS] Report generated")

                if response.Detail:
                    report = response.Detail

                    # Check what ReportBasis was actually used
                    if hasattr(report, 'ReportBasis') and report.ReportBasis:
                        actual_basis = report.ReportBasis.GetValue()
                        print(f"  Actual ReportBasis in response: {actual_basis}")
                    else:
                        print(f"  No ReportBasis in response")

                    # Look for job materials in COGS
                    if hasattr(report, 'ReportData') and report.ReportData:
                        if hasattr(report.ReportData, 'ORReportDataList'):
                            found_materials = False
                            materials_amount = 0.0

                            for i in range(report.ReportData.ORReportDataList.Count):
                                data = report.ReportData.ORReportDataList.GetAt(i)

                                if hasattr(data, 'DataRow') and data.DataRow:
                                    # Look for column data
                                    if hasattr(data.DataRow, 'ColDataList'):
                                        for j in range(data.DataRow.ColDataList.Count):
                                            col_data = data.DataRow.ColDataList.GetAt(j)
                                            if hasattr(col_data, 'value') and col_data.value:
                                                value = col_data.value.GetValue()
                                                if 'job materials' in str(value).lower():
                                                    found_materials = True

                                    # Get amounts from RowData
                                    if hasattr(data.DataRow, 'RowData'):
                                        row_data = data.DataRow.RowData
                                        if hasattr(row_data, 'value') and row_data.value:
                                            desc = row_data.value.GetValue()
                                            if 'job materials' in str(desc).lower():
                                                found_materials = True
                                                # Try to get amount from next columns
                                                if hasattr(data.DataRow, 'ColDataList'):
                                                    if data.DataRow.ColDataList.Count >= 2:
                                                        # Column 1 is usually COGS
                                                        col = data.DataRow.ColDataList.GetAt(1)
                                                        if hasattr(col, 'value') and col.value:
                                                            amount_str = col.value.GetValue()
                                                            try:
                                                                materials_amount = float(amount_str.replace('$','').replace(',',''))
                                                            except:
                                                                pass

                            if found_materials:
                                print(f"  Found job materials in report: ${materials_amount:.2f}")
                            else:
                                print(f"  Job materials NOT found in report")
            else:
                print(f"  [ERROR] Failed to generate report: {response.StatusMessage}")

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    test_report_basis()