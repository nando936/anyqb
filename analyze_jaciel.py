"""
Analyze Jaciel payments for duplicates
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'qb'))

from shared_utilities.fast_qb_connection import FastQBConnection

# Connect using fast connection
fast_conn = FastQBConnection()
qb_app = fast_conn.connect()

if qb_app:
    try:
        # Query bill payment checks for Jaciel
        request_set = qb_app.CreateMsgSetRequest('US', 15, 0)
        payment_query = request_set.AppendBillPaymentCheckQueryRq()

        # Add vendor filter
        vendor_filter = payment_query.ORTxnQuery.TxnFilter.EntityFilter.OREntityFilter.FullNameList
        vendor_filter.Add('jaciel')

        # Execute query
        response_set = qb_app.DoRequests(request_set)
        response = response_set.ResponseList.GetAt(0)

        if response.StatusCode == 0:
            payment_list = response.Detail

            print(f"JACIEL PAYMENT ANALYSIS")
            print("=" * 80)
            print(f"Total payments found: {payment_list.Count}")
            print()

            # Collect all $750 payments
            payments_750 = []
            all_payments = []

            for i in range(payment_list.Count):
                payment = payment_list.GetAt(i)

                # Get payment details
                txn_id = payment.TxnID.GetValue()
                date = payment.TxnDate.GetValue()
                amount = payment.Amount.GetValue()

                # Get check number if available
                check_num = 'N/A'
                if hasattr(payment, 'RefNumber') and payment.RefNumber:
                    check_num = payment.RefNumber.GetValue()

                all_payments.append({
                    'date': date,
                    'amount': amount,
                    'check_num': check_num,
                    'txn_id': txn_id
                })

                # Track $750 payments specifically
                if amount == 750.00:
                    payments_750.append({
                        'date': date,
                        'check_num': check_num,
                        'txn_id': txn_id
                    })

            # Sort by date (newest first)
            all_payments.sort(key=lambda x: x['date'], reverse=True)

            # Show recent payments
            print("RECENT PAYMENTS (newest first):")
            print("-" * 80)
            for p in all_payments[:15]:  # Show last 15 payments
                marker = ""
                if p['txn_id'] == '51C84-1758056555':
                    marker = " <-- JUST CREATED"
                elif p['date'][:10] == '2025-07-12' and p['amount'] == 750.00:
                    marker = " <-- JULY 12 ATM"

                print(f"{p['date'][:10]} | ${p['amount']:8.2f} | Check# {p['check_num']:10s} | {p['txn_id']}{marker}")

            print()
            print("$750 PAYMENT ANALYSIS:")
            print("-" * 80)
            print(f"Found {len(payments_750)} payments of exactly $750:")

            for p in payments_750:
                marker = ""
                if p['txn_id'] == '51C84-1758056555':
                    marker = " <-- WE JUST CREATED THIS"
                if p['date'][:10] == '2025-07-12':
                    marker += " <-- JULY 12"

                print(f"  {p['date'][:10]} | Check# {p['check_num']:10s} | ID: {p['txn_id']}{marker}")

            # Check for July 2025 payments
            print()
            print("JULY 2025 PAYMENTS:")
            print("-" * 80)
            july_payments = [p for p in all_payments if p['date'][:7] == '2025-07']

            if july_payments:
                for p in july_payments:
                    marker = ""
                    if p['txn_id'] == '51C84-1758056555':
                        marker = " <-- JUST CREATED"
                    print(f"  {p['date'][:10]} | ${p['amount']:8.2f} | Check# {p['check_num']:10s}{marker}")
            else:
                print("  No payments found in July 2025")

            # DUPLICATE CHECK
            print()
            print("DUPLICATE CHECK:")
            print("-" * 80)

            # Count July 12, 2025 payments of $750
            july_12_750 = [p for p in all_payments
                           if p['date'][:10] == '2025-07-12' and p['amount'] == 750.00]

            if len(july_12_750) > 1:
                print(f"WARNING: Found {len(july_12_750)} payments of $750 on July 12, 2025:")
                for p in july_12_750:
                    print(f"  ID: {p['txn_id']} | Check# {p['check_num']}")
                print("  THIS APPEARS TO BE A DUPLICATE!")
            elif len(july_12_750) == 1:
                print(f"OK: Only one payment of $750 on July 12, 2025")
                print(f"  ID: {july_12_750[0]['txn_id']} | Check# {july_12_750[0]['check_num']}")
            else:
                print("No payments of $750 found on July 12, 2025")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        fast_conn.disconnect()