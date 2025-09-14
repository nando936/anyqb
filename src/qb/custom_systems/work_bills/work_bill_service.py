"""
Work Bill Service - Custom business logic for work week bills
Uses BillRepository for QB operations per architecture plan
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from quickbooks_standard.entities.bills.bill_repository import BillRepository
from quickbooks_standard.entities.vendors.vendor_repository import VendorRepository
from quickbooks_standard.entities.items.item_repository import ItemRepository
from quickbooks_standard.entities.customers.customer_repository import CustomerRepository
from shared_utilities.work_bill_formatter import WorkBillFormatter

logger = logging.getLogger(__name__)

class WorkBillService:
    """Manages work week bills with custom business logic"""
    
    def __init__(self):
        """Initialize work bill service"""
        self.bill_repo = BillRepository()  # Use standard repository per architecture
        self.vendor_repo = VendorRepository()
        self.item_repo = ItemRepository()
        self.customer_repo = CustomerRepository()
        self.formatter = WorkBillFormatter(width=40)
        self.work_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    def get_work_bill(self, vendor_name: Optional[str] = None, ref_number: Optional[str] = None, week: Optional[str] = None) -> Dict:
        """Get work bill for vendor using BillRepository
        
        Args:
            vendor_name: Name of the vendor (optional if ref_number provided)
            ref_number: Optional specific bill reference number (can be used alone)
            week: Optional week selector - 'current', 'last', 'next' or numeric (-2, -1, 0, 1, 2)
        """
        try:
            logger.info(f"get_work_bill called with vendor_name={vendor_name}, ref_number={ref_number}, week={week}")
            
            # If only ref_number provided, search by ref_number
            if ref_number and not vendor_name:
                bills = self.bill_repo.search_by_ref_number(ref_number, include_line_items=True)
                if bills:
                    # Found bill(s) by ref number - format and return directly
                    target_bill = bills[0]  # Take first match
                    vendor_name = target_bill.get('vendor_name', 'Unknown')
                    logger.info(f"Found bill with ref {ref_number} for vendor {vendor_name}")
                    
                    # Format the bill
                    formatted_output = self.formatter.format_work_bill(target_bill)
                    return {
                        'success': True,
                        'bill': formatted_output
                    }
                else:
                    return {
                        'success': True,
                        'bill': f"No bill found with ref number {ref_number}"
                    }
            
            # Original logic with vendor name
            if vendor_name:
                # Resolve vendor alias first
                import sys
                if 'shared_utilities.vendor_aliases' in sys.modules:
                    del sys.modules['shared_utilities.vendor_aliases']
                from shared_utilities.vendor_aliases import resolve_vendor_alias
                original_name = vendor_name
                vendor_name = resolve_vendor_alias(vendor_name)
                logger.info(f"Vendor alias check: '{original_name}' -> '{vendor_name}' (changed: {original_name != vendor_name})")
                
                # CRITICAL FIX: Use fuzzy matching to find the exact vendor name in QuickBooks
                # This ensures we use the correct vendor name when querying for bills
                vendor = self.vendor_repo.find_vendor_fuzzy(vendor_name)
                if vendor:
                    actual_vendor_name = vendor['name']
                    logger.info(f"Fuzzy match found: '{vendor_name}' -> '{actual_vendor_name}'")
                    vendor_name = actual_vendor_name
                else:
                    logger.warning(f"No vendor found matching '{vendor_name}' - using as-is")
            
            # Get bills from repository (proper architecture)
            bills = self.bill_repo.find_bills_by_vendor(vendor_name, include_line_items=True) if vendor_name else []
            logger.info(f"Found {len(bills) if bills else 0} bills")
            
            if not bills:
                week_desc = self._get_week_description(week) if week else "this week"
                return {
                    'success': True,
                    'bill': f"No bill found for {vendor_name}" + 
                           (f" with ref {ref_number}" if ref_number else f" for {week_desc}")
                }
            
            # Apply custom business logic to find the right bill
            target_bill = None
            
            if ref_number:
                # Find specific bill by ref number
                for bill in bills:
                    if bill.get('ref_number') == ref_number:
                        target_bill = bill
                        break
            elif week:
                # Find bill for specified week
                week_dates = self._calculate_week_dates(week)
                if not week_dates:
                    return {
                        'success': False,
                        'error': f"Invalid week parameter: {week}. Use 'current', 'last', 'next' or numeric like -1, 0, 1"
                    }
                
                monday = week_dates['monday']
                saturday = week_dates['saturday']
                
                logger.info(f"Looking for bill between {monday.strftime('%m/%d/%Y')} and {saturday.strftime('%m/%d/%Y')}")
                
                # Check each bill to see if it falls in this week
                for bill in bills:
                    bill_date_str = bill.get('txn_date')
                    if bill_date_str:
                        try:
                            # Parse bill date - handle timezone info if present
                            if ' ' in str(bill_date_str):
                                # Has timezone info like "2025-08-25 00:00:00+00:00"
                                bill_date_str = str(bill_date_str).split(' ')[0]
                            
                            bill_date = datetime.strptime(bill_date_str, '%Y-%m-%d')
                            # Check if bill date falls within the week
                            if monday.date() <= bill_date.date() <= saturday.date():
                                target_bill = bill
                                logger.info(f"Found bill dated {bill_date_str} for week {week}")
                                break
                        except Exception as e:
                            logger.error(f"Error parsing bill date {bill_date_str}: {e}")
                            continue
            else:
                # Look for current week's bill
                today = datetime.now()
                days_since_monday = today.weekday()
                current_monday = today - timedelta(days=days_since_monday)
                current_saturday = current_monday + timedelta(days=5)
                week_str = f"{current_monday.strftime('%m/%d/%y')} - {current_saturday.strftime('%m/%d/%y')}"
                week_ref = f"{vendor_name.lower()}_{current_monday.strftime('%m%d%y')}"
                
                # Check each bill for current week
                for bill in bills:
                    memo = bill.get('memo')
                    if memo is None:
                        memo = ''
                    ref = bill.get('ref_number')
                    if ref is None:
                        ref = ''
                    
                    # Check if this is current week's bill
                    try:
                        if week_str in memo or (ref and (week_ref in ref or current_monday.strftime('%m%d%y') in ref)):
                            target_bill = bill
                            break
                    except TypeError as e:
                        logger.error(f"Type error checking bill: memo={memo}, ref={ref}, error={e}")
                        continue
            
            # No fallback - if we didn't find a bill, return error
            if not target_bill:
                if ref_number:
                    return {
                        'success': True,
                        'bill': f"No bill found for {vendor_name} with ref {ref_number}"
                    }
                elif week:
                    week_desc = self._get_week_description(week)
                    return {
                        'success': True,
                        'bill': f"No bill found for {vendor_name} for {week_desc}"
                    }
                else:
                    return {
                        'success': True,
                        'bill': f"No bill found for {vendor_name} for current week"
                    }
            
            # Prepare bill data for formatter (custom business logic)
            bill_data = {
                'vendor': vendor_name,
                'txn_id': target_bill.get('txn_id'),
                'ref_number': target_bill.get('ref_number'),
                'txn_date': target_bill.get('txn_date'),
                'due_date': target_bill.get('due_date'),
                'amount': target_bill.get('amount_due', 0.0),
                'memo': target_bill.get('memo'),
                'line_items': [],
                # Add payment and status info
                'IsPaid': target_bill.get('is_paid', False),
                'open_amount': target_bill.get('open_amount'),
                'payment_info': target_bill.get('payment_info', {})
            }
            
            # Transform line items for work bill display
            job_summary = {}  # Track totals by job
            for line_item in target_bill.get('line_items', []):
                line_data = {
                    'description': line_item.get('description', ''),
                    'quantity': line_item.get('quantity', 1.0),
                    'cost': line_item.get('cost', 0.0),
                    'amount': line_item.get('amount', 0.0),
                    'item': line_item.get('item_name'),
                    'customer': line_item.get('customer_name'),
                    'billable': line_item.get('billable')  # Pass through billable status
                }
                
                # Extract day from description for sorting
                desc = (line_item.get('description') or '').lower()
                for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                    if day[:3] in desc:
                        line_data['day'] = day
                        break
                
                bill_data['line_items'].append(line_data)
                
                # Add to job summary
                customer_job = line_item.get('customer_name', 'Unknown Job')
                amount = line_item.get('amount', 0.0)
                if customer_job in job_summary:
                    job_summary[customer_job] += amount
                else:
                    job_summary[customer_job] = amount
            
            # Add job summary to bill data
            if job_summary:
                bill_data['job_summary'] = job_summary
            
            # Get vendor info to get daily cost
            vendor = self.vendor_repo.find_vendor_fuzzy(vendor_name)
            daily_cost = None
            if vendor:
                daily_cost = self.vendor_repo.get_vendor_daily_cost(vendor['name'])
            
            # Format the bill for display
            formatted_bill = self.formatter.format_work_bill(bill_data, vendor_ref=vendor, daily_cost=daily_cost)
            
            return {
                'success': True,
                'bill': formatted_bill,
                'data': bill_data
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Error getting work bill: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def get_all_work_week_summaries(self, week_ending_date: Optional[str] = None) -> Dict:
        """Get work bills for ALL vendors for the specified week
        
        Args:
            week_ending_date: Optional week ending date (Saturday) in MM/DD/YYYY format
                            If not provided, uses current week
        
        Returns:
            Dictionary with summary of all vendor bills for the week
        """
        try:
            logger.info(f"get_all_work_week_summaries called with week_ending_date={week_ending_date}")
            
            # Calculate week range
            if week_ending_date:
                # Parse the provided date - assume it's Saturday
                try:
                    end_date = datetime.strptime(week_ending_date, '%m/%d/%Y')
                except ValueError:
                    try:
                        end_date = datetime.strptime(week_ending_date, '%m-%d-%Y')
                    except ValueError:
                        return {
                            'success': False,
                            'error': f"Invalid date format: {week_ending_date}. Use MM/DD/YYYY"
                        }
                # Ensure it's a Saturday
                if end_date.weekday() != 5:
                    # Adjust to nearest Saturday
                    days_to_saturday = (5 - end_date.weekday()) % 7
                    end_date = end_date + timedelta(days=days_to_saturday)
            else:
                # Use current week
                today = datetime.now()
                days_since_monday = today.weekday()
                end_date = today + timedelta(days=(5 - days_since_monday))  # Saturday
            
            # Calculate Monday of the week
            start_date = end_date - timedelta(days=5)  # Monday
            week_str = f"{start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}"
            week_ref_pattern = start_date.strftime('%m%d%y')
            
            # Get all vendors
            all_vendors = self.vendor_repo.get_all_vendors()
            
            # Collect bills for vendors who have work this week
            work_bills = []
            total_amount = 0.0
            
            for vendor in all_vendors:
                vendor_name = vendor.get('name')
                if not vendor_name:
                    continue
                
                # Try to get this vendor's bill for the week
                bills = self.bill_repo.find_bills_by_vendor(vendor_name, include_line_items=True)
                
                for bill in bills:
                    # Check if this bill is for the target week
                    memo = bill.get('memo') or ''
                    ref = bill.get('ref_number') or ''
                    
                    # Check if this is the week's bill
                    if week_str in memo or week_ref_pattern in ref:
                        # This is a work bill for the week
                        bill_amount = bill.get('amount_due', 0.0)
                        work_bills.append({
                            'vendor': vendor_name,
                            'txn_id': bill.get('txn_id'),
                            'ref_number': bill.get('ref_number'),
                            'amount': bill_amount,
                            'is_paid': bill.get('is_paid', False),
                            'line_items': bill.get('line_items', [])
                        })
                        total_amount += bill_amount
                        break  # Found this vendor's bill for the week
            
            # Sort bills by vendor name
            work_bills.sort(key=lambda x: x['vendor'].lower())
            
            # Format the summary
            summary_lines = []
            summary_lines.append(f"WORK WEEK SUMMARY")
            summary_lines.append(f"Week: {week_str}")
            summary_lines.append("=" * 50)
            summary_lines.append("")
            
            if not work_bills:
                summary_lines.append("No work bills found for this week")
            else:
                # Summary section
                summary_lines.append(f"Total Vendors: {len(work_bills)}")
                summary_lines.append(f"Total Amount: ${total_amount:,.2f}")
                summary_lines.append("")
                summary_lines.append("-" * 50)
                
                # Individual vendor summaries
                for bill in work_bills:
                    status = "[PAID]" if bill['is_paid'] else "[UNPAID]"
                    summary_lines.append(f"\n{bill['vendor'].upper()}")
                    summary_lines.append(f"  Ref: {bill['ref_number']}")
                    summary_lines.append(f"  Amount: ${bill['amount']:,.2f} {status}")
                    
                    # Show work days summary
                    days_worked = {}
                    for item in bill['line_items']:
                        desc = item.get('description', '').lower()
                        qty = item.get('quantity', 0)
                        # Extract day from description
                        for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat']:
                            if day in desc:
                                days_worked[day] = days_worked.get(day, 0) + qty
                                break
                    
                    if days_worked:
                        days_str = ", ".join([f"{day}: {qty}" for day, qty in sorted(days_worked.items(), 
                                                                                   key=lambda x: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat'].index(x[0]))])
                        summary_lines.append(f"  Days: {days_str}")
                
                # Total summary at bottom
                summary_lines.append("")
                summary_lines.append("-" * 50)
                summary_lines.append(f"WEEK TOTAL: ${total_amount:,.2f}")
                
                # Count paid vs unpaid
                paid_count = sum(1 for b in work_bills if b['is_paid'])
                unpaid_count = len(work_bills) - paid_count
                paid_amount = sum(b['amount'] for b in work_bills if b['is_paid'])
                unpaid_amount = total_amount - paid_amount
                
                summary_lines.append(f"Paid: {paid_count} bills (${paid_amount:,.2f})")
                summary_lines.append(f"Unpaid: {unpaid_count} bills (${unpaid_amount:,.2f})")
            
            return {
                'success': True,
                'summary': '\n'.join(summary_lines),
                'bills': work_bills,
                'week': week_str
            }
            
        except Exception as e:
            logger.error(f"Error getting all work week summaries: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_work_bill(self, vendor_name: str, week_data: Dict) -> Dict:
        """
        Update a work week bill with new data using BillRepository
        Supports adding new days (like Saturday) to existing bills
        
        Args:
            vendor_name: Name of the vendor
            week_data: Dictionary with updates like:
                {
                    'ref_number': 'optional ref',
                    'add_days': ['saturday'],  # Days to add
                    'saturday': {'hours': 8, 'item': 'repairs', 'customer': 'Fox:prestegard'},
                    'memo': 'Optional memo update'
                }
        
        Returns:
            Result dictionary with status and details
        """
        try:
            # Resolve vendor alias first
            import sys
            if 'shared_utilities.vendor_aliases' in sys.modules:
                del sys.modules['shared_utilities.vendor_aliases']
            from shared_utilities.vendor_aliases import resolve_vendor_alias
            original_name = vendor_name
            vendor_name = resolve_vendor_alias(vendor_name)
            logger.info(f"Vendor alias check: '{original_name}' -> '{vendor_name}' (changed: {original_name != vendor_name})")
            
            # Find vendor using fuzzy matching - this now happens BEFORE querying bills
            vendor = self.vendor_repo.find_vendor_fuzzy(vendor_name)
            if not vendor:
                return {
                    'success': False,
                    'error': f"Vendor '{vendor_name}' not found"
                }
            
            # Generate ref number for current week if not provided
            ref_number = week_data.get('ref_number')
            if not ref_number:
                today = datetime.now()
                days_since_monday = today.weekday()
                current_monday = today - timedelta(days=days_since_monday)
                current_sunday = current_monday + timedelta(days=6)
                
                # Get vendor initials: first 2 letters of first name
                # If vendor has first and last name, use first letter of each
                parts = vendor_name.split()
                if len(parts) == 1:
                    # Single name - use first 2 letters
                    initials = vendor_name[:2].lower()
                else:
                    # Multiple names - use first letter of each (first 2 parts)
                    initials = ''.join([p[0].lower() for p in parts[:2]])
                
                # Format: xx_MM/DD-MM/DD/YY
                ref_number = f"{initials}_{current_monday.strftime('%m/%d')}-{current_sunday.strftime('%m/%d/%y')}"
                # Ensure under 20 chars (QB limit)
                ref_number = ref_number[:20]
            
            # Check if we have a TxnID for direct access
            if 'txn_id' in week_data:
                # Direct access using TxnID - most efficient!
                txn_id = week_data['txn_id']
                logger.info(f"Using provided TxnID for direct access: {txn_id}")
                existing_bill = self.bill_repo.get_bill(txn_id)
                
                if not existing_bill:
                    return {
                        'success': False,
                        'error': f"Bill with TxnID {txn_id} not found"
                    }
            else:
                # Check if bill exists by searching (less efficient but necessary without TxnID)
                # Since QB doesn't support direct ref number search for bills, we need to search by vendor
                logger.info(f"Looking for bill with ref_number: {ref_number}")
                
                # Get bills for this vendor (unavoidable in QB API without TxnID)
                bills = self.bill_repo.find_bills_by_vendor(vendor['name'], include_line_items=True)
                
                # Find the specific bill with our ref_number
                existing_bill = None
                for bill in bills:
                    if bill.get('ref_number') == ref_number:
                        existing_bill = bill
                        logger.info(f"Found bill with TxnID: {existing_bill.get('txn_id')}")
                        break
                
                if not existing_bill:
                    # No existing bill, create new one
                    logger.info(f"No bill found with ref {ref_number}, creating new bill")
                    return self._create_new_bill(vendor['name'], week_data, ref_number)
            
            # We already have the bill with line_items from search_by_ref_number
            # No need to fetch it again since we requested include_line_items=True
            if existing_bill.get('line_items'):
                logger.info(f"Using bill data with {len(existing_bill['line_items'])} line items")
            else:
                # Only fetch if line_items are missing for some reason
                txn_id = existing_bill.get('txn_id')
                if txn_id:
                    direct_bill = self.bill_repo.get_bill(txn_id)
                    if direct_bill and direct_bill.get('line_items'):
                        logger.info(f"Fetched line items: {len(direct_bill['line_items'])} items")
                        existing_bill['line_items'] = direct_bill['line_items']
            
            # Get vendor's daily cost from notes
            daily_cost = self.vendor_repo.get_vendor_daily_cost(vendor['name'])
            if not daily_cost:
                daily_cost = week_data.get('default_cost', 150.0)  # Default cost if not in notes
            
            # Prepare update data for repository
            update_data = {
                'txn_id': existing_bill['txn_id'],
                'edit_sequence': existing_bill.get('edit_sequence')
            }
            
            # Update header fields if provided
            if 'memo' in week_data:
                update_data['memo'] = week_data['memo']
            
            # Process days - handle updates and removals
            days_to_update = []
            days_to_remove = []
            
            for day_name in self.work_days:
                param_name = f"{day_name}_days"  # These are DAYS!
                if param_name in week_data:
                    days_value = week_data[param_name]  # Days worked (1.0 = 1 day)
                    if days_value == -1:
                        # -1 means remove this day
                        days_to_remove.append(day_name)
                    elif days_value > 0:
                        # Positive value means add/update
                        days_to_update.append((day_name, days_value))
            
            # Handle removals (when days == -1)
            if days_to_remove:
                update_data['line_items_to_delete'] = []
                # IMPORTANT: When deleting, we must also pass all existing line items
                update_data['existing_line_items'] = existing_bill['line_items']
                
                for item in existing_bill['line_items']:
                    desc = item.get('description', '').lower()
                    for day_name in days_to_remove:
                        if day_name[:3].lower() in desc:
                            txn_line_id = item.get('txn_line_id')
                            if txn_line_id:
                                logger.info(f"Removing {day_name} (set to -1): TxnLineID={txn_line_id}")
                                update_data['line_items_to_delete'].append({
                                    'txn_line_id': txn_line_id
                                })
                            else:
                                logger.warning(f"No TxnLineID found for {day_name} line item")
                            break
            
            # Handle updates and additions (when days > 0)  
            if days_to_update:
                update_data['line_items_to_modify'] = []
                update_data['line_items_to_add'] = []
                
                # Get daily cost
                daily_cost = week_data.get('default_cost', 150.0)
                if not daily_cost:
                    # Try to get from vendor
                    vendor = self.vendor_repo.find_vendor_fuzzy(vendor_name)
                    if vendor:
                        daily_cost = self.vendor_repo.get_vendor_daily_cost(vendor['list_id'])
                    if not daily_cost:
                        daily_cost = 150.0  # Fallback
                
                # Calculate week dates using bill's actual week
                current_monday = self._get_bill_week_monday(existing_bill, ref_number)
                
                # Track which days to update and their new values
                days_to_update_dict = {day_name: days for day_name, days in days_to_update}
                
                # Check for new items that don't exist yet
                existing_days = []
                for item in existing_bill['line_items']:
                    desc = item.get('description', '').lower()
                    for day_name in days_to_update_dict:
                        if day_name[:3].lower() in desc:
                            existing_days.append(day_name)
                            break
                
                # Check if we need to add any new days
                for day_name, days in days_to_update:
                    if day_name not in existing_days:
                        # This day doesn't exist, add it as new
                        day_index = self.work_days.index(day_name.lower())
                        day_date = current_monday + timedelta(days=day_index)
                        
                        # ERROR: Cannot add line items without customer:job
                        error_msg = f"ERROR in update_work_bill (adding {day_name}): customer:job is required for all line items. Use add_days parameter with 'job' field specified."
                        logger.error(error_msg)
                        return {
                            'success': False,
                            'error': error_msg
                        }
                
                # CRITICAL: Build line_items_to_modify in ORIGINAL ORDER
                # QuickBooks requires ALL line items in their original sequence
                # Process each existing item and either modify or preserve it
                for existing_item in existing_bill['line_items']:
                    txn_line_id = existing_item.get('txn_line_id')
                    if not txn_line_id:
                        logger.warning(f"Line item missing TxnLineID, skipping")
                        continue
                    
                    desc = existing_item.get('description', '').lower()
                    modified = False
                    
                    # Check if this item needs to be updated
                    for day_name, days in days_to_update:
                        if day_name[:3].lower() in desc:
                            logger.info(f"Updating {day_name} to {days} days: TxnLineID={txn_line_id}")
                            update_data['line_items_to_modify'].append({
                                'txn_line_id': txn_line_id,
                                'quantity': float(days)  # QUANTITY = DAYS for work bills!
                            })
                            modified = True
                            break
                    
                    # If not modified, preserve it as-is
                    if not modified:
                        logger.info(f"Preserving unchanged line item: TxnLineID={txn_line_id}")
                        update_data['line_items_to_modify'].append({
                            'txn_line_id': txn_line_id,
                            'item_name': existing_item.get('item_name'),
                            'description': existing_item.get('description'),
                            'quantity': existing_item.get('quantity'),
                            'cost': existing_item.get('cost'),
                            'customer': existing_item.get('customer_name')
                        })
                
                logger.info(f"Total items to modify (in original order): {len(update_data['line_items_to_modify'])}")
            
            # Handle explicit removals (when specified via 'remove_days' parameter)
            # Supports multiple methods: by day name, by TxnLineID, or by day+item+job
            if 'remove_days' in week_data:
                if 'line_items_to_delete' not in update_data:
                    update_data['line_items_to_delete'] = []
                
                # CRITICAL FIX: Preserve non-deleted line items when removing specific items
                # If we don't include non-deleted items, QuickBooks may delete them!
                if 'line_items_to_modify' not in update_data:
                    update_data['line_items_to_modify'] = []
                
                # We'll track which items to delete, then preserve the rest
                items_to_delete_ids = []
                
                logger.info(f"Processing removal with remove_days: {week_data['remove_days']}")
                
                for removal_spec in week_data['remove_days']:
                    if isinstance(removal_spec, str):
                        # Method 1: Remove all items for a day (string day name)
                        day_name = removal_spec.lower()
                        for item in existing_bill['line_items']:
                            desc = item.get('description', '').lower()
                            if day_name[:3] in desc:
                                txn_line_id = item.get('txn_line_id')
                                if txn_line_id:
                                    logger.info(f"Removing all items for {day_name}: TxnLineID={txn_line_id}")
                                    update_data['line_items_to_delete'].append({
                                        'txn_line_id': txn_line_id
                                    })
                                    items_to_delete_ids.append(txn_line_id)
                    
                    elif isinstance(removal_spec, dict):
                        if 'txn_line_id' in removal_spec:
                            # Method 2: Remove specific line item by TxnLineID
                            logger.info(f"Removing specific item by TxnLineID: {removal_spec['txn_line_id']}")
                            update_data['line_items_to_delete'].append({
                                'txn_line_id': removal_spec['txn_line_id']
                            })
                            items_to_delete_ids.append(removal_spec['txn_line_id'])
                        
                        elif 'day' in removal_spec:
                            # Method 3: Remove by day+item+job match
                            day_to_match = removal_spec['day'].lower()[:3]
                            item_to_match = removal_spec.get('item', '').lower()
                            job_to_match = removal_spec.get('job', '').lower()
                            
                            for item in existing_bill['line_items']:
                                desc = item.get('description', '').lower()
                                item_name = item.get('item_name', '').lower()
                                customer = item.get('customer', '').lower()
                                
                                # Check if day matches
                                if day_to_match in desc:
                                    # Check if item matches (if specified)
                                    if item_to_match and item_to_match not in item_name:
                                        continue
                                    # Check if job matches (if specified)
                                    if job_to_match and job_to_match not in customer:
                                        continue
                                    
                                    # All criteria match, remove this item
                                    txn_line_id = item.get('txn_line_id')
                                    if txn_line_id:
                                        logger.info(f"Removing matched item: day={removal_spec['day']}, item={item_name}, job={customer}")
                                        update_data['line_items_to_delete'].append({
                                            'txn_line_id': txn_line_id
                                        })
                                        items_to_delete_ids.append(txn_line_id)
                                        break
                
                # Preserve all non-deleted existing line items
                # IMPORTANT: We must pass ALL fields for items we're keeping
                for existing_item in existing_bill['line_items']:
                    txn_line_id = existing_item.get('txn_line_id')
                    if txn_line_id and txn_line_id not in items_to_delete_ids:
                        logger.info(f"Preserving non-deleted line item: TxnLineID={txn_line_id}")
                        # Pass all fields to ensure QuickBooks keeps the item unchanged
                        preserved_item = {
                            'txn_line_id': txn_line_id,
                            'item_name': existing_item.get('item_name'),
                            'description': existing_item.get('description'),
                            'quantity': existing_item.get('quantity'),
                            'cost': existing_item.get('cost')
                        }
                        # Only add customer if it exists (not None/empty)
                        if existing_item.get('customer_name'):
                            preserved_item['customer'] = existing_item['customer_name']
                        update_data['line_items_to_modify'].append(preserved_item)
            
            # Process days to add - enhanced to support array of day objects
            if 'add_days' in week_data:
                update_data['line_items_to_add'] = []
                
                # Initialize line_items_to_modify if needed (preservation will be handled by _prepare_line_items_for_update)
                if 'line_items_to_modify' not in update_data:
                    update_data['line_items_to_modify'] = []
                
                # Calculate week dates using bill's actual week
                current_monday = self._get_bill_week_monday(existing_bill, ref_number)
                
                # Get daily cost for defaults
                daily_cost = week_data.get('default_cost')  # Don't set default here
                if not daily_cost:
                    # Try to get from vendor
                    vendor = self.vendor_repo.find_vendor_fuzzy(vendor_name)
                    if vendor:
                        daily_cost = self.vendor_repo.get_vendor_daily_cost(vendor['name'])  # Use name not list_id
                    if not daily_cost:
                        raise ValueError(f"No daily cost found for vendor {vendor_name}. Please set daily cost in vendor notes.")
                
                # Build a set of existing items to avoid duplicates
                # Key is (day, item_name, customer) to identify unique line items
                existing_items_set = set()
                for existing_item in existing_bill.get('line_items', []):
                    desc = existing_item.get('description', '').lower()
                    item_name = existing_item.get('item_name', '').lower() if existing_item.get('item_name') else ''
                    customer = existing_item.get('customer_name', '').lower() if existing_item.get('customer_name') else ''
                    
                    # Extract day from description (first 3 chars typically)
                    for work_day in self.work_days:
                        if work_day[:3] in desc:
                            existing_items_set.add((work_day, item_name, customer))
                            break
                
                logger.info(f"Existing items in bill: {existing_items_set}")
                
                for day_spec in week_data['add_days']:
                    # Support both string (legacy) and object formats
                    if isinstance(day_spec, str):
                        # Legacy format: just day name as string
                        day_name = day_spec.lower()
                        day_data = {}
                    else:
                        # New format: object with day and other properties
                        day_name = day_spec.get('day', '').lower()
                        day_data = day_spec
                    
                    if day_name not in self.work_days:
                        logger.warning(f"Invalid day name: {day_name}")
                        continue
                    
                    # Calculate day date
                    day_index = self.work_days.index(day_name)
                    day_date = current_monday + timedelta(days=day_index)
                    
                    # Check if this is a "no work" entry
                    is_no_work = day_data.get('no_work', False)
                    
                    if is_no_work:
                        # For no work days, use "no work provided" item with 0 quantity
                        desc = f"{day_name[:3]}. {day_date.strftime('%m/%d/%y')}"
                        # NOTE: line_memo is NOT a QB field - it's our convention to append text to the description
                        # This is different from 'memo' which is an actual QuickBooks bill-level field
                        # line_memo gets appended to the desc field for this specific line item only
                        if 'line_memo' in day_data:
                            desc += f" - {day_data['line_memo']}"
                        
                        line_item = {
                            'description': desc,
                            'quantity': 0,
                            'cost': 0,
                            'item_name': 'no work provided',  # Use the actual "no work provided" item
                            # No customer needed for no work entries - QB doesn't require it for $0 items
                        }
                        logger.info(f"Adding no work day for {day_name}")
                        update_data['line_items_to_add'].append(line_item)
                        continue  # Skip the regular processing
                    
                    # Build description with optional line_memo
                    # NOTE: line_memo is NOT a QB field - it's appended to the desc field (which IS a QB field)
                    # 'memo' is the bill-level QB field; 'line_memo' is per line item text we add to description
                    desc = f"{day_name[:3]}. {day_date.strftime('%m/%d/%y')}"
                    if 'line_memo' in day_data:
                        desc += f" {day_data['line_memo']}"
                    
                    # Prepare line item for regular work day
                    logger.info(f"[ADD_DAYS DEBUG] day_data: {day_data}, daily_cost: {daily_cost}")
                    line_item = {
                        'description': desc,
                        'quantity': float(day_data.get('qty', day_data.get('days', 1.0))),  # Support both qty and days
                        'cost': float(day_data.get('cost', daily_cost)),
                        'billable_status': 1  # Default to non-billable (1 = Not Billable in QB)
                    }
                    logger.info(f"[ADD_DAYS] Creating line item with billable_status=1 (Not Billable) for {day_name}, cost={line_item['cost']}")
                    
                    # Handle item and job (required for all line items)
                    # Handle item (with fuzzy matching)
                    item_name = day_data.get('item', 'repairs')
                    item = self.item_repo.find_item_fuzzy(item_name)
                    resolved_item_name = None
                    if item:
                        line_item['item_name'] = item['name']
                        resolved_item_name = item['name']
                    else:
                        line_item['item_name'] = item_name  # Use as-is if not found
                        resolved_item_name = item_name
                    
                    # Handle customer/job (with unified resolution)
                    customer_resolved = None
                    if 'job' in day_data:
                        job_spec = day_data['job']
                        resolved = self.customer_repo.resolve_customer_or_job(job_spec)
                        if resolved:
                            line_item['customer'] = resolved
                            customer_resolved = resolved
                            logger.info(f"[RESOLVED] '{job_spec}' -> '{resolved}'")
                        else:
                            line_item['customer'] = job_spec
                            customer_resolved = job_spec
                            logger.warning(f"[NOT FOUND] Using '{job_spec}' as-is")
                    elif 'customer' in day_data:
                        # Handle customer field with unified resolution
                        customer_spec = day_data['customer']
                        resolved = self.customer_repo.resolve_customer_or_job(customer_spec)
                        if resolved:
                            line_item['customer'] = resolved
                            customer_resolved = resolved
                            logger.info(f"[RESOLVED] '{customer_spec}' -> '{resolved}'")
                        else:
                            line_item['customer'] = customer_spec
                            customer_resolved = customer_spec
                            logger.warning(f"[NOT FOUND] Using '{customer_spec}' as-is")
                    
                    # Check if this exact combination already exists
                    item_key = (day_name, 
                               (resolved_item_name or '').lower(), 
                               (customer_resolved or '').lower())
                    if item_key in existing_items_set:
                        logger.info(f"Skipping duplicate item: {day_name}, {resolved_item_name}, {customer_resolved}")
                        continue
                    
                    logger.info(f"Adding line item for {day_name}: qty={line_item['quantity']}, cost={line_item['cost']}")
                    update_data['line_items_to_add'].append(line_item)
            
            # Process days to modify (if specified) - legacy parameter
            if 'modify_days' in week_data:
                update_data['line_items_to_modify'] = []
                
                # Find existing line items to modify
                for day_name in week_data['modify_days']:
                    day_data = week_data.get(day_name.lower(), {})
                    
                    # Find the line item with matching day in description
                    for existing_item in existing_bill['line_items']:
                        if day_name[:3].lower() in existing_item.get('description', '').lower():
                            mod_item = {
                                'txn_line_id': existing_item['txn_line_id']
                            }
                            
                            # Update fields if provided
                            if 'days' in day_data or 'qty' in day_data:
                                mod_item['quantity'] = day_data.get('days', day_data.get('qty'))
                            if 'cost' in day_data:
                                mod_item['cost'] = day_data['cost']
                            if 'item' in day_data:
                                item = self.item_repo.find_item_fuzzy(day_data['item'])
                                if item:
                                    mod_item['item_name'] = item['name']
                            
                            update_data['line_items_to_modify'].append(mod_item)
                            break
            
            # Process update_days parameter - supports multiple methods
            if 'update_days' in week_data:
                if 'line_items_to_modify' not in update_data:
                    update_data['line_items_to_modify'] = []
                
                logger.info(f"Processing update_days: {week_data['update_days']}")
                
                # CRITICAL: Track which line items are being modified
                # We'll need to include ALL line items (modified + unchanged) in line_items_to_modify
                modified_txn_ids = set()
                
                for update_spec in week_data['update_days']:
                    if 'txn_line_id' in update_spec:
                        # Method 1: Update by TxnLineID (most precise)
                        # First find the existing item to preserve its fields
                        existing_item_data = None
                        for existing_item in existing_bill['line_items']:
                            if existing_item.get('txn_line_id') == update_spec['txn_line_id']:
                                existing_item_data = existing_item
                                break
                        
                        if not existing_item_data:
                            logger.warning(f"TxnLineID {update_spec['txn_line_id']} not found in existing bill")
                            continue
                        
                        # Start with existing data to preserve all fields
                        mod_item = {
                            'txn_line_id': update_spec['txn_line_id'],
                            'item_name': existing_item_data.get('item_name'),
                            'description': existing_item_data.get('description'),
                            'quantity': existing_item_data.get('quantity'),
                            'cost': existing_item_data.get('cost')
                        }
                        
                        # Add customer if present
                        if existing_item_data.get('customer_name'):
                            mod_item['customer'] = existing_item_data['customer_name']
                        
                        # Update quantity if provided
                        if 'qty' in update_spec:
                            mod_item['quantity'] = float(update_spec['qty'])
                        
                        # Update cost if provided
                        if 'cost' in update_spec:
                            mod_item['cost'] = float(update_spec['cost'])
                        
                        # Update billable status if provided
                        if 'billable' in update_spec:
                            # Convert boolean to QB status: False=1 (Not Billable), True=0 (Billable)
                            mod_item['billable_status'] = 1 if not update_spec['billable'] else 0
                            logger.info(f"[UPDATE_DAYS] Setting billable_status={mod_item['billable_status']} for TxnLineID {update_spec['txn_line_id']}")
                            logger.info(f"[UPDATE_DAYS] Input billable={update_spec['billable']} -> QB status={mod_item['billable_status']}")
                        
                        # Update line memo if provided
                        if 'line_memo' in update_spec:
                            desc = existing_item_data.get('description', '')
                            # Extract day and date portion
                            parts = desc.split(' ', 2)
                            if len(parts) >= 2:
                                new_desc = f"{parts[0]} {parts[1]} {update_spec['line_memo']}"
                                mod_item['description'] = new_desc
                        
                        logger.info(f"Updating by TxnLineID: {update_spec['txn_line_id']}")
                        update_data['line_items_to_modify'].append(mod_item)
                        modified_txn_ids.add(update_spec['txn_line_id'])
                    
                    elif 'day' in update_spec:
                        # Method 2: Update by day + optional item/job match
                        day_to_match = update_spec['day'].lower()[:3]
                        # Support both old and new ways of specifying what to match
                        # match_item/match_job are for finding the line to update
                        # item/job without 'match_' prefix are values to update TO
                        match_item = update_spec.get('match_item', '').lower()
                        match_job = update_spec.get('match_job', '').lower()

                        for existing_item in existing_bill['line_items']:
                            desc = existing_item.get('description', '').lower()
                            item_name = existing_item.get('item_name', '').lower()
                            customer = existing_item.get('customer', '').lower()

                            # Check if day matches
                            if day_to_match in desc:
                                # If match_item specified, use it to find the right line
                                if match_item and match_item not in item_name:
                                    continue

                                # If match_job specified, use it to find the right line
                                if match_job and match_job not in customer:
                                    continue
                                
                                # All criteria match, update this item
                                # Start with all existing fields to preserve them
                                mod_item = {
                                    'txn_line_id': existing_item['txn_line_id'],
                                    'item_name': existing_item.get('item_name'),
                                    'description': existing_item.get('description'),
                                    'quantity': existing_item.get('quantity'),
                                    'cost': existing_item.get('cost')
                                }
                                # Include customer if present
                                if existing_item.get('customer_name'):
                                    mod_item['customer'] = existing_item['customer_name']
                                
                                # Now update specific fields if provided
                                logger.info(f"About to check qty/cost/billable/item in update_spec")
                                if 'qty' in update_spec:
                                    mod_item['quantity'] = float(update_spec['qty'])
                                if 'cost' in update_spec:
                                    mod_item['cost'] = float(update_spec['cost'])
                                
                                # Update item field if specified
                                # 'item' means the new item value to set
                                # 'new_item' also means the new item value (explicit)
                                # 'match_item' was already used above to find this line
                                new_item_name = update_spec.get('new_item') or update_spec.get('item')
                                if new_item_name:
                                    # Use fuzzy matching to find the actual item
                                    item = self.item_repo.find_item_fuzzy(new_item_name)
                                    if item:
                                        mod_item['item_name'] = item['name']
                                        logger.info(f"[UPDATE_DAYS] Updating item from '{existing_item.get('item_name')}' to '{item['name']}' (fuzzy matched from '{new_item_name}')")
                                    else:
                                        logger.warning(f"[UPDATE_DAYS] Could not find item '{new_item_name}' - keeping existing item")
                                        # Keep the existing item if fuzzy match fails
                                        mod_item['item_name'] = existing_item.get('item_name')
                                
                                # Update job/customer field if specified
                                # 'job' means the new job value to set
                                # 'new_job' also means the new job value (explicit)
                                # 'match_job' was already used above to find this line
                                new_job = update_spec.get('new_job') or update_spec.get('job')
                                if new_job:
                                    resolved = self.customer_repo.resolve_customer_or_job(new_job)
                                    if resolved:
                                        mod_item['customer'] = resolved
                                        logger.info(f"[UPDATE_DAYS] Updating job to '{resolved}'")
                                    else:
                                        mod_item['customer'] = new_job
                                        logger.info(f"[UPDATE_DAYS] Setting job to '{new_job}' (not resolved)")

                                # Update billable status if provided
                                logger.info(f"Checking for billable in update_spec: {update_spec}")
                                if 'billable' in update_spec:
                                    # Convert boolean to QB status: False=1 (Not Billable), True=0 (Billable)
                                    mod_item['billable_status'] = 1 if not update_spec['billable'] else 0
                                    logger.info(f"[UPDATE_DAYS] Setting billable_status={mod_item['billable_status']} for day {update_spec['day']}")
                                    logger.info(f"[UPDATE_DAYS] Input billable={update_spec['billable']} -> QB status={mod_item['billable_status']}")
                                else:
                                    logger.info(f"No billable field in update_spec")
                                
                                # Update line memo if provided
                                if 'line_memo' in update_spec:
                                    desc_existing = existing_item.get('description', '')
                                    # Extract day and date portion (e.g., "tue. 08/26/25")
                                    parts = desc_existing.split(' ', 2)
                                    if len(parts) >= 2:
                                        new_desc = f"{parts[0]} {parts[1]} {update_spec['line_memo']}"
                                        mod_item['description'] = new_desc
                                        logger.info(f"Adding line memo to description: '{new_desc}'")
                                
                                logger.info(f"Updating by match: day={update_spec['day']}, item={item_name}, job={customer}")
                                update_data['line_items_to_modify'].append(mod_item)
                                modified_txn_ids.add(existing_item['txn_line_id'])

                                # If no specific item/job match criteria specified, update ALL items for that day
                                if not match_item and not match_job:
                                    continue  # Process next matching item for same day
                                else:
                                    break  # Only update first match when specific item/job given
                
            
            # CRITICAL: Ensure ALL line items are included (modified + unchanged)
            self._prepare_line_items_for_update(existing_bill, update_data)
            
            # Log what we're about to update
            logger.info(f"Updating bill with data: items_to_delete={len(update_data.get('line_items_to_delete', []))}, "
                       f"items_to_modify={len(update_data.get('line_items_to_modify', []))}, "
                       f"items_to_add={len(update_data.get('line_items_to_add', []))}")
            
            # Use repository to update bill with line items
            success = self.bill_repo.update_bill_with_line_items(update_data)
            
            if success:
                # Get the updated bill directly by TxnID (more efficient than searching all bills)
                logger.info(f"Fetching updated bill by TxnID: {existing_bill['txn_id']}")
                updated_bill = self.bill_repo.get_bill(existing_bill['txn_id'])
                
                if updated_bill:
                    # Format the bill for display
                    daily_cost = self.vendor_repo.get_vendor_daily_cost(vendor['name']) if vendor else None
                    formatted_bill = self.formatter.format_work_bill(updated_bill, vendor_ref=vendor, daily_cost=daily_cost)
                    
                    return {
                        'success': True,
                        'message': 'Bill updated successfully',
                        'bill': formatted_bill,
                        'data': updated_bill
                    }
                
                return {
                    'success': True,
                    'message': 'Bill updated'
                }
            else:
                # Get the actual QB error from the repository
                qb_error = getattr(self.bill_repo, 'last_error', None)
                
                if qb_error:
                    # Pass through the exact QB error
                    return {
                        'success': False,
                        'error': qb_error
                    }
                else:
                    # Fallback if no detailed error available
                    error_msg = f"[WorkBillService.update_work_bill] Failed to update bill for {vendor_name}"
                    error_msg += f"\n  - Vendor: {vendor_name}"
                    error_msg += f"\n  - Ref Number: {ref_number}"
                    error_msg += f"\n  - Operations attempted: Delete={len(update_data.get('line_items_to_delete', []))}, "
                    error_msg += f"Modify={len(update_data.get('line_items_to_modify', []))}, "
                    error_msg += f"Add={len(update_data.get('line_items_to_add', []))}"
                    
                    return {
                        'success': False,
                        'error': error_msg
                    }
                
        except Exception as e:
            logger.error(f"Failed to update work bill: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_new_bill(self, vendor_name: str, week_data: Dict, ref_number: str) -> Dict:
        """Create new work week bill using BillRepository"""
        try:
            # Check if simple day parameters are being used without customer:job
            # BUT only if add_days is not provided (add_days takes precedence)
            has_simple_days = False
            if 'add_days' not in week_data or not week_data['add_days']:
                for day_name in self.work_days:
                    param_name = f"{day_name}_days"
                    if param_name in week_data and week_data[param_name] > 0:
                        has_simple_days = True
                        break
            
            if has_simple_days:
                # Cannot create line items without customer:job
                error_msg = "[WorkBillService._create_new_bill] Cannot create bill with simple day parameters"
                logger.error(error_msg)
                logger.error(f"  - Vendor: {vendor_name}")
                logger.error(f"  - Problem: customer:job is required for all line items in QuickBooks")
                logger.error(f"  - Solution: Use add_days parameter with 'job' field specified for each day")
                logger.error(f"  - Example: add_days=[{{'day': 'monday', 'qty': 1.0, 'item': 'Labor', 'job': 'rws:HQ'}}]")
                return {
                    'success': False,
                    'error': error_msg + " - Use add_days parameter with 'job' field specified"
                }
            
            # Set dates - try to parse from ref_number first
            parsed_dates = self._parse_dates_from_ref_number(ref_number)
            if parsed_dates:
                current_monday = parsed_dates['monday']
                current_saturday = parsed_dates['saturday']
            else:
                # Fallback to current week if can't parse ref_number
                today = datetime.now()
                days_since_monday = today.weekday()
                current_monday = today - timedelta(days=days_since_monday)
                current_saturday = current_monday + timedelta(days=5)
            
            # Prepare bill data for repository
            bill_data = {
                'vendor_name': vendor_name,
                'txn_date': current_monday,
                'due_date': current_saturday,
                'ref_number': ref_number,
                'memo': week_data.get('memo', f"Work week {current_monday.strftime('%m/%d/%y')} - {current_saturday.strftime('%m/%d/%y')}"),
                'line_items': []
            }
            
            # Process add_days parameter which includes job
            if 'add_days' in week_data:
                # Get daily cost for defaults
                daily_cost = week_data.get('default_cost')  # Don't set default here
                if not daily_cost:
                    # Try to get from vendor
                    vendor = self.vendor_repo.find_vendor_fuzzy(vendor_name)
                    if vendor:
                        daily_cost = self.vendor_repo.get_vendor_daily_cost(vendor['name'])  # Use name not list_id
                    if not daily_cost:
                        raise ValueError(f"No daily cost found for vendor {vendor_name}. Please set daily cost in vendor notes.")
                
                for day_spec in week_data['add_days']:
                    # Support both string (legacy) and object formats
                    if isinstance(day_spec, str):
                        # Legacy format: just day name as string
                        day_name = day_spec.lower()
                        day_data = {}
                    else:
                        # New format: object with day and other properties
                        day_name = day_spec.get('day', '').lower()
                        day_data = day_spec
                    
                    if day_name not in self.work_days:
                        logger.warning(f"Invalid day name: {day_name}")
                        continue
                    
                    # Calculate day date
                    day_index = self.work_days.index(day_name)
                    day_date = current_monday + timedelta(days=day_index)
                    
                    # Check if this is a "no work" entry
                    is_no_work = day_data.get('no_work', False)
                    
                    if is_no_work:
                        # SIMPLE PATH FOR NO WORK DAYS
                        desc = f"{day_name[:3]}. {day_date.strftime('%m/%d/%y')}"
                        # NOTE: line_memo is NOT a QB field - it's our convention to append text to the description
                        # This is different from 'memo' which is an actual QuickBooks bill-level field
                        # line_memo gets appended to the desc field for this specific line item only
                        if 'line_memo' in day_data:
                            desc += f" - {day_data['line_memo']}"
                        
                        line_item = {
                            'description': desc,
                            'quantity': 0,
                            'cost': 0,
                            'item_name': 'no work provided',  # Use the actual "no work provided" item
                            # No customer needed for no work entries - QB doesn't require it for $0 items
                        }
                        
                        logger.info(f"Adding no work day for {day_name}")
                        bill_data['line_items'].append(line_item)
                        continue  # Skip all the regular processing
                    
                    # REGULAR WORK DAY PROCESSING
                    # Build description with optional line_memo
                    # NOTE: line_memo is NOT a QB field - it's appended to the desc field (which IS a QB field)
                    # 'memo' is the bill-level QB field; 'line_memo' is per line item text we add to description
                    desc = f"{day_name[:3]}. {day_date.strftime('%m/%d/%y')}"
                    if 'line_memo' in day_data:
                        desc += f" {day_data['line_memo']}"
                    
                    # Prepare line item
                    line_item = {
                        'description': desc,
                        'quantity': float(day_data.get('qty', day_data.get('days', 1.0))),
                        'cost': float(day_data.get('cost', daily_cost)),
                        'billable_status': 1  # Default to non-billable (1 = Not Billable in QB)
                    }
                    
                    # Handle item (with fuzzy matching)
                    item_name = day_data.get('item', 'repairs')
                    item = self.item_repo.find_item_fuzzy(item_name)
                    if item:
                        line_item['item_name'] = item['name']
                    else:
                        line_item['item_name'] = item_name
                    
                    # Handle customer/job (REQUIRED!)
                    if 'job' in day_data:
                        job_spec = day_data['job']
                        resolved = self.customer_repo.resolve_customer_or_job(job_spec)
                        if resolved:
                            line_item['customer'] = resolved
                            logger.info(f"[RESOLVED] '{job_spec}' -> '{resolved}'")
                        else:
                            line_item['customer'] = job_spec
                            logger.warning(f"[NOT FOUND] Using '{job_spec}' as-is")
                    else:
                        # No job specified - this is an error
                        return {
                            'success': False,
                            'error': f"ERROR: customer:job is required. Day '{day_name}' in add_days is missing 'job' field."
                        }
                    
                    bill_data['line_items'].append(line_item)
            
            # Check if we have any line items to create
            if not bill_data['line_items']:
                error_msg = "ERROR in _create_new_bill: Cannot create bill without line items. Use add_days parameter with 'job' field specified."
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Create bill through repository
            result = self.bill_repo.create_bill(bill_data)
            
            if result['success']:
                # Get the created bill to return formatted
                get_result = self.get_work_bill(vendor_name, ref_number)
                if get_result['success']:
                    return {
                        'success': True,
                        'message': 'Bill created successfully',
                        'bill': get_result.get('bill', ''),
                    }
                
                return {
                    'success': True,
                    'message': 'Bill created'
                }
            else:
                # Pass through the detailed error from repository
                error_msg = f"[WorkBillService._create_new_bill] {result.get('error', 'Unknown error')}"
                logger.error(error_msg)
                logger.error(f"  - Vendor: {vendor_name}")
                logger.error(f"  - Line items attempted: {len(bill_data.get('line_items', []))}")
                
                return {
                    'success': False, 
                    'error': result.get('error', 'Failed to create bill'),
                    'error_code': result.get('error_code'),
                    'error_message': result.get('error_message'),
                    'explanation': result.get('explanation')
                }
                
        except Exception as e:
            logger.error(f"Error creating bill: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_week_dates(self, week: str) -> Optional[Dict]:
        """Calculate Monday and Saturday dates for the specified week
        
        Args:
            week: 'current', 'last', 'next' or numeric (-2, -1, 0, 1, 2)
        
        Returns:
            Dict with 'monday' and 'saturday' datetime objects, or None if invalid
        """
        try:
            today = datetime.now()
            
            # Convert week parameter to offset
            if week is None or week == 'current' or week == '0':
                offset = 0
            elif week == 'last' or week == '-1':
                offset = -1
            elif week == 'next' or week == '1':
                offset = 1
            else:
                # Try to parse as integer
                try:
                    offset = int(week)
                except:
                    return None
            
            # Calculate current week's Monday
            days_since_monday = today.weekday()
            current_monday = today - timedelta(days=days_since_monday)
            
            # Apply offset
            target_monday = current_monday + timedelta(weeks=offset)
            target_saturday = target_monday + timedelta(days=5)
            
            return {
                'monday': target_monday,
                'saturday': target_saturday
            }
        except Exception as e:
            logger.error(f"Error calculating week dates: {e}")
            return None
    
    def _get_bill_week_monday(self, existing_bill: Dict, ref_number: Optional[str] = None) -> datetime:
        """Get the Monday date for a bill's week from various sources
        
        Args:
            existing_bill: The existing bill data (may have ref_number or txn_date)
            ref_number: Optional ref_number to parse
            
        Returns:
            Monday datetime for the bill's week
        """
        # First try ref_number (most reliable)
        ref_to_parse = ref_number or existing_bill.get('ref_number')
        if ref_to_parse:
            parsed_dates = self._parse_dates_from_ref_number(ref_to_parse)
            if parsed_dates:
                return parsed_dates['monday']
        
        # Then try txn_date from bill
        if existing_bill and 'txn_date' in existing_bill:
            txn_date = existing_bill['txn_date']
            if isinstance(txn_date, str):
                # Parse date string
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y']:
                    try:
                        date = datetime.strptime(txn_date, fmt)
                        # Assume txn_date is Monday
                        return date
                    except:
                        continue
            elif isinstance(txn_date, datetime):
                return txn_date
        
        # Fallback to current week (not ideal)
        logger.warning("Could not determine bill week, using current week")
        today = datetime.now()
        days_since_monday = today.weekday()
        return today - timedelta(days=days_since_monday)
    
    def _prepare_line_items_for_update(self, existing_bill: Dict, update_data: Dict) -> None:
        """Ensure ALL line items are included when updating (modified + unchanged)
        
        QuickBooks requires ALL line items to be sent when modifying a bill.
        This method ensures unchanged items are preserved IN PROPER ORDER.
        
        Args:
            existing_bill: The current bill with all line items
            update_data: The update data being prepared (modified in place)
        """
        if 'line_items_to_modify' not in update_data:
            return
        
        logger.info(f"_prepare_line_items_for_update: Bill has {len(existing_bill.get('line_items', []))} items, update has {len(update_data['line_items_to_modify'])} items to modify")
        
        # Track which items are already being modified
        modified_items = {}
        for item in update_data['line_items_to_modify']:
            if 'txn_line_id' in item:
                modified_items[item['txn_line_id']] = item
        
        # Track which items are being deleted
        deleted_txn_ids = set()
        if 'line_items_to_delete' in update_data:
            for item in update_data['line_items_to_delete']:
                if 'txn_line_id' in item:
                    deleted_txn_ids.add(item['txn_line_id'])
                    logger.info(f"Item marked for deletion: {item['txn_line_id']}")
        
        # Create new list with ALL items in proper TxnLineID order
        all_items = []
        for existing_item in existing_bill.get('line_items', []):
            txn_id = existing_item.get('txn_line_id')
            if txn_id:
                # Skip items marked for deletion
                if txn_id in deleted_txn_ids:
                    logger.info(f"Skipping deleted item: {txn_id}")
                    continue
                    
                if txn_id in modified_items:
                    # Use the modified version
                    mod_item = modified_items[txn_id]
                    logger.info(f"Using modified item for {txn_id}: billable_status={mod_item.get('billable_status', 'not set')}")
                    all_items.append(mod_item)
                else:
                    # Preserve unchanged item
                    preserve_item = {
                        'txn_line_id': txn_id,
                        'item_name': existing_item.get('item_name'),
                        'description': existing_item.get('description'),
                        'quantity': existing_item.get('quantity'),
                        'cost': existing_item.get('cost')
                    }
                    if existing_item.get('customer_name'):
                        preserve_item['customer'] = existing_item['customer_name']
                        # Don't set billable_status for items with customers - let QuickBooks handle it
                    
                    all_items.append(preserve_item)
                    logger.info(f"Preserving unchanged item: {txn_id}")
        
        # Replace the list with properly ordered items
        update_data['line_items_to_modify'] = all_items
        logger.info(f"Final line_items_to_modify has {len(all_items)} items in TxnLineID order")
    
    def _parse_dates_from_ref_number(self, ref_number: str) -> Optional[Dict]:
        """Parse Monday date from reference number format: xx_MM/DD-MM/DD/YY
        
        Returns:
            Dict with 'monday' datetime object, or None if cannot parse
        """
        try:
            # Expected format: xx_MM/DD-MM/DD/YY (e.g., ja_08/25-08/31/25)
            if '_' not in ref_number or '-' not in ref_number:
                return None
                
            # Split to get date part: "08/25-08/31/25"
            date_part = ref_number.split('_', 1)[1]  # Get everything after first underscore
            
            # Split to get start date: "08/25"
            start_date_str = date_part.split('-')[0]  # "08/25"
            
            # Get end date to extract year: "08/31/25"
            end_date_str = date_part.split('-')[1]  # "08/31/25"
            year_str = end_date_str.split('/')[2]  # "25"
            
            # Construct full date string with year
            full_date_str = f"{start_date_str}/{year_str}"  # "08/25/25"
            
            # Parse the date
            monday_date = datetime.strptime(full_date_str, '%m/%d/%y')
            
            return {
                'monday': monday_date,
                'saturday': monday_date + timedelta(days=5)
            }
        except Exception as e:
            logger.warning(f"Could not parse dates from ref_number '{ref_number}': {e}")
            return None
    
    def _get_week_description(self, week: str) -> str:
        """Get human-readable description of the week
        
        Args:
            week: 'current', 'last', 'next' or numeric
        
        Returns:
            Human-readable description like 'last week' or 'week ending MM/DD/YYYY'
        """
        if week is None or week == 'current' or week == '0':
            return 'current week'
        elif week == 'last' or week == '-1':
            return 'last week'
        elif week == 'next' or week == '1':
            return 'next week'
        else:
            try:
                offset = int(week)
                if offset < 0:
                    return f'{abs(offset)} weeks ago'
                else:
                    return f'{offset} weeks from now'
            except:
                return f'week {week}'