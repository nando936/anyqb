"""
Invoice repository for QuickBooks invoice operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import logging
from shared_utilities.fuzzy_matcher import FuzzyMatcher
from shared_utilities.xml_qb_connection import XMLQBConnection

logger = logging.getLogger(__name__)

class InvoiceRepository:
    """Repository for invoice operations"""
    
    def __init__(self):
        self.connection = XMLQBConnection()
        self.fuzzy_matcher = FuzzyMatcher()
    
    def search_invoices(
        self,
        search_term: Optional[str] = None,
        customer_name: Optional[str] = None,
        amount: Optional[float] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        ref_number: Optional[str] = None,
        paid_status: Optional[str] = None,  # "paid", "unpaid", "all"
        max_returned: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Search for invoices with various filters

        Args:
            search_term: General search term for fuzzy matching
            customer_name: Filter by customer/job name (uses fuzzy matching)
            amount: Exact amount match
            amount_min/max: Amount range
            date_from/to: Date range (MM-DD-YYYY or MM/DD/YYYY)
            ref_number: Invoice reference number
            paid_status: Filter by paid status
            max_returned: Maximum results to return

        Returns:
            List of invoice dictionaries
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return []

        try:
            # For customer_name, we'll do fuzzy matching in post-processing
            # So don't pass it to the query builder
            request_xml = self._build_invoice_query(
                customer_name=None,  # Don't filter at QB level for fuzzy matching
                date_from=date_from,
                date_to=date_to,
                ref_number=ref_number,
                paid_status=paid_status,
                max_returned=max_returned * 3 if customer_name else max_returned  # Get more results for client-side filtering
            )
            
            # Process the request
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            # Parse the response
            root = ET.fromstring(response_xml)
            
            # Check for errors
            error = root.find('.//InvoiceQueryRs')
            if error is not None and error.get('statusCode') != '0':
                status_msg = error.get('statusMessage', 'Unknown error')
                logger.error(f"QuickBooks error: {status_msg}")
                return []
            
            # Find all invoice elements
            invoices = root.findall('.//InvoiceRet')
            
            if not invoices:
                logger.info("No invoices found")
                return []
            
            # Process invoices
            results = []
            for invoice in invoices:
                invoice_dict = self._parse_invoice(invoice)

                # Apply additional filters
                if amount and float(invoice_dict.get('total', 0)) != amount:
                    continue
                if amount_min and float(invoice_dict.get('total', 0)) < amount_min:
                    continue
                if amount_max and float(invoice_dict.get('total', 0)) > amount_max:
                    continue

                # Apply fuzzy customer name filter if provided
                if customer_name:
                    invoice_customer = invoice_dict.get('customer', '').lower()
                    search_customer = customer_name.lower()
                    # Check if search term is contained in customer name (fuzzy match)
                    if search_customer not in invoice_customer:
                        continue

                # Apply fuzzy search if search term provided
                if search_term:
                    searchable_text = f"{invoice_dict.get('customer', '')} {invoice_dict.get('ref_number', '')} {invoice_dict.get('memo', '')}".lower()
                    if search_term.lower() not in searchable_text:
                        continue

                results.append(invoice_dict)
            
            return results[:max_returned]
            
        except Exception as e:
            logger.error(f"Error searching invoices: {str(e)}")
            return []
    
    def get_invoice(self, ref_number: Optional[str] = None, txn_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a specific invoice by reference number or transaction ID"""
        if not self.connection.connect():
            return None
        
        try:
            # Build query for specific invoice
            if txn_id:
                filter_xml = f"<TxnID>{txn_id}</TxnID>"
            elif ref_number:
                filter_xml = f"<RefNumber>{ref_number}</RefNumber>"
            else:
                return None
            
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <InvoiceQueryRq>
            {filter_xml}
            <IncludeLineItems>true</IncludeLineItems>
            <IncludeLinkedTxns>true</IncludeLinkedTxns>
        </InvoiceQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            root = ET.fromstring(response_xml)
            invoice = root.find('.//InvoiceRet')
            
            if invoice is not None:
                return self._parse_invoice(invoice)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting invoice: {str(e)}")
            return None
    
    def _build_invoice_query(
        self,
        customer_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        ref_number: Optional[str] = None,
        paid_status: Optional[str] = None,
        max_returned: int = 100
    ) -> str:
        """Build the invoice query XML"""
        
        filters = []
        
        # Add date range filter
        if date_from or date_to:
            date_filter = "<TxnDateRangeFilter>"
            if date_from:
                date_obj = self._parse_date(date_from)
                if date_obj:
                    date_filter += f"<FromTxnDate>{date_obj.strftime('%Y-%m-%d')}</FromTxnDate>"
            if date_to:
                date_obj = self._parse_date(date_to)
                if date_obj:
                    date_filter += f"<ToTxnDate>{date_obj.strftime('%Y-%m-%d')}</ToTxnDate>"
            date_filter += "</TxnDateRangeFilter>"
            filters.append(date_filter)
        
        # Add customer filter
        if customer_name:
            filters.append(f"""<EntityFilter>
                <FullName>{customer_name}</FullName>
            </EntityFilter>""")
        
        # Add ref number filter
        if ref_number:
            filters.append(f"<RefNumber>{ref_number}</RefNumber>")
        
        # Add paid status filter
        if paid_status:
            if paid_status.lower() == "paid":
                filters.append("<PaidStatus>Paid</PaidStatus>")
            elif paid_status.lower() == "unpaid":
                filters.append("<PaidStatus>NotPaidOnly</PaidStatus>")
            # "all" means no filter
        
        # Build the request
        filter_xml = "\n".join(filters) if filters else ""
        
        return f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <InvoiceQueryRq requestID="1">
            <MaxReturned>{max_returned}</MaxReturned>
            {filter_xml}
            <IncludeLineItems>true</IncludeLineItems>
            <IncludeLinkedTxns>true</IncludeLinkedTxns>
        </InvoiceQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
    
    def _parse_invoice(self, invoice_elem: ET.Element) -> Dict[str, Any]:
        """Parse an invoice XML element into a dictionary"""
        
        def get_text(elem, path, default=""):
            found = elem.find(path)
            return found.text if found is not None else default
        
        # Extract basic fields
        result = {
            'txn_id': get_text(invoice_elem, 'TxnID'),
            'ref_number': get_text(invoice_elem, 'RefNumber'),
            'txn_date': get_text(invoice_elem, 'TxnDate'),
            'customer': get_text(invoice_elem, './/CustomerRef/FullName'),
            'subtotal': float(get_text(invoice_elem, 'Subtotal', '0')),
            'sales_tax': float(get_text(invoice_elem, 'SalesTaxTotal', '0')),
            'total': float(get_text(invoice_elem, 'Subtotal', '0')) + float(get_text(invoice_elem, 'SalesTaxTotal', '0')),
            'applied_amount': float(get_text(invoice_elem, 'AppliedAmount', '0')),
            'balance': float(get_text(invoice_elem, 'BalanceRemaining', '0')),
            'is_paid': get_text(invoice_elem, 'IsPaid', 'false') == 'true',
            'is_pending': get_text(invoice_elem, 'IsPending', 'false') == 'true',
            'po_number': get_text(invoice_elem, 'PONumber'),
            'terms': get_text(invoice_elem, './/TermsRef/FullName'),
            'due_date': get_text(invoice_elem, 'DueDate'),
            'ship_date': get_text(invoice_elem, 'ShipDate'),
            'memo': get_text(invoice_elem, 'Memo'),
        }
        
        # Parse line items
        line_items = []
        for line in invoice_elem.findall('.//InvoiceLineRet'):
            item = {
                'item': get_text(line, './/ItemRef/FullName'),
                'description': get_text(line, 'Desc'),
                'quantity': float(get_text(line, 'Quantity', '0')),
                'rate': float(get_text(line, 'Rate', '0')),
                'amount': float(get_text(line, 'Amount', '0')),
                'service_date': get_text(line, 'ServiceDate'),
            }
            line_items.append(item)
        
        result['line_items'] = line_items
        
        # Parse linked transactions (payments)
        linked_txns = []
        for linked in invoice_elem.findall('.//LinkedTxn'):
            txn = {
                'type': get_text(linked, 'TxnType'),
                'txn_id': get_text(linked, 'TxnID'),
                'date': get_text(linked, 'TxnDate'),
                'ref_number': get_text(linked, 'RefNumber'),
                'amount': float(get_text(linked, 'Amount', '0')),
            }
            linked_txns.append(txn)
        
        result['linked_transactions'] = linked_txns
        
        return result
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string in various formats"""
        if not date_str:
            return None
        
        # Try different date formats
        formats = [
            '%m-%d-%Y',
            '%m/%d/%Y',
            '%Y-%m-%d',
            '%m-%d-%y',
            '%m/%d/%y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def create_invoice(
        self,
        customer_name: str,
        items: List[Dict[str, Any]],
        date: Optional[str] = None,
        ref_number: Optional[str] = None,
        po_number: Optional[str] = None,
        terms: Optional[str] = None,
        due_date: Optional[str] = None,
        memo: Optional[str] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new invoice in QuickBooks
        
        Args:
            customer_name: Customer or job name (e.g., "jeck:Jeff trailer")
            items: List of item lines, each dict should have:
                - item: Item name (required)
                - quantity: Quantity (default: 1)
                - rate: Unit rate (optional)
                - amount: Total amount (optional)
                - description: Line description (optional)
            date: Invoice date (MM-DD-YYYY or MM/DD/YYYY)
            ref_number: Invoice number (auto-generated if not provided)
            po_number: Purchase order number
            terms: Payment terms
            due_date: Due date
            memo: Internal memo
            message: Customer-facing message
        
        Returns:
            Dictionary with invoice details or error
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return {'error': 'Failed to connect to QuickBooks'}
        
        try:
            # Format date
            if date:
                parsed_date = self._parse_date(date)
                date_str = parsed_date.strftime('%Y-%m-%d') if parsed_date else ''
            else:
                date_str = datetime.now().strftime('%Y-%m-%d')
            
            # Build line items XML
            line_items_xml = ""
            for item_data in items:
                quantity = item_data.get('quantity', 1)
                rate = item_data.get('rate', '')
                amount = item_data.get('amount', '')
                description = item_data.get('description', '')
                
                # Format numbers properly for QuickBooks
                if rate:
                    rate = f"{float(rate):.2f}"
                if amount:
                    amount = f"{float(amount):.2f}"
                
                line_items_xml += f"""
                <InvoiceLineAdd>
                    <ItemRef>
                        <FullName>{item_data['item']}</FullName>
                    </ItemRef>
                    {f'<Desc>{description}</Desc>' if description else ''}
                    <Quantity>{quantity}</Quantity>
                    {f'<Rate>{rate}</Rate>' if rate else ''}
                    {f'<Amount>{amount}</Amount>' if amount else ''}
                </InvoiceLineAdd>"""
            
            # Build the invoice add request
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <InvoiceAddRq requestID="1">
            <InvoiceAdd>
                <CustomerRef>
                    <FullName>{customer_name}</FullName>
                </CustomerRef>
                <TxnDate>{date_str}</TxnDate>
                {f'<RefNumber>{ref_number}</RefNumber>' if ref_number else ''}
                {f'<PONumber>{po_number}</PONumber>' if po_number else ''}
                {f'<TermsRef><FullName>{terms}</FullName></TermsRef>' if terms else ''}
                {f'<DueDate>{due_date}</DueDate>' if due_date else ''}
                {f'<Memo>{memo}</Memo>' if memo else ''}
                {f'<CustomerMsgRef><FullName>{message}</FullName></CustomerMsgRef>' if message else ''}
                {line_items_xml}
            </InvoiceAdd>
        </InvoiceAddRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            # Process the request
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            # Parse the response
            root = ET.fromstring(response_xml)
            
            # Check for errors
            error = root.find('.//InvoiceAddRs')
            if error is not None and error.get('statusCode') != '0':
                status_msg = error.get('statusMessage', 'Unknown error')
                logger.error(f"QuickBooks error creating invoice: {status_msg}")
                return {'error': f'QuickBooks error: {status_msg}'}
            
            # Parse the created invoice
            invoice_ret = root.find('.//InvoiceRet')
            if invoice_ret is not None:
                invoice_dict = self._parse_invoice(invoice_ret)
                logger.info(f"Created invoice #{invoice_dict.get('ref_number')} for {customer_name}")
                return invoice_dict
            else:
                return {'error': 'Invoice created but no data returned'}
            
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            return {'error': str(e)}
        finally:
            self.connection.disconnect()
    
    def format_invoice(self, invoice: Dict[str, Any]) -> str:
        """Format invoice for display"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"Invoice #{invoice['ref_number']}")
        lines.append("=" * 60)
        lines.append(f"Date: {invoice['txn_date']}")
        lines.append(f"Customer: {invoice['customer']}")
        lines.append(f"PO Number: {invoice.get('po_number', 'N/A')}")
        lines.append(f"Terms: {invoice.get('terms', 'N/A')}")
        lines.append(f"Due Date: {invoice.get('due_date', 'N/A')}")
        
        if invoice.get('memo'):
            lines.append(f"Memo: {invoice['memo']}")
        
        lines.append("")
        lines.append("LINE ITEMS:")
        lines.append("-" * 60)
        
        for item in invoice.get('line_items', []):
            lines.append(f"{item['item']}")
            if item.get('description'):
                lines.append(f"  {item['description']}")
            lines.append(f"  Qty: {item['quantity']} x ${item['rate']:,.2f} = ${item['amount']:,.2f}")
        
        lines.append("-" * 60)
        lines.append(f"Subtotal: ${invoice['subtotal']:,.2f}")
        if invoice['sales_tax'] > 0:
            lines.append(f"Sales Tax: ${invoice['sales_tax']:,.2f}")
        lines.append(f"Total: ${invoice['total']:,.2f}")
        lines.append(f"Applied: ${invoice['applied_amount']:,.2f}")
        lines.append(f"Balance: ${invoice['balance']:,.2f}")
        
        status = "PAID" if invoice['is_paid'] else "UNPAID"
        if invoice.get('is_pending'):
            status += " (PENDING)"
        lines.append(f"Status: {status}")
        
        if invoice.get('linked_transactions'):
            lines.append("")
            lines.append("PAYMENTS:")
            for txn in invoice['linked_transactions']:
                if txn['type'] == 'ReceivePayment':
                    lines.append(f"  {txn['date']} - Check #{txn.get('ref_number', 'N/A')} - ${txn['amount']:,.2f}")
        
        lines.append("")
        lines.append(f"TxnID: {invoice['txn_id']}")
        
        return "\n".join(lines)