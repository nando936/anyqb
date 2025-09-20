"""Check company preferences for report basis"""

import sys
sys.path.insert(0, 'src')

from qb.shared_utilities.fast_qb_connection import FastQBConnection

def test_company_prefs():
    """Check company preferences"""
    conn = FastQBConnection()

    if not conn.connect():
        print("[ERROR] Failed to connect to QuickBooks")
        return

    try:
        # Query company preferences
        request_set = conn.create_request_set()
        prefs_query = request_set.AppendPreferencesQueryRq()

        print("Querying company preferences...")
        response_set = conn.process_request_set(request_set)
        response = response_set.ResponseList.GetAt(0)

        if response.StatusCode == 0:
            print("[SUCCESS] Got preferences")

            if response.Detail:
                prefs = response.Detail

                # Check for report-related preferences
                if hasattr(prefs, 'ReportingPreferences') and prefs.ReportingPreferences:
                    report_prefs = prefs.ReportingPreferences
                    print("\nReporting Preferences:")

                    # Check various report preferences
                    if hasattr(report_prefs, 'AgingReportBasis'):
                        print(f"  AgingReportBasis: {report_prefs.AgingReportBasis.GetValue()}")

                    if hasattr(report_prefs, 'SummaryReportBasis'):
                        print(f"  SummaryReportBasis: {report_prefs.SummaryReportBasis.GetValue()}")
                        # 0 = Accrual, 1 = Cash, 2 = None

                    # List all attributes
                    attrs = [a for a in dir(report_prefs) if not a.startswith('_')]
                    print(f"\n  All ReportingPreferences attributes:")
                    for attr in attrs:
                        if not attr.startswith(('Get', 'Set', 'Release', 'Query')):
                            try:
                                val = getattr(report_prefs, attr)
                                if hasattr(val, 'GetValue'):
                                    print(f"    {attr}: {val.GetValue()}")
                            except:
                                pass

                # Check accounting preferences
                if hasattr(prefs, 'AccountingPreferences') and prefs.AccountingPreferences:
                    acct_prefs = prefs.AccountingPreferences
                    print("\nAccounting Preferences:")

                    # Check if using accrual
                    if hasattr(acct_prefs, 'IsUsingAccountNumbers'):
                        print(f"  IsUsingAccountNumbers: {acct_prefs.IsUsingAccountNumbers.GetValue()}")

                    # List attributes
                    attrs = [a for a in dir(acct_prefs) if not a.startswith('_')]
                    for attr in attrs:
                        if not attr.startswith(('Get', 'Set', 'Release', 'Query')):
                            try:
                                val = getattr(acct_prefs, attr)
                                if hasattr(val, 'GetValue'):
                                    print(f"    {attr}: {val.GetValue()}")
                            except:
                                pass
        else:
            print(f"[ERROR] {response.StatusMessage}")

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    test_company_prefs()