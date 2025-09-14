"""
Fast QuickBooks Connection using QBFC SDK
Based on anyqb's faster connection method
"""

import win32com.client
import pythoncom
import atexit
import logging

logger = logging.getLogger(__name__)

class FastQBConnection:
    """Fast QuickBooks connection using QBFC SDK"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.qb = None
            self.is_connected = False
            self.request_set = None
            self.response_set = None
            # Don't register atexit for MCP server - it needs to stay connected
            # atexit.register(self.disconnect)
    
    def connect(self):
        """Connect to QuickBooks using QBFC"""
        if self.is_connected and self.qb:
            return True
        
        try:
            pythoncom.CoInitialize()
            # Use QBFC16 like anyqb does - much faster!
            self.qb = win32com.client.Dispatch("QBFC16.QBSessionManager")
            
            # Open connection
            self.qb.OpenConnection("", "qbmcp")
            
            # Begin session (mode 2 = DoNotCare - connects to open file)
            self.qb.BeginSession("", 2)
            
            self.is_connected = True
            logger.info("Connected to QuickBooks via QBFC (fast mode)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.disconnect()
            return False
    
    def create_request_set(self):
        """Create a new request set"""
        if not self.is_connected:
            if not self.connect():
                raise ConnectionError("Cannot connect to QuickBooks")
        
        # Create message set request
        self.request_set = self.qb.CreateMsgSetRequest("US", 16, 0)
        self.request_set.Attributes.OnError = 0  # stopOnError
        return self.request_set
    
    def process_request_set(self, request_set):
        """Process a request set and return response"""
        if not self.is_connected:
            if not self.connect():
                raise ConnectionError("Cannot connect to QuickBooks")
        
        try:
            self.response_set = self.qb.DoRequests(request_set)
            return self.response_set
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from QuickBooks"""
        try:
            if self.qb and self.is_connected:
                self.qb.EndSession()
                self.qb.CloseConnection()
                self.qb = None
            self.is_connected = False
            logger.info("Disconnected from QuickBooks")
        except:
            self.is_connected = False
            self.qb = None

# Global instance
fast_qb_connection = FastQBConnection()