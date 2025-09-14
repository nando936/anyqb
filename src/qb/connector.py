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
            from quickbooks_standard.entities.accounts.account_repository import AccountRepository
            from quickbooks_standard.entities.checks.check_repository import CheckRepository
            from quickbooks_standard.entities.invoices.invoice_repository import InvoiceRepository
            from quickbooks_standard.entities.deposits.deposit_repository import DepositRepository
            from quickbooks_standard.entities.payments.payment_repository import PaymentRepository
            from quickbooks_standard.reports.job_profitability_report import JobProfitabilityReportRepository
            from custom_systems.work_bills.work_bill_service import WorkBillService
            from shared_utilities.vendor_aliases import resolve_vendor_alias
            
            # Initialize repositories
            self.vendor_repo = VendorRepository()
            self.bill_repo = BillRepository()
            self.customer_repo = CustomerRepository()
            self.item_repo = ItemRepository()
            self.account_repo = AccountRepository()
            self.check_repo = CheckRepository()
            self.invoice_repo = InvoiceRepository()
            self.deposit_repo = DepositRepository()
            self.payment_repo = PaymentRepository()
            self.job_profit_repo = JobProfitabilityReportRepository()
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
                
                # Customer Commands
                "SEARCH_CUSTOMERS": self.search_customers,
                "CREATE_CUSTOMER": self.create_customer,
                
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
                
                # Report Commands
                "GET_JOB_PROFIT": self.get_job_profit,
            }
            
            if command not in command_map:
                return {
                    "success": False,
                    "error": f"Unknown command: {command}",
                    "output": f"[ERROR] Command '{command}' not recognized"
                }
            
            # Execute the command
            result = command_map[command](**params)
            
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
        """Get vendor's work bill"""
        vendor_name = self.resolve_vendor(vendor_name)
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

                    # For work bills, job is optional (can be empty for general labor)
                    # The MCP server doesn't require job for add_days
                    formatted_day = {
                        "day": day,
                        "qty": day_qty,
                        "item": day_item or kwargs.get('item', 'Labor')
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
            return f"[OK] Bill updated\n{result.get('bill', '')}"
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

            for bill in bills:
                vendor_name = bill.get('vendor_name', 'Unknown')
                bill_amount = bill.get('amount_due', 0.0)

                if vendor_name not in vendor_data:
                    vendor_data[vendor_name] = {'total': 0, 'items': {}}

                vendor_data[vendor_name]['total'] += bill_amount
                grand_total += bill_amount

                # Process line items
                for line in bill.get('line_items', []):
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

            # Format output (40 chars wide)
            lines = []
            lines.append("WORK WEEK SUMMARY")
            lines.append(f"Week: {week_str}")
            lines.append("=" * 40)
            lines.append("")

            if not vendor_data:
                lines.append("No bills found for this week")
                return "\n".join(lines)

            # VENDOR TOTALS section
            lines.append("VENDOR TOTALS:")
            lines.append("-" * 40)

            for vendor in sorted(vendor_data.keys()):
                vdata = vendor_data[vendor]
                # Vendor name and total
                vendor_line = vendor[:30]
                amount_str = f"${vdata['total']:,.2f}"
                spaces = 40 - len(vendor_line) - len(amount_str)
                lines.append(f"{vendor_line}{' ' * spaces}{amount_str}")

                # Item breakdown for this vendor
                for item in sorted(vdata['items'].keys()):
                    item_amount = vdata['items'][item]
                    item_line = f"  {item[:28]}"
                    amount_str = f"${item_amount:,.2f}"
                    spaces = 40 - len(item_line) - len(amount_str)
                    lines.append(f"{item_line}{' ' * spaces}{amount_str}")

                lines.append("")  # Blank line between vendors

            lines.append("-" * 40)
            total_line = "TOTAL"
            amount_str = f"${grand_total:,.2f}"
            spaces = 40 - len(total_line) - len(amount_str)
            lines.append(f"{total_line}{' ' * spaces}{amount_str}")
            lines.append("")
            lines.append("=" * 40)
            lines.append("")

            # ITEM TOTALS section
            lines.append("ITEM TOTALS:")
            lines.append("-" * 40)

            for item in sorted(item_data.keys()):
                idata = item_data[item]
                # Item name and total
                item_line = item[:30]
                amount_str = f"${idata['total']:,.2f}"
                spaces = 40 - len(item_line) - len(amount_str)
                lines.append(f"{item_line}{' ' * spaces}{amount_str}")

                # Job breakdown for this item
                for job in sorted(idata['jobs'].keys()):
                    job_amount = idata['jobs'][job]
                    job_line = f"  {job[:28]}"
                    amount_str = f"${job_amount:,.2f}"
                    spaces = 40 - len(job_line) - len(amount_str)
                    lines.append(f"{job_line}{' ' * spaces}{amount_str}")

                lines.append("")  # Blank line between items

            lines.append("-" * 40)
            total_line = "TOTAL"
            amount_str = f"${grand_total:,.2f}"
            spaces = 40 - len(total_line) - len(amount_str)
            lines.append(f"{total_line}{' ' * spaces}{amount_str}")
            lines.append("")
            lines.append("=" * 40)
            lines.append("")

            # JOB TOTALS section
            lines.append("JOB TOTALS:")
            lines.append("-" * 40)

            for job in sorted(job_totals.keys()):
                job_line = job[:30]
                amount_str = f"${job_totals[job]:,.2f}"
                spaces = 40 - len(job_line) - len(amount_str)
                lines.append(f"{job_line}{' ' * spaces}{amount_str}")

            lines.append("-" * 40)
            total_line = "TOTAL"
            amount_str = f"${grand_total:,.2f}"
            spaces = 40 - len(total_line) - len(amount_str)
            lines.append(f"{total_line}{' ' * spaces}{amount_str}")

            return "\n".join(lines)

        except Exception as e:
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
    
    # Customer Methods
    def search_customers(self, search_term: str = None, active_only: bool = True, 
                        jobs_only: bool = False) -> str:
        """Search for customers"""
        # Use get_all_customers since search_customers doesn't exist
        customers = self.customer_repo.get_all_customers(include_jobs=not jobs_only)
        
        # Filter by search term if provided
        if search_term and customers:
            search_lower = search_term.lower()
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
    def create_check(self, payee: str, amount: float, **kwargs) -> str:
        """Create a check"""
        try:
            check_id = self.check_repo.create_check(payee, amount, **kwargs)
            return f"[OK] Check created for {payee}: ${amount:.2f} (ID: {check_id})"
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
            result += f"  Amount: ${check.get('amount', 0):.2f}\n\n"
        
        return result
    
    def update_check(self, check_id: str, **kwargs) -> str:
        """Update check information"""
        try:
            result = self.check_repo.update_check(check_id, **kwargs)
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
    
    def get_checks_this_week(self) -> str:
        """Get checks from current week"""
        try:
            # Use search_checks with date filter for this week
            from datetime import datetime, timedelta
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            checks = self.check_repo.search_checks(
                date_from=week_start.strftime('%Y-%m-%d'),
                date_to=today.strftime('%Y-%m-%d')
            )
            if not checks:
                return "[OK] No checks this week"
            
            result = f"[OK] {len(checks)} checks this week\n\n"
            for check in checks:
                result += f"- {check.get('payee_name')}: ${check.get('amount', 0):.2f}\n"
            
            return result
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    # Invoice Methods (simplified examples)
    def search_invoices(self, **kwargs) -> str:
        """Search for invoices"""
        try:
            invoices = self.invoice_repo.search_invoices(**kwargs)
            if not invoices:
                return "[NOT FOUND] No invoices found"
            
            result = f"[OK] Found {len(invoices)} invoices\n"
            for inv in invoices[:10]:
                result += f"- Invoice #{inv.get('ref_number')}: ${inv.get('total', 0):.2f}\n"
            
            return result
        except Exception as e:
            return f"[ERROR] {str(e)}"
    
    def get_invoices_this_week(self) -> str:
        """Get invoices from current week"""
        try:
            # Use search_invoices with date filter for this week
            from datetime import datetime, timedelta
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            invoices = self.invoice_repo.search_invoices(
                date_from=week_start.strftime('%Y-%m-%d'),
                date_to=today.strftime('%Y-%m-%d')
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
            
            # Create the bill payment
            result = self.payment_repo.create_bill_payment(
                vendor_list_id=vendor['list_id'],
                bill_txn_id=unpaid_bill['txn_id'],
                amount=amount,
                bank_account_list_id=bank_account_id,
                payment_method=kwargs.get('payment_method', 'Check'),
                check_number=kwargs.get('check_number'),
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
    
    # Report Methods
    def get_job_profit(self, job_name: str, **kwargs) -> str:
        """Get job profitability report"""
        try:
            # Generate the report
            report = self.job_profit_repo.generate_job_report(job_name)
            
            if report.get('status') == 'error':
                return f"[ERROR] {report.get('error_message', 'Failed to generate report')}"
            
            # Format the output with right-justified amounts (40 char width)
            output = []
            output.append(f"\nJOB PROFITABILITY BY ITEM")
            output.append(f"Job: {report.get('job_name', job_name)}")
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
            
            return "\n".join(output)
            
        except Exception as e:
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