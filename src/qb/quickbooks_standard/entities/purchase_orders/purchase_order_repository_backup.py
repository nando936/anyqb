"""
Purchase Order repository for QuickBooks purchase order operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import xml.etree.ElementTree as ET
import logging
from shared_utilities.fuzzy_matcher import FuzzyMatcher
from shared_utilities.xml_qb_connection import XMLQBConnection

logger = logging.getLogger(__name__)

class PurchaseOrderRepository:
    """Repository for purchase order operations"""
    
    def __init__(self):
        self.connection = XMLQBConnection()
        self.fuzzy_matcher = FuzzyMatcher()
    
    def create_purchase_order(
        self,
        vendor_name: str,
        items: List[Dict[str, Any]],
        date: Optional[str] = None,
        ref_number: Optional[str] = None,
        expected_date: Optional[str] = None,
        memo: Optional[str] = None,
        vendor_msg: Optional[str] = None,
        ship_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new purchase order in QuickBooks
        
        Args:
            vendor_name: Vendor name
            items: List of item lines, each dict should have:
                - item: Item name (required)
                - quantity: Quantity (default: 1)
                - rate: Unit cost (optional)
                - amount: Total amount (optional)
                - description: Line description (optional)
                - customer_job: Customer:Job for job costing (optional)
            date: PO date (MM-DD-YYYY or MM/DD/YYYY)
            ref_number: PO number (auto-generated if not provided)
            expected_date: Expected delivery date
            memo: Internal memo
            vendor_msg: Message to vendor
            ship_to: Ship to address
        
        Returns:
            Dictionary with PO details or error
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return {'error': 'Failed to connect to QuickBooks'}
        
        try:
            # Fuzzy match vendor name
            from quickbooks_standard.entities.vendors.vendor_repository import VendorRepository
            from quickbooks_standard.entities.items.item_repository import ItemRepository
            
            vendor_repo = VendorRepository()
            vendors = vendor_repo.search_vendors(active_only=True)
            
            # Get list of vendor names for fuzzy matching
            vendor_names = [v['name'] for v in vendors]
            vendor_match = self.fuzzy_matcher.find_best_match(
                vendor_name, 
                vendor_names, 
                entity_type='vendor'
            )
            
            if not vendor_match.found:
                return {'error': f"Vendor '{vendor_name}' not found. Please check the spelling or create the vendor first."}
            
            # Use the exact matched vendor name
            matched_vendor_name = vendor_match.exact_name
            logger.info(f"Matched vendor '{vendor_name}' to '{matched_vendor_name}' ({vendor_match.match_type} match)")
            
            # Get all items for fuzzy matching
            item_repo = ItemRepository()
            all_items = item_repo.get_all_items()
            # Filter to active items only
            item_names = [item['name'] for item in all_items if item.get('is_active', True)]
            
            # Get all jobs for fuzzy matching
            from quickbooks_standard.entities.customers.customer_repository import CustomerRepository
            customer_repo = CustomerRepository()
            all_customers = customer_repo.get_all_customers(include_jobs=True)
            # Create a list of customer:job combinations using full_name
            job_names = []
            for cust in all_customers:
                # Use full_name which includes the complete path (e.g., "jeck:Jeff trailer")
                full_name = cust.get('full_name', '')
                if full_name:
                    job_names.append(full_name)
            
            # Fuzzy match and validate each item
            for i, item_data in enumerate(items):
                # Match item name
                item_name = item_data.get('item', '')
                if item_name:
                    item_match = self.fuzzy_matcher.find_best_match(
                        item_name,
                        item_names,
                        entity_type='item'
                    )
                    
                    if not item_match.found:
                        return {'error': f"Item '{item_name}' in line {i+1} not found. Please check the spelling or create the item first."}
                    
                    # Update the item name to the exact match
                    item_data['item'] = item_match.exact_name
                    logger.info(f"Matched item '{item_name}' to '{item_match.exact_name}' ({item_match.match_type} match)")
                
                # Match customer_job if provided
                job_name = item_data.get('customer_job', '')
                if job_name:
                    job_match = self.fuzzy_matcher.find_best_match(
                        job_name,
                        job_names,
                        entity_type='job'
                    )
                    
                    if not job_match.found:
                        return {'error': f"Job '{job_name}' in line {i+1} not found. Please check the spelling or create the job first."}
                    
                    # Update the job name to the exact match
                    item_data['customer_job'] = job_match.exact_name
                    logger.info(f"Matched job '{job_name}' to '{job_match.exact_name}' ({job_match.match_type} match)")
            
            # Format date
            if date:
                parsed_date = self._parse_date(date)
                date_str = parsed_date.strftime('%Y-%m-%d') if parsed_date else ''
            else:
                date_str = datetime.now().strftime('%Y-%m-%d')
            
            # Format expected date
            expected_date_str = ""
            if expected_date:
                parsed_exp_date = self._parse_date(expected_date)
                expected_date_str = parsed_exp_date.strftime('%Y-%m-%d') if parsed_exp_date else ''
            
            # Build line items XML
            line_items_xml = ""
            for item_data in items:
                quantity = item_data.get('quantity', 1)
                rate = item_data.get('rate', '')
                amount = item_data.get('amount', '')
                description = item_data.get('description', '')
                customer_job = item_data.get('customer_job', '')
                
                # Format numbers properly for QuickBooks
                if rate:
                    rate = f"{float(rate):.2f}"
                if amount:
                    amount = f"{float(amount):.2f}"
                
                line_items_xml += f"""
                <PurchaseOrderLineAdd>
                    <ItemRef>
                        <FullName>{item_data['item']}</FullName>
                    </ItemRef>
                    {f'<Desc>{description}</Desc>' if description else ''}
                    <Quantity>{quantity}</Quantity>
                    {f'<Rate>{rate}</Rate>' if rate else ''}
                    {f'<Amount>{amount}</Amount>' if amount else ''}
                    {f'<CustomerRef><FullName>{customer_job}</FullName></CustomerRef>' if customer_job else ''}
                </PurchaseOrderLineAdd>"""
            
            # Build the purchase order add request (using matched vendor name)
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <PurchaseOrderAddRq requestID="1">
            <PurchaseOrderAdd>
                <VendorRef>
                    <FullName>{matched_vendor_name}</FullName>
                </VendorRef>
                <TxnDate>{date_str}</TxnDate>
                {f'<RefNumber>{ref_number}</RefNumber>' if ref_number else ''}
                {f'<ExpectedDate>{expected_date_str}</ExpectedDate>' if expected_date_str else ''}
                {f'<Memo>{memo}</Memo>' if memo else ''}
                {f'<VendorMsg>{vendor_msg}</VendorMsg>' if vendor_msg else ''}
                {f'<ShipToEntityRef><FullName>{ship_to}</FullName></ShipToEntityRef>' if ship_to else ''}
                {line_items_xml}
            </PurchaseOrderAdd>
        </PurchaseOrderAddRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            # Process the request
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            # Parse the response
            root = ET.fromstring(response_xml)
            
            # Check for errors
            error = root.find('.//PurchaseOrderAddRs')
            if error is not None and error.get('statusCode') != '0':
                status_msg = error.get('statusMessage', 'Unknown error')
                logger.error(f"QuickBooks error creating PO: {status_msg}")
                return {'error': f'QuickBooks error: {status_msg}'}
            
            # Parse the created PO
            po_ret = root.find('.//PurchaseOrderRet')
            if po_ret is not None:
                po_dict = self._parse_purchase_order(po_ret)
                logger.info(f"Created PO #{po_dict.get('ref_number')} for {vendor_name}")
                return po_dict
            else:
                return {'error': 'PO created but no data returned'}
            
        except Exception as e:
            logger.error(f"Error creating PO: {str(e)}")
            return {'error': str(e)}
        finally:
            self.connection.disconnect()
    
    def _parse_purchase_order(self, po_elem: ET.Element) -> Dict[str, Any]:
        """Parse a purchase order XML element into a dictionary"""
        
        def get_text(elem, path, default=""):
            found = elem.find(path)
            return found.text if found is not None else default
        
        # Extract basic fields
        result = {
            'txn_id': get_text(po_elem, 'TxnID'),
            'ref_number': get_text(po_elem, 'RefNumber'),
            'txn_date': get_text(po_elem, 'TxnDate'),
            'vendor': get_text(po_elem, './/VendorRef/FullName'),
            'total': float(get_text(po_elem, 'TotalAmount', '0')),
            'is_fully_received': get_text(po_elem, 'IsFullyReceived', 'false') == 'true',
            'expected_date': get_text(po_elem, 'ExpectedDate'),
            'memo': get_text(po_elem, 'Memo'),
            'vendor_msg': get_text(po_elem, 'VendorMsg'),
        }
        
        # Parse line items
        line_items = []
        for line in po_elem.findall('.//PurchaseOrderLineRet'):
            item = {
                'item': get_text(line, './/ItemRef/FullName'),
                'description': get_text(line, 'Desc'),
                'quantity': float(get_text(line, 'Quantity', '0')),
                'rate': float(get_text(line, 'Rate', '0')),
                'amount': float(get_text(line, 'Amount', '0')),
                'customer_job': get_text(line, './/CustomerRef/FullName'),
                'received': float(get_text(line, 'ReceivedQuantity', '0')),
            }
            line_items.append(item)
        
        result['line_items'] = line_items
        
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
    
    def format_purchase_order(self, po: Dict[str, Any]) -> str:
        """Format purchase order for display"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"Purchase Order #{po['ref_number']}")
        lines.append("=" * 60)
        lines.append(f"Date: {po['txn_date']}")
        lines.append(f"Vendor: {po['vendor']}")
        
        if po.get('expected_date'):
            lines.append(f"Expected Date: {po['expected_date']}")
        
        if po.get('memo'):
            lines.append(f"Memo: {po['memo']}")
        
        if po.get('vendor_msg'):
            lines.append(f"Vendor Message: {po['vendor_msg']}")
        
        lines.append("")
        lines.append("LINE ITEMS:")
        lines.append("-" * 60)
        
        for item in po.get('line_items', []):
            lines.append(f"{item['item']}")
            if item.get('description'):
                lines.append(f"  {item['description']}")
            if item.get('customer_job'):
                lines.append(f"  Job: {item['customer_job']}")
            lines.append(f"  Qty: {item['quantity']} x ${item['rate']:.2f} = ${item['amount']:.2f}")
            if item.get('received', 0) > 0:
                lines.append(f"  Received: {item['received']}")
        
        lines.append("-" * 60)
        lines.append(f"Total: ${po['total']:.2f}")
        
        if po.get('is_fully_received'):
            lines.append("Status: FULLY RECEIVED")
        else:
            lines.append("Status: OPEN")
        
        lines.append(f"\nTxnID: {po['txn_id']}")
        
        return "\n".join(lines)
    
    def get_purchase_orders(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        vendor_name: Optional[str] = None,
        open_only: bool = True,
        include_line_items: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get purchase orders with various filters
        
        Args:
            date_from: Start date (MM-DD-YYYY or MM/DD/YYYY)
            date_to: End date (MM-DD-YYYY or MM/DD/YYYY)
            vendor_name: Filter by vendor name (optional)
            open_only: If True, only return open POs (default: True)
            include_line_items: Include line item details (default: True)
        
        Returns:
            List of purchase orders with details
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return []
        
        try:
            # Build the query request
            # Start with basic query structure
            query_parts = []
            
            # Add date filter if both dates provided
            if date_from and date_to:
                # Parse and format dates
                parsed_from = self._parse_date(date_from)
                parsed_to = self._parse_date(date_to)
                
                if parsed_from and parsed_to:
                    from_date = parsed_from.strftime('%Y-%m-%d')
                    to_date = parsed_to.strftime('%Y-%m-%d')
                    query_parts.append(f"""
            <TxnDateRangeFilter>
                <FromTxnDate>{from_date}</FromTxnDate>
                <ToTxnDate>{to_date}</ToTxnDate>
            </TxnDateRangeFilter>""")
                    logger.info(f"Querying POs from {from_date} to {to_date}")
            
            # Add vendor filter if provided
            if vendor_name:
                query_parts.append(f"""
            <EntityFilter>
                <FullName>{vendor_name}</FullName>
            </EntityFilter>""")
            
            # Add line items flag
            query_parts.append(f"""
            <IncludeLineItems>{str(include_line_items).lower()}</IncludeLineItems>""")
            
            # Build complete request
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <PurchaseOrderQueryRq requestID="1">{''.join(query_parts)}
        </PurchaseOrderQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            # Process the request
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            # Parse the response
            root = ET.fromstring(response_xml)
            
            # Check for errors
            error = root.find('.//PurchaseOrderQueryRs')
            if error is not None and error.get('statusCode') != '0':
                status_msg = error.get('statusMessage', 'Unknown error')
                logger.error(f"QuickBooks error querying POs: {status_msg}")
                return []
            
            # Parse all purchase orders
            purchase_orders = []
            for po_elem in root.findall('.//PurchaseOrderRet'):
                po = self._parse_purchase_order(po_elem)
                
                # Filter by open status if requested
                if open_only and po.get('is_fully_received', False):
                    continue  # Skip fully received (closed) POs
                
                purchase_orders.append(po)
            
            logger.info(f"Found {len(purchase_orders)} purchase orders")
            return purchase_orders
            
        except Exception as e:
            logger.error(f"Error getting purchase orders: {str(e)}")
            return []
        finally:
            self.connection.disconnect()
    
    def delete_purchase_order(self, txn_id: str) -> Dict[str, Any]:
        """
        Delete a purchase order from QuickBooks
        
        Args:
            txn_id: Transaction ID of the purchase order to delete
        
        Returns:
            Dictionary with success status or error
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return {'error': 'Failed to connect to QuickBooks'}
        
        try:
            # Build the delete request
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <TxnDelRq requestID="1">
            <TxnDelType>PurchaseOrder</TxnDelType>
            <TxnID>{txn_id}</TxnID>
        </TxnDelRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            # Process the request
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            # Parse the response
            root = ET.fromstring(response_xml)
            
            # Check for errors
            del_rs = root.find('.//TxnDelRs')
            if del_rs is not None:
                status_code = del_rs.get('statusCode')
                status_msg = del_rs.get('statusMessage', '')
                
                if status_code == '0':
                    logger.info(f"Successfully deleted PO with TxnID: {txn_id}")
                    return {'success': True, 'message': f'Purchase Order deleted successfully (TxnID: {txn_id})'}
                else:
                    logger.error(f"Failed to delete PO: {status_msg}")
                    return {'error': f'Failed to delete: {status_msg}'}
            
            return {'error': 'No response from QuickBooks'}
            
        except Exception as e:
            logger.error(f"Error deleting purchase order: {str(e)}")
            return {'error': str(e)}
        finally:
            self.connection.disconnect()
    
    def receive_purchase_order(
        self,
        po_ref_number: Optional[str] = None,
        po_txn_id: Optional[str] = None,
        line_items: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Receive items from a purchase order (create Item Receipt)
        
        Args:
            po_ref_number: PO reference number (e.g., "269066")
            po_txn_id: PO transaction ID (alternative to ref_number)
            line_items: List of items to receive, each dict should have:
                - item: Item name (will be fuzzy matched)
                - quantity: Quantity to receive
                - line_number: Optional specific line number from PO
        
        Returns:
            Dictionary with receipt details or error
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return {'error': 'Failed to connect to QuickBooks'}
        
        try:
            # First, get the PO details to validate
            if not po_txn_id and not po_ref_number:
                return {'error': 'Either po_ref_number or po_txn_id must be provided'}
            
            # Get the PO details first
            po_details = None
            if po_txn_id:
                # Query by TxnID
                request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <PurchaseOrderQueryRq requestID="1">
            <TxnID>{po_txn_id}</TxnID>
            <IncludeLineItems>true</IncludeLineItems>
        </PurchaseOrderQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
            else:
                # Query by RefNumber
                request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <PurchaseOrderQueryRq requestID="1">
            <RefNumber>{po_ref_number}</RefNumber>
            <IncludeLineItems>true</IncludeLineItems>
        </PurchaseOrderQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            root = ET.fromstring(response_xml)
            po_elem = root.find('.//PurchaseOrderRet')
            
            if po_elem is None:
                return {'error': f'Purchase Order not found: {po_ref_number or po_txn_id}'}
            
            po_details = self._parse_purchase_order(po_elem)
            
            # Build the Item Receipt
            vendor_name = po_details['vendor']
            po_txn_id_actual = po_details['txn_id']
            
            # Build line items for receipt
            receipt_lines_xml = ""
            
            if line_items:
                # User specified which items to receive
                for receive_item in line_items:
                    item_name = receive_item.get('item', '')
                    quantity = receive_item.get('quantity', 0)
                    
                    # Fuzzy match the item name
                    from quickbooks_standard.entities.items.item_repository import ItemRepository
                    item_repo = ItemRepository()
                    all_items = item_repo.get_all_items()
                    item_names = [item['name'] for item in all_items if item.get('is_active', True)]
                    
                    item_match = self.fuzzy_matcher.find_best_match(
                        item_name,
                        item_names,
                        entity_type='item'
                    )
                    
                    if not item_match.found:
                        return {'error': f"Item '{item_name}' not found"}
                    
                    matched_item_name = item_match.exact_name
                    
                    # Find the corresponding PO line
                    po_line = None
                    for line in po_details.get('line_items', []):
                        if line['item'] == matched_item_name:
                            po_line = line
                            break
                    
                    if not po_line:
                        return {'error': f"Item '{matched_item_name}' not found in PO #{po_details['ref_number']}"}
                    
                    # Add the receipt line
                    # For linked POs, we need to specify OverrideItemAccountRef
                    receipt_lines_xml += f"""
                <ItemReceiptLineAdd>
                    <ItemRef>
                        <FullName>{matched_item_name}</FullName>
                    </ItemRef>
                    <Quantity>{quantity}</Quantity>
                </ItemReceiptLineAdd>"""
            else:
                # Receive all items from PO in full
                for line in po_details.get('line_items', []):
                    remaining = line['quantity'] - line.get('received', 0)
                    if remaining > 0:
                        receipt_lines_xml += f"""
                <ItemReceiptLineAdd>
                    <ItemRef>
                        <FullName>{line['item']}</FullName>
                    </ItemRef>
                    <Quantity>{remaining}</Quantity>
                </ItemReceiptLineAdd>"""
            
            # Create the Item Receipt
            from datetime import datetime
            receipt_date = datetime.now().strftime('%Y-%m-%d')
            
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <ItemReceiptAddRq requestID="1">
            <ItemReceiptAdd>
                <VendorRef>
                    <FullName>{vendor_name}</FullName>
                </VendorRef>
                <TxnDate>{receipt_date}</TxnDate>
                <RefNumber>Receipt-{po_details['ref_number']}</RefNumber>
                <Memo>Receipt for PO #{po_details['ref_number']}</Memo>
                <LinkToTxnID>{po_txn_id_actual}</LinkToTxnID>
                {receipt_lines_xml}
            </ItemReceiptAdd>
        </ItemReceiptAddRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            # Process the receipt
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            # Parse response
            root = ET.fromstring(response_xml)
            
            # Check for errors
            receipt_rs = root.find('.//ItemReceiptAddRs')
            if receipt_rs is not None:
                status_code = receipt_rs.get('statusCode')
                status_msg = receipt_rs.get('statusMessage', '')
                
                if status_code == '0':
                    receipt_ret = root.find('.//ItemReceiptRet')
                    if receipt_ret:
                        receipt_txn_id = receipt_ret.find('TxnID').text if receipt_ret.find('TxnID') is not None else ''
                        receipt_ref = receipt_ret.find('RefNumber').text if receipt_ret.find('RefNumber') is not None else ''
                        
                        # Format success message
                        message = f"Successfully received items from PO #{po_details['ref_number']}\n"
                        message += f"Receipt Reference: {receipt_ref}\n"
                        message += f"Receipt TxnID: {receipt_txn_id}\n\n"
                        message += "Items Received:\n"
                        
                        if line_items:
                            for item in line_items:
                                message += f"  - {item['item']}: {item['quantity']} units\n"
                        else:
                            for line in po_details.get('line_items', []):
                                remaining = line['quantity'] - line.get('received', 0)
                                if remaining > 0:
                                    message += f"  - {line['item']}: {remaining} units\n"
                        
                        return {'success': True, 'message': message, 'receipt_txn_id': receipt_txn_id}
                else:
                    return {'error': f'Failed to create receipt: {status_msg}'}
            
            return {'error': 'No response from QuickBooks'}
            
        except Exception as e:
            logger.error(f"Error receiving purchase order: {str(e)}")
            return {'error': str(e)}
        finally:
            self.connection.disconnect()