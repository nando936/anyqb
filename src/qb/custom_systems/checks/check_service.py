"""
Check Service - Business logic for check operations
Handles check CRUD operations with formatting
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pytz
from quickbooks_standard.entities.checks.check_repository import CheckRepository
from quickbooks_standard.entities.vendors.vendor_repository import VendorRepository
from quickbooks_standard.entities.customers.customer_repository import CustomerRepository
from quickbooks_standard.entities.items.item_repository import ItemRepository
from quickbooks_standard.entities.payees.payee_repository import PayeeRepository
from quickbooks_standard.entities.accounts.account_repository import AccountRepository
from quickbooks_standard.entities.other_names.other_name_repository import OtherNameRepository
from shared_utilities.gas_station_consolidator import GasStationConsolidator

logger = logging.getLogger(__name__)

class CheckService:
    """Service for managing check operations with business logic"""
    
    def __init__(self):
        """Initialize check service"""
        self.check_repo = CheckRepository()
        self.vendor_repo = VendorRepository()
        self.customer_repo = CustomerRepository()
        self.item_repo = ItemRepository()
        self.payee_repo = PayeeRepository()
        self.account_repo = AccountRepository()
        self.other_name_repo = OtherNameRepository()
        self.gas_consolidator = GasStationConsolidator()
    
    def search_checks(self, search_params: Dict) -> str:
        """
        Search checks with formatted output
        """
        try:
            # Extract search parameters
            search_term = search_params.get('search_term')
            payee_name = search_params.get('payee_name')
            check_number = search_params.get('check_number')
            amount = search_params.get('amount')
            date_from = search_params.get('date_from')
            date_to = search_params.get('date_to')
            
            logger.info(f"CheckService.search_checks: amount={amount}, date_from={date_from}, date_to={date_to}")
            bank_account = search_params.get('bank_account')
            memo_contains = search_params.get('memo_contains')
            created_from = search_params.get('created_from')
            created_to = search_params.get('created_to')
            modified_from = search_params.get('modified_from')
            modified_to = search_params.get('modified_to')
            
            checks = []
            
            # If only amount is specified, we need to get all checks then filter
            if amount is not None and not any([search_term, payee_name, check_number, date_from, date_to, 
                                               bank_account, memo_contains, created_from, created_to, 
                                               modified_from, modified_to]):
                # Get recent checks without date filter to search by amount
                # We need to set a wide date range to avoid the default "today" filter
                from datetime import datetime, timedelta
                wide_date_from = datetime.now() - timedelta(days=365)
                wide_date_to = datetime.now() + timedelta(days=30)
                checks = self.check_repo.search_checks(
                    date_from=wide_date_from,
                    date_to=wide_date_to,
                    amount=amount,
                    max_returned=500
                )
            # If search_term is provided, use cached payees to find matches
            elif search_term and not payee_name:
                # First try to get cached payees
                cached_payees = self.payee_repo.get_cached_payees()
                
                if cached_payees:
                    # Find matching payees using fuzzy search
                    from shared_utilities.fuzzy_matcher import FuzzyMatcher
                    matcher = FuzzyMatcher()
                    matching_payees = []
                    
                    # Get all payee names for matching
                    payee_names = [p.get('name', '') for p in cached_payees if p.get('name')]
                    
                    # Find best match
                    match_result = matcher.find_best_match(search_term, payee_names, entity_type="generic")
                    
                    if match_result.found:
                        # Find the payee with the matched name
                        for payee in cached_payees:
                            if payee.get('name', '') == match_result.exact_name:
                                matching_payees.append(payee)
                                break
                    
                    # Get checks for top matching payees
                    for payee in matching_payees[:5]:  # Limit to 5 to avoid too many queries
                        try:
                            payee_checks = self.check_repo.find_checks_by_payee(payee['name'])
                            checks.extend(payee_checks)
                        except:
                            continue
                            
                    logger.info(f"Found {len(checks)} checks for {len(matching_payees[:5])} matching payees")
                else:
                    # No cache, use hardcoded fallback for known searches
                    if 'conroe' in search_term.lower():
                        known_conroe_payees = [
                            "Conroe Door & Hardware  Inc",
                            "CONROE DOOR & HAR 09/28 PURC",
                            "BRANNEN'S CONROE 06/28 PURCHASE"
                        ]
                        for payee in known_conroe_payees:
                            try:
                                payee_checks = self.check_repo.find_checks_by_payee(payee)
                                checks.extend(payee_checks)
                            except:
                                continue
            elif payee_name:
                # If payee_name specified, try exact match first
                checks = self.check_repo.find_checks_by_payee(payee_name)
            else:
                # Use search_all_checks for creation date searches to include bill payment checks
                # This ensures we get ALL checks from ALL bank accounts and transaction types
                if created_from or created_to or modified_from or modified_to:
                    checks = self.check_repo.search_all_checks(
                        date_from=date_from,
                        date_to=date_to,
                        bank_account=bank_account,
                        created_from=created_from or modified_from,
                        created_to=created_to or modified_to,
                        amount=amount
                    )
                else:
                    # Use regular search for other criteria
                    checks = self.check_repo.search_checks(
                        ref_number=check_number,
                        date_from=date_from,
                        date_to=date_to,
                        bank_account=bank_account,
                        memo_contains=memo_contains,
                        amount=amount
                    )
            
            # Apply additional filtering
            if (search_term or amount is not None) and checks:
                filtered = []
                for check in checks:
                    # Filter by search term if provided
                    if search_term:
                        search_lower = search_term.lower()
                        # Search across all fields
                        if not (search_lower in str(check.get('check_number', '')).lower() or
                                search_lower in str(check.get('payee', '')).lower() or
                                search_lower in str(check.get('memo', '')).lower() or
                                search_lower in str(check.get('bank_account', '')).lower() or
                                search_lower in str(check.get('amount', '')).lower()):
                            continue
                    
                    # Filter by amount if provided
                    if amount is not None:
                        check_amount = check.get('amount', 0.0)
                        # Compare with small tolerance for floating point
                        if abs(check_amount - amount) > 0.01:
                            continue
                    
                    filtered.append(check)
                checks = filtered
            
            if not checks:
                return "[OK] No checks found matching criteria"
            
            # Format output - 40 char width max
            output = []
            output.append("```")
            output.append("[OK] Checks Found - 40 CHAR WIDTH")
            output.append("=" * 40)
            
            total_amount = 0.0
            
            for check in checks:
                output.append("")
                # Check number header - use ref_number field from repository
                check_num = check.get('ref_number', check.get('check_number', 'N/A'))
                output.append(f"[Check #{check_num}]")
                output.append("-" * 40)
                
                # Transaction ID (truncate if needed)
                txn_id = check.get('txn_id', 'N/A')
                if len(txn_id) > 23:  # 40 - len("Transaction ID: ")
                    txn_id = txn_id[:20] + "..."
                output.append(f"Transaction ID: {txn_id}")
                
                # Format dates helper function
                def format_date_time(dt_value):
                    """Format datetime to MM-DD-YYYY HH:MM CT"""
                    if not dt_value or dt_value == 'N/A':
                        return 'N/A'
                    
                    try:
                        from datetime import datetime
                        import pytz
                        
                        # Parse if string
                        if isinstance(dt_value, str):
                            # Try parsing ISO format with timezone
                            if '+' in dt_value or 'Z' in dt_value:
                                dt = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                            else:
                                dt = datetime.fromisoformat(dt_value)
                        else:
                            dt = dt_value
                        
                        # Convert to Central Time
                        if dt.tzinfo is None:
                            # Assume UTC if no timezone
                            utc = pytz.UTC
                            dt = utc.localize(dt)
                        
                        central = pytz.timezone('America/Chicago')
                        dt_central = dt.astimezone(central)
                        
                        # Format as MM-DD-YYYY HH:MM CT
                        return dt_central.strftime('%m-%d-%Y %H:%M CT')
                    except:
                        # If can't parse, try to extract just date
                        try:
                            if ' ' in str(dt_value):
                                date_part = str(dt_value).split(' ')[0]
                                if '-' in date_part:
                                    parts = date_part.split('-')
                                    if len(parts) == 3:
                                        return f"{parts[1]}-{parts[2]}-{parts[0]}"
                            return str(dt_value)[:19]  # Truncate to reasonable length
                        except:
                            return str(dt_value)[:19]
                
                # Check Date (txn_date) - just date, no time
                check_date = check.get('txn_date', check.get('date', 'N/A'))
                if check_date and check_date != 'N/A':
                    try:
                        from datetime import datetime
                        if isinstance(check_date, str):
                            if '+' in check_date or 'Z' in check_date:
                                dt = datetime.fromisoformat(check_date.replace('Z', '+00:00'))
                            else:
                                dt = datetime.fromisoformat(check_date)
                        else:
                            dt = check_date
                        date_str = dt.strftime('%m-%d-%Y')
                    except:
                        date_str = str(check_date)[:10]
                else:
                    date_str = 'N/A'
                output.append(f"Check Date: {date_str}")
                
                # Check Number (if available and different from N/A)
                check_ref = check.get('ref_number', check.get('check_number', 'N/A'))
                if check_ref and check_ref != 'N/A':
                    output.append(f"Check Number: {check_ref}")
                
                # Created Date with time in Central
                created = format_date_time(check.get('time_created', 'N/A'))
                if len(created) > 31:  # 40 - len("Created: ")
                    created = created[:31]
                output.append(f"Created: {created}")
                
                # Modified Date with time in Central
                modified = format_date_time(check.get('time_modified', 'N/A'))
                if len(modified) > 30:  # 40 - len("Modified: ")
                    modified = modified[:30]
                output.append(f"Modified: {modified}")
                
                # Payee (truncate if needed) - use payee_name field from repository
                payee = str(check.get('payee_name', check.get('payee', 'N/A')))
                if len(payee) > 33:  # 40 - len("Payee: ")
                    payee = payee[:30] + "..."
                output.append(f"Payee: {payee}")
                
                # Amount (right-aligned)
                amt_str = f"${check.get('amount', 0.0):,.2f}"
                amt_line = f"Amount: {amt_str}"
                if len(amt_line) > 40:
                    amt_line = amt_line[:40]
                output.append(amt_line)
                
                # Bank Account (truncate if needed)
                bank = str(check.get('bank_account', 'N/A'))
                if len(bank) > 26:  # 40 - len("Bank Account: ")
                    bank = bank[:23] + "..."
                output.append(f"Bank Account: {bank}")
                
                # Memo (truncate if needed)
                memo = str(check.get('memo', 'None'))
                if len(memo) > 34:  # 40 - len("Memo: ")
                    memo = memo[:31] + "..."
                output.append(f"Memo: {memo}")
                
                # Only show printed status if True
                if check.get('is_printed'):
                    output.append("Printed: Yes")
                
                # Show expense line items with details
                expense_lines = check.get('expense_lines', [])
                if expense_lines:
                    output.append("")
                    output.append("EXPENSE LINES:")
                    for exp_line in expense_lines:
                        account = exp_line.get('expense_account', 'Unknown')
                        amount = exp_line.get('amount', 0.0)
                        # Truncate account to fit
                        if len(account) > 22:
                            account = account[:19] + "..."
                        amt_str = f"${amount:,.2f}"
                        # Format: "  Account: $amount"
                        line = f"  {account}: {amt_str}"
                        if len(line) > 40:
                            line = line[:40]
                        output.append(line)
                        # Show job if present
                        if exp_line.get('customer_job'):
                            job = exp_line['customer_job']
                            job_line = f"    Job: {job}"
                            if len(job_line) > 40:
                                job_line = job_line[:37] + "..."
                            output.append(job_line)
                
                # Show item line items with details
                item_lines = check.get('item_lines', [])
                if item_lines:
                    output.append("")
                    output.append("ITEM LINES:")
                    for item_line in item_lines:
                        item = item_line.get('item', 'Unknown')
                        qty = item_line.get('quantity', 0)
                        cost = item_line.get('cost', 0.0)
                        amount = item_line.get('amount', 0.0)
                        # Format: "  Item (qty): $amount"
                        if len(item) > 20:
                            item = item[:17] + "..."
                        amt_str = f"${amount:,.2f}"
                        line = f"  {item} ({qty}): {amt_str}"
                        if len(line) > 40:
                            line = line[:40]
                        output.append(line)
                        # Show job if present
                        if item_line.get('customer_job'):
                            job = item_line['customer_job']
                            job_line = f"    Job: {job}"
                            if len(job_line) > 40:
                                job_line = job_line[:37] + "..."
                            output.append(job_line)
                
                total_amount += check.get('amount', 0.0)
            
            output.append("")
            output.append("=" * 40)
            output.append(f"Total Checks: {len(checks)}")
            
            # Format total amount to fit
            total_str = f"${total_amount:,.2f}"
            total_line = f"Total Amount: {total_str}"
            if len(total_line) > 40:
                total_line = total_line[:40]
            output.append(total_line)
            output.append("```")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to search checks: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def create_check(self, check_data: Dict) -> str:
        """
        Create a new check with validation and formatting
        """
        try:
            # Validate ALL required fields
            missing_fields = []
            
            if not check_data.get('bank_account'):
                missing_fields.append("bank_account")
            
            if not check_data.get('payee'):
                missing_fields.append("payee")
            
            # Date is required but we'll default to today if not provided
            # Don't add to missing fields since we have a sensible default
            
            # IMPORTANT: Checks with check numbers require approval
            if check_data.get('check_number') and check_data['check_number'].lower() != 'debit' and not check_data.get('check_number_approved'):
                return (
                    "[APPROVAL REQUIRED] Physical check number specified.\n"
                    "Check numbers should only be used for actual printed checks.\n"
                    "Most payments are electronic debits and should not have check numbers.\n"
                    "\nTo proceed with check number, user must explicitly approve:\n"
                    "  - Add 'check_number_approved: true' to confirm physical check is needed\n"
                    "\nRecommended: Leave check_number blank for electronic payments (defaults to 'Debit')."
                )
            
            # IMPORTANT: "To be printed" checks require approval
            if check_data.get('to_be_printed') and not check_data.get('to_be_printed_approved'):
                return (
                    "[APPROVAL REQUIRED] 'To be printed' check requested.\n"
                    "Printed checks should only be used when physical checks are actually needed.\n"
                    "Most payments are electronic and should not be marked for printing.\n"
                    "\nTo proceed with printed check, user must explicitly approve:\n"
                    "  - Add 'to_be_printed_approved: true' to confirm printed check is needed\n"
                    "\nRecommended: Use electronic payments (default behavior)."
                )
            
            # IMPORTANT: Expense checks require approval first
            if check_data.get('expenses') and not check_data.get('expense_approved'):
                return (
                    "[APPROVAL REQUIRED] Expense line checks must be approved first.\n"
                    "Expense checks should only be used when no item exists for the purchase.\n"
                    "Consider using item lines instead (e.g., 'job materials' for purchases).\n"
                    "\nTo proceed with expense lines, user must explicitly approve:\n"
                    "  - Add 'expense_approved: true' to confirm expense lines are necessary\n"
                    "\nRecommended: Use item lines for better job costing and reporting."
                )
            
            # Check for expense lines
            if not check_data.get('expenses') and not check_data.get('items'):
                missing_fields.append("items (at least one line item required)")
            else:
                # Validate expense lines have required fields
                if check_data.get('expenses'):
                    for i, expense in enumerate(check_data['expenses']):
                        if not expense.get('account'):
                            missing_fields.append(f"expense[{i}].account")
                        if expense.get('amount') is None:
                            missing_fields.append(f"expense[{i}].amount")
                
                # Validate item lines have required fields
                if check_data.get('items'):
                    for i, item in enumerate(check_data['items']):
                        if not item.get('item'):
                            missing_fields.append(f"item[{i}].item")
                        # Cost and quantity have defaults, so not required
            
            if missing_fields:
                return f"[ERROR] Required fields missing:\n" + "\n".join([f"  * {field}" for field in missing_fields])
            
            # Fuzzy search for bank account if needed
            bank_account = check_data['bank_account']
            # Try to find exact match first, if not found, do fuzzy search
            accounts = self.account_repo.search_accounts(search_term=bank_account, account_type="Bank")
            if accounts and len(accounts) == 1:
                bank_account = accounts[0]['name']
            elif accounts and len(accounts) > 1:
                # Multiple matches - show options
                account_list = "\n".join([f"  * {acc['name']}" for acc in accounts[:5]])
                return f"[ERROR] Multiple bank accounts match '{bank_account}':\n{account_list}\nPlease be more specific."
            
            # Prepare check data
            formatted_data = {
                'bank_account': bank_account,
                'date': check_data.get('date', datetime.now()),
                'line_items': []
            }
            
            # Fuzzy search for payee if provided
            if check_data.get('payee'):
                payee_name = check_data['payee']
                
                # Check if this might be a gas station
                if self.gas_consolidator.is_gas_station(payee_name):
                    # Try to consolidate the gas station name
                    consolidated_name = self.gas_consolidator.consolidate(payee_name)
                    logger.info(f"Gas station detected: '{payee_name}' -> '{consolidated_name}'")
                    
                    # Search for the consolidated name first
                    payees = self.payee_repo.search_all_payees(consolidated_name, active_only=True)
                    
                    if not payees:
                        # If consolidated name not found, search original
                        payees = self.payee_repo.search_all_payees(payee_name, active_only=True)
                    
                    if not payees:
                        # Try inactive payees
                        payees = self.payee_repo.search_all_payees(payee_name, active_only=False)
                    
                    # Use gas station consolidator to find best match
                    if payees:
                        payee_names = [p['name'] for p in payees if p.get('name')]
                        best_match = self.gas_consolidator.find_best_gas_station_match(payee_name, payee_names)
                        if best_match:
                            formatted_data['payee'] = best_match
                            logger.info(f"Gas station matched: '{payee_name}' -> '{best_match}'")
                        else:
                            # Fall through to regular matching
                            pass
                else:
                    # Not a gas station, use regular search
                    payees = self.payee_repo.search_all_payees(payee_name, active_only=True)
                    
                    if not payees:
                        # Try partial match
                        payees = self.payee_repo.search_all_payees(payee_name, active_only=False)
                
                # Only do regular matching if payee not already set by gas consolidator
                if 'payee' not in formatted_data and payees:
                    if len(payees) == 1:
                        formatted_data['payee'] = payees[0]['name']
                    elif len(payees) > 1:
                        # Look for exact match first
                        exact_match = [p for p in payees if p['name'].lower() == payee_name.lower()]
                        if exact_match:
                            formatted_data['payee'] = exact_match[0]['name']
                        else:
                            # Use fuzzy matcher to find best match
                            from shared_utilities.fuzzy_matcher import FuzzyMatcher
                            matcher = FuzzyMatcher(min_confidence=0.5)  # Lower threshold for partial matches
                            payee_names = [p['name'] for p in payees if p.get('name')]
                            match_result = matcher.find_best_match(payee_name, payee_names, entity_type="generic")
                            
                            if match_result.found:
                                # Find the payee with the matched name
                                for payee in payees:
                                    if payee.get('name') == match_result.exact_name:
                                        formatted_data['payee'] = payee['name']
                                        logger.info(f"Fuzzy matched '{payee_name}' to '{payee['name']}' (confidence: {match_result.confidence:.1%})")
                                        break
                            else:
                                # If still no match, show options
                                payee_list = "\n".join([f"  * {p['name']} ({p['payee_type']})" for p in payees[:5]])
                                return f"[ERROR] Multiple payees match '{payee_name}':\n{payee_list}\nPlease be more specific."
                
                # Only set payee if not already set by gas consolidator
                if 'payee' not in formatted_data:
                    # Payee not found - check if we should auto-create Other Name
                    if check_data.get('auto_create_other_name', False):
                        logger.info(f"Auto-creating Other Name: {payee_name}")
                        other_name_result = self.other_name_repo.create_other_name(payee_name)
                        if other_name_result:
                            logger.info(f"Successfully created Other Name: {payee_name}")
                            formatted_data['payee'] = payee_name
                        else:
                            logger.warning(f"Failed to create Other Name: {payee_name}, using as-is")
                            formatted_data['payee'] = payee_name
                    else:
                        formatted_data['payee'] = payee_name  # Use as-is if not found
            
            if check_data.get('check_number'):
                formatted_data['check_number'] = check_data['check_number']
            
            if check_data.get('memo'):
                formatted_data['memo'] = check_data['memo']
            
            if check_data.get('address'):
                formatted_data['address'] = check_data['address']
            
            # Process line items
            if check_data.get('items'):
                for item_data in check_data['items']:
                    if not item_data.get('item'):
                        continue
                    
                    # Fuzzy search for item
                    item_name = item_data['item']
                    items = self.item_repo.search_items(search_term=item_name, active_only=True)
                    if not items:
                        # Try inactive items if not found
                        items = self.item_repo.search_items(search_term=item_name, active_only=False)
                    
                    if items and len(items) == 1:
                        item_name = items[0]['name']
                    elif items and len(items) > 1:
                        # Look for exact match first
                        exact_match = [i for i in items if i['name'].lower() == item_data['item'].lower()]
                        if exact_match:
                            item_name = exact_match[0]['name']
                        else:
                            # Use the first match
                            item_name = items[0]['name']
                    
                    line_item = {
                        'item': item_name,
                        'quantity': item_data.get('quantity', 1.0),
                        'cost': item_data.get('cost', 0.0)
                    }
                    
                    # Calculate amount
                    line_item['amount'] = line_item['quantity'] * line_item['cost']
                    
                    # Add customer/job (required for job costing)
                    if item_data.get('customer_job'):
                        line_item['customer_job'] = item_data['customer_job']
                    
                    # Add optional fields
                    if item_data.get('description'):
                        line_item['description'] = item_data['description']
                    
                    if item_data.get('class'):
                        line_item['class'] = item_data['class']
                    
                    # Non-billable by default unless specified
                    line_item['billable'] = item_data.get('billable', False)
                    
                    formatted_data['line_items'].append(line_item)
            
            # Process expense lines
            if check_data.get('expenses'):
                for expense_data in check_data['expenses']:
                    if not expense_data.get('account'):
                        continue
                    
                    # Fuzzy search for expense account
                    account_name = expense_data['account']
                    
                    # Special handling for "gas" - default to fuel:Gas Nando
                    if account_name.lower() == 'gas':
                        account_name = 'fuel:Gas Nando'
                        logger.info(f"Auto-selecting 'fuel:Gas Nando' for generic 'gas' input")
                    else:
                        # Normal fuzzy search for other accounts
                        accounts = self.account_repo.search_accounts(search_term=account_name, account_type="Expense")
                        if not accounts:
                            # Try all account types if not found in Expense
                            accounts = self.account_repo.search_accounts(search_term=account_name)
                        
                        if accounts and len(accounts) == 1:
                            # Use full_name for hierarchical accounts (e.g., "fuel:Gas Erick")
                            account_name = accounts[0].get('full_name') or accounts[0]['name']
                        elif accounts and len(accounts) > 1:
                            # Look for exact match first
                            exact_match = [a for a in accounts if (a.get('full_name', '').lower() == expense_data['account'].lower() or
                                                                    a.get('name', '').lower() == expense_data['account'].lower())]
                            if exact_match:
                                account_name = exact_match[0].get('full_name') or exact_match[0]['name']
                            else:
                                # For gas-related accounts, prefer fuel:Gas Nando
                                if 'gas' in account_name.lower():
                                    nando_gas = [a for a in accounts if a.get('full_name', '').lower() == 'fuel:gas nando']
                                    if nando_gas:
                                        account_name = nando_gas[0].get('full_name') or nando_gas[0]['name']
                                        logger.info(f"Auto-selected 'fuel:Gas Nando' from multiple gas matches")
                                    else:
                                        # Use the first match with full_name
                                        account_name = accounts[0].get('full_name') or accounts[0]['name']
                                else:
                                    # Use the first match with full_name
                                    account_name = accounts[0].get('full_name') or accounts[0]['name']
                    
                    expense_item = {
                        'expense_account': account_name,
                        'amount': expense_data.get('amount', 0.0)
                    }
                    
                    # Add customer/job for job costing
                    if expense_data.get('customer_job'):
                        expense_item['customer_job'] = expense_data['customer_job']
                    
                    if expense_data.get('memo'):
                        expense_item['memo'] = expense_data['memo']
                    
                    if expense_data.get('class'):
                        expense_item['class'] = expense_data['class']
                    
                    # Non-billable by default
                    expense_item['billable'] = expense_data.get('billable', False)
                    
                    formatted_data['line_items'].append(expense_item)
            
            # Create the check
            logger.info(f"Creating check with formatted_data: {formatted_data}")
            result = self.check_repo.create_check(formatted_data)
            
            if not result:
                return "[ERROR] Failed to create check in QuickBooks"
            
            # Format success response
            output = []
            output.append("[OK] Check Created Successfully")
            output.append("=" * 40)
            output.append(f"Check Number: {result.get('check_number', 'N/A')}")
            output.append(f"Date:         {result.get('date', 'N/A')}")
            output.append(f"Payee:        {result.get('payee', 'N/A')}")
            output.append(f"Amount:       ${result.get('amount', 0.0):,.2f}")
            output.append(f"Bank Account: {result.get('bank_account', 'N/A')}")
            output.append(f"TxnID:        {result.get('txn_id', 'N/A')}")
            
            if result.get('item_lines'):
                output.append("\nItem Lines Created:")
                for line in result['item_lines']:
                    output.append(f"  * {line.get('item')}: ${line.get('amount', 0.0):,.2f}")
                    if line.get('customer_job'):
                        output.append(f"    Job: {line['customer_job']}")
            
            if result.get('expense_lines'):
                output.append("\nExpense Lines Created:")
                for line in result['expense_lines']:
                    output.append(f"  * {line.get('expense_account')}: ${line.get('amount', 0.0):,.2f}")
                    if line.get('customer_job'):
                        output.append(f"    Job: {line['customer_job']}")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to create check: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def update_check(self, txn_id: str, updates: Dict) -> str:
        """
        Update an existing check
        """
        try:
            # Get existing check first
            existing = self.check_repo.get_check(txn_id)
            if not existing:
                return f"[ERROR] Check {txn_id} not found"
            
            # Update the check
            result = self.check_repo.update_check(txn_id, updates)
            
            if not result:
                return "[ERROR] Failed to update check in QuickBooks"
            
            # Get the full updated check details
            updated_check = self.check_repo.get_check(txn_id)
            if not updated_check:
                # Fall back to result if can't refetch
                updated_check = result
            
            # Format the full check details (same as get_check)
            output = []
            output.append("[OK] Check Updated Successfully")
            output.append("=" * 40)
            output.append(f"Check Number: {updated_check.get('ref_number', 'N/A')}")
            output.append(f"Date: {updated_check.get('txn_date', 'N/A')}")
            output.append(f"Payee: {updated_check.get('payee_name', 'N/A')}")
            output.append(f"Amount: ${updated_check.get('amount', 0.0):,.2f}")
            output.append(f"Bank Account: {updated_check.get('bank_account', 'N/A')}")
            
            if updated_check.get('memo'):
                output.append(f"Memo: {updated_check['memo']}")
            
            output.append(f"TxnID: {updated_check.get('txn_id', 'N/A')}")
            output.append(f"Edit Seq: {updated_check.get('edit_sequence', 'N/A')}")
            
            # Show expense lines if present
            if updated_check.get('expense_lines'):
                output.append("\n" + "-" * 40)
                output.append("EXPENSE LINE ITEMS:")
                output.append("-" * 40)
                for idx, line in enumerate(updated_check['expense_lines'], 1):
                    output.append(f"{idx}. {line.get('expense_account', 'Unknown Account')} ${line.get('amount', 0.0):,.2f}")
                    if line.get('memo'):
                        output.append(f"   Memo: {line['memo']}")
                    # Always show job status
                    job = line.get('customer_job')
                    output.append(f"   Job: {job if job else 'None'}")
            
            # Show item lines if present
            if updated_check.get('item_lines'):
                output.append("\n" + "-" * 40)
                output.append("ITEM LINE ITEMS:")
                output.append("-" * 40)
                for idx, line in enumerate(updated_check['item_lines'], 1):
                    qty = line.get('quantity', 0)
                    cost = line.get('cost', 0.0)
                    amount = line.get('amount', 0.0)
                    output.append(f"{idx}. {line.get('item', 'Unknown Item')} - Qty: {qty} × ${cost:,.2f} = ${amount:,.2f}")
                    if line.get('description'):
                        output.append(f"   Desc: {line['description']}")
                    # Always show job status
                    job = line.get('customer_job')
                    output.append(f"   Job: {job if job else 'None'}")
            
            output.append("\n" + "-" * 40)
            output.append("Updated Fields:")
            for field, value in updates.items():
                output.append(f"  * {field}: {value}")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to update check: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def delete_check(self, txn_id: str) -> str:
        """
        Delete a check
        """
        try:
            # Get check details first for confirmation
            check = self.check_repo.get_check(txn_id)
            if not check:
                return f"[ERROR] Check {txn_id} not found"
            
            # Try to delete the check
            try:
                success = self.check_repo.delete_check(txn_id)
                
                if not success:
                    return "[ERROR] Failed to delete check from QuickBooks (repository returned False)"
            except Exception as repo_error:
                # Repository raised an error with details
                error_msg = f"[ERROR] Failed to delete check\n"
                error_msg += f"  Operation: CheckService.delete_check\n"
                error_msg += f"  Transaction ID: {txn_id}\n"
                error_msg += f"  Details: {str(repo_error)}"
                logger.error(error_msg)
                return error_msg
            
            # Format success response
            output = []
            output.append("[OK] Check Deleted Successfully")
            output.append("=" * 40)
            output.append(f"Check Number: {check.get('check_number', 'N/A')}")
            output.append(f"Date:         {check.get('date', 'N/A')}")
            output.append(f"Payee:        {check.get('payee', 'N/A')}")
            output.append(f"Amount:       ${check.get('amount', 0.0):,.2f}")
            output.append(f"TxnID:        {txn_id}")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to delete check: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def get_check(self, txn_id: str) -> str:
        """
        Get a specific check by transaction ID
        """
        try:
            check = self.check_repo.get_check(txn_id)
            
            if not check:
                return f"[ERROR] Check {txn_id} not found"
            
            # Format output - 40 character width
            output = []
            output.append("[OK] Check Details")
            output.append("=" * 40)
            
            # Helper function to truncate strings to fit width
            def format_field(label: str, value: str, width: int = 40) -> str:
                # Calculate space for value after label
                label_str = f"{label}: "
                max_value_len = width - len(label_str)
                value_str = str(value)[:max_value_len] if value else 'N/A'
                return f"{label_str}{value_str}"
            
            output.append(format_field("Check Number", check.get('ref_number', check.get('check_number', 'N/A'))))
            output.append(format_field("Date", check.get('txn_date', check.get('date', 'N/A'))))
            output.append(format_field("Payee", check.get('payee_name', check.get('payee', 'N/A'))))
            output.append(format_field("Amount", f"${check.get('amount', 0.0):,.2f}"))
            output.append(format_field("Bank Account", check.get('bank_account', 'N/A')))
            output.append(format_field("Memo", check.get('memo', 'N/A')))
            output.append(format_field("TxnID", check.get('txn_id', 'N/A')))
            output.append(format_field("Edit Seq", check.get('edit_sequence', 'N/A')))
            
            # Show address if present (40 char width)
            if check.get('address'):
                output.append("\nAddress:")
                for line in check['address'].split('\n'):
                    output.append(f"  {line[:38]}")  # Truncate to fit
            
            # Show expense lines (40 char width)
            if check.get('expense_lines'):
                output.append("\n" + "-" * 40)
                output.append("EXPENSE LINE ITEMS:")
                output.append("-" * 40)
                for i, line in enumerate(check['expense_lines'], 1):
                    # Format account and amount on one line (40 chars)
                    account = line.get('expense_account', 'Unknown')
                    amount = line.get('amount', 0.0)
                    
                    # Truncate account name if needed to fit with amount
                    amt_str = f"${amount:,.2f}"
                    max_acct_len = 40 - len(amt_str) - len(f"{i}. ") - 1
                    acct_str = account[:max_acct_len] if len(account) > max_acct_len else account
                    
                    # Right-align amount
                    line_str = f"{i}. {acct_str}"
                    padding = 40 - len(line_str) - len(amt_str)
                    output.append(f"{line_str}{' ' * padding}{amt_str}")
                    
                    # Show job on next line if present
                    if line.get('customer_job'):
                        job = line['customer_job']
                        output.append(f"   Job: {job[:33]}")  # Indent and truncate
                    if line.get('memo'):
                        memo = line['memo']
                        output.append(f"   Memo: {memo[:32]}")
            
            # Show item lines (40 char width)
            if check.get('item_lines'):
                output.append("\n" + "-" * 40)
                output.append("ITEM LINE ITEMS:")
                output.append("-" * 40)
                for i, line in enumerate(check['item_lines'], 1):
                    item = line.get('item', 'Unknown')
                    qty = line.get('quantity', 0)
                    cost = line.get('cost', 0.0)
                    amount = line.get('amount', 0.0)
                    
                    # Format: "1. Item (Qty @ Cost)"
                    qty_cost_str = f"({qty:.1f}@${cost:.2f})"
                    amt_str = f"${amount:,.2f}"
                    
                    # Calculate max item name length
                    prefix = f"{i}. "
                    max_item_len = 40 - len(prefix) - len(qty_cost_str) - len(amt_str) - 2
                    item_str = item[:max_item_len] if len(item) > max_item_len else item
                    
                    # Build the line
                    left_part = f"{prefix}{item_str} {qty_cost_str}"
                    padding = 40 - len(left_part) - len(amt_str)
                    output.append(f"{left_part}{' ' * padding}{amt_str}")
                    
                    # Show description and job on next lines if present  
                    if line.get('description'):
                        desc = line['description']
                        output.append(f"   Desc: {desc[:32]}")
                    if line.get('customer_job'):
                        job = line['customer_job']
                        output.append(f"   Job: {job[:33]}")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to get check: {str(e)}"
            logger.error(error_msg)
            return error_msg