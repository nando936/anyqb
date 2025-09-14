"""
Vendor Repository - Standard QuickBooks vendor operations
Part of the quickbooks_standard layer - handles all direct QB SDK interactions for vendors
"""

import logging
import re
from typing import List, Dict, Optional
from shared_utilities.fast_qb_connection import fast_qb_connection
from shared_utilities.fuzzy_matcher import FuzzyMatcher, MatchResult

logger = logging.getLogger(__name__)

class VendorRepository:
    """Repository for QuickBooks Vendor operations"""
    
    def __init__(self):
        """Initialize vendor repository"""
        self.fuzzy_matcher = FuzzyMatcher()
    
    def search_vendors(self, search_term: Optional[str] = None, active_only: bool = True) -> List[Dict]:
        """
        Search vendors using fuzzy matching across all fields
        
        Args:
            search_term: Optional search term to match against any field
            active_only: Filter for active vendors only
        
        Returns:
            List of matching vendor dictionaries
        """
        try:
            all_vendors = self.get_all_vendors()
            
            # Filter by active status
            if active_only:
                all_vendors = [v for v in all_vendors if v.get('is_active', True)]
            
            # Apply fuzzy search if search_term provided
            if search_term and all_vendors:
                search_lower = search_term.lower()
                matched_vendors = []
                
                for vendor in all_vendors:
                    # Check if search term matches any field
                    searchable_fields = [
                        str(vendor.get('list_id', '')),
                        str(vendor.get('name', '')),
                        str(vendor.get('company_name', '')),
                        str(vendor.get('phone', '')),
                        str(vendor.get('email', '')),
                        str(vendor.get('address', '')),
                        str(vendor.get('notes', ''))
                    ]
                    
                    for field in searchable_fields:
                        if search_lower in field.lower():
                            matched_vendors.append(vendor)
                            break
                
                return matched_vendors
            
            return all_vendors
            
        except Exception as e:
            logger.error(f"Error searching vendors: {e}")
            return []
    
    def get_all_vendors(self) -> List[Dict]:
        """
        Get all vendors from QuickBooks
        
        Returns:
            List of vendor dictionaries
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            query_rq = request_set.AppendVendorQueryRq()
            # Don't specify includes - get all fields
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            vendors = []
            vendor_ret_list = response.Detail
            if vendor_ret_list is not None:
                for i in range(vendor_ret_list.Count):
                    vendor = vendor_ret_list.GetAt(i)
                    
                    vendor_data = {
                        'list_id': vendor.ListID.GetValue() if vendor.ListID else None,
                        'name': vendor.Name.GetValue() if vendor.Name else None,
                        'is_active': vendor.IsActive.GetValue() if vendor.IsActive else True,
                        'company_name': vendor.CompanyName.GetValue() if vendor.CompanyName else None,
                        'address': None,
                        'phone': vendor.Phone.GetValue() if vendor.Phone else None,
                        'email': vendor.Email.GetValue() if vendor.Email else None,
                        'notes': vendor.Notes.GetValue() if vendor.Notes else None
                    }
                    
                    # Get vendor address
                    if vendor.VendorAddress:
                        addr_lines = []
                        for j in range(1, 6):  # QB supports up to 5 address lines
                            line_attr = getattr(vendor.VendorAddress, f'Addr{j}', None)
                            if line_attr:
                                line_value = line_attr.GetValue()
                                if line_value:
                                    addr_lines.append(line_value)
                        vendor_data['address'] = '\n'.join(addr_lines)
                    
                    vendors.append(vendor_data)
            
            return vendors
            
        except Exception as e:
            logger.error(f"Failed to get vendors: {e}")
            return []
    
    def find_vendor_by_name(self, name: str) -> Optional[Dict]:
        """
        Find a vendor by exact name
        
        Args:
            name: Exact vendor name
        
        Returns:
            Vendor dictionary if found, None otherwise
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            query_rq = request_set.AppendVendorQueryRq()
            query_rq.ORVendorListQuery.FullNameList.Add(name)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0 and response.Detail and response.Detail.Count > 0:
                vendor = response.Detail.GetAt(0)
                return {
                    'list_id': vendor.ListID.GetValue() if vendor.ListID else None,
                    'name': vendor.Name.GetValue() if vendor.Name else None,
                    'is_active': vendor.IsActive.GetValue() if vendor.IsActive else True,
                    'notes': vendor.Notes.GetValue() if vendor.Notes else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find vendor {name}: {e}")
            return None
    
    def find_vendor_fuzzy(self, query: str) -> Optional[Dict]:
        """
        Find a vendor using fuzzy matching
        Handles first name only matching (e.g., "selvin" -> "Selvin Lopez")
        
        Args:
            query: Search term (can be first name only)
        
        Returns:
            Best matching vendor dictionary if found
        """
        try:
            # Get all vendors
            all_vendors = self.get_all_vendors()
            if not all_vendors:
                logger.warning("No vendors found in QuickBooks")
                return None
            
            # Extract vendor names for matching
            vendor_names = [v['name'] for v in all_vendors if v.get('name')]
            
            # Find best match
            match_result = self.fuzzy_matcher.match_vendor(query, vendor_names)
            
            if match_result.found:
                logger.info(f"Vendor fuzzy match: {match_result}")
                # Find the full vendor data
                for vendor in all_vendors:
                    if vendor.get('name') == match_result.exact_name:
                        return vendor
            
            logger.warning(f"No fuzzy match found for vendor: {query}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fuzzy match vendor {query}: {e}")
            return None
    
    def create_vendor(self, vendor_data: Dict) -> bool:
        """
        Create a new vendor in QuickBooks
        
        Args:
            vendor_data: Dictionary with vendor details
        
        Returns:
            True if created successfully
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            request_set = fast_qb_connection.create_request_set()
            add_rq = request_set.AppendVendorAddRq()
            
            add_rq.Name.SetValue(vendor_data['name'])
            
            if vendor_data.get('company_name'):
                add_rq.CompanyName.SetValue(vendor_data['company_name'])
            
            if vendor_data.get('address'):
                # Parse address into lines (up to 5)
                addr_lines = vendor_data['address'].split('\n')[:5]
                for i, line in enumerate(addr_lines, 1):
                    line_attr = getattr(add_rq.VendorAddress, f'Addr{i}', None)
                    if line_attr:
                        line_attr.SetValue(line)
            
            if vendor_data.get('phone'):
                add_rq.Phone.SetValue(vendor_data['phone'])
            
            if vendor_data.get('email'):
                add_rq.Email.SetValue(vendor_data['email'])
            
            if vendor_data.get('notes'):
                add_rq.Notes.SetValue(vendor_data['notes'])
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Created vendor: {vendor_data['name']}")
                return True
            else:
                logger.error(f"Failed to create vendor: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to create vendor: {e}")
            return False
    
    def update_vendor(self, vendor_data: Dict) -> bool:
        """
        Update an existing vendor in QuickBooks
        
        Args:
            vendor_data: Dictionary with vendor details including list_id and edit_sequence
        
        Returns:
            True if updated successfully
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            request_set = fast_qb_connection.create_request_set()
            mod_rq = request_set.AppendVendorModRq()
            
            mod_rq.ListID.SetValue(vendor_data['list_id'])
            mod_rq.EditSequence.SetValue(vendor_data['edit_sequence'])
            
            if vendor_data.get('name'):
                mod_rq.Name.SetValue(vendor_data['name'])
            
            if vendor_data.get('company_name'):
                mod_rq.CompanyName.SetValue(vendor_data['company_name'])
            
            if vendor_data.get('notes'):
                mod_rq.Notes.SetValue(vendor_data['notes'])
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Updated vendor: {vendor_data.get('name', vendor_data['list_id'])}")
                return True
            else:
                logger.error(f"Failed to update vendor: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update vendor: {e}")
            return False
    
    def get_vendor_daily_cost(self, vendor_name: str) -> Optional[float]:
        """
        Extract daily cost from vendor notes field
        Looks for pattern like "Daily Cost: $150"
        
        Args:
            vendor_name: Name of the vendor
        
        Returns:
            Daily cost as float if found, None otherwise
        """
        vendor = self.find_vendor_by_name(vendor_name)
        if not vendor:
            vendor = self.find_vendor_fuzzy(vendor_name)
        
        if vendor and vendor.get('notes'):
            notes = vendor['notes']
            
            # Look for Daily Cost patterns only
            patterns = [
                r'Daily Cost:\s*\$?([\d,]+(?:\.\d{2})?)',
                r'Cost:\s*\$?([\d,]+(?:\.\d{2})?)/day',
                r'Cost:\s*\$?([\d,]+(?:\.\d{2})?)\s*per day',
                r'\$?([\d,]+(?:\.\d{2})?)/day',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, notes, re.IGNORECASE)
                if match:
                    cost_str = match.group(1).replace(',', '')
                    try:
                        return float(cost_str)
                    except ValueError:
                        continue
        
        return None
    
    
    def set_vendor_daily_cost(self, vendor_name: str, daily_cost: float) -> bool:
        """
        Update vendor's notes field with daily cost
        Preserves existing notes and updates/adds the Daily Cost line
        
        Args:
            vendor_name: Name of the vendor
            daily_cost: Daily cost amount
        
        Returns:
            True if updated successfully
        """
        try:
            # Find the vendor
            vendor = self.find_vendor_by_name(vendor_name)
            if not vendor:
                vendor = self.find_vendor_fuzzy(vendor_name)
            
            if not vendor:
                logger.error(f"Vendor not found: {vendor_name}")
                return False
            
            # Get current notes
            current_notes = vendor.get('notes', '')
            
            # Remove any existing Daily Rate or Daily Cost lines
            lines = current_notes.split('\n') if current_notes else []
            new_lines = []
            for line in lines:
                # Skip lines that contain daily rate/cost
                if not re.search(r'Daily (Cost|Rate):', line, re.IGNORECASE):
                    new_lines.append(line)
            
            # Add the new Daily Cost line at the beginning
            new_lines.insert(0, f"Daily Cost: ${daily_cost:.2f}")
            new_notes = '\n'.join(new_lines).strip()
            
            # Get the vendor with edit sequence for update
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            request_set = fast_qb_connection.create_request_set()
            query_rq = request_set.AppendVendorQueryRq()
            query_rq.ORVendorListQuery.ListIDList.Add(vendor['list_id'])
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0 or not response.Detail or response.Detail.Count == 0:
                logger.error(f"Failed to get vendor for update: {vendor_name}")
                return False
            
            vendor_ret = response.Detail.GetAt(0)
            edit_sequence = vendor_ret.EditSequence.GetValue()
            
            # Update the vendor with new notes
            update_data = {
                'list_id': vendor['list_id'],
                'edit_sequence': edit_sequence,
                'notes': new_notes
            }
            
            return self.update_vendor(update_data)
            
        except Exception as e:
            logger.error(f"Failed to set vendor daily cost: {e}")
            return False