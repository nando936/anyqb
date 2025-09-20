#!/usr/bin/env python
"""
QuickBooks Direct Connector - No MCP Required
Provides direct access to QB functionality for Claude API integration
"""
import sys
import os
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Setup path for QB imports
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class QBConnector:
    """Direct QuickBooks connector without MCP server"""
    
    def __init__(self):
        """Initialize direct access to QB functionality"""
        try:
            # Import all the actual implementations
            from quickbooks_standard.entities.vendors.vendor_repository import VendorRepository
            from quickbooks_standard.entities.bills.bill_repository import BillRepository
            from quickbooks_standard.entities.customers.customer_repository import CustomerRepository
            from quickbooks_standard.entities.items.item_repository import ItemRepository
            from quickbooks_standard.entities.payees.payee_repository import PayeeRepository
            from quickbooks_standard.entities.other_names.other_name_repository import OtherNameRepository
            from quickbooks_standard.entities.accounts.account_repository import AccountRepository
            from quickbooks_standard.entities.checks.check_repository import CheckRepository
            from quickbooks_standard.entities.invoices.invoice_repository import InvoiceRepository
            from quickbooks_standard.entities.deposits.deposit_repository import DepositRepository
            from quickbooks_standard.entities.payments.payment_repository import PaymentRepository
            from quickbooks_standard.entities.receive_payments.receive_payment_repository import ReceivePaymentRepository
            from quickbooks_standard.reports.job_profitability_report import JobProfitabilityReportRepository
            from quickbooks_standard.entities.purchase_orders.purchase_order_repository import PurchaseOrderRepository
            from quickbooks_standard.entities.item_receipts.item_receipt_repository import ItemReceiptRepository
            from quickbooks_standard.reports.transaction_search import TransactionSearch
            from custom_systems.work_bills.work_bill_service import WorkBillService
            from shared_utilities.vendor_aliases import resolve_vendor_alias
            
            # Initialize repositories
            self.vendor_repo = VendorRepository()
            self.bill_repo = BillRepository()
            self.customer_repo = CustomerRepository()
            self.item_repo = ItemRepository()
            self.account_repo = AccountRepository()
            self.payee_repo = PayeeRepository()
            self.other_name_repo = OtherNameRepository()
            self.check_repo = CheckRepository()
            self.invoice_repo = InvoiceRepository()
            self.deposit_repo = DepositRepository()
            self.payment_repo = PaymentRepository()
            self.receive_payment_repo = ReceivePaymentRepository()
            self.job_profit_repo = JobProfitabilityReportRepository()
            self.po_repo = PurchaseOrderRepository()
            self.item_receipt_repo = ItemReceiptRepository()
            self.transaction_search = TransactionSearch()
            self.work_bill_service = WorkBillService()
            self.resolve_vendor = resolve_vendor_alias
            
            self.connected = True
            logger.info("[OK] QB Connector initialized successfully")
        except Exception as e:
            self.connected = False
            logger.error(f"[ERROR] Failed to initialize QB: {e}")
    
    def execute_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a QB command and return results"""
        if not self.connected:
            return {
                "success": False,
                "error": "QB not connected",
                "output": "[ERROR] QuickBooks connection not available"
            }
        
        params = params or {}
        
        try:
            # Map commands to methods
            command_map = {
                # Work Bill Commands
                "GET_WORK_BILL": self.get_work_bill,
                "CREATE_WORK_BILL": self.create_work_bill,
                "UPDATE_WORK_BILL": self.update_work_bill,
                "DELETE_BILL": self.delete_bill,
                "GET_WORK_WEEK_SUMMARY": self.get_work_week_summary,
                
                # Vendor Commands
                "SEARCH_VENDORS": self.search_vendors,
                "CREATE_VENDOR": self.create_vendor,
                "UPDATE_VENDOR": self.update_vendor,
                "SET_VENDOR_DAILY_COST": self.set_vendor_daily_cost,

                # Payee and Other Name Commands
                "SEARCH_PAYEES": self.search_payees,
                "CREATE_OTHER_NAME": self.create_other_name,
                "SEARCH_OTHER_NAMES": self.search_other_names,
                
                # Customer Commands
                "SEARCH_CUSTOMERS": self.search_customers,
                "CREATE_CUSTOMER": self.create_customer,
                "UPDATE_CUSTOMER": self.update_customer,
                
                # Check Commands
                "CREATE_CHECK": self.create_check,
                "SEARCH_CHECKS": self.search_checks,
                "UPDATE_CHECK": self.update_check,
                "DELETE_CHECK": self.delete_check,
                "GET_CHECK": self.get_check,
                "GET_CHECKS_THIS_WEEK": self.get_checks_this_week,
                
                # Invoice Commands
                "SEARCH_INVOICES": self.search_invoices,
                "GET_INVOICES_THIS_WEEK": self.get_invoices_this_week,
                "GET_INVOICE": self.get_invoice,
                "CREATE_INVOICE": self.create_invoice,
                
                # Bill Payment Commands
                "PAY_BILLS": self.pay_bills,
                "CREATE_BILL_PAYMENT": self.create_bill_payment,
                "SEARCH_BILL_PAYMENTS": self.search_bill_payments,
                "DELETE_BILL_PAYMENT": self.delete_bill_payment,
                "UPDATE_BILL_PAYMENT": self.update_bill_payment,
                
                # Item Commands
                "SEARCH_ITEMS": self.search_items,
                "CREATE_ITEM": self.create_item,
                "UPDATE_ITEM": self.update_item,
                
                # Account Commands
                "SEARCH_ACCOUNTS": self.search_accounts,
                "CREATE_ACCOUNT": self.create_account,
                "UPDATE_ACCOUNT": self.update_account,
                
                # Deposit Commands
                "SEARCH_DEPOSITS": self.search_deposits,
                "DEPOSIT_CUSTOMER_PAYMENT": self.deposit_customer_payment,

                # Customer Payment Commands
                "RECEIVE_PAYMENT": self.receive_payment,
                "DELETE_CUSTOMER_PAYMENT": self.delete_customer_payment,
                "SEARCH_CUSTOMER_PAYMENTS": self.search_customer_payments,
                
                # Report Commands
                "GET_JOB_PROFIT": self.get_job_profit,

                # Purchase Order Commands
                "GET_PURCHASE_ORDERS": self.get_purchase_orders,
                "CREATE_PURCHASE_ORDER": self.create_purchase_order,
                "DELETE_PURCHASE_ORDER": self.delete_purchase_order,
                "RECEIVE_PURCHASE_ORDER": self.receive_purchase_order,

                # Item Receipt Commands
                "GET_ITEM_RECEIPTS": self.get_item_receipts,
                "SEARCH_ITEM_RECEIPTS": self.search_item_receipts,

                # Transaction Search Commands
                "SEARCH_TRANSACTION_BY_AMOUNT": self.search_transaction_by_amount,
            }
            
            if command not in command_map:
                return {
                    "success": False,
                    "error": f"Unknown command: {command}",
                    "output": f"[ERROR] Command '{command}' not recognized"
                }
            
            # Execute the command
            result = command_map[command](**params)

            # Add AGGRESSIVE reminders for Claude to display output
            if result and not result.startswith("[ERROR]"):
                result = ("=== ACTUAL QB COMMAND OUTPUT - MUST DISPLAY IMMEDIATELY ===\n" +
                         result +
                         "\n\n[CLAUDE: Display this output in chat]" +
                         "\n[CRITICAL: COPY AND PASTE THE ABOVE OUTPUT INTO YOUR RESPONSE NOW]" +
                         "\n[DO NOT SUMMARIZE - SHOW THE ACTUAL OUTPUT]" +
                         "\n[FAILURE TO DISPLAY = CRITICAL ERROR]")

            return {
                "success": True,
                "output": result,
                "command": command,
                "params": params
            }
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": f"[ERROR] {str(e)}"
            }
    
    # Work Bill Methods
    def get_work_bill(self, vendor_name: str, week: str = None) -> str:
        """Get vendor's work bill - searches by date range then filters by vendor"""
        vendor_name = self.resolve_vendor(vendor_name)

        # Just use the work_bill_service which already handles everything correctly
        # The only change is it now searches by date range internally
        result = self.work_bill_service.get_work_bill(vendor_name, week=week)

        if result['success']:
            return result.get('bill', 'No bill data')
        else:
            return f"[ERROR] {result.get('error', 'Failed to get bill')}"
    
    def create_work_bill(self, vendor_name: str, **kwargs) -> str:
        """Create new work bill - properly aliases to update_work_bill"""
        vendor_name = self.resolve_vendor(vendor_name)

        # CREATE_WORK_BILL should be an alias for UPDATE_WORK_BILL
        # The WorkBillService.update_work_bill auto-creates if no bill exists
        return self.update_work_bill(vendor_name, **kwargs)
    
    def update_work_bill(self, vendor_name: str, **kwargs) -> str:
        """Update existing work bill"""
        print(f"[DEBUG] update_work_bill called with vendor_name={vendor_name}, kwargs={kwargs}")
        vendor_name = self.resolve_vendor(vendor_name)
        
        # Build week_data dict for WorkBillService.update_work_bill
        week_data = {}
        
        # If txn_id is provided, pass it through for direct access
        if 'txn_id' in kwargs:
            week_data['txn_id'] = kwargs['txn_id']

        # Handle job updates (updating existing line items to different jobs)
        if 'update_jobs' in kwargs:
            week_data['update_jobs'] = kwargs['update_jobs']

        # Handle advanced day operations (lists)
        if 'add_days' in kwargs:
            # Convert simple day names to proper format if needed
            add_days = kwargs['add_days']
            if add_days and isinstance(add_days[0], str):
                # Simple format: ["thursday"] -> [{"day": "thursday", "qty": 1.0, "item": "Labor", "job": "..."}]
                formatted_days = []
                for day in add_days:
                    # Check for day-specific parameters first
                    day_desc = kwargs.get(f'{day}_desc')
                    day_job = kwargs.get(f'{day}_job')
                    day_item = kwargs.get(f'{day}_item')
                    day_qty = kwargs.get(f'{day}_qty', 1.0)

                    # If no day-specific job, check for generic job/customer param
                    if not day_job:
                        day_job = kwargs.get('job') or kwargs.get('customer')

                    # NO DEFAULTS POLICY - item must be explicitly specified
                    if not day_item and not kwargs.get('item'):
                        return "[ERROR] NO DEFAULTS: Item must be specified for each day. Use {day}_item='itemname' or item='itemname'"

                    formatted_day = {
                        "day": day,
                        "qty": day_qty,
                        "item": day_item or kwargs.get('item')
                    }

                    # Only add job if specified
                    if day_job:
                        formatted_day["job"] = day_job

                    # Only add description if provided
                    if day_desc:
                        formatted_day["desc"] = day_desc

                    formatted_days.append(formatted_day)
                week_data['add_days'] = formatted_days
            else:
                week_data['add_days'] = add_days
            
        if 'remove_days' in kwargs:
            week_data['remove_days'] = kwargs['remove_days']

        # Support removing specific line items by TxnLineID
        if 'remove_line_id' in kwargs:
            week_data['remove_days'] = [{'txn_line_id': kwargs['remove_line_id']}]
            
        if 'update_days' in kwargs:
            week_data['update_days'] = kwargs['update_days']
            
        # Add other parameters
        if 'ref_number' in kwargs:
            week_data['ref_number'] = kwargs['ref_number']
        if 'memo' in kwargs:
            week_data['memo'] = kwargs['memo']
            
        # Handle daily cost override
        if 'daily_cost' in kwargs:
            week_data['default_cost'] = kwargs['daily_cost']
            
        # Handle individual day quantities (the _days format)
        # These are QUANTITIES in days, not hours!
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
            day_key = f"{day}_days"
            if day_key in kwargs:
                week_data[day_key] = kwargs[day_key]
            # Also check if day data is passed directly
            elif day in kwargs:
                # If it's a dict with day info, add to add_days
                if isinstance(kwargs[day], dict):
                    if 'add_days' not in week_data:
                        week_data['add_days'] = []
                    day_info = kwargs[day].copy()
                    day_info['day'] = day
                    week_data['add_days'].append(day_info)
                else:
                    # If it's a number, treat as quantity
                    week_data[f"{day}_days"] = kwargs[day]
        
        print(f"[DEBUG] Calling work_bill_service.update_work_bill with vendor_name={vendor_name}, week_data={week_data}")
        result = self.work_bill_service.update_work_bill(vendor_name, week_data)

        if result['success']:
            bill_output = result.get('bill', '')
            return f"=== ACTUAL QB COMMAND OUTPUT - MUST DISPLAY IMMEDIATELY ===\n[OK] Bill updated\n{bill_output}\n\n[CLAUDE: Display this output in chat]\n[CRITICAL: COPY AND PASTE THE ABOVE OUTPUT INTO YOUR RESPONSE NOW]\n[DO NOT SUMMARIZE - SHOW THE ACTUAL OUTPUT]\n[FAILURE TO DISPLAY = CRITICAL ERROR]"
        else:
            return f"[ERROR] {result.get('error', 'Failed to update bill')}"
    
    def delete_bill(self, bill_id: str) -> str:
        """Delete a bill"""
        try:
            result = self.bill_repo.delete_bill(bill_id)
            return "[OK] Bill deleted" if result else "[ERROR] Failed to delete bill"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def get_work_week_summary(self, week: str = None) -> str:
        """Get enhanced work week summary with vendor, item, and job breakdowns"""
        try:
            from datetime import datetime, timedelta
            from shared_utilities.work_week_summary_formatter import WorkWeekSummaryFormatter

            # Parse week parameter (current, last, next, or numeric)
            if week:
                week_lower = str(week).lower()
                if week_lower == 'last':
                    week_offset = -1
                elif week_lower == 'next':
                    week_offset = 1
                elif week_lower == 'current':
                    week_offset = 0
                else:
                    try:
                        week_offset = int(week)
                    except:
                        week_offset = 0
            else:
                week_offset = 0

            # Calculate week dates
            today = datetime.now()
            days_since_monday = today.weekday()
            monday = today - timedelta(days=days_since_monday)
            monday = monday + timedelta(weeks=week_offset)
            saturday = monday + timedelta(days=5)

            week_str = f"{monday.strftime('%m/%d/%y')} - {saturday.strftime('%m/%d/%y')}"

            # Query bills by date range (much faster than querying all vendors)
            start_date = monday.strftime('%Y-%m-%d')
            end_date = saturday.strftime('%Y-%m-%d')

            # Get all bills for the week
            bills = self.bill_repo.find_bills_by_date_range(start_date, end_date, include_line_items=True)

            # Process bills to collect data
            vendor_data = {}  # vendor -> {total: 0, items: {item -> amount}}
            item_data = {}    # item -> {total: 0, jobs: {job -> amount}}
            job_totals = {}   # job -> total amount
            grand_total = 0.0

            # Handle case where bills is None or empty
            if not bills:
                bills = []

            for bill in bills:
                # Skip None bills
                if bill is None:
                    continue

                # Skip if bill is not a dictionary
                if not isinstance(bill, dict):
                    continue

                vendor_name = bill.get('vendor_name', 'Unknown')
                bill_amount = bill.get('amount_due', 0.0)

                if vendor_name not in vendor_data:
                    vendor_data[vendor_name] = {'total': 0, 'items': {}}

                vendor_data[vendor_name]['total'] += bill_amount
                grand_total += bill_amount

                # Process line items
                line_items = bill.get('line_items', [])
                if line_items is None:
                    line_items = []

                for line in line_items:
                    if line is None or not isinstance(line, dict):
                        continue
                    item_name = line.get('item_name', 'Unknown Item')
                    job_name = line.get('customer_name', '(No job assigned)')
                    amount = line.get('amount', 0.0)

                    # Vendor item breakdown
                    if item_name not in vendor_data[vendor_name]['items']:
                        vendor_data[vendor_name]['items'][item_name] = 0
                    vendor_data[vendor_name]['items'][item_name] += amount

                    # Item breakdown by job
                    if item_name not in item_data:
                        item_data[item_name] = {'total': 0, 'jobs': {}}
                    item_data[item_name]['total'] += amount
                    if job_name not in item_data[item_name]['jobs']:
                        item_data[item_name]['jobs'][job_name] = 0
                    item_data[item_name]['jobs'][job_name] += amount

                    # Job totals
                    if job_name not in job_totals:
                        job_totals[job_name] = 0
                    job_totals[job_name] += amount

            # Prepare data for formatter
            summary_data = {
                'week_str': week_str,
                'vendor_data': vendor_data,
                'item_data': item_data,
                'job_totals': job_totals,
                'grand_total': grand_total
            }

            # Use formatter to format the output
            formatter = WorkWeekSummaryFormatter()
            return formatter.format_summary(summary_data)

        except Exception as e:
            import traceback
            logger.error(f"Work week summary error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"[ERROR] Failed to get work week summary: {str(e)}"
    
    # Vendor Methods
    def search_vendors(self, search_term: str = None, active_only: bool = True) -> str:
        """Search for vendors"""
        # If search_term provided, try fuzzy matching first
        if search_term:
            # Resolve alias first
            resolved_term = self.resolve_vendor(search_term)
            
            # Try fuzzy match to find exact vendor
            vendor = self.vendor_repo.find_vendor_fuzzy(resolved_term)
            if vendor:
                # Found specific vendor via fuzzy match
                vendors = [vendor]
            else:
                # Fallback to regular search
                vendors = self.vendor_repo.search_vendors(resolved_term, active_only)
        else:
            vendors = self.vendor_repo.search_vendors(search_term, active_only)
        
        if not vendors:
            return f"[NOT FOUND] No vendors matching '{search_term}'"
        
        result = f"[OK] Found {len(vendors)} vendors\n\n"
        for vendor in vendors:
            result += f"- {vendor.get('name')}"
            daily_cost = self.vendor_repo.get_vendor_daily_cost(vendor.get('name'))
            if daily_cost:
                result += f" (${daily_cost}/day)"
            result += "\n"
        
        return result
    
    def create_vendor(self, name: str, **kwargs) -> str:
        """Create new vendor"""
        try:
            vendor_id = self.vendor_repo.create_vendor(name, **kwargs)
            return f"[OK] Vendor created: {name} (ID: {vendor_id})"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def update_vendor(self, vendor_id: str, **kwargs) -> str:
        """Update vendor information"""
        try:
            result = self.vendor_repo.update_vendor(vendor_id, **kwargs)
            return "[OK] Vendor updated" if result else "[ERROR] Failed to update vendor"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def set_vendor_daily_cost(self, vendor_name: str, daily_cost: float) -> str:
        """Set vendor's daily cost"""
        try:
            vendor_name = self.resolve_vendor(vendor_name)
            result = self.vendor_repo.set_vendor_daily_cost(vendor_name, daily_cost)
            if result:
                return f"[OK] Daily cost for {vendor_name} set to ${daily_cost:.2f}/day"
            else:
                return f"[ERROR] Failed to update daily cost for {vendor_name}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    # Payee and Other Name Methods
    def search_payees(self, search_term: str = None, active_only: bool = True) -> str:
        """Search for payees across all entity types (vendors, customers, employees, other names)"""
        try:
            payees = self.payee_repo.search_all_payees(search_term, active_only)

            if not payees:
                return f"[NOT FOUND] No payees matching '{search_term}'"

            result = f"[OK] Found {len(payees)} payees\n\n"

            # Group by type
            by_type = {}
            for payee in payees:
                ptype = payee.get('payee_type', 'Unknown')
                if ptype not in by_type:
                    by_type[ptype] = []
                by_type[ptype].append(payee)

            # Display grouped results
            for ptype, items in by_type.items():
                result += f"{ptype.upper()}S:\n"
                for item in items:
                    result += f"  - {item.get('name')}\n"
                result += "\n"

            return result
        except Exception as e:
            return f"[ERROR] Failed to search payees: {str(e)}"

    def create_other_name(self, name: str, company_name: str = None) -> str:
        """Create a new Other Name entity in QuickBooks"""
        try:
            result = self.other_name_repo.create_other_name(name, company_name)

            if result:
                return f"[OK] Other Name created: {name} (ID: {result.get('list_id', 'N/A')})"
            else:
                return f"[ERROR] Failed to create Other Name: {name}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def search_other_names(self, search_term: str = None, active_only: bool = True) -> str:
        """Search for Other Names specifically"""
        try:
            other_names = self.other_name_repo.search_other_names(search_term, active_only)

            if not other_names:
                return f"[NOT FOUND] No Other Names matching '{search_term}'"

            result = f"[OK] Found {len(other_names)} Other Names\n\n"
            for other in other_names:
                result += f"- {other.get('name')}"
                if other.get('company_name'):
                    result += f" ({other.get('company_name')})"
                result += "\n"

            return result
        except Exception as e:
            return f"[ERROR] Failed to search Other Names: {str(e)}"

    # Customer Methods
    def search_customers(self, search_term: str = None, active_only: bool = True,
                        jobs_only: bool = False) -> str:
        """Search for customers"""
        # Use get_all_customers since search_customers doesn't exist
        customers = self.customer_repo.get_all_customers(include_jobs=not jobs_only)
        
        # Filter by search term if provided
        if search_term and customers:
            search_lower = str(search_term).lower()  # Convert to string first
            customers = [c for c in customers
                        if search_lower in c.get('name', '').lower()]
        
        if not customers:
            return f"[NOT FOUND] No customers matching '{search_term}'"
        
        result = f"[OK] Found {len(customers)} customers/jobs\n\n"
        
        # Separate customers and jobs
        top_level = [c for c in customers if ':' not in c.get('name', '')]
        jobs = [c for c in customers if ':' in c.get('name', '')]
        
        if top_level:
            result += "CUSTOMERS:\n"
            for customer in top_level:
                result += f"  {customer.get('name')}\n"
        
        if jobs:
            result += "\nJOBS:\n"
            for job in jobs:
                result += f"  {job.get('name')}\n"
        
        return result
    
    def update_customer(self, name: str, **kwargs) -> str:
        """Update customer to make it a job or change other properties"""
        try:
            # Get customer details first
            customer = self.customer_repo.get_customer_details(name)
            if not customer:
                return f"[ERROR] Customer '{name}' not found"

            # Build updates dictionary
            updates = {}
            if 'parent_name' in kwargs or 'parent' in kwargs:
                updates['parent_ref'] = kwargs.get('parent_name') or kwargs.get('parent')

            if 'is_active' in kwargs:
                updates['is_active'] = kwargs['is_active']

            if not updates:
                return "[ERROR] No updates specified"

            # Update the customer
            result = self.customer_repo.update_customer(
                customer['list_id'],
                customer['edit_sequence'],
                updates
            )

            if result.get('success'):
                if 'parent_ref' in updates:
                    return f"[OK] Converted '{name}' to job under '{updates['parent_ref']}'"
                else:
                    return f"[OK] Updated customer '{name}'"
            else:
                return f"[ERROR] {result.get('error', 'Failed to update customer')}"

        except Exception as e:
            return f"[ERROR] {str(e)}"

    def create_customer(self, name: str, **kwargs) -> str:
        """Create new customer"""
        try:
            # Prepare customer data dictionary
            customer_data = {
                'name': name,
                'company_name': kwargs.get('company_name'),
                'phone': kwargs.get('phone'),
                'email': kwargs.get('email'),
                'address': kwargs.get('address'),
                'parent_customer': kwargs.get('parent_customer')
            }
            # Remove None values
            customer_data = {k: v for k, v in customer_data.items() if v is not None}

            # Create customer using create_customer method
            result = self.customer_repo.create_customer(customer_data)

            if result.get('success'):
                customer_id = result.get('list_id', 'N/A')
                return f"[OK] Customer created: {name} (ID: {customer_id})"
            else:
                return f"[ERROR] {result.get('error', 'Failed to create customer')}"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    # Check Methods
    def create_check(self, **kwargs) -> str:
        """Create a check - properly builds dictionary for repository with fuzzy matching"""
        try:
            # Build check_data dictionary from kwargs
            check_data = {}

            # Handle payee with fuzzy matching
            if 'payee' in kwargs:
                payee_name = kwargs['payee']
                # Try to find vendor using fuzzy matching
                vendor = self.vendor_repo.find_vendor_fuzzy(payee_name)
                if vendor:
                    check_data['payee'] = vendor['name']
                    logger.info(f"Vendor fuzzy match: Found '{vendor['name']}' for '{payee_name}'")
                else:
                    # If not a vendor, could be customer or other name
                    # For now, use as-is
                    check_data['payee'] = payee_name
                    logger.info(f"No vendor match for '{payee_name}', using as-is")

            # Handle bank account with fuzzy matching
            if 'bank_account' not in kwargs:
                return "[ERROR] bank_account is required for check creation"

            bank_account = kwargs['bank_account']
            # Try to find account using fuzzy matching (similar to vendor)
            all_accounts = self.account_repo.search_accounts()
            if all_accounts:
                # Filter accounts with valid names and convert to strings
                account_names = []
                for a in all_accounts:
                    name = a.get('name')
                    if name is not None:
                        # Convert to string if it's not already (in case it's an int)
                        account_names.append(str(name))

                if account_names:
                    from shared_utilities.fuzzy_matcher import FuzzyMatcher
                    matcher = FuzzyMatcher()
                    # Convert bank_account to string as well
                    match_result = matcher.find_best_match(str(bank_account), account_names, entity_type="account")
                    if match_result.found:
                        check_data['bank_account'] = match_result.exact_name
                        logger.info(f"Account fuzzy match: Found '{match_result.exact_name}' for '{bank_account}'")
                    else:
                        check_data['bank_account'] = str(bank_account)
                        logger.info(f"No account match for '{bank_account}', using as-is")
                else:
                    check_data['bank_account'] = str(bank_account)
            else:
                check_data['bank_account'] = str(bank_account)

            # Optional fields
            if 'date' in kwargs:
                check_data['date'] = kwargs['date']

            if 'check_number' in kwargs:
                check_data['check_number'] = kwargs['check_number']

            if 'memo' in kwargs:
                check_data['memo'] = kwargs['memo']

            if 'to_be_printed' in kwargs:
                check_data['to_be_printed'] = kwargs['to_be_printed']

            # Handle line items - support both single item and multiple items
            line_items = []

            # Single item shorthand
            if 'item' in kwargs and 'amount' in kwargs:
                # Use fuzzy matching for item
                item_name = kwargs['item']
                item = self.item_repo.find_item_fuzzy(item_name)
                if item:
                    actual_item_name = item['name']
                    logger.info(f"Item fuzzy match: Found '{actual_item_name}' for '{item_name}'")
                else:
                    actual_item_name = item_name
                    logger.info(f"No item match for '{item_name}', using as-is")

                line_item = {
                    'item': actual_item_name,
                    'amount': kwargs['amount'],
                    'billable': False  # Default to non-billable for checks
                }

                # Add optional item fields
                if 'description' in kwargs:
                    line_item['description'] = kwargs['description']

                # Handle job/customer with proper resolution (like work_bill_service does)
                if 'job' in kwargs or 'customer_job' in kwargs:
                    job_name = kwargs.get('job') or kwargs.get('customer_job')
                    # Use customer_repo.resolve_customer_or_job like work_bill_service does
                    resolved = self.customer_repo.resolve_customer_or_job(job_name)
                    if resolved:
                        line_item['customer_job'] = resolved
                        logger.info(f"Customer/job resolved: '{job_name}' -> '{resolved}'")
                    else:
                        line_item['customer_job'] = job_name
                        logger.warning(f"No customer/job match for '{job_name}', using as-is")

                if 'quantity' in kwargs:
                    line_item['quantity'] = kwargs['quantity']
                if 'cost' in kwargs:
                    line_item['cost'] = kwargs['cost']

                line_items.append(line_item)

            # Multiple items
            elif 'line_items' in kwargs:
                line_items = kwargs['line_items']

            # Expense lines (backward compatibility)
            elif 'expense_account' in kwargs and 'amount' in kwargs:
                line_item = {
                    'expense_account': kwargs['expense_account'],
                    'amount': kwargs['amount']
                }
                if 'expense_memo' in kwargs:
                    line_item['memo'] = kwargs['expense_memo']
                if 'job' in kwargs or 'customer_job' in kwargs:
                    line_item['customer_job'] = kwargs.get('job') or kwargs.get('customer_job')

                line_items.append(line_item)

            # Add line items to check data if any exist
            if line_items:
                check_data['line_items'] = line_items

            # Create the check with the properly structured dictionary
            result = self.check_repo.create_check(check_data)

            if result:
                payee_name = kwargs.get('payee', 'Unknown')
                amount = kwargs.get('amount', 0)
                return f"[OK] Check created for {payee_name}: ${amount:.2f} (ID: {result.get('txn_id', 'Unknown')})"
            else:
                return "[ERROR] Failed to create check in QuickBooks"

        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def search_checks(self, **kwargs) -> str:
        """Search for checks"""
        checks = self.check_repo.search_checks(**kwargs)

        if not checks:
            return "[NOT FOUND] No checks matching criteria"

        result = f"[OK] Found {len(checks)} checks\n\n"

        for check in checks[:10]:  # Limit to 10
            result += f"Check #{check.get('ref_number', 'N/A')}\n"
            result += f"  Date: {check.get('txn_date', 'N/A')}\n"
            result += f"  Payee: {check.get('payee_name', 'N/A')}\n"
            result += f"  Amount: ${check.get('amount', 0):.2f}\n"
            result += f"  Bank Account: {check.get('bank_account', 'N/A')}\n"

            if check.get('memo'):
                result += f"  Memo: {check.get('memo')}\n"

            # Display item lines if present
            item_lines = check.get('item_lines', [])
            if item_lines:
                result += "  Items:\n"
                for item in item_lines:
                    result += f"    - {item.get('item', 'N/A')}: ${item.get('amount', 0):.2f}\n"
                    if item.get('customer_job'):
                        result += f"      Job: {item.get('customer_job')}\n"
                    if item.get('description'):
                        result += f"      Description: {item.get('description')}\n"

            # Display expense lines if present
            expense_lines = check.get('expense_lines', [])
            if expense_lines:
                result += "  Expenses:\n"
                for expense in expense_lines:
                    result += f"    - {expense.get('account', 'N/A')}: ${expense.get('amount', 0):.2f}\n"
                    if expense.get('customer_job'):
                        result += f"      Job: {expense.get('customer_job')}\n"
                    if expense.get('memo'):
                        result += f"      Memo: {expense.get('memo')}\n"

            result += "\n"

        return result
    
    def update_check(self, check_id: str, **kwargs) -> str:
        """Update check information"""
        try:
            # Build updates dictionary from kwargs
            updates = {}

            # Map common field names to QB field names
            field_mapping = {
                'payee': 'payee',
                'amount': 'amount',
                'memo': 'memo',
                'check_number': 'check_number',
                'date': 'date',
                'bank_account': 'bank_account'
            }

            for key, value in kwargs.items():
                if key in field_mapping:
                    updates[field_mapping[key]] = value
                else:
                    updates[key] = value

            result = self.check_repo.update_check(check_id, updates)
            return "[OK] Check updated" if result else "[ERROR] Failed to update check"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def delete_check(self, check_id: str) -> str:
        """Delete a check"""
        try:
            result = self.check_repo.delete_check(check_id)
            return "[OK] Check deleted" if result else "[ERROR] Failed to delete check"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def get_check(self, check_id: str) -> str:
        """Get specific check details"""
        try:
            check = self.check_repo.get_check(check_id)
            if check:
                return f"[OK] Check Details:\n{json.dumps(check, indent=2)}"
            else:
                return "[NOT FOUND] Check not found"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def get_checks_this_week(self, week: str = None) -> str:
        """Get checks from a specific week

        Args:
            week: Optional week selector - 'current', 'last', 'next' or numeric (-2, -1, 0, 1, 2)
                  where 0 = current week, -1 = last week, 1 = next week, etc.
                  If not specified, shows current week
        """
        try:
            from datetime import datetime, timedelta

            # Default to current week if not specified
            if week is None:
                week = 'current'

            # Convert week parameter to offset
            if week == 'current' or week == '0':
                offset = 0
                week_desc = 'current week'
            elif week == 'last' or week == '-1':
                offset = -1
                week_desc = 'last week'
            elif week == 'next' or week == '1':
                offset = 1
                week_desc = 'next week'
            else:
                try:
                    offset = int(week)
                    if offset < 0:
                        week_desc = f'{abs(offset)} weeks ago'
                    elif offset > 0:
                        week_desc = f'{offset} weeks from now'
                    else:
                        week_desc = 'current week'
                except:
                    return f"[ERROR] Invalid week parameter: {week}\nUse 'current', 'last', 'next' or numeric (-2, -1, 0, 1, 2)"

            # Calculate Monday and Sunday for the specified week
            today = datetime.now()
            days_since_monday = today.weekday()
            current_monday = today - timedelta(days=days_since_monday)

            # Apply offset
            target_monday = current_monday + timedelta(weeks=offset)
            target_sunday = target_monday + timedelta(days=6)

            # Set date range from Monday 00:00:00 to Sunday 23:59:59
            week_start = datetime(target_monday.year, target_monday.month, target_monday.day, 0, 0, 0)
            week_end = datetime(target_sunday.year, target_sunday.month, target_sunday.day, 23, 59, 59)

            checks = self.check_repo.search_checks(
                date_from=week_start,
                date_to=week_end
            )

            # Build formatted output with header
            result = f"[OK] Checks for {week_desc}\n"
            result += f"Week: {target_monday.strftime('%m/%d/%Y')} to {target_sunday.strftime('%m/%d/%Y')}\n"
            result += "=" * 60 + "\n\n"

            if not checks:
                result += f"No checks found for {week_desc}"
            else:
                result += f"Found {len(checks)} check(s):\n\n"
                for check in checks:
                    result += f"Check #{check.get('ref_number', 'N/A')}\n"
                    result += f"  Date: {check.get('txn_date')}\n"
                    result += f"  Payee: {check.get('payee_name')}\n"
                    result += f"  Amount: ${check.get('amount', 0):.2f}\n"
                    result += f"  Bank Account: {check.get('bank_account', 'N/A')}\n"

                    if check.get('memo'):
                        result += f"  Memo: {check.get('memo')}\n"

                    # Display item lines if present
                    item_lines = check.get('item_lines', [])
                    if item_lines:
                        result += "  Items:\n"
                        for item in item_lines:
                            result += f"    - {item.get('item', 'N/A')}: ${item.get('amount', 0):.2f}\n"
                            if item.get('customer_job'):
                                result += f"      Job: {item.get('customer_job')}\n"
                            if item.get('description'):
                                result += f"      Description: {item.get('description')}\n"

                    # Display expense lines if present
                    expense_lines = check.get('expense_lines', [])
                    if expense_lines:
                        result += "  Expenses:\n"
                        for expense in expense_lines:
                            result += f"    - {expense.get('account', 'N/A')}: ${expense.get('amount', 0):.2f}\n"
                            if expense.get('customer_job'):
                                result += f"      Job: {expense.get('customer_job')}\n"
                            if expense.get('memo'):
                                result += f"      Memo: {expense.get('memo')}\n"

                    result += "\n"

            return result
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    # Invoice Methods (simplified examples)
    def search_invoices(self, **kwargs) -> str:
        """Search for invoices"""
        try:
            # Default to current quarter if no dates provided
            from datetime import date

            if not kwargs.get('date_from') and not kwargs.get('date_to'):
                today = date.today()
                current_month = today.month
                current_year = today.year

                # Determine quarter
                if current_month <= 3:  # Q1: Jan-Mar
                    default_from = f"{current_year}-01-01"
                    default_to = f"{current_year}-03-31"
                elif current_month <= 6:  # Q2: Apr-Jun
                    default_from = f"{current_year}-04-01"
                    default_to = f"{current_year}-06-30"
                elif current_month <= 9:  # Q3: Jul-Sep
                    default_from = f"{current_year}-07-01"
                    default_to = f"{current_year}-09-30"
                else:  # Q4: Oct-Dec
                    default_from = f"{current_year}-10-01"
                    default_to = f"{current_year}-12-31"

                kwargs.setdefault('date_from', default_from)
                kwargs.setdefault('date_to', default_to)

            invoices = self.invoice_repo.search_invoices(**kwargs)
            if not invoices:
                return "[NOT FOUND] No invoices found"

            result = f"[OK] Found {len(invoices)} invoices\n"
            # Show ALL invoices, not just first 10
            for inv in invoices:
                # Include customer name for clarity
                customer = inv.get('customer', 'Unknown')
                result += f"- Invoice #{inv.get('ref_number')}: ${inv.get('total', 0):.2f} ({customer})\n"

            return result
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def get_invoices_this_week(self) -> str:
        """Get invoices from current week"""
        try:
            # Use search_invoices with date filter for this week
            from datetime import datetime, timedelta
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())  # Monday
            week_end = week_start + timedelta(days=6)  # Sunday
            invoices = self.invoice_repo.search_invoices(
                date_from=week_start.strftime('%Y-%m-%d'),
                date_to=week_end.strftime('%Y-%m-%d')
            )
            if not invoices:
                return "[OK] No invoices this week"
            
            result = f"[OK] {len(invoices)} invoices this week\n"
            total = sum(inv.get('total', 0) for inv in invoices)
            result += f"Total: ${total:.2f}\n"
            
            return result
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def get_invoice(self, invoice_id: str) -> str:
        """Get specific invoice"""
        try:
            invoice = self.invoice_repo.get_invoice(invoice_id)
            if invoice:
                return f"[OK] Invoice Details:\n{json.dumps(invoice, indent=2)}"
            else:
                return "[NOT FOUND] Invoice not found"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def create_invoice(self, customer: str, **kwargs) -> str:
        """Create new invoice"""
        try:
            invoice_id = self.invoice_repo.create_invoice(customer, **kwargs)
            return f"[OK] Invoice created for {customer} (ID: {invoice_id})"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    # Payment Methods
    def pay_bills(self, vendor_name: str, **kwargs) -> str:
        """Pay vendor bills"""
        try:
            vendor_name = self.resolve_vendor(vendor_name)
            amount = kwargs.get('amount', 0)
            bank_account = kwargs.get('bank_account', '1887 b')

            # Load vendor payment settings if not explicitly provided
            check_number = kwargs.get('check_number')
            if not check_number:
                try:
                    import json
                    import os
                    settings_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'vendor_payment_settings.json')
                    if os.path.exists(settings_path):
                        with open(settings_path, 'r') as f:
                            settings = json.load(f)
                            vendor_settings = settings.get('vendor_payment_settings', {})
                            # Check for vendor-specific settings (case insensitive)
                            vendor_key = vendor_name.lower()
                            if vendor_key in vendor_settings:
                                check_number = vendor_settings[vendor_key].get('check_number')
                                # Also get payment method and memo prefix if available
                                if 'payment_method' in vendor_settings[vendor_key]:
                                    kwargs['payment_method'] = vendor_settings[vendor_key]['payment_method']
                                if 'memo_prefix' in vendor_settings[vendor_key] and not kwargs.get('memo'):
                                    kwargs['memo'] = f"{vendor_settings[vendor_key]['memo_prefix']} {vendor_name}"
                except Exception as e:
                    # If settings can't be loaded, continue without them
                    pass
            
            # Get vendor ListID
            vendor = self.vendor_repo.find_vendor_by_name(vendor_name)
            if not vendor:
                return f"[ERROR] Vendor '{vendor_name}' not found"
            
            # Find the bill to pay
            bills = self.bill_repo.find_bills_by_vendor(vendor_name)
            if not bills:
                return f"[ERROR] No bills found for {vendor_name}"
            
            # Get the specific bill to pay
            ref_number = kwargs.get('ref_number')
            unpaid_bill = None

            if ref_number:
                # Find specific bill by ref_number
                for bill in bills:
                    if bill.get('ref_number') == ref_number:
                        unpaid_bill = bill
                        break
                if not unpaid_bill:
                    return f"[ERROR] Bill with ref_number '{ref_number}' not found for {vendor_name}"
            else:
                # Try to find the current week's bill (with vendor prefix in ref_number)
                # Bills are typically named like "ja_09/08-09/14/25" for current week
                vendor_prefix = vendor_name[:2].lower()
                current_week_bills = []
                all_unpaid_bills = []

                for bill in bills:
                    is_unpaid = not bill.get('is_paid', True) or bill.get('balance', 0) > 0 or (bill.get('amount_due', 0) > 0 and not bill.get('IsPaid', True))
                    if is_unpaid:
                        all_unpaid_bills.append(bill)
                        ref = bill.get('ref_number', '')
                        # Check if this looks like a current week bill with vendor prefix
                        if ref.lower().startswith(vendor_prefix + '_'):
                            current_week_bills.append(bill)

                if len(current_week_bills) == 1:
                    # Only one current week bill, use it
                    unpaid_bill = current_week_bills[0]
                elif len(current_week_bills) > 1:
                    # Multiple current week bills, need ref_number
                    bill_list = "\n".join([f"  - {b.get('ref_number')}: ${b.get('amount_due', 0):.2f}" for b in current_week_bills])
                    return f"[ERROR] Multiple unpaid bills found for {vendor_name}. Please specify ref_number:\n{bill_list}"
                elif all_unpaid_bills:
                    # No current week bills, show all unpaid and ask for ref_number
                    bill_list = "\n".join([f"  - {b.get('ref_number')}: ${b.get('amount_due', 0):.2f}" for b in all_unpaid_bills[:5]])
                    return f"[ERROR] No current week bill found for {vendor_name}. Unpaid bills:\n{bill_list}\nPlease specify ref_number parameter"
            
            if not unpaid_bill:
                return f"[ERROR] No unpaid bills found for {vendor_name}"
            
            # Get bank account ListID
            accounts = self.account_repo.search_accounts()
            bank_account_id = None
            for acc in accounts:
                if bank_account.lower() in acc.get('name', '').lower():
                    bank_account_id = acc.get('list_id')
                    break
            
            if not bank_account_id:
                return f"[ERROR] Bank account '{bank_account}' not found"
            
            # Create the bill payment (check_number now includes vendor settings)
            result = self.payment_repo.create_bill_payment(
                vendor_list_id=vendor['list_id'],
                bill_txn_id=unpaid_bill['txn_id'],
                amount=amount,
                bank_account_list_id=bank_account_id,
                payment_method=kwargs.get('payment_method', 'Check'),
                payment_date=kwargs.get('payment_date'),  # Accept payment date from document
                check_number=check_number,  # Now includes vendor settings
                memo=kwargs.get('memo', f'Payment to {vendor_name}')
            )
            
            if result.get('success'):
                return f"[OK] Payment created for {vendor_name}: ${amount:.2f}\nTransaction ID: {result.get('txn_id')}"
            else:
                return f"[ERROR] Failed to create payment: {result.get('error')}"
                
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def create_bill_payment(self, **kwargs) -> str:
        """Create bill payment"""
        try:
            # Use create_bill since create_bill_payment doesn't exist
            payment_data = {
                'vendor_name': kwargs.get('vendor_name'),
                'amount': kwargs.get('amount', 0),
                'ref_number': f"PMT-{kwargs.get('vendor_name', 'UNK')[:3]}",
                'memo': 'Payment'
            }
            payment_id = self.bill_repo.create_bill(payment_data)
            return f"[OK] Payment created (ID: {payment_id})"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def search_bill_payments(self, **kwargs) -> str:
        """Search bill payments"""
        try:
            # Use payment repository
            payments = self.payment_repo.search_payments(**kwargs)
            if not payments:
                return "[NOT FOUND] No payments found"
            
            result = f"[OK] Found {len(payments)} payments\n"
            for payment in payments[:10]:
                result += f"- Payment: ${payment.get('amount', 0):.2f}\n"
            
            return result
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def delete_bill_payment(self, payment_id: str) -> str:
        """Delete bill payment"""
        try:
            # Use delete_bill since delete_bill_payment doesn't exist
            result = self.bill_repo.delete_bill(payment_id)
            return "[OK] Payment deleted" if result else "[ERROR] Failed to delete payment"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def update_bill_payment(self, payment_id: str, **kwargs) -> str:
        """Update bill payment"""
        try:
            # Use update_bill since update_bill_payment doesn't exist
            result = self.bill_repo.update_bill(payment_id, **kwargs)
            return "[OK] Payment updated" if result else "[ERROR] Failed to update payment"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    # Item Methods
    def search_items(self, search_term: str = None, item_type: str = None,
                     active_only: bool = True) -> str:
        """Search for items - improved to match MCP implementation"""

        # Get all items first (like MCP does)
        try:
            all_items = self.item_repo.get_all_items()

            # Apply filters
            items = all_items

            # Filter by search term if provided
            if search_term and search_term.strip():
                search_lower = search_term.lower()
                items = [i for i in items if (search_lower in i.get('name', '').lower() or
                        (i.get('description') and search_lower in i.get('description', '').lower()))]

            # Filter by active status
            if active_only:
                items = [i for i in items if i.get('is_active', True)]

            # Filter by item type if specified
            if item_type:
                items = [i for i in items if i.get('type', '').lower() == item_type.lower()]

            # Check if no items found
            if not items:
                if search_term:
                    return f"[NOT FOUND] No items matching '{search_term}'"
                else:
                    filter_desc = f" ({item_type})" if item_type else ""
                    return f"[OK] No items found{filter_desc}"

            # Sort items by type and name
            items.sort(key=lambda i: (i.get('type', ''), i.get('name', '').lower()))

            # Format result with grouping by type (like MCP)
            if search_term:
                result = f"[OK] Found {len(items)} items matching '{search_term}'\n\n"
            else:
                result = f"[OK] Found {len(items)} items\n\n"

            # Group items by type
            items_by_type = {}
            for item in items:
                item_type_key = item.get('type', 'Unknown')
                if item_type_key not in items_by_type:
                    items_by_type[item_type_key] = []
                items_by_type[item_type_key].append(item)

            # Display grouped items
            for item_type_key, type_items in sorted(items_by_type.items()):
                result += f"{item_type_key.upper()} ITEMS:\n"
                result += "-" * 40 + "\n"
                for item in type_items[:50]:  # Limit per type
                    name = item.get('name', 'Unknown')
                    active = " [INACTIVE]" if not item.get('is_active', True) else ""
                    desc = f" - {item.get('description')}" if item.get('description') else ""
                    price = f" (${item.get('price'):.2f})" if item.get('price') else ""
                    result += f"  {name}{price}{desc}{active}\n"
                result += "\n"

            return result

        except Exception as e:
            return f"[ERROR] Failed to search items: {str(e)}"
    
    def create_item(self, name: str, **kwargs) -> str:
        """Create new item"""
        try:
            item_id = self.item_repo.create_item(name, **kwargs)
            return f"[OK] Item created: {name} (ID: {item_id})"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def update_item(self, item_id: str, **kwargs) -> str:
        """Update item"""
        try:
            result = self.item_repo.update_item(item_id, **kwargs)
            return "[OK] Item updated" if result else "[ERROR] Failed to update item"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    # Account Methods
    def search_accounts(self, **kwargs) -> str:
        """Search for accounts"""
        try:
            accounts = self.account_repo.search_accounts(**kwargs)
            if not accounts:
                return "[NOT FOUND] No accounts found"
            
            result = f"[OK] Found {len(accounts)} accounts\n"
            for account in accounts[:20]:
                result += f"- {account.get('name')} ({account.get('type')})\n"
            
            return result
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def create_account(self, name: str, account_type: str, **kwargs) -> str:
        """Create new account"""
        try:
            account_id = self.account_repo.create_account(name, account_type, **kwargs)
            return f"[OK] Account created: {name} (ID: {account_id})"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def update_account(self, account_id: str, **kwargs) -> str:
        """Update account"""
        try:
            result = self.account_repo.update_account(account_id, **kwargs)
            return "[OK] Account updated" if result else "[ERROR] Failed to update account"
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    # Deposit Methods
    def search_deposits(self, **kwargs) -> str:
        """Search for deposits"""
        try:
            deposits = self.deposit_repo.search_deposits(**kwargs)
            if not deposits:
                return "[NOT FOUND] No deposits found"
            
            result = f"[OK] Found {len(deposits)} deposits\n"
            for deposit in deposits[:10]:
                result += f"- Deposit: ${deposit.get('total', 0):.2f}\n"
            
            return result
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def deposit_customer_payment(self, **kwargs) -> str:
        """Deposit customer payment"""
        try:
            deposit_id = self.deposit_repo.create_deposit(**kwargs)
            return f"[OK] Deposit created (ID: {deposit_id})"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def receive_payment(self, invoice_id: str, amount: float, **kwargs) -> str:
        """Receive payment for an invoice"""
        try:
            # Get invoice details first
            invoice = self.invoice_repo.get_invoice(invoice_id)
            if not invoice:
                return f"[ERROR] Invoice {invoice_id} not found"

            # Prepare payment data
            payment_data = {
                'customer_name': invoice['customer'],
                'amount': amount,
                'invoice_txn_id': invoice['txn_id'],
                'payment_method': kwargs.get('payment_method', 'Check'),
                'check_number': kwargs.get('check_number', ''),
                'deposit_account': kwargs.get('deposit_to_account'),  # Repository expects 'deposit_account'
                'date': kwargs.get('payment_date', datetime.now().strftime('%Y-%m-%d')),
                'memo': kwargs.get('memo', f'Payment for Invoice #{invoice_id}')
            }

            # Create the payment
            result = self.receive_payment_repo.create_payment(payment_data)

            if result:
                return f"[OK] Payment received for Invoice #{invoice_id}\n" \
                       f"Payment ID: {result.get('txn_id')}\n" \
                       f"Amount: ${amount:.2f}\n" \
                       f"Customer: {invoice['customer']}\n" \
                       f"Deposited to: {result.get('deposit_account', 'Undeposited Funds')}"
            else:
                return "[ERROR] Failed to create payment"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def delete_customer_payment(self, payment_id: str) -> str:
        """Delete a customer payment transaction"""
        try:
            result = self.receive_payment_repo.delete_payment(payment_id)
            return "[OK] Customer payment deleted" if result else "[ERROR] Failed to delete payment"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def search_customer_payments(self, **kwargs) -> str:
        """Search for customer payments

        Args:
            customer_name: Customer name to search for (optional)
            date_from: Start date MM-DD-YYYY or MM/DD/YYYY (optional, defaults to current quarter start)
            date_to: End date MM-DD-YYYY or MM/DD/YYYY (optional, defaults to current quarter end)

        Returns:
            List of customer payments matching the criteria
        """
        try:
            # Get customer name if provided
            customer_name = kwargs.get('customer_name')

            # Default to current quarter if no dates provided
            from datetime import date

            if not kwargs.get('date_from') or not kwargs.get('date_to'):
                today = date.today()
                current_month = today.month
                current_year = today.year

                # Determine quarter
                if current_month <= 3:  # Q1: Jan-Mar
                    default_from = f"01-01-{current_year}"
                    default_to = f"03-31-{current_year}"
                elif current_month <= 6:  # Q2: Apr-Jun
                    default_from = f"04-01-{current_year}"
                    default_to = f"06-30-{current_year}"
                elif current_month <= 9:  # Q3: Jul-Sep
                    default_from = f"07-01-{current_year}"
                    default_to = f"09-30-{current_year}"
                else:  # Q4: Oct-Dec
                    default_from = f"10-01-{current_year}"
                    default_to = f"12-31-{current_year}"

                # Use provided dates or defaults
                date_from = kwargs.get('date_from', default_from)
                date_to = kwargs.get('date_to', default_to)
            else:
                date_from = kwargs.get('date_from')
                date_to = kwargs.get('date_to')

            if customer_name:
                # Search by specific customer
                payments = self.receive_payment_repo.find_payments_by_customer(customer_name)
                search_desc = f"customer '{customer_name}'"
            else:
                # Convert date format for repository (MM-DD-YYYY to YYYY-MM-DD)
                repo_date_from = None
                repo_date_to = None

                if date_from:
                    parts = date_from.replace('/', '-').split('-')
                    if len(parts) == 3 and len(parts[0]) == 2:  # MM-DD-YYYY
                        repo_date_from = f"{parts[2]}-{parts[0]}-{parts[1]}"
                    else:
                        repo_date_from = date_from

                if date_to:
                    parts = date_to.replace('/', '-').split('-')
                    if len(parts) == 3 and len(parts[0]) == 2:  # MM-DD-YYYY
                        repo_date_to = f"{parts[2]}-{parts[0]}-{parts[1]}"
                    else:
                        repo_date_to = date_to

                # Get all payments with date filter applied in query
                payments = self.receive_payment_repo.get_all_payments(repo_date_from, repo_date_to)
                search_desc = "all customers"

            # Additional date filtering for customer-specific searches
            # (since find_payments_by_customer doesn't support date filtering yet)
            if customer_name and (date_from or date_to):
                from datetime import datetime

                # Parse dates
                def parse_date(date_str):
                    if not date_str:
                        return None
                    for fmt in ['%m-%d-%Y', '%m/%d/%Y', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(date_str, fmt).date()
                        except:
                            continue
                    return None

                from_date = parse_date(date_from) if date_from else None
                to_date = parse_date(date_to) if date_to else None

                filtered_payments = []
                for payment in payments:
                    payment_date = parse_date(payment.get('date'))
                    if payment_date:
                        if from_date and payment_date < from_date:
                            continue
                        if to_date and payment_date > to_date:
                            continue
                        filtered_payments.append(payment)

                payments = filtered_payments
                if date_from and date_to:
                    search_desc += f" from {date_from} to {date_to}"
                elif date_from:
                    search_desc += f" from {date_from}"
                elif date_to:
                    search_desc += f" up to {date_to}"

            if not payments:
                return f"[!] No customer payments found for {search_desc}"

            # Format output
            output = [f"[OK] Found {len(payments)} customer payment(s) for {search_desc}"]
            output.append("=" * 60)

            for i, payment in enumerate(payments, 1):
                output.append(f"\n{i}. Payment #{payment.get('ref_number', 'N/A')} - {payment.get('txn_date', 'N/A')}")
                output.append(f"   Customer: {payment.get('customer_name', 'N/A')}")
                output.append(f"   Amount: ${payment.get('amount', 0):.2f}")
                if payment.get('payment_method'):
                    output.append(f"   Method: {payment.get('payment_method')}")
                if payment.get('check_number'):
                    output.append(f"   Check #: {payment.get('check_number')}")
                if payment.get('deposit_account'):
                    output.append(f"   Deposit To: {payment.get('deposit_account')}")
                if payment.get('memo'):
                    output.append(f"   Memo: {payment.get('memo')}")
                output.append(f"   Transaction ID: {payment.get('txn_id', 'N/A')}")

            return "\n".join(output)

        except Exception as e:
            logger.error(f"Search customer payments failed: {e}")
            return f"[ERROR] {str(e)}"

    # Report Methods
    def get_job_profit(self, job_name: str, **kwargs) -> str:
        """Get job profitability report with vendor breakdown"""
        try:
            # Use fuzzy matching to find the correct job name
            from quickbooks_standard.entities.customers.customer_repository import CustomerRepository
            from shared_utilities.fuzzy_matcher import FuzzyMatcher

            customer_repo = CustomerRepository()
            fuzzy_matcher = FuzzyMatcher()

            # Get all customers and jobs
            all_customers = customer_repo.get_all_customers(include_jobs=True)
            job_names = []
            for customer in all_customers:
                if ':' in customer.get('full_name', ''):
                    # This is a job (has parent:job format)
                    job_names.append(customer['full_name'])

            # Find best match
            match = fuzzy_matcher.find_best_match(
                job_name,
                job_names,
                entity_type='job'
            )

            if not match.found:
                return f"[ERROR] Job '{job_name}' not found. Available jobs: {', '.join(job_names[:5])}..."

            matched_job_name = match.exact_name

            # Generate the report
            report = self.job_profit_repo.generate_job_report(matched_job_name)

            if report.get('status') == 'error':
                return f"[ERROR] {report.get('error_message', 'Failed to generate report')}"

            # Get vendor breakdown using JobTransactionDetailReport
            from quickbooks_standard.reports.job_transaction_detail_report import JobTransactionDetailReport
            job_detail_repo = JobTransactionDetailReport()

            # Get last 90 days of transactions
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)

            transactions = job_detail_repo.get_job_transactions(
                matched_job_name,
                start_date.strftime('%m-%d-%Y'),
                end_date.strftime('%m-%d-%Y')
            )

            # Get ALL transactions for this job using GeneralDetailReport
            vendor_by_items = {}  # vendor/payee -> {item -> amount}

            # Use GeneralDetailReport to get all transactions for this job
            from quickbooks_standard.reports.general_detail_report import GeneralDetailReportRepository
            general_report = GeneralDetailReportRepository()

            # Get transactions for up to 1 year for this job
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)

            # Get all transactions filtered by this job/entity
            all_transactions = general_report.generate_report(
                entity_filter=matched_job_name,
                date_from=start_date.strftime('%m-%d-%Y'),
                date_to=end_date.strftime('%m-%d-%Y'),
                max_returned=500
            )

            # Process all transactions to build vendor/item breakdown
            for txn in all_transactions:
                # For expense transactions, track vendor/payee and item
                if txn.get('account_type') in ['Expense', 'Cost of Goods Sold', 'Other Expense']:
                    vendor_name = txn.get('entity_name', txn.get('vendor_name', 'Unknown'))
                    item_name = txn.get('item_name', txn.get('memo', 'General'))
                    amount = abs(txn.get('amount', 0))  # Use absolute value for expenses

                    if amount > 0:
                        if vendor_name not in vendor_by_items:
                            vendor_by_items[vendor_name] = {}
                        if item_name not in vendor_by_items[vendor_name]:
                            vendor_by_items[vendor_name][item_name] = 0
                        vendor_by_items[vendor_name][item_name] += amount

            # If GeneralDetailReport doesn't give us enough, also check bills and checks directly
            # Always check bills for line item details
            if True:  # Always do this to get line item details
                # Query bills with line items
                bills = self.bill_repo.find_bills_by_date_range(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    include_line_items=True
                )

                for bill in bills:
                    vendor_name = bill.get('vendor_name', 'Unknown')
                    for line in bill.get('line_items', []):
                        customer = line.get('customer_name', '')
                        if customer and customer.lower() == matched_job_name.lower():
                            item_name = line.get('item_name', line.get('description', 'Labor'))
                            amount = line.get('amount', 0)

                            if vendor_name not in vendor_by_items:
                                vendor_by_items[vendor_name] = {}
                            if item_name not in vendor_by_items[vendor_name]:
                                vendor_by_items[vendor_name][item_name] = 0
                            vendor_by_items[vendor_name][item_name] += amount

                # Also query checks with line items for this job
                from quickbooks_standard.entities.checks.check_repository import CheckRepository
                check_repo = CheckRepository()

                # Search all checks in date range
                checks = check_repo.search_checks(date_from=start_date,
                                                 date_to=end_date)

                logger.info(f"Found {len(checks) if checks else 0} checks to process")

                check_count_with_job = 0
                for check_summary in checks or []:
                    # Get full check details with line items
                    check_id = check_summary.get('txn_id')
                    if check_id:
                        check = check_repo.get_check(check_id)
                        if check:
                            payee = check.get('payee_name', 'Unknown')
                            found_job_item = False
                            # Check item lines
                            for line in check.get('item_lines', []):
                                # XML returns 'customer_job' while QBFC returns 'customer_name'
                                customer = line.get('customer_name', line.get('customer_job', ''))
                                if customer and customer.lower() == matched_job_name.lower():
                                    # XML returns 'item' while QBFC returns 'item_name'
                                    item_name = line.get('item_name', line.get('item', line.get('description', 'Labor')))
                                    amount = line.get('amount', 0)
                                    found_job_item = True

                                    # Log if we find job materials
                                    if 'material' in item_name.lower():
                                        logger.info(f"Found job materials in check {check_id}: {item_name} ${amount} from {payee}")

                                    if payee not in vendor_by_items:
                                        vendor_by_items[payee] = {}
                                    if item_name not in vendor_by_items[payee]:
                                        vendor_by_items[payee][item_name] = 0
                                    vendor_by_items[payee][item_name] += amount

                            # Check expense lines
                            for line in check.get('expense_lines', []):
                                # XML returns 'customer_job' while QBFC returns 'customer_name'
                                customer = line.get('customer_name', line.get('customer_job', ''))
                                if customer and customer.lower() == matched_job_name.lower():
                                    account_name = line.get('account_name', 'Expense')
                                    amount = line.get('amount', 0)
                                    found_job_item = True

                                    if payee not in vendor_by_items:
                                        vendor_by_items[payee] = {}
                                    if account_name not in vendor_by_items[payee]:
                                        vendor_by_items[payee][account_name] = 0
                                    vendor_by_items[payee][account_name] += amount

                            if found_job_item:
                                check_count_with_job += 1

                logger.info(f"Found {check_count_with_job} checks with items for job {matched_job_name}")

            # Format the output with right-justified amounts (40 char width)
            output = []
            output.append(f"\nJOB PROFITABILITY BY ITEM")
            output.append(f"Job: {report.get('job_name', matched_job_name)}")
            output.append("=" * 40)
            
            # Items sold/revenue section
            output.append("\nITEMS SOLD:")
            income_data = report.get('income', {})
            income_items = income_data.get('items', [])
            for item in income_items:
                if isinstance(item, dict):
                    # Try 'item' key first (from report), then 'name'
                    item_name = item.get('item') or item.get('name', 'Unknown')
                    amount_str = f"${item.get('amount', 0):,.2f}"
                    # Format: item name left, amount right, total 40 chars
                    line = f"  {item_name[:30]}".ljust(40 - len(amount_str)) + amount_str
                    output.append(line)
            if not income_items:
                output.append("  [No item details available]")
            
            total_rev_str = f"${income_data.get('total', 0):,.2f}"
            output.append(f"  {'Total Revenue:'.ljust(38 - len(total_rev_str))}{total_rev_str}")
            
            # Cost of items/labor section
            output.append("\nCOST OF GOODS SOLD:")
            expense_data = report.get('expenses', {})
            expense_items = expense_data.get('items', [])
            for item in expense_items:
                if isinstance(item, dict):
                    # Try 'item' key first (from report), then 'name'
                    item_name = item.get('item') or item.get('name', 'Unknown')
                    amount_str = f"${item.get('amount', 0):,.2f}"
                    # Format: item name left, amount right, total 40 chars
                    line = f"  {item_name[:30]}".ljust(40 - len(amount_str)) + amount_str
                    output.append(line)
            if not expense_items:
                output.append("  [No cost details available]")
            
            total_cogs_str = f"${expense_data.get('total', 0):,.2f}"
            output.append(f"  {'Total COGS:'.ljust(38 - len(total_cogs_str))}{total_cogs_str}")
            
            # Profit calculation
            output.append("\n" + "=" * 40)
            profit = report.get('profit_loss', 0)
            margin = report.get('profit_margin', 0)

            profit_str = f"${profit:,.2f}"
            margin_str = f"{margin:.1f}%"
            output.append(f"{'GROSS PROFIT:'.ljust(40 - len(profit_str))}{profit_str}")
            output.append(f"{'PROFIT MARGIN:'.ljust(40 - len(margin_str))}{margin_str}")
            output.append("=" * 40)

            # Add vendor/payee by items summary if we have vendor data
            if vendor_by_items:
                output.append("\nITEMS BY VENDOR/PAYEE:")
                output.append("-" * 40)

                vendor_total = 0
                for vendor in sorted(vendor_by_items.keys()):
                    # Vendor/payee name
                    vendor_line = vendor[:30] if vendor else "Unknown"
                    vendor_subtotal = sum(vendor_by_items[vendor].values())
                    vendor_total += vendor_subtotal
                    amount_str = f"${vendor_subtotal:,.2f}"
                    output.append(f"{vendor_line.ljust(40 - len(amount_str))}{amount_str}")

                    # Item breakdown for this vendor/payee
                    for item in sorted(vendor_by_items[vendor].keys()):
                        amount = vendor_by_items[vendor][item]
                        if amount > 0:
                            item_line = f"  {item[:28]}"
                            item_amount_str = f"${amount:,.2f}"
                            output.append(f"{item_line.ljust(40 - len(item_amount_str))}{item_amount_str}")
                    output.append("")  # Blank line between vendors

                output.append("-" * 40)
                total_str = f"${vendor_total:,.2f}"
                output.append(f"{'TOTAL COSTS:'.ljust(40 - len(total_str))}{total_str}")

                # Show discrepancy if totals don't match
                cogs_total = expense_data.get('total', 0)
                if abs(cogs_total - vendor_total) > 0.01:
                    diff = cogs_total - vendor_total
                    output.append(f"[!] Missing: ${diff:,.2f} from COGS total")
                    output.append(f"    COGS shows ${cogs_total:,.2f} but vendor")
                    output.append(f"    breakdown only shows ${vendor_total:,.2f}")
                    output.append(f"    Likely from transactions without")
                    output.append(f"    vendor/payee or outside date range")

                output.append("=" * 40)

            return "\n".join(output)

        except Exception as e:
            return f"[ERROR] {str(e)}"

    # Purchase Order Methods
    def get_purchase_orders(self, **kwargs) -> str:
        """Get purchase orders with filters"""
        try:
            from datetime import datetime

            # Handle quarter parameter (prev, current, next)
            quarter = kwargs.get('quarter', 'current')

            # Default to current quarter if no dates specified
            if not kwargs.get('date_from') and not kwargs.get('date_to'):
                today = datetime.now()
                month = today.month
                year = today.year

                # Determine current quarter
                if month <= 3:
                    current_q = 1
                elif month <= 6:
                    current_q = 2
                elif month <= 9:
                    current_q = 3
                else:
                    current_q = 4

                # Adjust quarter based on parameter
                if quarter == 'prev':
                    current_q -= 1
                    if current_q < 1:
                        current_q = 4
                        year -= 1
                elif quarter == 'next':
                    current_q += 1
                    if current_q > 4:
                        current_q = 1
                        year += 1
                # else 'current' stays as is

                # Set date range based on quarter
                if current_q == 1:
                    kwargs['date_from'] = f"01-01-{year}"
                    kwargs['date_to'] = f"03-31-{year}"
                elif current_q == 2:
                    kwargs['date_from'] = f"04-01-{year}"
                    kwargs['date_to'] = f"06-30-{year}"
                elif current_q == 3:
                    kwargs['date_from'] = f"07-01-{year}"
                    kwargs['date_to'] = f"09-30-{year}"
                else:
                    kwargs['date_from'] = f"10-01-{year}"
                    kwargs['date_to'] = f"12-31-{year}"

            # Get purchase orders
            pos = self.po_repo.get_purchase_orders(
                date_from=kwargs.get('date_from'),
                date_to=kwargs.get('date_to'),
                vendor_name=kwargs.get('vendor_name'),
                open_only=kwargs.get('open_only', True)
            )

            if not pos:
                return "[NOT FOUND] No purchase orders found"

            # Format output
            output = []
            output.append(f"[OK] Found {len(pos)} purchase orders\n")

            # Show summary first
            open_count = sum(1 for po in pos if not po.get('is_fully_received', False))
            if open_count > 0:
                output.append(f"OPEN PURCHASE ORDERS: {open_count}\n")
                output.append("=" * 60)

            for po in pos:
                if not po.get('is_fully_received', False):
                    output.append(f"\nPO #{po['ref_number']} - {po['vendor']}")
                    output.append(f"  Date: {po['txn_date']}")
                    output.append(f"  Total: ${po['total']:.2f}")

                    # Show items not fully received
                    for item in po.get('line_items', []):
                        ordered = item['quantity']
                        received = item.get('received', 0)
                        remaining = ordered - received
                        if remaining > 0:
                            output.append(f"    - {item['item']}: Ordered={ordered:.0f}, Received={received:.0f}, Pending={remaining:.0f}")
                            if item.get('customer_job'):
                                output.append(f"      Job: {item['customer_job']}")

            return "\n".join(output)

        except Exception as e:
            return f"[ERROR] {str(e)}"

    def create_purchase_order(self, vendor_name: str, items: list, **kwargs) -> str:
        """Create a new purchase order"""
        try:
            # Validate that all items have customer_job specified
            for i, item in enumerate(items):
                if not item.get('customer_job'):
                    return f"[ERROR] Purchase order line item #{i+1} is missing required 'customer_job' field.\n\nAll purchase order items must be assigned to a job for proper job costing."
                if not item.get('item'):
                    return f"[ERROR] Purchase order line item #{i+1} is missing required 'item' field."

            # Create the PO
            result = self.po_repo.create_purchase_order(
                vendor_name=vendor_name,
                items=items,
                date=kwargs.get('date'),
                ref_number=kwargs.get('ref_number'),
                expected_date=kwargs.get('expected_date'),
                memo=kwargs.get('memo'),
                vendor_msg=kwargs.get('vendor_msg'),
                ship_to=kwargs.get('ship_to')
            )

            if 'error' in result:
                return f"[ERROR] {result['error']}"

            # Format the created PO
            return f"[OK] Purchase Order created\n{self.po_repo.format_purchase_order(result)}"

        except Exception as e:
            return f"[ERROR] {str(e)}"

    def delete_purchase_order(self, txn_id: str) -> str:
        """Delete a purchase order"""
        try:
            result = self.po_repo.delete_purchase_order(txn_id)

            if result.get('success'):
                return f"[OK] {result.get('message', 'Purchase order deleted')}"
            else:
                return f"[ERROR] {result.get('error', 'Failed to delete purchase order')}"

        except Exception as e:
            return f"[ERROR] {str(e)}"

    def receive_purchase_order(self, **kwargs) -> str:
        """Receive items from a purchase order"""
        try:
            result = self.po_repo.receive_purchase_order(
                po_ref_number=kwargs.get('po_ref_number'),
                po_txn_id=kwargs.get('po_txn_id'),
                line_items=kwargs.get('line_items')
            )

            if result.get('success'):
                return f"[OK] {result.get('message', 'Items received')}"
            else:
                return f"[ERROR] {result.get('error', 'Failed to receive items')}"

        except Exception as e:
            return f"[ERROR] {str(e)}"

    # Item Receipt Methods
    def get_item_receipts(self, **kwargs) -> str:
        """Get item receipts with quarter support"""
        try:
            from datetime import datetime

            # Handle quarter parameter (prev, current, next)
            quarter = kwargs.get('quarter', 'current')

            # Default to current quarter if no dates specified
            if not kwargs.get('date_from') and not kwargs.get('date_to'):
                today = datetime.now()
                month = today.month
                year = today.year

                # Determine current quarter
                if month <= 3:
                    current_q = 1
                elif month <= 6:
                    current_q = 2
                elif month <= 9:
                    current_q = 3
                else:
                    current_q = 4

                # Adjust quarter based on parameter
                if quarter == 'prev' or quarter == 'previous':
                    current_q -= 1
                    if current_q < 1:
                        current_q = 4
                        year -= 1
                elif quarter == 'next':
                    current_q += 1
                    if current_q > 4:
                        current_q = 1
                        year += 1
                elif quarter.startswith('Q'):
                    # Handle Q1, Q2, Q3, Q4
                    try:
                        current_q = int(quarter[1])
                    except:
                        pass
                # else 'current' stays as is

                # Set date range based on quarter
                if current_q == 1:
                    date_from = f"{year}-01-01"
                    date_to = f"{year}-03-31"
                elif current_q == 2:
                    date_from = f"{year}-04-01"
                    date_to = f"{year}-06-30"
                elif current_q == 3:
                    date_from = f"{year}-07-01"
                    date_to = f"{year}-09-30"
                else:
                    date_from = f"{year}-10-01"
                    date_to = f"{year}-12-31"

                kwargs['date_from'] = date_from
                kwargs['date_to'] = date_to

            # Search for receipts
            receipts = self.item_receipt_repo.search_item_receipts(
                vendor_name=kwargs.get('vendor_name'),
                date_from=kwargs.get('date_from'),
                date_to=kwargs.get('date_to')
            )

            if not receipts:
                return f"[NOT FOUND] No item receipts found for Q{current_q} {year}"

            # Format output
            output = []
            output.append(f"[OK] Found {len(receipts)} item receipts for Q{current_q} {year}\n")
            output.append("=" * 60)

            for receipt in receipts:
                output.append(f"\nReceipt #{receipt.get('ref_number', 'N/A')}")
                output.append(f"  Date: {receipt.get('txn_date', 'N/A')}")
                output.append(f"  Vendor: {receipt.get('vendor', 'N/A')}")
                output.append(f"  Total: ${receipt.get('total_amount', 0):.2f}")

                if receipt.get('linked_po'):
                    output.append(f"  Linked to PO: #{receipt['linked_po']}")

                # Show items
                for item in receipt.get('line_items', []):
                    qty = item.get('quantity', 0)
                    amount = item.get('amount', 0)
                    if amount > 0:
                        output.append(f"    - {item.get('item', 'Unknown')}: {qty:.0f} units @ ${amount:.2f}")
                    else:
                        output.append(f"    - {item.get('item', 'Unknown')}: {qty:.0f} units")

            return "\n".join(output)

        except Exception as e:
            return f"[ERROR] {str(e)}"

    def search_item_receipts(self, **kwargs) -> str:
        """Search item receipts with filters"""
        try:
            receipts = self.item_receipt_repo.search_item_receipts(
                vendor_name=kwargs.get('vendor_name'),
                ref_number=kwargs.get('ref_number'),
                date_from=kwargs.get('date_from'),
                date_to=kwargs.get('date_to'),
                txn_id=kwargs.get('txn_id')
            )

            if not receipts:
                return "[NOT FOUND] No item receipts found"

            # Format output
            output = []
            output.append(f"[OK] Found {len(receipts)} item receipts\n")

            for receipt in receipts:
                output.append(f"Receipt #{receipt.get('ref_number', 'N/A')} - {receipt.get('vendor', 'N/A')}")
                output.append(f"  Date: {receipt.get('txn_date', 'N/A')}, Total: ${receipt.get('total_amount', 0):.2f}")

            return "\n".join(output)

        except Exception as e:
            return f"[ERROR] {str(e)}"

    def search_transaction_by_amount(self, amount: float, **kwargs) -> str:
        """Search for transactions by amount across ALL transaction types

        Args:
            amount: Amount to search for (required)
            date_from: Start date MM-DD-YYYY or MM/DD/YYYY (optional, defaults to current quarter start)
            date_to: End date MM-DD-YYYY or MM/DD/YYYY (optional, defaults to current quarter end)
            tolerance: Amount tolerance for matching (default 0.01)

        Returns:
            All transactions matching the amount across checks, bills, invoices, deposits, etc.
        """
        try:
            # Default to current quarter if no dates provided
            from datetime import datetime, date

            if not kwargs.get('date_from') or not kwargs.get('date_to'):
                today = date.today()
                current_month = today.month
                current_year = today.year

                # Determine quarter
                if current_month <= 3:  # Q1: Jan-Mar
                    default_from = f"01-01-{current_year}"
                    default_to = f"03-31-{current_year}"
                elif current_month <= 6:  # Q2: Apr-Jun
                    default_from = f"04-01-{current_year}"
                    default_to = f"06-30-{current_year}"
                elif current_month <= 9:  # Q3: Jul-Sep
                    default_from = f"07-01-{current_year}"
                    default_to = f"09-30-{current_year}"
                else:  # Q4: Oct-Dec
                    default_from = f"10-01-{current_year}"
                    default_to = f"12-31-{current_year}"

                date_from = kwargs.get('date_from', default_from)
                date_to = kwargs.get('date_to', default_to)

                logger.info(f"Searching all transactions for amount ${amount:.2f} (Quarter: {date_from} to {date_to})")
            else:
                date_from = kwargs.get('date_from')
                date_to = kwargs.get('date_to')
                logger.info(f"Searching all transactions for amount ${amount:.2f}")

            result = self.transaction_search.search_by_amount(
                amount=amount,
                date_from=date_from,
                date_to=date_to,
                tolerance=kwargs.get('tolerance', 0.01)
            )

            if not result.get('success'):
                return f"[ERROR] {result.get('error', 'Search failed')}"

            transactions = result.get('transactions', [])

            if not transactions:
                output = f"[!] No transactions found for amount ${amount:.2f}"
                output += f"\n  Date range: {date_from} to {date_to}"
            else:
                output = f"[OK] Found {len(transactions)} transaction(s) for ${amount:.2f}\n"
                output += f"  Date range: {date_from} to {date_to}\n"
                output += "=" * 50 + "\n"

                for i, txn in enumerate(transactions, 1):
                    output += f"\n{i}. {txn.get('type', 'Unknown')} - {txn.get('date', 'N/A')}\n"
                    output += f"   Name: {txn.get('name', 'N/A')}\n"
                    if txn.get('ref_number'):
                        output += f"   Ref #: {txn.get('ref_number')}\n"
                    if txn.get('memo'):
                        output += f"   Memo: {txn.get('memo')}\n"
                    if txn.get('account'):
                        output += f"   Account: {txn.get('account')}\n"
                    output += f"   Amount: ${abs(txn.get('amount', 0)):.2f}\n"
                    output += f"   Transaction ID: {txn.get('txn_id', 'N/A')}\n"

            return output

        except Exception as e:
            logger.error(f"Search by amount failed: {e}")
            return f"[ERROR] {str(e)}"


# Test functionality if run directly
if __name__ == "__main__":
    qb = QBConnector()
    
    print("\n=== Testing QB Connector ===\n")
    
    # Test searching vendors
    print("1. Testing vendor search:")
    result = qb.execute_command("SEARCH_VENDORS", {"search_term": "martinez"})
    print(result['output'])
    
    print("\n2. Testing get work bill:")
    result = qb.execute_command("GET_WORK_BILL", {"vendor_name": "jaciel"})
    print(result['output'])