import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))

from qb.connector import QBConnector
qb = QBConnector()

# Search for checks on 9/10
from qb.quickbooks_standard.entities.checks.check_repository import CheckRepository
from datetime import datetime

check_repo = CheckRepository()

# Search for checks on 9/10/2025
search_date = datetime(2025, 9, 10)
checks = check_repo.search_checks(date_from=search_date, date_to=search_date)

print(f'Found {len(checks)} checks on 9/10/2025')

for check_summary in checks:
    check_id = check_summary.get('txn_id')
    if check_id:
        check = check_repo.get_check(check_id)
        if check:
            print(f'\nCheck {check_id}:')
            print(f'  Payee: {check.get("payee_name")}')
            print(f'  Amount: ${check.get("amount")}')

            # Check item lines
            item_lines = check.get('item_lines', [])
            if item_lines:
                print(f'  Item lines: {len(item_lines)}')
                for line in item_lines:
                    item_name = line.get('item_name', '')
                    customer = line.get('customer_name', '')
                    amount = line.get('amount', 0)
                    print(f'    Item: {item_name} | Customer: {customer} | Amount: ${amount}')
                    if 'material' in item_name.lower():
                        print(f'    ^^^ FOUND JOB MATERIALS!')

            # Check expense lines
            expense_lines = check.get('expense_lines', [])
            if expense_lines:
                print(f'  Expense lines: {len(expense_lines)}')
                for line in expense_lines:
                    account = line.get('account_name', '')
                    customer = line.get('customer_name', '')
                    amount = line.get('amount', 0)
                    print(f'    Account: {account} | Customer: {customer} | Amount: ${amount}')