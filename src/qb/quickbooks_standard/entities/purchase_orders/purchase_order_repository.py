"""
Purchase Order repository for QuickBooks purchase order operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import xml.etree.ElementTree as ET
import logging
from qb.shared_utilities.fuzzy_matcher import FuzzyMatcher
from qb.shared_utilities.xml_qb_connection import XMLQBConnection
from qb.shared_utilities.fast_qb_connection import FastQBConnection

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
            vendor_name: Name of the vendor (will be fuzzy matched)
            items: List of items to order, each dict should have:
                - item: Item name (will be fuzzy matched)
                - quantity: Quantity to order
                - rate: Optional rate per unit
                - customer_job: Optional customer:job assignment
            date: Order date (defaults to today)
            ref_number: PO reference number (QuickBooks will auto-generate if not provided)
            expected_date: Expected delivery date
            memo: Internal memo
            vendor_msg: Message to vendor (prints on PO)
            ship_to: Shipping address

        Returns:
            Dictionary with PO details or error
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return {'error': 'Failed to connect to QuickBooks'}

        try:
            # Fuzzy match the vendor name
            from qb.quickbooks_standard.entities.vendors.vendor_repository import VendorRepository
            vendor_repo = VendorRepository()
            all_vendors = vendor_repo.get_all_vendors()
            vendor_names = [v['name'] for v in all_vendors if v.get('is_active', True)]

            vendor_match = self.fuzzy_matcher.find_best_match(
                vendor_name,
                vendor_names,
                entity_type='vendor'
            )

            if not vendor_match.found:
                return {'error': f"Vendor '{vendor_name}' not found"}

            matched_vendor_name = vendor_match.exact_name

            # Fuzzy match item names
            from qb.quickbooks_standard.entities.items.item_repository import ItemRepository
            item_repo = ItemRepository()
            all_items = item_repo.get_all_items()
            item_names = [item['name'] for item in all_items if item.get('is_active', True)]

            # Build the line items XML
            line_items_xml = ""
            for item_data in items:
                item_name = item_data.get('item', '')
                quantity = item_data.get('quantity', 0)
                rate = item_data.get('rate')
                customer_job = item_data.get('customer_job')

                # Fuzzy match the item name
                item_match = self.fuzzy_matcher.find_best_match(
                    item_name,
                    item_names,
                    entity_type='item'
                )

                if not item_match.found:
                    return {'error': f"Item '{item_name}' not found"}

                matched_item_name = item_match.exact_name

                # Build the line item XML
                line_xml = f"""
                <PurchaseOrderLineAdd>
                    <ItemRef>
                        <FullName>{matched_item_name}</FullName>
                    </ItemRef>
                    <Quantity>{quantity}</Quantity>"""

                if rate is not None:
                    line_xml += f"""
                    <Rate>{rate}</Rate>"""

                if customer_job:
                    # Fuzzy match the customer:job
                    from qb.quickbooks_standard.entities.customers.customer_repository import CustomerRepository
                    customer_repo = CustomerRepository()
                    all_customers = customer_repo.get_all_customers(include_jobs=True)
                    customer_job_names = [c['full_name'] for c in all_customers]

                    job_match = self.fuzzy_matcher.find_best_match(
                        customer_job,
                        customer_job_names,
                        entity_type='customer:job'
                    )

                    if job_match.found:
                        line_xml += f"""
                    <CustomerRef>
                        <FullName>{job_match.exact_name}</FullName>
                    </CustomerRef>"""

                line_xml += """
                </PurchaseOrderLineAdd>"""

                line_items_xml += line_xml

            # Build the purchase order XML
            po_date = date or datetime.now().strftime('%Y-%m-%d')

            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <PurchaseOrderAddRq requestID="1">
            <PurchaseOrderAdd>
                <VendorRef>
                    <FullName>{matched_vendor_name}</FullName>
                </VendorRef>
                <TxnDate>{po_date}</TxnDate>"""

            if ref_number:
                request_xml += f"""
                <RefNumber>{ref_number}</RefNumber>"""

            if expected_date:
                request_xml += f"""
                <ExpectedDate>{expected_date}</ExpectedDate>"""

            if memo:
                request_xml += f"""
                <Memo>{memo}</Memo>"""

            if vendor_msg:
                request_xml += f"""
                <VendorMsg>{vendor_msg}</VendorMsg>"""

            request_xml += f"""
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
            add_rs = root.find('.//PurchaseOrderAddRs')
            if add_rs is not None:
                status_code = add_rs.get('statusCode')
                status_msg = add_rs.get('statusMessage', '')

                if status_code == '0':
                    # Parse the created PO
                    po_ret = add_rs.find('PurchaseOrderRet')
                    if po_ret is not None:
                        txn_id = po_ret.find('TxnID').text
                        ref_num = po_ret.find('RefNumber').text
                        total = po_ret.find('TotalAmount').text

                        logger.info(f"Successfully created PO #{ref_num} for {matched_vendor_name}")
                        return {
                            'success': True,
                            'txn_id': txn_id,
                            'ref_number': ref_num,
                            'vendor': matched_vendor_name,
                            'total': float(total),
                            'message': f'Purchase Order #{ref_num} created successfully for {matched_vendor_name}'
                        }
                else:
                    logger.error(f"Failed to create PO: {status_msg}")
                    return {'error': f'Failed to create PO: {status_msg}'}

            return {'error': 'No response from QuickBooks'}

        except Exception as e:
            logger.error(f"Error creating purchase order: {str(e)}")
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
                'txn_line_id': get_text(line, 'TxnLineID'),
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
            lines.append(f"  Quantity: {item['quantity']}")
            if item.get('rate'):
                lines.append(f"  Rate: ${item['rate']:.2f}")
            lines.append(f"  Amount: ${item['amount']:.2f}")
            if item.get('customer_job'):
                lines.append(f"  Customer/Job: {item['customer_job']}")
            if item.get('received', 0) > 0:
                lines.append(f"  Received: {item['received']}")
                remaining = item['quantity'] - item['received']
                lines.append(f"  Remaining: {remaining}")
            lines.append("")

        lines.append("-" * 60)
        lines.append(f"TOTAL: ${po['total']:.2f}")

        if po.get('is_fully_received'):
            lines.append("STATUS: Fully Received")
        else:
            lines.append("STATUS: Open")

        lines.append("=" * 60)

        return "\n".join(lines)

    def get_purchase_orders(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        vendor_name: Optional[str] = None,
        open_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get purchase orders from QuickBooks

        Args:
            date_from: Start date (format: MM-DD-YYYY or YYYY-MM-DD)
            date_to: End date (format: MM-DD-YYYY or YYYY-MM-DD)
            vendor_name: Filter by vendor name (fuzzy matched)
            open_only: If True, only return open (not fully received) POs

        Returns:
            List of purchase order dictionaries
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return []

        try:
            # Build the query
            request_xml = """<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <PurchaseOrderQueryRq requestID="1">"""

            # Add date range filter if provided
            if date_from or date_to:
                # Parse dates to ensure proper format
                from_date = self._parse_date(date_from) if date_from else None
                to_date = self._parse_date(date_to) if date_to else None

                if from_date or to_date:
                    request_xml += """
            <ModifiedDateRangeFilter>"""
                    if from_date:
                        request_xml += f"""
                <FromModifiedDate>{from_date.strftime('%Y-%m-%dT00:00:00')}</FromModifiedDate>"""
                    if to_date:
                        request_xml += f"""
                <ToModifiedDate>{to_date.strftime('%Y-%m-%dT23:59:59')}</ToModifiedDate>"""
                    request_xml += """
            </ModifiedDateRangeFilter>"""

            # Add vendor filter if provided
            if vendor_name:
                # Fuzzy match the vendor name first
                from qb.quickbooks_standard.entities.vendors.vendor_repository import VendorRepository
                vendor_repo = VendorRepository()
                all_vendors = vendor_repo.get_all_vendors()
                vendor_names = [v['name'] for v in all_vendors if v.get('is_active', True)]

                vendor_match = self.fuzzy_matcher.find_best_match(
                    vendor_name,
                    vendor_names,
                    entity_type='vendor'
                )

                if vendor_match.found:
                    request_xml += f"""
            <EntityFilter>
                <FullNameList>
                    <FullName>{vendor_match.exact_name}</FullName>
                </FullNameList>
            </EntityFilter>"""

            request_xml += """
            <IncludeLineItems>true</IncludeLineItems>
        </PurchaseOrderQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""

            # Process the request
            logger.info(f"Querying POs from {date_from} to {date_to}")
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
        Receive items from a purchase order using QBFC (create Item Receipt)

        Args:
            po_ref_number: PO reference number (e.g., "269066")
            po_txn_id: PO transaction ID (alternative to ref_number)
            line_items: List of items to receive, each dict should have:
                - item: Item name (will be fuzzy matched)
                - quantity: Quantity to receive

        Returns:
            Dictionary with receipt details or error
        """
        from datetime import datetime

        # Use QBFC connection for proper job assignment handling
        fast_conn = FastQBConnection()

        if not fast_conn.connect():
            logger.error("Failed to connect to QuickBooks via QBFC")
            return {'error': 'Failed to connect to QuickBooks'}

        try:
            # First, query the PO to get details
            request_set = fast_conn.create_request_set()
            po_query = request_set.AppendPurchaseOrderQueryRq()

            if po_ref_number:
                po_query.ORTxnQuery.RefNumberList.Add(po_ref_number)
            elif po_txn_id:
                po_query.ORTxnQuery.TxnIDList.Add(po_txn_id)
            else:
                return {'error': 'Either po_ref_number or po_txn_id is required'}

            po_query.IncludeLineItems.SetValue(True)

            # Process the query
            response_set = fast_conn.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)

            if response.StatusCode != 0:
                return {'error': f'Failed to query PO: {response.StatusMessage}'}

            if response.Detail is None or response.Detail.Count == 0:
                return {'error': f'Purchase Order not found: {po_ref_number or po_txn_id}'}

            # Get PO details
            po = response.Detail.GetAt(0)
            po_txn_id_actual = po.TxnID.GetValue()
            po_ref_num = po.RefNumber.GetValue()
            vendor_name = po.VendorRef.FullName.GetValue()

            # Get PO line details including CustomerRef
            po_lines = []
            line_count = po.ORPurchaseOrderLineRetList.Count if po.ORPurchaseOrderLineRetList else 0

            for i in range(line_count):
                line_ret = po.ORPurchaseOrderLineRetList.GetAt(i)
                if hasattr(line_ret, 'PurchaseOrderLineRet'):
                    po_line = line_ret.PurchaseOrderLineRet
                    line_info = {
                        'txn_line_id': po_line.TxnLineID.GetValue(),
                        'item': po_line.ItemRef.FullName.GetValue() if po_line.ItemRef else None,
                        'quantity': float(po_line.Quantity.GetValue()) if po_line.Quantity else 0,
                        'received': float(po_line.ReceivedQuantity.GetValue()) if po_line.ReceivedQuantity else 0,
                        'customer_job': po_line.CustomerRef.FullName.GetValue() if po_line.CustomerRef else None
                    }
                    if line_info['item']:
                        po_lines.append(line_info)

            # Create Item Receipt
            receipt_request = fast_conn.create_request_set()
            item_receipt_add = receipt_request.AppendItemReceiptAddRq()

            # Set basic receipt info
            item_receipt_add.VendorRef.FullName.SetValue(vendor_name)
            item_receipt_add.TxnDate.SetValue(datetime.now())
            item_receipt_add.RefNumber.SetValue(f"Receipt-{po_ref_num}-{datetime.now().strftime('%H%M')}")
            item_receipt_add.Memo.SetValue(f"Receipt for PO #{po_ref_num}")

            if line_items:
                # User specified which items to receive - partial receipt
                for receive_item in line_items:
                    item_name = receive_item.get('item', '')
                    quantity = receive_item.get('quantity', 0)

                    # Fuzzy match the item name
                    from qb.quickbooks_standard.entities.items.item_repository import ItemRepository
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
                    matching_po_line = None
                    for po_line in po_lines:
                        if po_line['item'] == matched_item_name:
                            matching_po_line = po_line
                            break

                    if not matching_po_line:
                        return {'error': f"Item '{matched_item_name}' not found in PO #{po_ref_num}"}

                    # Add line item to receipt
                    line_add = item_receipt_add.ORItemLineAddList.Append()
                    item_line = line_add.ItemLineAdd

                    # IMPORTANT: When using LinkToTxn, do NOT set ItemRef
                    # The item info is pulled from the PO line automatically
                    item_line.Quantity.SetValue(float(quantity))

                    # Link to PO line (this pulls item info automatically)
                    item_line.LinkToTxn.TxnID.SetValue(po_txn_id_actual)
                    item_line.LinkToTxn.TxnLineID.SetValue(matching_po_line['txn_line_id'])

                    # CRITICAL: Set CustomerRef to preserve job assignment
                    # This must come AFTER LinkToTxn
                    if matching_po_line.get('customer_job'):
                        item_line.CustomerRef.FullName.SetValue(matching_po_line['customer_job'])
                        # BillableStatus: 0=NotBillable, 1=Billable, 2=HasBeenBilled
                        item_line.BillableStatus.SetValue(1)  # Set as Billable
            else:
                # Receive all items from PO in full
                # Use header-level link for simplicity
                item_receipt_add.LinkToTxnIDList.Add(po_txn_id_actual)

            # Process the Item Receipt
            receipt_response_set = fast_conn.process_request_set(receipt_request)
            receipt_response = receipt_response_set.ResponseList.GetAt(0)

            # Check for errors
            if receipt_response.StatusCode != 0:
                return {'error': f'Failed to create receipt: {receipt_response.StatusMessage}'}

            receipt_ret = receipt_response.Detail
            if receipt_ret:
                receipt_txn_id = receipt_ret.TxnID.GetValue()
                receipt_ref = receipt_ret.RefNumber.GetValue()

                result = {
                    'success': True,
                    'txn_id': receipt_txn_id,
                    'ref_number': receipt_ref,
                    'po_ref_number': po_ref_num,
                    'message': f'Successfully created receipt {receipt_ref} from PO #{po_ref_num}'
                }

                # Get received items details
                received_items = []
                line_count = receipt_ret.ORItemLineRetList.Count if receipt_ret.ORItemLineRetList else 0

                for i in range(line_count):
                    line_ret = receipt_ret.ORItemLineRetList.GetAt(i)
                    if hasattr(line_ret, 'ItemLineRet'):
                        item_line = line_ret.ItemLineRet
                        if item_line.ItemRef and item_line.Quantity:
                            item_detail = {
                                'item': item_line.ItemRef.FullName.GetValue(),
                                'quantity': float(item_line.Quantity.GetValue())
                            }
                            # Check if CustomerRef was preserved
                            if hasattr(item_line, 'CustomerRef') and item_line.CustomerRef:
                                item_detail['customer_job'] = item_line.CustomerRef.FullName.GetValue()
                            received_items.append(item_detail)

                result['received_items'] = received_items
                return result

            return {'error': 'No receipt details returned'}

        except Exception as e:
            logger.error(f"Error receiving purchase order: {str(e)}")
            return {'error': str(e)}
        finally:
            fast_conn.disconnect()