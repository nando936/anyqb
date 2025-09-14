"""
Comprehensive SDK Search Engine
Provides detailed SDK information from the complete OSR database
"""
import sqlite3
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import re

class ComprehensiveSDKEngine:
    """Complete SDK documentation engine with full OSR data"""
    
    def __init__(self):
        # Try the comprehensive database first
        self.db_path = Path(r"C:\Users\nando\Projects\anyQBMCP\docs\sdk docs\osr_data\sdk_complete.db")
        if not self.db_path.exists():
            # Fallback to old database
            self.db_path = Path(r"C:\Users\nando\Projects\anyQBMCP\docs\sdk docs\db\sdk_docs.db")
        
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Connect to the SDK database"""
        if self.db_path.exists():
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        else:
            raise FileNotFoundError(f"SDK database not found at {self.db_path}")
    
    def ask_sdk(self, question: str) -> Dict[str, Any]:
        """
        Answer natural language questions about the SDK
        
        Args:
            question: Natural language question about SDK
            
        Returns:
            Detailed answer with examples and references
        """
        question_lower = question.lower()
        
        # Determine what type of question this is
        if 'field' in question_lower and 'report' in question_lower:
            return self._answer_report_fields(question)
        elif 'error' in question_lower and any(str(i) in question for i in range(1000, 9999)):
            # Extract error code
            error_code = int(re.search(r'\d{4}', question).group())
            return self._answer_error_code(error_code)
        elif 'how' in question_lower or 'create' in question_lower or 'add' in question_lower:
            return self._answer_how_to(question)
        elif 'what' in question_lower and 'return' in question_lower:
            return self._answer_return_fields(question)
        else:
            return self._general_search(question)
    
    def _answer_report_fields(self, question: str) -> Dict[str, Any]:
        """Answer questions about report fields"""
        result = {
            'question': question,
            'answer': '',
            'details': [],
            'examples': []
        }
        
        # Extract report type from question
        report_types = ['CheckDetail', 'GeneralDetail', 'CustomDetail', 'TransactionDetail']
        found_report = None
        
        for report in report_types:
            if report.lower() in question.lower():
                found_report = report
                break
        
        if not found_report:
            # Try to find any report query
            cursor = self.conn.execute('''
                SELECT message_type, description 
                FROM sdk_messages 
                WHERE message_type LIKE '%Report%'
                ORDER BY message_type
            ''')
            reports = cursor.fetchall()
            
            result['answer'] = "Available report types in SDK:"
            for report in reports:
                result['details'].append({
                    'type': report['message_type'],
                    'description': report['description']
                })
        else:
            # Get fields for specific report
            cursor = self.conn.execute('''
                SELECT f.field_name, f.field_type, f.is_required, f.description
                FROM sdk_fields f
                JOIN sdk_messages m ON f.message_type = m.message_type
                WHERE m.message_type LIKE ?
                ORDER BY f.is_request DESC, f.field_name
            ''', (f'%{found_report}%',))
            
            fields = cursor.fetchall()
            
            if fields:
                result['answer'] = f"{found_report} report fields:"
                for field in fields:
                    result['details'].append({
                        'field': field['field_name'],
                        'type': field['field_type'],
                        'required': field['is_required'],
                        'description': field['description'] or ''
                    })
            else:
                result['answer'] = f"No specific field information found for {found_report}. Common report fields include: TxnID, TxnDate, RefNumber, Amount, Memo, AccountRef"
        
        return result
    
    def _answer_error_code(self, error_code: int) -> Dict[str, Any]:
        """Answer questions about specific error codes"""
        result = {
            'question': f"Error code {error_code}",
            'answer': '',
            'details': [],
            'examples': []
        }
        
        # First check comprehensive database
        if 'sdk_complete' in str(self.db_path):
            cursor = self.conn.execute('''
                SELECT * FROM sdk_errors WHERE error_code = ?
            ''', (error_code,))
            error_info = cursor.fetchone()
            
            if error_info:
                result['answer'] = f"Error {error_code}: {error_info['description']}"
                result['details'].append({
                    'solution': error_info['solution'] or 'Check field requirements and data types',
                    'page': error_info['page']
                })
                return result
        
        # Common error codes
        error_map = {
            3000: "Invalid object ID - The referenced object does not exist",
            3070: "Invalid name - Vendor/Customer name doesn't match exactly",
            3120: "Invalid date format - Use YYYY-MM-DD format",
            3140: "Required field missing - Check all required fields for transaction type",
            3180: "Cannot modify - Transaction is closed or locked",
            3200: "Name already exists - Duplicate vendor/customer name",
            3210: "Invalid field value - Check field constraints",
            3250: "Permission denied - User lacks permission for this operation"
        }
        
        if error_code in error_map:
            result['answer'] = f"Error {error_code}: {error_map[error_code]}"
        else:
            result['answer'] = f"Error {error_code} not documented. Common issues: Check required fields, verify object references, ensure proper date formats"
        
        return result
    
    def _answer_how_to(self, question: str) -> Dict[str, Any]:
        """Answer 'how to' questions"""
        result = {
            'question': question,
            'answer': '',
            'details': [],
            'examples': []
        }
        
        # Extract the object type
        objects = ['bill', 'invoice', 'customer', 'vendor', 'check', 'item', 'account']
        found_object = None
        
        for obj in objects:
            if obj in question.lower():
                found_object = obj.capitalize()
                break
        
        if found_object:
            # Get Add operation fields
            cursor = self.conn.execute('''
                SELECT field_name, field_type, is_required
                FROM sdk_fields
                WHERE message_type = ? AND is_request = 1
                ORDER BY is_required DESC, field_name
            ''', (f'{found_object}Add',))
            
            fields = cursor.fetchall()
            
            if fields:
                result['answer'] = f"To create a {found_object}, use {found_object}Add with these fields:"
                
                required_fields = []
                optional_fields = []
                
                for field in fields:
                    field_info = f"{field['field_name']} ({field['field_type']})"
                    if field['is_required']:
                        required_fields.append(field_info)
                    else:
                        optional_fields.append(field_info)
                
                if required_fields:
                    result['details'].append({
                        'section': 'Required Fields',
                        'fields': required_fields
                    })
                
                if optional_fields:
                    result['details'].append({
                        'section': 'Optional Fields',
                        'fields': optional_fields[:10]  # Limit to first 10
                    })
                
                # Add example
                result['examples'].append(self._generate_example(found_object))
            else:
                result['answer'] = f"Use {found_object}Add message. Common fields: Name/RefNumber (required), Date, Memo"
        else:
            result['answer'] = "Please specify what object you want to create (bill, invoice, customer, vendor, check, etc.)"
        
        return result
    
    def _answer_return_fields(self, question: str) -> Dict[str, Any]:
        """Answer questions about what fields are returned"""
        result = {
            'question': question,
            'answer': '',
            'details': [],
            'examples': []
        }
        
        # Extract object type
        objects = ['bill', 'invoice', 'customer', 'vendor', 'check', 'item', 'account']
        found_object = None
        
        for obj in objects:
            if obj in question.lower():
                found_object = obj.capitalize()
                break
        
        if found_object:
            # Get Query response fields
            cursor = self.conn.execute('''
                SELECT field_name, field_type, description
                FROM sdk_fields
                WHERE message_type = ? AND is_request = 0
                ORDER BY field_name
            ''', (f'{found_object}Query',))
            
            fields = cursor.fetchall()
            
            if fields:
                result['answer'] = f"{found_object}Query returns these fields:"
                for field in fields:
                    result['details'].append({
                        'field': field['field_name'],
                        'type': field['field_type'],
                        'description': field['description'] or ''
                    })
            else:
                # Provide common return fields
                result['answer'] = f"{found_object} typically returns:"
                common_fields = [
                    'TxnID - Transaction/Object ID',
                    'EditSequence - Version for updates',
                    'TimeCreated - Creation timestamp',
                    'TimeModified - Last modified time',
                    'RefNumber - Reference number',
                    'Memo - Memo/notes field'
                ]
                result['details'] = [{'field': f} for f in common_fields]
        
        return result
    
    def _general_search(self, query: str) -> Dict[str, Any]:
        """General search across all SDK documentation"""
        result = {
            'question': query,
            'answer': '',
            'details': [],
            'examples': []
        }
        
        # Search in messages
        cursor = self.conn.execute('''
            SELECT message_type, description, operation_type, object_type
            FROM sdk_messages
            WHERE message_type LIKE ? OR description LIKE ?
            LIMIT 10
        ''', (f'%{query}%', f'%{query}%'))
        
        messages = cursor.fetchall()
        
        if messages:
            result['answer'] = f"Found {len(messages)} related SDK messages:"
            for msg in messages:
                result['details'].append({
                    'message': msg['message_type'],
                    'operation': msg['operation_type'],
                    'object': msg['object_type'],
                    'description': msg['description']
                })
        else:
            result['answer'] = "No direct matches found. Try being more specific or check available message types with LIST_SDK_MESSAGES"
        
        return result
    
    def _generate_example(self, object_type: str) -> str:
        """Generate a basic example for an object type"""
        examples = {
            'Bill': '''<BillAdd>
    <VendorRef>
        <FullName>Vendor Name</FullName>
    </VendorRef>
    <TxnDate>2024-01-01</TxnDate>
    <RefNumber>BILL-001</RefNumber>
    <ItemLineAdd>
        <ItemRef>
            <FullName>Labor</FullName>
        </ItemRef>
        <Quantity>1</Quantity>
        <Cost>100.00</Cost>
    </ItemLineAdd>
</BillAdd>''',
            'Invoice': '''<InvoiceAdd>
    <CustomerRef>
        <FullName>Customer Name</FullName>
    </CustomerRef>
    <TxnDate>2024-01-01</TxnDate>
    <RefNumber>INV-001</RefNumber>
    <InvoiceLineAdd>
        <ItemRef>
            <FullName>Service Item</FullName>
        </ItemRef>
        <Quantity>1</Quantity>
        <Rate>150.00</Rate>
    </InvoiceLineAdd>
</InvoiceAdd>''',
            'Check': '''<CheckAdd>
    <AccountRef>
        <FullName>Checking Account</FullName>
    </AccountRef>
    <PayeeEntityRef>
        <FullName>Payee Name</FullName>
    </PayeeEntityRef>
    <TxnDate>2024-01-01</TxnDate>
    <RefNumber>1001</RefNumber>
    <Amount>500.00</Amount>
</CheckAdd>'''
        }
        
        return examples.get(object_type, f'<{object_type}Add>\n    <!-- Add required fields -->\n</{object_type}Add>')
    
    def list_sdk_messages(self, object_type: Optional[str] = None) -> List[Dict]:
        """List all SDK messages, optionally filtered by object type"""
        if object_type:
            cursor = self.conn.execute('''
                SELECT message_type, operation_type, description
                FROM sdk_messages
                WHERE object_type = ?
                ORDER BY message_type
            ''', (object_type,))
        else:
            cursor = self.conn.execute('''
                SELECT message_type, operation_type, object_type, description
                FROM sdk_messages
                ORDER BY object_type, message_type
            ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_message_fields(self, message_type: str) -> Dict[str, List[Dict]]:
        """Get all fields for a specific message type"""
        cursor = self.conn.execute('''
            SELECT field_name, field_type, is_required, is_request, description
            FROM sdk_fields
            WHERE message_type = ?
            ORDER BY is_request DESC, is_required DESC, field_name
        ''', (message_type,))
        
        fields = cursor.fetchall()
        
        request_fields = []
        response_fields = []
        
        for field in fields:
            field_dict = {
                'name': field['field_name'],
                'type': field['field_type'],
                'required': field['is_required'],
                'description': field['description'] or ''
            }
            
            if field['is_request']:
                request_fields.append(field_dict)
            else:
                response_fields.append(field_dict)
        
        return {
            'request_fields': request_fields,
            'response_fields': response_fields
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None