"""
Work Bill Formatter - Formats vendor work week bills for display
Adapted from anyqbcli project for MCP server
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class WorkBillFormatter:
    """Formats work bills for clean text display"""
    
    def __init__(self, width: int = 30):
        self.width = width
        self.separator = "-" * (self.width - 2)  # Leave space for leading space
    
    def format_work_bill(self, bill_data: Dict[str, Any], vendor_ref: Dict[str, Any] = None, daily_cost: float = None) -> str:
        """Format complete work bill from MCP response data"""
        lines = []
        
        # Header
        lines.append("WORK BILL")
        
        # Vendor name - truncate if needed
        vendor_name = (vendor_ref.get('Name') if vendor_ref else None) or bill_data.get('vendor_name') or bill_data.get('vendor') or bill_data.get('VendorRef_FullName', 'Unknown')
        vendor_name = vendor_name.lower()
        if len(vendor_name) > self.width - 1:
            vendor_name = vendor_name[:self.width - 4] + "..."
        lines.append(f" {vendor_name}")
        
        # Reference (week range)
        week = bill_data.get('week', {})
        ref = week.get('display', bill_data.get('ref_number', bill_data.get('RefNumber', '')))
        if len(ref) > self.width - 6:  # " Ref: " is 6 chars
            ref = ref[:self.width - 9] + "..."
        lines.append(f" Ref: {ref}")
        
        # Transaction ID if exists
        txn_id = bill_data.get('txn_id', bill_data.get('TxnID'))
        if txn_id:
            txn_line = f" TxnID: {txn_id}"
            if len(txn_line) > self.width:
                txn_line = txn_line[:self.width - 3] + "..."
            lines.append(txn_line)
        
        # Daily cost - use the passed-in value or extract from bill
        if daily_cost is None:
            daily_cost = 0.0
        lines.append(f" Daily Cost: ${daily_cost:.2f}")
        
        # Total
        total = bill_data.get('amount', bill_data.get('amount_due', bill_data.get('AmountDue', 0)))
        lines.append(f" Total: ${total:.2f}")
        
        # OpenAmount (Vendor's total balance across ALL bills in QuickBooks)
        open_amount = bill_data.get('open_amount')
        if open_amount is not None:
            lines.append(f" Vendor Balance (all bills): ${open_amount:.2f}")
        
        # Line items - sort by day to keep same day items together
        line_items = bill_data.get('line_items', [])
        if line_items:
            # Define day order
            day_order = {'monday': 1, 'tuesday': 2, 'wednesday': 3, 'thursday': 4, 'friday': 5, 'saturday': 6, 'sunday': 7}
            
            # Sort line items by day - also sort by TxnLineID within same day for consistency
            sorted_items = sorted(line_items, key=lambda x: (
                day_order.get(x.get('day', '').lower(), 99),
                x.get('TxnLineID', '')
            ))
            
            lines.append("")
            lines.append(" LINE ITEMS:")
            lines.append(f" {self.separator}")
            
            # Track the previous day to know when to add separator
            # Also track no work days for the job summary
            previous_day = None
            no_work_days = []
            
            for i, item in enumerate(sorted_items):
                current_day = item.get('day', '').lower()
                
                # Check if this is a no work day (0 quantity with "no work provided" item)
                item_name = item.get('item_name', item.get('item', '')).lower()
                quantity = item.get('quantity', 0)
                if 'no work provided' in item_name and quantity == 0:
                    # Extract day abbreviation from description
                    desc = item.get('description', '')
                    day_abbrev = desc[:3] if len(desc) >= 3 else current_day[:3]
                    if day_abbrev and day_abbrev not in no_work_days:
                        no_work_days.append(day_abbrev)
                
                # Add separator between different days (but not before first item)
                if previous_day is not None and previous_day != current_day:
                    lines.append(f" {self.separator}")
                elif previous_day is not None and previous_day == current_day:
                    # Add blank line between items of the same day
                    lines.append("")
                
                lines.extend(self._format_line_item(item))
                
                # If not the same day as next item, we'll add separator next iteration
                previous_day = current_day
            
            # Store no_work_days in bill_data for job summary
            bill_data['_no_work_days'] = no_work_days
            
            # Add final separator after all items
            lines.append(f" {self.separator}")
        
        # Get payment info early for use in job summary
        payment_info = bill_data.get('payment_info', {})
        payments = payment_info.get('payments', []) if payment_info else []
        bill_total = bill_data.get('amount', bill_data.get('AmountDue', bill_data.get('total_amount', 0)))
        amount_paid = payment_info.get('amount_paid', 0) if payment_info else 0
        remaining_balance = bill_total - amount_paid
        
        # Job summary
        job_summary = bill_data.get('job_summary', {})
        if job_summary:
            lines.append("")
            lines.append(" JOB SUMMARY:")
            lines.append(f" {self.separator}")
            
            for job, amount in job_summary.items():
                lines.append(self._format_job_summary_line(job, amount, bill_data.get('_no_work_days', [])))
            
            lines.append(f" {self.separator}")
            lines.append(self._format_total_line(total))
            
            if payments:
                for payment in payments:
                    pay_amount = payment.get('amount_paid', payment.get('amount', 0))
                    pay_date = payment.get('payment_date', '')
                    
                    # Format date as MM-DD-YYYY
                    if pay_date:
                        try:
                            date_str = str(pay_date)
                            # Handle datetime string with timezone (e.g., "2025-08-25 00:00:00+00:00")
                            if '+' in date_str or 'T' in date_str:
                                date_str = date_str.split('+')[0].split('T')[0].strip()
                            elif ' ' in date_str:
                                date_str = date_str.split(' ')[0]  # Take date part only
                            
                            if '-' in date_str and date_str.index('-') == 4:
                                # YYYY-MM-DD format
                                dt = datetime.strptime(date_str, '%Y-%m-%d')
                                formatted_date = dt.strftime("%m-%d-%Y")
                            else:
                                formatted_date = date_str
                        except:
                            formatted_date = str(pay_date)[:10] if pay_date else ''
                    else:
                        formatted_date = ''
                    
                    # Format payment line - align amount like TOTAL line
                    label = f"PAYMENT: {formatted_date}"
                    amount_str = f"-${pay_amount:.2f}"
                    spaces_needed = self.width - len(f" {label}") - len(amount_str)
                    if spaces_needed > 0:
                        payment_line = f" {label}{' ' * spaces_needed}{amount_str}"
                    else:
                        payment_line = f" {label} {amount_str}"[:self.width]
                    lines.append(payment_line)
            elif payment_info.get('amount_paid', 0) > 0:
                # Single payment info (old format)
                pay_amount = payment_info.get('amount_paid', 0)
                pay_date = payment_info.get('payment_date', '')
                
                # Format date as MM-DD-YYYY
                if pay_date:
                    try:
                        date_str = str(pay_date)
                        # Handle datetime string with timezone (e.g., "2025-08-25 00:00:00+00:00")
                        if '+' in date_str or 'T' in date_str:
                            date_str = date_str.split('+')[0].split('T')[0].strip()
                        elif ' ' in date_str:
                            date_str = date_str.split(' ')[0]  # Take date part only
                        
                        if '-' in date_str and date_str.index('-') == 4:
                            # YYYY-MM-DD format
                            dt = datetime.strptime(date_str, '%Y-%m-%d')
                            formatted_date = dt.strftime("%m-%d-%Y")
                        else:
                            formatted_date = date_str
                    except Exception as e:
                        formatted_date = str(pay_date)[:10] if pay_date else ''
                else:
                    formatted_date = ''
                
                # Format payment line - align amount like TOTAL line
                label = f"PAYMENT: {formatted_date}"
                amount_str = f"-${pay_amount:.2f}"
                spaces_needed = self.width - len(f" {label}") - len(amount_str)
                if spaces_needed > 0:
                    payment_line = f" {label}{' ' * spaces_needed}{amount_str}"
                else:
                    payment_line = f" {label} {amount_str}"[:self.width]
                lines.append(payment_line)
            
            # Show balance - align amount like TOTAL line
            lines.append(f" {self.separator}")
            label = "BALANCE:"
            amount_str = f"${remaining_balance:.2f}"
            spaces_needed = self.width - len(f" {label}") - len(amount_str)
            if spaces_needed > 0:
                balance_line = f" {label}{' ' * spaces_needed}{amount_str}"
            else:
                balance_line = f" {label} {amount_str}"[:self.width]
            lines.append(balance_line)
        
        # Status and payment info
        is_paid = bill_data.get('IsPaid', False)
        
        lines.append("")
        # Show appropriate status based on actual payment status
        if is_paid and amount_paid > 0:
            # Fully paid with payment details
            lines.append(f" Status: [PAID]")
            lines.append(f" Bill Total: ${bill_total:.2f}")
            
            # Show payment details if available
            if payments:
                lines.append("")
                lines.append(" PAYMENTS:")
                for payment in payments:
                    # Payment amount
                    pay_amount = payment.get('amount_paid', payment.get('amount', 0))
                    amount_line = f" Amount: ${pay_amount:.2f}"
                    if len(amount_line) > self.width:
                        amount_line = amount_line[:self.width]
                    lines.append(amount_line)
                    
                    # Payment date
                    pay_date = payment.get('payment_date')
                    if pay_date:
                        try:
                            date_str = str(pay_date)
                            # Handle various date formats
                            # Remove timezone info if present (e.g., "2025-08-25 00:00:00+00:00")
                            if '+' in date_str or 'T' in date_str:
                                date_str = date_str.split('+')[0].split('T')[0].strip()
                            elif ' ' in date_str:
                                date_str = date_str.split(' ')[0]  # Take date part only
                            
                            if '-' in date_str and date_str.index('-') == 4:
                                # YYYY-MM-DD format
                                dt = datetime.strptime(date_str, '%Y-%m-%d')
                                formatted_date = dt.strftime("%m-%d-%Y")
                            elif '/' in date_str:
                                # Already in MM/DD/YYYY or similar format
                                formatted_date = date_str
                            else:
                                formatted_date = date_str
                            date_line = f" Date: {formatted_date}"
                            if len(date_line) > self.width:
                                date_line = date_line[:self.width]
                            lines.append(date_line)
                        except Exception as e:
                            # Fallback: show raw date
                            if pay_date:
                                date_line = f" Date: {pay_date}"
                                if len(date_line) > self.width:
                                    date_line = date_line[:self.width]
                                lines.append(date_line)
                    
                    # Bank account
                    bank = payment.get('bank_account', 'Unknown')
                    if bank and bank != 'Unknown Account':
                        bank_line = f" From: {bank}"
                        if len(bank_line) > self.width:
                            bank_line = bank_line[:self.width - 3] + "..."
                        lines.append(bank_line)
                    
                    # Check number
                    check_num = payment.get('check_number')
                    if check_num:
                        check_line = f" Check #: {check_num}"
                        if len(check_line) > self.width:
                            check_line = check_line[:self.width]
                        lines.append(check_line)
                    
                    # Payment TxnID
                    pay_txn = payment.get('payment_txn_id')
                    if pay_txn:
                        txn_line = f" TxnID: {pay_txn}"
                        if len(txn_line) > self.width:
                            txn_line = txn_line[:self.width - 3] + "..."
                        lines.append(txn_line)
                
                # Show balance after all payments
                lines.append("")
                lines.append(f" Balance: ${remaining_balance:.2f}")
                        
            elif payment_info:
                # Single payment - show inline as before
                # Show bank account if available
                bank_account = payment_info.get('bank_account')
                if bank_account and bank_account != "Unknown Account":
                    lines.append(f" Paid from: {bank_account}")
                
                # Show payment date if available
                payment_date = payment_info.get('payment_date')
                if payment_date:
                    # Format date nicely
                    try:
                        from datetime import datetime
                        if isinstance(payment_date, str) and payment_date:
                            # Try to parse and format the date
                            if 'T' in payment_date:
                                # ISO format
                                dt = datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
                                formatted_date = dt.strftime("%m-%d-%Y")
                            else:
                                # Might already be formatted or other format
                                formatted_date = payment_date[:10] if len(payment_date) > 10 else payment_date
                            lines.append(f" Payment Date: {formatted_date}")
                        else:
                            lines.append(f" Payment Date: {payment_date}")
                    except:
                        # If parsing fails, just use the raw value
                        if payment_date:
                            lines.append(f" Payment Date: {payment_date}")
                
                # Show check number if available
                check_number = payment_info.get('check_number')
                if check_number:
                    lines.append(f" Check #: {check_number}")
                
                # Show payment transaction ID
                payment_txn_id = payment_info.get('payment_txn_id')
                if payment_txn_id:
                    lines.append(f" Payment TxnID: {payment_txn_id}")
                elif payment_info.get('payment_txn_ids'):
                    # Fallback to old format if new format not available
                    payment_txn_ids = payment_info.get('payment_txn_ids', [])
                    if payment_txn_ids:
                        lines.append(f" Payment TxnID: {payment_txn_ids[0]}")
                
                # Note about unknown account if we couldn't get bank info
                if (not bank_account or bank_account == "Unknown Account") and is_paid:
                    lines.append(" [!] Bank account information unavailable")
                
                # Show balance
                lines.append("")
                lines.append(f" Balance: ${remaining_balance:.2f}")
        elif is_paid and amount_paid == 0:
            # Marked as paid but no payment details available
            lines.append(f" Status: [PAID]")
            lines.append(f" Bill Total: ${bill_total:.2f}")
            lines.append(" [!] Payment details not available")
            lines.append("")
            lines.append(f" Balance: $0.00")
        elif amount_paid > 0 and remaining_balance > 0.01:
            # Partial payment
            lines.append(f" Status: [PARTIAL PAYMENT]")
            lines.append(f" Bill Total: ${bill_total:.2f}")
            
            # Show payment details for partial payments too
            if payments:
                for payment in payments:
                    lines.append("")
                    
                    # Payment amount
                    pay_amount = payment.get('amount_paid', payment.get('amount', 0))
                    amount_line = f" Amount: ${pay_amount:.2f}"
                    if len(amount_line) > self.width:
                        amount_line = amount_line[:self.width]
                    lines.append(amount_line)
                    
                    # Payment date
                    pay_date = payment.get('payment_date')
                    if pay_date:
                        try:
                            if isinstance(pay_date, str) and 'T' in pay_date:
                                dt = datetime.fromisoformat(pay_date.replace('Z', '+00:00'))
                                formatted_date = dt.strftime("%m-%d-%Y")
                            else:
                                formatted_date = str(pay_date)[:10] if len(str(pay_date)) > 10 else str(pay_date)
                            date_line = f" Date: {formatted_date}"
                            if len(date_line) > self.width:
                                date_line = date_line[:self.width]
                            lines.append(date_line)
                        except:
                            if pay_date:
                                date_line = f" Date: {pay_date}"
                                if len(date_line) > self.width:
                                    date_line = date_line[:self.width]
                                lines.append(date_line)
                    
                    # Bank account
                    bank = payment.get('bank_account', 'Unknown')
                    if bank and bank != 'Unknown Account':
                        bank_line = f" From: {bank}"
                        if len(bank_line) > self.width:
                            bank_line = bank_line[:self.width - 3] + "..."
                        lines.append(bank_line)
                    
                    # Check number
                    check_num = payment.get('check_number')
                    if check_num:
                        check_line = f" Check #: {check_num}"
                        if len(check_line) > self.width:
                            check_line = check_line[:self.width]
                        lines.append(check_line)
                    
                    # Payment TxnID
                    pay_txn = payment.get('payment_txn_id')
                    if pay_txn:
                        txn_line = f" TxnID: {pay_txn}"
                        if len(txn_line) > self.width:
                            txn_line = txn_line[:self.width - 3] + "..."
                        lines.append(txn_line)
            
            # Show balance after partial payments
            lines.append("")
            lines.append(f" Balance: ${remaining_balance:.2f}")
        else:
            # Check if there are actually payments even though IsPaid is False
            if amount_paid > 0 and remaining_balance < 0.01:
                # Has payments that fully cover the bill
                lines.append(f" Status: [PAID]")
            else:
                # Truly unpaid
                lines.append(f" Status: [UNPAID]")
            lines.append(f" Bill Total: ${bill_total:.2f}")
            lines.append("")
            lines.append(f" Balance: ${remaining_balance:.2f}")  # Use calculated balance, not bill_total
        
        # Validation messages if any
        validation = bill_data.get('validation', {})
        errors = validation.get('errors', [])
        warnings = validation.get('warnings', [])
        
        if errors:
            lines.append("")
            lines.append(" ERRORS:")
            for error in errors:
                lines.append(f" - {error}")
        
        if warnings:
            lines.append("")
            lines.append(" WARNINGS:")
            for warning in warnings:
                lines.append(f" - {warning}")
        
        return "\n".join(lines)
    
    def _format_line_item(self, item: Dict[str, Any]) -> List[str]:
        """Format a single line item"""
        lines = []
        
        # Line 1: Description field (contains day, date, and any line memo)
        desc_str = item.get('description', item.get('Desc', item.get('desc', '')))
        
        if desc_str:
            # Just display the description as-is
            # It already contains: "day. MM/DD/YY [optional line memo]"
            if len(desc_str) > self.width - 1:
                desc_str = desc_str[:self.width - 4] + "..."
            lines.append(f" {desc_str}")
        else:
            lines.append(" unknown date")
        
        # Line 2: Item name
        item_name = item.get('item') or item.get('item_name') or item.get('ItemRef_FullName', 'Unknown Item')
        if len(item_name) > self.width - 1:
            item_name = item_name[:self.width - 4] + "..."
        lines.append(f" {item_name}")
        
        # Line 3: Customer:Job
        customer_job = item.get('customer') or item.get('customer_name') or item.get('CustomerRef_FullName', '')
        if customer_job:
            if len(customer_job) > self.width - 1:
                customer_job = customer_job[:self.width - 4] + "..."
            lines.append(f" {customer_job}")
        else:
            lines.append(" No job assigned")
        
        # Line 4: Qty x Cost = Amount with billable indicator
        qty = float(item.get('quantity', item.get('Quantity', 1.0)))
        cost = float(item.get('cost', item.get('Cost', 0.0)))
        amount = float(item.get('amount', item.get('Amount', 0.0)))
        
        # Check billable status from QuickBooks
        # BillableStatus values:
        # 0 = Billable
        # 1 = Not Billable
        # 2 = Has Been Billed
        billable = item.get('billable', item.get('BillableStatus', None))
        
        billable_marker = ""
        if billable is not None:
            if billable == 0:
                billable_marker = " [B]"  # Billable
            elif billable == 1:
                billable_marker = " [NB]"  # Not Billable
            elif billable == 2:
                billable_marker = " [BILLED]"  # Has been billed
        
        # Always show qty x cost = amount format with billable marker
        qty_cost_total_line = f" {qty:.2f} x ${cost:.2f} = ${amount:.2f}{billable_marker}"
        if len(qty_cost_total_line) > self.width:
            # If too long, use shorter format
            qty_cost_total_line = f" {qty:.1f}x${cost:.0f}=${amount:.2f}{billable_marker}"
        lines.append(qty_cost_total_line)
        
        return lines
    
    def _format_job_summary_line(self, job: str, amount: float, no_work_days: list = None) -> str:
        """Format a job summary line"""
        # Special handling for no work items (0 amount with no job)
        if not job and amount == 0:
            if no_work_days:
                # Format as "No work provided: wed" or "No work provided: mon, wed"
                days_str = ", ".join(no_work_days)
                job = f"No work provided: {days_str}"
            else:
                job = "No work provided"
        else:
            job = job or "Unknown"  # Handle other None job cases
        amount_str = f"${amount:.2f}"
        
        # Truncate job name if needed
        max_job_len = self.width - len(amount_str) - 2  # 2 for spaces
        if len(job) > max_job_len:
            job = job[:max_job_len - 3] + "..."
        
        # Right-align amount
        spaces_needed = self.width - len(f" {job}") - len(amount_str)
        if spaces_needed > 0:
            return f" {job}{' ' * spaces_needed}{amount_str}"
        else:
            return f" {job} {amount_str}"[:self.width]
    
    def _format_total_line(self, total: float) -> str:
        """Format the total line"""
        label = "TOTAL:"
        amount_str = f"${total:.2f}"
        
        spaces_needed = self.width - len(f" {label}") - len(amount_str)
        if spaces_needed > 0:
            return f" {label}{' ' * spaces_needed}{amount_str}"
        else:
            return f" {label} {amount_str}"[:self.width]
    
    def format_work_bill_list(self, bills: List[Dict[str, Any]]) -> str:
        """Format a list of work bills for display"""
        if not bills:
            return "No work bills found"
        
        lines = []
        lines.append("WORK BILLS")
        lines.append("=" * self.width)
        
        for i, bill in enumerate(bills, 1):
            vendor = bill.get('vendor', 'Unknown')[:20]
            total = bill.get('total_amount', 0)
            total_str = f"${total:.2f}"
            days = len(bill.get('line_items', []))
            
            lines.append(f"{i}. {vendor}")
            lines.append(f"   {days} days - {total_str}")
            lines.append("")
        
        lines.append(f"Total bills: {len(bills)}")
        
        return "\n".join(lines)
    
    def format_week_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format comprehensive weekly summary"""
        lines = []
        width = 50
        
        lines.append("=" * width)
        lines.append("WORK WEEK SUMMARY")
        lines.append("=" * width)
        
        # Week info
        week = summary_data.get('week', {})
        date_range = week.get('display', '')
        lines.append(f"Week: {date_range}")
        lines.append("")
        
        # Vendor totals section
        lines.append("VENDOR TOTALS:")
        lines.append("-" * 30)
        
        vendor_totals = summary_data.get('vendor_totals', {})
        for vendor in sorted(vendor_totals.keys()):
            amount = vendor_totals[vendor]
            vendor_display = vendor[:20] if len(vendor) > 20 else vendor
            amount_str = f"${amount:,.2f}"
            spaces = 30 - len(vendor_display) - len(amount_str)
            lines.append(f"{vendor_display}{' ' * spaces}{amount_str}")
        
        lines.append("-" * 30)
        grand_total = summary_data.get('grand_total', 0)
        total_str = f"${grand_total:,.2f}"
        spaces = 30 - len("TOTAL:") - len(total_str)
        lines.append(f"TOTAL:{' ' * spaces}{total_str}")
        
        # Job totals section
        job_totals = summary_data.get('job_totals', {})
        if job_totals:
            lines.append("")
            lines.append("JOB TOTALS:")
            lines.append("-" * 30)
            
            # Sort jobs by amount descending
            sorted_jobs = sorted(job_totals.items(), key=lambda x: x[1], reverse=True)
            for job, amount in sorted_jobs:
                # Parse job name to show cleaner format
                if ':' in job:
                    customer, job_name = job.split(':', 1)
                    display_name = job_name[:20]
                else:
                    display_name = job[:20]
                
                amount_str = f"${amount:,.2f}"
                spaces = 30 - len(display_name) - len(amount_str)
                lines.append(f"{display_name}{' ' * spaces}{amount_str}")
            
            lines.append("-" * 30)
            job_total = sum(job_totals.values())
            job_total_str = f"${job_total:,.2f}"
            spaces = 30 - len("TOTAL:") - len(job_total_str)
            lines.append(f"TOTAL:{' ' * spaces}{job_total_str}")
        
        # Vendor per Job breakdown
        vendor_job_breakdown = summary_data.get('vendor_job_breakdown', {})
        if vendor_job_breakdown:
            lines.append("")
            lines.append("VENDOR PER JOB:")
            lines.append("-" * 30)
            
            # Sort jobs by total amount descending
            sorted_jobs_breakdown = sorted(
                vendor_job_breakdown.items(), 
                key=lambda x: sum(x[1].values()), 
                reverse=True
            )
            
            for job, vendors in sorted_jobs_breakdown:
                # Parse job name for cleaner display
                if ':' in job:
                    customer, job_name = job.split(':', 1)
                    display_job = job_name[:20]
                else:
                    display_job = job[:20]
                
                # Show job header
                job_total_amount = sum(vendors.values())
                lines.append(f"{display_job}: ${job_total_amount:,.2f}")
                
                # Show each vendor for this job
                for vendor, amount in sorted(vendors.items(), key=lambda x: x[1], reverse=True):
                    vendor_display = vendor[:17] if len(vendor) > 17 else vendor
                    amount_str = f"${amount:,.2f}"
                    spaces = 28 - len(vendor_display) - len(amount_str)
                    lines.append(f"  {vendor_display}{' ' * spaces}{amount_str}")
        
        lines.append("")
        bill_count = summary_data.get('bill_count', 0)
        lines.append(f"Bills Found: {bill_count}")
        lines.append("=" * width)
        
        return "\n".join(lines)
    
    def format_work_bill_preview(self, bill: Dict[str, Any]) -> str:
        """Format a brief preview of work bill"""
        lines = []
        
        vendor = bill.get('vendor', 'Unknown')[:25]
        week = bill.get('week', {})
        ref = week.get('display', bill.get('ref_number', ''))
        days = len(bill.get('line_items', []))
        total = bill.get('total_amount', 0)
        status = bill.get('status', 'pending')
        
        lines.append(f"Work Bill: {vendor}")
        lines.append(f"Week: {ref}")
        lines.append(f"Days: {days}")
        lines.append(f"Total: ${total:.2f}")
        lines.append(f"Status: {status.upper()}")
        
        return "\n".join(lines)