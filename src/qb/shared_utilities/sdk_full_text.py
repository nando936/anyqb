"""
Full SDK Text Search Engine
Loads and searches the complete extracted SDK documentation
"""
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
import re

class FullSDKTextSearch:
    """Search engine for the complete extracted SDK documentation"""
    
    def __init__(self):
        """Load all extracted SDK documentation"""
        self.base_path = Path(r"C:\Users\nando\Projects\anyQBMCP\docs\sdk docs\complete_extraction")
        
        # Load the complete raw text
        self.raw_text = self._load_raw_text()
        self.raw_lines = self.raw_text.split('\n') if self.raw_text else []
        
        # Load structured data
        self.structured_data = self._load_json("complete_sdk_structured.json")
        self.methods = self._load_json("all_methods_complete.json")
        self.objects = self._load_json("all_objects_complete.json")
        self.examples = self._load_json("all_examples.json")
        self.errors = self._load_json("all_errors_complete.json")
        
        print(f"[SDK] Loaded {len(self.raw_lines)} lines of documentation")
        print(f"[SDK] Loaded {len(self.methods)} methods")
        print(f"[SDK] Loaded {len(self.objects)} objects")
    
    def _load_raw_text(self) -> str:
        """Load the complete raw SDK text"""
        raw_file = self.base_path / "complete_sdk_raw.txt"
        if raw_file.exists():
            with open(raw_file, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    def _load_json(self, filename: str) -> Any:
        """Load a JSON file from the extraction folder"""
        json_file = self.base_path / filename
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def search_text(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the raw SDK text for matches
        
        Args:
            query: Search term or phrase
            limit: Maximum results to return
            
        Returns:
            List of matching text snippets with context
        """
        query_lower = query.lower()
        results = []
        
        for i, line in enumerate(self.raw_lines):
            if query_lower in line.lower():
                # Get context (2 lines before and after)
                start = max(0, i - 2)
                end = min(len(self.raw_lines), i + 3)
                context = '\n'.join(self.raw_lines[start:end])
                
                results.append({
                    'line_number': i + 1,
                    'text': line,
                    'context': context
                })
                
                if len(results) >= limit:
                    break
        
        return results
    
    def find_object_fields(self, object_name: str) -> Dict[str, Any]:
        """
        Find all fields for a specific QB object
        
        Args:
            object_name: Name of the object (e.g., 'Invoice', 'Estimate')
            
        Returns:
            Dictionary with object details and fields
        """
        # Search in methods for Add/Mod/Query operations
        object_methods = {}
        for method_name, method_data in self.methods.items():
            if object_name.lower() in method_name.lower():
                object_methods[method_name] = method_data
        
        # Search raw text for field information
        field_pattern = rf"{object_name}.*?(Add|Mod|Query).*?Field"
        field_matches = []
        
        for line in self.raw_lines:
            if re.search(field_pattern, line, re.IGNORECASE):
                field_matches.append(line)
        
        return {
            'object': object_name,
            'methods': object_methods,
            'field_references': field_matches[:20]  # Limit to 20 matches
        }
    
    def search_estimate_to_invoice(self) -> Dict[str, Any]:
        """
        Search for estimate to invoice conversion information
        """
        results = {
            'direct_conversion': [],
            'estimate_references': [],
            'invoice_references': [],
            'linking_fields': []
        }
        
        # Search for direct conversion references
        conversion_terms = ['estimate.*invoice', 'convert.*estimate', 'progress.*invoice', 'LinkToTxn']
        
        for term in conversion_terms:
            pattern = re.compile(term, re.IGNORECASE)
            for i, line in enumerate(self.raw_lines):
                if pattern.search(line):
                    results['direct_conversion'].append({
                        'line': i + 1,
                        'text': line,
                        'context': self._get_context(i, 3)
                    })
        
        # Search for LinkToTxnID field
        link_pattern = re.compile(r'LinkToTxn(ID)?', re.IGNORECASE)
        for i, line in enumerate(self.raw_lines):
            if link_pattern.search(line):
                results['linking_fields'].append({
                    'line': i + 1,
                    'text': line,
                    'context': self._get_context(i, 5)
                })
        
        return results
    
    def _get_context(self, line_index: int, context_lines: int = 2) -> str:
        """Get context lines around a specific line"""
        start = max(0, line_index - context_lines)
        end = min(len(self.raw_lines), line_index + context_lines + 1)
        return '\n'.join(self.raw_lines[start:end])
    
    def get_invoice_add_fields(self) -> Dict[str, Any]:
        """
        Get all fields available for InvoiceAdd
        """
        # Search for InvoiceAdd in methods
        invoice_add = self.methods.get('InvoiceAdd', {})
        
        # Search raw text for InvoiceAdd field definitions
        field_lines = []
        in_invoice_add = False
        
        for i, line in enumerate(self.raw_lines):
            if 'InvoiceAdd' in line:
                in_invoice_add = True
            elif in_invoice_add and ('Query' in line or 'Add' in line or 'Mod' in line) and 'Invoice' not in line:
                in_invoice_add = False
            
            if in_invoice_add and any(field_indicator in line for field_indicator in ['Field', 'Ref', 'ID', 'Date', 'Amount']):
                field_lines.append(line)
                if len(field_lines) > 50:  # Limit to 50 field references
                    break
        
        return {
            'method_data': invoice_add,
            'field_references': field_lines,
            'has_link_field': any('LinkTo' in line for line in field_lines)
        }