"""
XML QuickBooks Connection for proper COGS account retrieval
Uses QBXML instead of QBFC to handle Cost of Goods Sold accounts correctly
"""

import win32com.client
import xml.etree.ElementTree as ET
import logging
import atexit

logger = logging.getLogger(__name__)

class XMLQBConnection:
    """XML QuickBooks connection that properly returns COGS accounts"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.session_manager = None
            self.ticket = None
            self.is_connected = False
            atexit.register(self.disconnect)
    
    def connect(self):
        """Connect to QuickBooks using XML"""
        if self.is_connected and self.session_manager:
            return True
        
        try:
            # Initialize COM for this thread
            import pythoncom
            pythoncom.CoInitialize()
            
            # Create the session manager
            self.session_manager = win32com.client.Dispatch("QBXMLRP2.RequestProcessor")
            
            # Open connection with qbmcp app name (CRITICAL - this is the authorized app)
            self.session_manager.OpenConnection2("", "qbmcp", 1)  # 1 = localQBD
            
            # Begin session
            self.ticket = self.session_manager.BeginSession("", 2)  # 2 = qbFileOpenDoNotCare
            
            self.is_connected = True
            logger.info("Connected to QuickBooks via XML (for COGS support)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect via XML: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from QuickBooks"""
        if self.is_connected and self.session_manager:
            try:
                if self.ticket:
                    self.session_manager.EndSession(self.ticket)
                self.session_manager.CloseConnection()
                logger.info("Disconnected from QuickBooks XML")
            except Exception as e:
                logger.error(f"Error during XML disconnect: {e}")
            finally:
                self.is_connected = False
                self.session_manager = None
                self.ticket = None
                # Uninitialize COM
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except:
                    pass
    
    def query_check(self, txn_id):
        """Query a check by transaction ID using XML"""
        if not self.connect():
            return None
        
        try:
            # Build XML request
            xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="13.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <CheckQueryRq>
            <TxnID>{txn_id}</TxnID>
            <IncludeLineItems>true</IncludeLineItems>
        </CheckQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
            
            # Process the request
            response_xml = self.session_manager.ProcessRequest(self.ticket, xml_request)
            
            # Parse the XML response
            root = ET.fromstring(response_xml)
            
            # Find CheckRet element
            check_ret = root.find(".//CheckRet")
            if check_ret is None:
                logger.error(f"No check found for TxnID {txn_id}")
                return None
            
            # Parse check data
            check_data = self._parse_check_xml(check_ret)
            return check_data
            
        except Exception as e:
            logger.error(f"Failed to query check via XML: {e}")
            return None
    
    def _parse_check_xml(self, check_ret):
        """Parse check data from XML response"""
        check_data = {}
        
        # Basic fields
        if check_ret.find("TxnID") is not None:
            check_data['txn_id'] = check_ret.find("TxnID").text
        
        if check_ret.find("EditSequence") is not None:
            check_data['edit_sequence'] = check_ret.find("EditSequence").text
        
        if check_ret.find("TxnNumber") is not None:
            check_data['txn_number'] = check_ret.find("TxnNumber").text
        
        if check_ret.find("TxnDate") is not None:
            check_data['txn_date'] = check_ret.find("TxnDate").text
        
        if check_ret.find("RefNumber") is not None:
            check_data['ref_number'] = check_ret.find("RefNumber").text
        
        if check_ret.find("Amount") is not None:
            check_data['amount'] = float(check_ret.find("Amount").text)
        
        if check_ret.find("Memo") is not None:
            check_data['memo'] = check_ret.find("Memo").text
        
        # Payee
        payee_ref = check_ret.find("PayeeEntityRef/FullName")
        if payee_ref is not None:
            check_data['payee_name'] = payee_ref.text
        
        # Bank account
        account_ref = check_ret.find("AccountRef/FullName")
        if account_ref is not None:
            check_data['bank_account'] = account_ref.text
        
        # Parse expense lines (THIS IS WHERE XML SHINES - IT RETURNS COGS!)
        expense_lines = []
        for expense_line in check_ret.findall("ExpenseLineRet"):
            line_data = {}
            
            account = expense_line.find("AccountRef/FullName")
            if account is not None:
                line_data['expense_account'] = account.text
            
            amount = expense_line.find("Amount")
            if amount is not None:
                line_data['amount'] = float(amount.text)
            
            customer = expense_line.find("CustomerRef/FullName")
            if customer is not None:
                line_data['customer_job'] = customer.text
            
            memo = expense_line.find("Memo")
            if memo is not None:
                line_data['memo'] = memo.text
            
            txn_line_id = expense_line.find("TxnLineID")
            if txn_line_id is not None:
                line_data['txn_line_id'] = txn_line_id.text
            
            expense_lines.append(line_data)
        
        check_data['expense_lines'] = expense_lines
        
        # Parse item lines
        item_lines = []
        for item_line in check_ret.findall("ItemLineRet"):
            line_data = {}
            
            item = item_line.find("ItemRef/FullName")
            if item is not None:
                line_data['item'] = item.text
            
            amount = item_line.find("Amount")
            if amount is not None:
                line_data['amount'] = float(amount.text)
            
            quantity = item_line.find("Quantity")
            if quantity is not None:
                line_data['quantity'] = float(quantity.text)
            
            cost = item_line.find("Cost")
            if cost is not None:
                line_data['cost'] = float(cost.text)
            
            desc = item_line.find("Desc")
            if desc is not None:
                line_data['description'] = desc.text
            
            customer = item_line.find("CustomerRef/FullName")
            if customer is not None:
                line_data['customer_job'] = customer.text
            
            item_lines.append(line_data)
        
        check_data['item_lines'] = item_lines
        
        return check_data

# Singleton instance
xml_qb_connection = XMLQBConnection()