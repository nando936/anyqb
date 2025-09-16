"""
Other Name Repository - Standard QuickBooks Other Name operations using QBFC SDK
NO custom business logic - only pure QB operations
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import pywintypes
from shared_utilities.fast_qb_connection import fast_qb_connection
from shared_utilities.fuzzy_matcher import FuzzyMatcher

logger = logging.getLogger(__name__)

class OtherNameRepository:
    """Handles standard QuickBooks Other Name operations using QBFC SDK"""
    
    def __init__(self):
        """Initialize other name repository"""
        self.fuzzy_matcher = FuzzyMatcher()
    
    def create_other_name(self, name: str, company_name: Optional[str] = None) -> Optional[Dict]:
        """
        Create a new Other Name in QuickBooks
        
        Args:
            name: Name of the other name entity (required)
            company_name: Company name (optional)
        
        Returns:
            Created other name details or None if failed
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            other_add = request_set.AppendOtherNameAddRq()
            
            # Set the name
            other_add.Name.SetValue(name)
            
            # Set company name if provided
            if company_name:
                other_add.CompanyName.SetValue(company_name)
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to create other name: StatusCode={response.StatusCode}, Message={error_msg}")
                return None
            
            if not response.Detail:
                logger.error("No other name data returned after creation")
                return None
            
            # Parse and return the created other name
            other_ret = response.Detail
            return self._parse_other_name_from_sdk(other_ret)
            
        except Exception as e:
            logger.error(f"Failed to create other name: {e}")
            return None
    
    def find_other_name(self, name: str) -> Optional[Dict]:
        """
        Find an Other Name by name
        
        Args:
            name: Name to search for
        
        Returns:
            Other name details or None if not found
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            other_query = request_set.AppendOtherNameQueryRq()
            
            # Search by name
            other_query.ORListQuery.FullNameList.Add(name)
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Query failed: {error_msg}")
                return None
            
            if not response.Detail or response.Detail.Count == 0:
                logger.info(f"Other name '{name}' not found")
                return None
            
            # Parse and return the other name
            other_ret = response.Detail.GetAt(0)
            return self._parse_other_name_from_sdk(other_ret)
            
        except Exception as e:
            logger.error(f"Failed to find other name: {e}")
            return None
    
    def update_other_name(self, list_id: str, edit_sequence: str, updates: Dict) -> Optional[Dict]:
        """
        Update an existing Other Name
        
        Args:
            list_id: ListID of the other name to update
            edit_sequence: Edit sequence for the update
            updates: Dictionary of fields to update
        
        Returns:
            Updated other name details or None if failed
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            other_mod = request_set.AppendOtherNameModRq()
            
            # Required fields
            other_mod.ListID.SetValue(list_id)
            other_mod.EditSequence.SetValue(edit_sequence)
            
            # Apply updates
            if 'name' in updates:
                other_mod.Name.SetValue(updates['name'])
            
            if 'company_name' in updates:
                other_mod.CompanyName.SetValue(updates['company_name'])
            
            if 'is_active' in updates:
                other_mod.IsActive.SetValue(updates['is_active'])
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to update other name: {error_msg}")
                return None
            
            if not response.Detail:
                logger.error("No other name data returned after update")
                return None
            
            # Parse and return the updated other name
            other_ret = response.Detail
            return self._parse_other_name_from_sdk(other_ret)
            
        except Exception as e:
            logger.error(f"Failed to update other name: {e}")
            return None
    
    def search_other_names(self, search_term: Optional[str] = None, active_only: bool = True) -> List[Dict]:
        """
        Search for Other Names
        
        Args:
            search_term: Optional search term for name matching
            active_only: Only return active other names
        
        Returns:
            List of matching other names
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            other_query = request_set.AppendOtherNameQueryRq()
            
            # Don't set active status - OtherNameQuery doesn't support it
            # Get all and filter with fuzzy matching later
            # Don't add any filters - get all Other Names
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Query failed: {error_msg}")
                return []
            
            if not response.Detail:
                return []
            
            # Parse all other names
            other_names = []
            for i in range(response.Detail.Count):
                other_ret = response.Detail.GetAt(i)
                other_data = self._parse_other_name_from_sdk(other_ret)
                if other_data:
                    # Apply fuzzy matching if search term provided
                    if search_term:
                        name = other_data.get('name', '')
                        match_result = self.fuzzy_matcher.find_best_match(search_term, [name])
                        if match_result.confidence >= 0.75:  # 75% confidence threshold
                            other_names.append(other_data)
                    else:
                        # No search term, include all
                        other_names.append(other_data)

            return other_names
            
        except Exception as e:
            logger.error(f"Failed to search other names: {e}")
            return []
    
    def _parse_other_name_from_sdk(self, other_ret) -> Optional[Dict]:
        """Parse Other Name data from SDK response"""
        try:
            other_data = {
                'list_id': other_ret.ListID.GetValue() if hasattr(other_ret, 'ListID') else None,
                'name': other_ret.Name.GetValue() if hasattr(other_ret, 'Name') else None,
                'is_active': other_ret.IsActive.GetValue() if hasattr(other_ret, 'IsActive') else True,
                'edit_sequence': other_ret.EditSequence.GetValue() if hasattr(other_ret, 'EditSequence') else None,
                'time_created': str(other_ret.TimeCreated.GetValue()) if hasattr(other_ret, 'TimeCreated') else None,
                'time_modified': str(other_ret.TimeModified.GetValue()) if hasattr(other_ret, 'TimeModified') else None,
            }
            
            # Optional fields
            if hasattr(other_ret, 'CompanyName') and other_ret.CompanyName:
                other_data['company_name'] = other_ret.CompanyName.GetValue()
            
            # Contact info
            if hasattr(other_ret, 'Phone') and other_ret.Phone:
                other_data['phone'] = other_ret.Phone.GetValue()
            
            if hasattr(other_ret, 'Email') and other_ret.Email:
                other_data['email'] = other_ret.Email.GetValue()
            
            # Address
            if hasattr(other_ret, 'BillAddress') and other_ret.BillAddress:
                addr = other_ret.BillAddress
                address_lines = []
                for field in ['Addr1', 'Addr2', 'Addr3', 'Addr4', 'Addr5']:
                    if hasattr(addr, field):
                        line = getattr(addr, field).GetValue() if getattr(addr, field) else None
                        if line:
                            address_lines.append(line)
                if address_lines:
                    other_data['address'] = '\n'.join(address_lines)
            
            return other_data
            
        except Exception as e:
            logger.error(f"Failed to parse other name data: {e}")
            return None