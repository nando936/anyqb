import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))

from qb.connector import QBConnector
qb = QBConnector()

# Search for all checks in September 2025
from qb.quickbooks_standard.entities.checks.check_repository import CheckRepository
from datetime import datetime

check_repo = CheckRepository()

# Search for checks in September 2025
start_date = datetime(2025, 9, 1)
end_date = datetime(2025, 9, 30)
checks = check_repo.search_checks(date_from=start_date, date_to=end_date)

print(f'Found {len(checks)} checks in September 2025')

total_with_jeff = 0
for check_summary in checks:
    check_id = check_summary.get('txn_id')
    if check_id:
        check = check_repo.get_check(check_id)
        if check:
            has_jeff = False

            # Check item lines
            for line in check.get('item_lines', []):
                item_name = line.get('item_name', 'NO_ITEM_NAME')
                customer = line.get('customer_name', 'NO_CUSTOMER')
                amount = line.get('amount', 0)

                # Check if this is for Jeff trailer in any way
                if ('jeff' in customer.lower() or 'jeck' in customer.lower() or
                    'jeff' in item_name.lower() or 'jeck' in item_name.lower()):
                    has_jeff = True

                # Check for job materials
                if 'material' in item_name.lower() and amount > 500:
                    has_jeff = True  # Likely the $523.88 we're looking for

            # Check expense lines
            for line in check.get('expense_lines', []):
                customer = line.get('customer_name', 'NO_CUSTOMER')
                if 'jeff' in customer.lower() or 'jeck' in customer.lower():
                    has_jeff = True

            if has_jeff or check.get('amount', 0) == 523.88:
                total_with_jeff += 1
                print(f'\nCheck {check_id} on {check.get("txn_date")}:')
                print(f'  Payee: {check.get("payee_name")}')
                print(f'  Amount: ${check.get("amount")}')

                # Show item lines
                for line in check.get('item_lines', []):
                    item_name = line.get('item_name', 'BLANK')
                    customer = line.get('customer_name', 'BLANK')
                    amount = line.get('amount', 0)
                    print(f'  Item: [{item_name}] Customer: [{customer}] Amount: ${amount}')

                # Show expense lines
                for line in check.get('expense_lines', []):
                    account = line.get('account_name', 'BLANK')
                    customer = line.get('customer_name', 'BLANK')
                    amount = line.get('amount', 0)
                    print(f'  Expense: [{account}] Customer: [{customer}] Amount: ${amount}')

print(f'\nTotal checks possibly for Jeff trailer: {total_with_jeff}')