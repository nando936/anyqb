"""
Check Jaciel payments for duplicates
"""
import win32com.client
from datetime import datetime

def check_jaciel_payments():
    qb_app = win32com.client.Dispatch('QBFC15.QBSessionManager')
    qb_app.OpenConnection('', 'QB Payment Checker')
    qb_app.BeginSession('', 2)

    try:
        # Get bill payments with details
        request_set = qb_app.CreateMsgSetRequest('US', 15, 0)
        payment_query = request_set.AppendBillPaymentCheckQueryRq()

        # Filter for Jaciel
        vendor_filter = payment_query.ORTxnQuery.TxnFilter.EntityFilter.OREntityFilter.FullNameList
        vendor_filter.Add('jaciel')

        response_set = qb_app.DoRequests(request_set)
        response = response_set.ResponseList.GetAt(0)

        if response.StatusCode == 0:
            payment_list = response.Detail
            count = payment_list.Count

            print(f'Found {count} Jaciel payments:')
            print('=' * 80)

            # Collect all payments
            payments = []
            for i in range(count):
                payment = payment_list.GetAt(i)
                txn_id = payment.TxnID.GetValue()
                date_str = payment.TxnDate.GetValue()
                amount = payment.Amount.GetValue()

                # Try to get check number
                check_num = 'N/A'
                if hasattr(payment, 'RefNumber') and payment.RefNumber:
                    check_num = payment.RefNumber.GetValue()

                # Parse date
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')

                payments.append({
                    'date': date_obj,
                    'date_str': date_str[:10],
                    'amount': amount,
                    'check_num': check_num,
                    'txn_id': txn_id
                })

            # Sort by date
            payments.sort(key=lambda x: x['date'], reverse=True)

            # Display payments
            for p in payments:
                print(f"Date: {p['date_str']} | Amount: ${p['amount']:8.2f} | Check#: {p['check_num']:10s} | ID: {p['txn_id']}")

                # Highlight our new payment
                if p['txn_id'] == '51C84-1758056555':
                    print('  ^^^ THIS IS THE PAYMENT WE JUST CREATED ^^^')

                # Check for July 12 payment
                if p['date_str'] == '2025-07-12' and p['amount'] == 750.00:
                    print('  *** JULY 12 PAYMENT FOR $750 ***')
                    if p['check_num'] == 'ATM':
                        print('  *** THIS IS AN ATM PAYMENT ***')

            # Check for duplicates around July 12
            print('\n' + '=' * 80)
            print('CHECKING FOR JULY 2025 PAYMENTS:')
            july_payments = [p for p in payments if p['date'].year == 2025 and p['date'].month == 7]

            if july_payments:
                print(f'Found {len(july_payments)} payment(s) in July 2025:')
                for p in july_payments:
                    print(f"  {p['date_str']} - ${p['amount']:.2f} - Check# {p['check_num']}")
            else:
                print('No payments found in July 2025')

            # Check for $750 payments
            print('\nALL $750 PAYMENTS:')
            payments_750 = [p for p in payments if p['amount'] == 750.00]
            for p in payments_750:
                print(f"  {p['date_str']} - Check# {p['check_num']} - ID: {p['txn_id']}")

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        qb_app.EndSession()
        qb_app.CloseConnection()

if __name__ == '__main__':
    check_jaciel_payments()