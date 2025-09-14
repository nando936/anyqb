"""
Item Receipt Repository - Handle ItemReceipt operations
"""

from typing import Dict, Any, List, Optional
from shared_utilities.xml_qb_connection import XMLQBConnection
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)

class ItemReceiptRepository:
    """Repository for ItemReceipt operations"""
    
    def __init__(self):
        self.connection = XMLQBConnection()
    
    def search_item_receipts(
        self,
        vendor_name: Optional[str] = None,
        ref_number: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        txn_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for ItemReceipts with various filters
        
        Args:
            vendor_name: Filter by vendor name
            ref_number: Filter by reference number
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            txn_id: Specific transaction ID
        
        Returns:
            List of ItemReceipt dictionaries
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return []
        
        try:
            # Build filters
            filters = []
            
            if txn_id:
                filters.append(f"<TxnID>{txn_id}</TxnID>")
            elif ref_number:
                filters.append(f"<RefNumber>{ref_number}</RefNumber>")
            else:
                # Use date filter if provided
                if date_from or date_to:
                    date_filter = "<TxnDateRangeFilter>"
                    if date_from:
                        date_filter += f"<FromTxnDate>{date_from}</FromTxnDate>"
                    if date_to:
                        date_filter += f"<ToTxnDate>{date_to}</ToTxnDate>"
                    date_filter += "</TxnDateRangeFilter>"
                    filters.append(date_filter)
                
                # Note: EntityFilter doesn't work with ItemReceiptQuery
                # We'll filter by vendor in Python after fetching
            
            filter_xml = "".join(filters)
            
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <ItemReceiptQueryRq requestID="1">
            {filter_xml}
            <IncludeLineItems>true</IncludeLineItems>
        </ItemReceiptQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            # Parse response
            root = ET.fromstring(response_xml)
            
            # Check status
            receipt_rs = root.find('.//ItemReceiptQueryRs')
            if receipt_rs:
                status_code = receipt_rs.get('statusCode')
                if status_code != '0':
                    logger.error(f"Query failed: {receipt_rs.get('statusMessage', '')}")
                    return []
            
            # Parse receipts
            receipts = []
            for receipt_elem in root.findall('.//ItemReceiptRet'):
                receipt = self._parse_item_receipt(receipt_elem)
                # Filter by vendor if specified
                if vendor_name:
                    if receipt['vendor'].lower() == vendor_name.lower():
                        receipts.append(receipt)
                else:
                    receipts.append(receipt)
            
            return receipts
            
        except Exception as e:
            logger.error(f"Error searching ItemReceipts: {str(e)}")
            return []
        finally:
            self.connection.disconnect()
    
    def _parse_item_receipt(self, receipt_elem) -> Dict[str, Any]:
        """Parse ItemReceiptRet element into dictionary"""
        receipt = {
            'txn_id': receipt_elem.find('TxnID').text if receipt_elem.find('TxnID') is not None else '',
            'ref_number': receipt_elem.find('RefNumber').text if receipt_elem.find('RefNumber') is not None else '',
            'vendor': receipt_elem.find('.//VendorRef/FullName').text if receipt_elem.find('.//VendorRef/FullName') is not None else '',
            'date': receipt_elem.find('TxnDate').text if receipt_elem.find('TxnDate') is not None else '',
            'memo': receipt_elem.find('Memo').text if receipt_elem.find('Memo') is not None else '',
            'line_items': []
        }
        
        # Parse line items
        for line in receipt_elem.findall('.//ItemLineRet'):
            item_name = line.find('.//ItemRef/FullName').text if line.find('.//ItemRef/FullName') is not None else ''
            qty = line.find('Quantity').text if line.find('Quantity') is not None else '0'
            
            receipt['line_items'].append({
                'item': item_name,
                'quantity': float(qty)
            })
        
        return receipt
    
    def delete_item_receipt(self, txn_id: str) -> Dict[str, Any]:
        """
        Delete an ItemReceipt by transaction ID
        
        Args:
            txn_id: Transaction ID of the ItemReceipt to delete
        
        Returns:
            Dictionary with success/error status
        """
        if not self.connection.connect():
            logger.error("Failed to connect to QuickBooks")
            return {'error': 'Failed to connect to QuickBooks'}
        
        try:
            # First, query the receipt to get details for confirmation
            # We need to do this query directly since search_item_receipts disconnects
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <ItemReceiptQueryRq requestID="1">
            <TxnID>{txn_id}</TxnID>
            <IncludeLineItems>true</IncludeLineItems>
        </ItemReceiptQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            # Parse response
            root = ET.fromstring(response_xml)
            receipt_elem = root.find('.//ItemReceiptRet')
            
            if receipt_elem is None:
                return {'error': f'ItemReceipt not found: {txn_id}'}
            
            receipt = self._parse_item_receipt(receipt_elem)
            
            # Build delete request
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <TxnDelRq requestID="1">
            <TxnDelType>ItemReceipt</TxnDelType>
            <TxnID>{txn_id}</TxnID>
        </TxnDelRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            response_xml = self.connection.session_manager.ProcessRequest(
                self.connection.ticket, request_xml
            )
            
            # Parse response
            root = ET.fromstring(response_xml)
            
            # Check status
            del_rs = root.find('.//TxnDelRs')
            if del_rs:
                status_code = del_rs.get('statusCode')
                status_msg = del_rs.get('statusMessage', '')
                
                if status_code == '0':
                    return {
                        'success': True,
                        'message': f"Successfully deleted ItemReceipt {receipt['ref_number']} (TxnID: {txn_id})",
                        'deleted_receipt': receipt
                    }
                else:
                    return {'error': f'Failed to delete ItemReceipt: {status_msg}'}
            
            return {'error': 'No response from QuickBooks'}
            
        except Exception as e:
            logger.error(f"Error deleting ItemReceipt: {str(e)}")
            return {'error': str(e)}
        finally:
            self.connection.disconnect()