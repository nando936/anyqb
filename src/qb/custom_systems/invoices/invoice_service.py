"""
Invoice Service - Business logic for invoice operations
Handles invoice CRUD operations with formatting
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from quickbooks_standard.entities.invoices.invoice_repository import InvoiceRepository
from quickbooks_standard.entities.customers.customer_repository import CustomerRepository
from quickbooks_standard.entities.items.item_repository import ItemRepository

logger = logging.getLogger(__name__)

class InvoiceService:
    """Service for managing invoice operations with business logic"""
    
    def __init__(self):
        """Initialize invoice service"""
        self.invoice_repo = InvoiceRepository()
        self.customer_repo = CustomerRepository()
        self.item_repo = ItemRepository()
    
    def search_invoices(self, search_params: Dict) -> str:
        """
        Search invoices with formatted output
        """
        try:
            # Extract search parameters
            search_term = search_params.get('search_term')
            customer_name = search_params.get('customer_name')
            invoice_number = search_params.get('invoice_number')
            date_from = search_params.get('date_from')
            date_to = search_params.get('date_to')
            is_paid = search_params.get('is_paid')
            memo_contains = search_params.get('memo_contains')
            
            invoices = []
            
            # If customer_name specified, use that method
            if customer_name and not (invoice_number or date_from or date_to or is_paid):
                invoices = self.invoice_repo.find_invoices_by_customer(customer_name)
            else:
                # Use general search
                invoices = self.invoice_repo.search_invoices(
                    ref_number=invoice_number,
                    date_from=date_from,
                    date_to=date_to,
                    customer_name=customer_name,
                    is_paid=is_paid,
                    memo_contains=memo_contains
                )
            
            # Apply additional filtering if search_term provided
            if search_term and invoices:
                search_lower = search_term.lower()
                filtered = []
                for invoice in invoices:
                    # Search across all fields
                    if (search_lower in str(invoice.get('invoice_number', '')).lower() or
                        search_lower in str(invoice.get('customer', '')).lower() or
                        search_lower in str(invoice.get('memo', '')).lower() or
                        search_lower in str(invoice.get('total', '')).lower() or
                        search_lower in str(invoice.get('po_number', '')).lower()):
                        filtered.append(invoice)
                invoices = filtered
            
            if not invoices:
                return "[OK] No invoices found matching criteria"
            
            # Format output
            output = []
            output.append("[OK] Invoices Found")
            output.append("=" * 40)
            
            total_amount = 0.0
            total_balance = 0.0
            
            for invoice in invoices:
                output.append(f"\n[Invoice #{invoice.get('invoice_number', 'N/A')}]")
                output.append("-" * 40)
                output.append(f"Date:         {invoice.get('date', 'N/A')}")
                output.append(f"Customer:     {invoice.get('customer', 'N/A')}")
                output.append(f"Total:        ${invoice.get('total', 0.0):,.2f}")
                output.append(f"Balance:      ${invoice.get('balance_remaining', 0.0):,.2f}")
                output.append(f"Status:       {'PAID' if invoice.get('is_paid') else 'UNPAID'}")
                
                if invoice.get('due_date'):
                    output.append(f"Due Date:     {invoice['due_date']}")
                
                if invoice.get('terms'):
                    output.append(f"Terms:        {invoice['terms']}")
                
                if invoice.get('po_number'):
                    output.append(f"PO Number:    {invoice['po_number']}")
                
                if invoice.get('memo'):
                    output.append(f"Memo:         {invoice['memo']}")
                
                output.append(f"TxnID:        {invoice.get('txn_id', 'N/A')}")
                
                # Show line items summary
                if invoice.get('line_items'):
                    output.append("\nLine Items:")
                    for line in invoice['line_items'][:5]:  # Show first 5 items
                        if line.get('is_group'):
                            output.append(f"  * [GROUP] {line.get('item_group')}: {line.get('quantity')} @ ${line.get('total_amount', 0.0):,.2f}")
                        else:
                            qty = line.get('quantity', 0)
                            rate = line.get('rate', 0.0)
                            output.append(f"  * {line.get('item')}: {qty} @ ${rate:,.2f} = ${line.get('amount', 0.0):,.2f}")
                    
                    if len(invoice['line_items']) > 5:
                        output.append(f"  ... and {len(invoice['line_items']) - 5} more items")
                
                total_amount += invoice.get('total', 0.0)
                total_balance += invoice.get('balance_remaining', 0.0)
            
            output.append("\n" + "=" * 40)
            output.append(f"Total Invoices:    {len(invoices)}")
            output.append(f"Total Amount:      ${total_amount:,.2f}")
            output.append(f"Total Outstanding: ${total_balance:,.2f}")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to search invoices: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def create_invoice(self, invoice_data: Dict) -> str:
        """
        Create a new invoice with validation and formatting
        """
        try:
            # Validate required fields
            if not invoice_data.get('customer'):
                return "[ERROR] Customer is required"
            
            # Prepare invoice data
            formatted_data = {
                'customer': invoice_data['customer'],
                'date': invoice_data.get('date', datetime.now()),
                'line_items': []
            }
            
            # Add optional fields
            if invoice_data.get('invoice_number'):
                formatted_data['invoice_number'] = invoice_data['invoice_number']
            
            if invoice_data.get('terms'):
                formatted_data['terms'] = invoice_data['terms']
            
            if invoice_data.get('due_date'):
                formatted_data['due_date'] = invoice_data['due_date']
            elif invoice_data.get('terms'):
                # Calculate due date based on terms if not provided
                # This is simplified - actual implementation would parse terms
                formatted_data['due_date'] = formatted_data['date'] + timedelta(days=30)
            
            if invoice_data.get('memo'):
                formatted_data['memo'] = invoice_data['memo']
            
            if invoice_data.get('po_number'):
                formatted_data['po_number'] = invoice_data['po_number']
            
            if invoice_data.get('sales_rep'):
                formatted_data['sales_rep'] = invoice_data['sales_rep']
            
            if invoice_data.get('fob'):
                formatted_data['fob'] = invoice_data['fob']
            
            if invoice_data.get('ship_method'):
                formatted_data['ship_method'] = invoice_data['ship_method']
            
            if invoice_data.get('ship_date'):
                formatted_data['ship_date'] = invoice_data['ship_date']
            
            if invoice_data.get('customer_msg'):
                formatted_data['customer_msg'] = invoice_data['customer_msg']
            
            if invoice_data.get('bill_address'):
                formatted_data['bill_address'] = invoice_data['bill_address']
            
            if invoice_data.get('ship_address'):
                formatted_data['ship_address'] = invoice_data['ship_address']
            
            # Process line items
            if invoice_data.get('items'):
                for item_data in invoice_data['items']:
                    if item_data.get('item_group'):
                        # Item group
                        line_item = {
                            'item_group': item_data['item_group'],
                            'quantity': item_data.get('quantity', 1.0)
                        }
                        
                        if item_data.get('unit_of_measure'):
                            line_item['unit_of_measure'] = item_data['unit_of_measure']
                        
                        formatted_data['line_items'].append(line_item)
                        
                    elif item_data.get('item'):
                        # Regular item
                        line_item = {
                            'item': item_data['item'],
                            'quantity': item_data.get('quantity', 1.0)
                        }
                        
                        if item_data.get('rate'):
                            line_item['rate'] = item_data['rate']
                        
                        # Calculate amount if rate provided
                        if 'rate' in line_item:
                            line_item['amount'] = line_item['quantity'] * line_item['rate']
                        elif item_data.get('amount'):
                            line_item['amount'] = item_data['amount']
                        
                        # Add optional fields
                        if item_data.get('description'):
                            line_item['description'] = item_data['description']
                        
                        if item_data.get('service_date'):
                            line_item['service_date'] = item_data['service_date']
                        
                        if item_data.get('other1'):
                            line_item['other1'] = item_data['other1']
                        
                        if item_data.get('other2'):
                            line_item['other2'] = item_data['other2']
                        
                        if item_data.get('sales_tax_code'):
                            line_item['sales_tax_code'] = item_data['sales_tax_code']
                        
                        formatted_data['line_items'].append(line_item)
            
            # Create the invoice
            result = self.invoice_repo.create_invoice(formatted_data)
            
            if not result:
                return "[ERROR] Failed to create invoice in QuickBooks"
            
            # Format success response
            output = []
            output.append("[OK] Invoice Created Successfully")
            output.append("=" * 40)
            output.append(f"Invoice Number: {result.get('invoice_number', 'N/A')}")
            output.append(f"Date:           {result.get('date', 'N/A')}")
            output.append(f"Customer:       {result.get('customer', 'N/A')}")
            output.append(f"Subtotal:       ${result.get('subtotal', 0.0):,.2f}")
            
            if result.get('sales_tax_total', 0) > 0:
                output.append(f"Sales Tax:      ${result.get('sales_tax_total', 0.0):,.2f}")
            
            output.append(f"Total:          ${result.get('total', 0.0):,.2f}")
            output.append(f"Due Date:       {result.get('due_date', 'N/A')}")
            output.append(f"Terms:          {result.get('terms', 'N/A')}")
            output.append(f"TxnID:          {result.get('txn_id', 'N/A')}")
            
            if result.get('line_items'):
                output.append("\nLine Items Created:")
                for line in result['line_items']:
                    if line.get('is_group'):
                        output.append(f"  * [GROUP] {line.get('item_group')}: {line.get('quantity')} = ${line.get('total_amount', 0.0):,.2f}")
                    else:
                        output.append(f"  * {line.get('item')}: {line.get('quantity')} @ ${line.get('rate', 0.0):,.2f} = ${line.get('amount', 0.0):,.2f}")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to create invoice: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def update_invoice(self, txn_id: str, updates: Dict) -> str:
        """
        Update an existing invoice
        """
        try:
            # Get existing invoice first
            existing = self.invoice_repo.get_invoice(txn_id)
            if not existing:
                return f"[ERROR] Invoice {txn_id} not found"
            
            # Update the invoice
            result = self.invoice_repo.update_invoice(txn_id, updates)
            
            if not result:
                return "[ERROR] Failed to update invoice in QuickBooks"
            
            # Format success response
            output = []
            output.append("[OK] Invoice Updated Successfully")
            output.append("=" * 40)
            output.append(f"Invoice Number: {result.get('invoice_number', 'N/A')}")
            output.append(f"Date:           {result.get('date', 'N/A')}")
            output.append(f"Customer:       {result.get('customer', 'N/A')}")
            output.append(f"Total:          ${result.get('total', 0.0):,.2f}")
            output.append(f"Balance:        ${result.get('balance_remaining', 0.0):,.2f}")
            output.append(f"Status:         {'PAID' if result.get('is_paid') else 'UNPAID'}")
            output.append(f"TxnID:          {result.get('txn_id', 'N/A')}")
            
            output.append("\nUpdated Fields:")
            for field, value in updates.items():
                output.append(f"  * {field}: {value}")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to update invoice: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def delete_invoice(self, txn_id: str) -> str:
        """
        Delete an invoice
        """
        try:
            # Get invoice details first for confirmation
            invoice = self.invoice_repo.get_invoice(txn_id)
            if not invoice:
                return f"[ERROR] Invoice {txn_id} not found"
            
            # Check if invoice has payments
            if invoice.get('balance_remaining', 0) != invoice.get('total', 0):
                return f"[ERROR] Cannot delete invoice with payments. Balance: ${invoice.get('balance_remaining', 0):,.2f} of ${invoice.get('total', 0):,.2f}"
            
            # Delete the invoice
            success = self.invoice_repo.delete_invoice(txn_id)
            
            if not success:
                return "[ERROR] Failed to delete invoice from QuickBooks"
            
            # Format success response
            output = []
            output.append("[OK] Invoice Deleted Successfully")
            output.append("=" * 40)
            output.append(f"Invoice Number: {invoice.get('invoice_number', 'N/A')}")
            output.append(f"Date:           {invoice.get('date', 'N/A')}")
            output.append(f"Customer:       {invoice.get('customer', 'N/A')}")
            output.append(f"Total:          ${invoice.get('total', 0.0):,.2f}")
            output.append(f"TxnID:          {txn_id}")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to delete invoice: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def get_invoice(self, txn_id: str) -> str:
        """
        Get a specific invoice by transaction ID
        """
        try:
            invoice = self.invoice_repo.get_invoice(txn_id)
            
            if not invoice:
                return f"[ERROR] Invoice {txn_id} not found"
            
            # Format output
            output = []
            output.append("[OK] Invoice Details")
            output.append("=" * 40)
            output.append(f"Invoice Number: {invoice.get('invoice_number', 'N/A')}")
            output.append(f"Date:           {invoice.get('date', 'N/A')}")
            output.append(f"Customer:       {invoice.get('customer', 'N/A')}")
            output.append(f"Subtotal:       ${invoice.get('subtotal', 0.0):,.2f}")
            
            if invoice.get('sales_tax_total', 0) > 0:
                output.append(f"Sales Tax:      ${invoice.get('sales_tax_total', 0.0):,.2f}")
            
            output.append(f"Total:          ${invoice.get('total', 0.0):,.2f}")
            output.append(f"Balance:        ${invoice.get('balance_remaining', 0.0):,.2f}")
            output.append(f"Status:         {'PAID' if invoice.get('is_paid') else 'UNPAID'}")
            
            if invoice.get('due_date'):
                output.append(f"Due Date:       {invoice['due_date']}")
            
            if invoice.get('terms'):
                output.append(f"Terms:          {invoice['terms']}")
            
            if invoice.get('po_number'):
                output.append(f"PO Number:      {invoice['po_number']}")
            
            if invoice.get('sales_rep'):
                output.append(f"Sales Rep:      {invoice['sales_rep']}")
            
            if invoice.get('ship_method'):
                output.append(f"Ship Method:    {invoice['ship_method']}")
            
            if invoice.get('ship_date'):
                output.append(f"Ship Date:      {invoice['ship_date']}")
            
            if invoice.get('fob'):
                output.append(f"FOB:            {invoice['fob']}")
            
            if invoice.get('memo'):
                output.append(f"Memo:           {invoice['memo']}")
            
            output.append(f"TxnID:          {invoice.get('txn_id', 'N/A')}")
            output.append(f"Edit Seq:       {invoice.get('edit_sequence', 'N/A')}")
            
            # Show addresses if present
            if invoice.get('bill_address'):
                output.append(f"\nBill To:")
                for line in invoice['bill_address'].split('\n'):
                    output.append(f"  {line}")
            
            if invoice.get('ship_address'):
                output.append(f"\nShip To:")
                for line in invoice['ship_address'].split('\n'):
                    output.append(f"  {line}")
            
            # Show line items
            if invoice.get('line_items'):
                output.append("\nLine Items:")
                for i, line in enumerate(invoice['line_items'], 1):
                    if line.get('is_group'):
                        output.append(f"  {i}. [GROUP] {line.get('item_group')}: {line.get('quantity')} = ${line.get('total_amount', 0.0):,.2f}")
                        if line.get('group_items'):
                            for sub_item in line['group_items']:
                                output.append(f"      - {sub_item.get('item')}: {sub_item.get('quantity')} = ${sub_item.get('amount', 0.0):,.2f}")
                    else:
                        qty = line.get('quantity', 0)
                        rate = line.get('rate', 0.0)
                        output.append(f"  {i}. {line.get('item')}: {qty} @ ${rate:,.2f} = ${line.get('amount', 0.0):,.2f}")
                        if line.get('description'):
                            output.append(f"     Desc: {line['description']}")
                        if line.get('service_date'):
                            output.append(f"     Service Date: {line['service_date']}")
            
            # Show linked transactions (payments)
            if invoice.get('linked_transactions'):
                output.append("\nPayments Applied:")
                for payment in invoice['linked_transactions']:
                    output.append(f"  * {payment.get('txn_type')}: ${payment.get('amount', 0.0):,.2f} on {payment.get('txn_date')} (#{payment.get('ref_number')})")
            
            return "\n".join(output)
            
        except Exception as e:
            error_msg = f"[ERROR] Failed to get invoice: {str(e)}"
            logger.error(error_msg)
            return error_msg