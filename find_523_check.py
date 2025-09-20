import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))

from qb.connector import QBConnector
qb = QBConnector()

# Search for check with amount $523.88
from qb.quickbooks_standard.entities.checks.check_repository import CheckRepository
from datetime import datetime

check_repo = CheckRepository()

# Search for checks in 2025
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 12, 31)
checks = check_repo.search_checks(date_from=start_date, date_to=end_date)

print(f'Found {len(checks)} checks in 2025')
print(f'Looking for check with amount $523.88...\n')

for check_summary in checks:
    check_id = check_summary.get('txn_id')
    if check_id:
        check = check_repo.get_check(check_id)
        if check:
            amount = check.get('amount', 0)
            # Look for amount close to 523.88
            if abs(amount - 523.88) < 0.01:
                print(f'FOUND IT! Check {check_id}:')
                print(f'  Date: {check.get("txn_date")}')
                print(f'  Payee: {check.get("payee_name")}')
                print(f'  Amount: ${amount}')
                print(f'  Memo: {check.get("memo")}')
                print(f'  Bank: {check.get("bank_account_name")}')

                # Show all item lines
                print('  Item lines:')
                for line in check.get('item_lines', []):
                    print(f'    Item: [{line.get("item_name", "BLANK")}]')
                    print(f'    Desc: [{line.get("description", "BLANK")}]')
                    print(f'    Customer: [{line.get("customer_name", "BLANK")}]')
                    print(f'    Amount: ${line.get("amount", 0)}')

                # Show all expense lines
                print('  Expense lines:')
                for line in check.get('expense_lines', []):
                    print(f'    Account: [{line.get("account_name", "BLANK")}]')
                    print(f'    Customer: [{line.get("customer_name", "BLANK")}]')
                    print(f'    Amount: ${line.get("amount", 0)}')

                # Show raw check data keys
                print(f'  Available fields: {list(check.keys())}')