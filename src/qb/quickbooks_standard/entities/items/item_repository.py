"""
Item Repository - Standard QuickBooks item operations
Part of the quickbooks_standard layer - handles all direct QB SDK interactions for items
"""

import logging
from typing import List, Dict, Optional
from shared_utilities.fast_qb_connection import fast_qb_connection
from shared_utilities.fuzzy_matcher import FuzzyMatcher, MatchResult

logger = logging.getLogger(__name__)

class ItemRepository:
    """Repository for QuickBooks Item operations"""
    
    def __init__(self):
        """Initialize item repository"""
        self.fuzzy_matcher = FuzzyMatcher()
    
    def search_items(self, search_term: Optional[str] = None, item_type: Optional[str] = None, active_only: bool = True) -> List[Dict]:
        """
        Search items using fuzzy matching across all fields
        
        Args:
            search_term: Optional search term to match against any field
            item_type: Filter by item type (Service, NonInventory, Inventory, etc.)
            active_only: Filter for active items only
        
        Returns:
            List of matching item dictionaries
        """
        try:
            all_items = self.get_all_items()
            
            # Filter by active status
            if active_only:
                all_items = [i for i in all_items if i.get('is_active', True)]
            
            # Filter by item type
            if item_type:
                all_items = [i for i in all_items if i.get('type', '').lower() == item_type.lower()]
            
            # Apply fuzzy search if search_term provided
            if search_term and all_items:
                search_lower = search_term.lower()
                matched_items = []
                
                for item in all_items:
                    # Check if search term matches any field
                    searchable_fields = [
                        str(item.get('list_id', '')),
                        str(item.get('name', '')),
                        str(item.get('full_name', '')),
                        str(item.get('description', '')),
                        str(item.get('type', ''))
                    ]
                    
                    for field in searchable_fields:
                        if search_lower in field.lower():
                            matched_items.append(item)
                            break
                
                return matched_items
            
            return all_items
            
        except Exception as e:
            logger.error(f"Error searching items: {e}")
            return []
    
    def get_all_items(self) -> List[Dict]:
        """
        Get all items from QuickBooks
        
        Returns:
            List of item dictionaries with structure:
            {
                'list_id': str,
                'name': str,
                'full_name': str,
                'is_active': bool,
                'type': str,
                'description': str,
                'price': float,
                'account': str
            }
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            query_rq = request_set.AppendItemQueryRq()
            # Don't set ActiveStatus - it may not be valid for all item types
            # query_rq.ActiveStatus.SetValue(2)  # All items
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            items = []
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    item_ret = response.Detail.GetAt(i)
                    
                    # Determine which type of item this is and get the actual item object
                    actual_item = None
                    item_type = None
                    
                    if hasattr(item_ret, 'ItemServiceRet') and item_ret.ItemServiceRet:
                        actual_item = item_ret.ItemServiceRet
                        item_type = 'Service'
                    elif hasattr(item_ret, 'ItemNonInventoryRet') and item_ret.ItemNonInventoryRet:
                        actual_item = item_ret.ItemNonInventoryRet
                        item_type = 'NonInventory'
                    elif hasattr(item_ret, 'ItemInventoryRet') and item_ret.ItemInventoryRet:
                        actual_item = item_ret.ItemInventoryRet
                        item_type = 'Inventory'
                    elif hasattr(item_ret, 'ItemOtherChargeRet') and item_ret.ItemOtherChargeRet:
                        actual_item = item_ret.ItemOtherChargeRet
                        item_type = 'OtherCharge'
                    elif hasattr(item_ret, 'ItemDiscountRet') and item_ret.ItemDiscountRet:
                        actual_item = item_ret.ItemDiscountRet
                        item_type = 'Discount'
                    
                    if not actual_item:
                        continue  # Skip if we can't determine the type
                    
                    # Parse item data from the actual item object
                    item_data = {
                        'list_id': actual_item.ListID.GetValue() if hasattr(actual_item, 'ListID') else None,
                        'name': actual_item.Name.GetValue() if hasattr(actual_item, 'Name') else (
                            actual_item.FullName.GetValue() if hasattr(actual_item, 'FullName') else None
                        ),
                        'full_name': actual_item.FullName.GetValue() if hasattr(actual_item, 'FullName') else None,
                        'is_active': actual_item.IsActive.GetValue() if hasattr(actual_item, 'IsActive') else True,
                        'type': item_type,
                        'description': None,
                        'price': 0.0,
                        'account': None
                    }
                    
                    # Get item-specific fields based on type - use actual_item not item_ret
                    if hasattr(actual_item, 'ORSalesPurchase') and actual_item.ORSalesPurchase:
                        sales_purchase = actual_item.ORSalesPurchase
                        if hasattr(sales_purchase, 'SalesOrPurchase') and sales_purchase.SalesOrPurchase:
                            sp = sales_purchase.SalesOrPurchase
                            if hasattr(sp, 'Desc') and sp.Desc:
                                item_data['description'] = sp.Desc.GetValue()
                            if hasattr(sp, 'ORPrice') and sp.ORPrice:
                                if hasattr(sp.ORPrice, 'Price') and sp.ORPrice.Price:
                                    item_data['price'] = float(sp.ORPrice.Price.GetValue())
                            if hasattr(sp, 'AccountRef') and sp.AccountRef:
                                item_data['account'] = sp.AccountRef.FullName.GetValue()
                    
                    items.append(item_data)
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get items: {e}")
            return []
        
    
    def find_item_by_name(self, name: str) -> Optional[Dict]:
        """
        Find an item by exact name
        
        Args:
            name: Exact item name
        
        Returns:
            Item dictionary if found, None otherwise
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return
            query_rq = fast_qb_connection.create_request_set().AppendItemQueryRq()
            query_rq.ORListQueryWithOwnerIDAndClass.FullNameList.Append(name)
            
            response_list = fast_qb_connection.process_request_set(request_set)
            
            for response in response_list:
                if response.StatusCode == 0:
                    item_ret_list = response.Detail
                    if item_ret_list is not None and len(item_ret_list) > 0:
                        item = item_ret_list.GetAt(0)
                        return {
                            'list_id': item.ListID.GetValue() if item.ListID else None,
                            'name': item.Name.GetValue() if item.Name else None,
                            'full_name': item.FullName.GetValue() if item.FullName else None,
                            'is_active': item.IsActive.GetValue() if item.IsActive else True
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find item {name}: {e}")
            return None
        
    
    def find_item_fuzzy(self, query: str) -> Optional[Dict]:
        """
        Find an item using fuzzy matching
        
        Args:
            query: Search term (can be partial, number prefix, etc.)
        
        Returns:
            Best matching item dictionary if found with confidence > threshold
        """
        try:
            # Get all items
            all_items = self.get_all_items()
            if not all_items:
                logger.warning("No items found in QuickBooks")
                return None
            
            # Extract item names for matching
            item_names = [item['name'] for item in all_items if item.get('name')]
            
            # Find best match
            match_result = self.fuzzy_matcher.match_item(query, item_names)
            
            if match_result.found:
                logger.info(f"Item fuzzy match: {match_result}")
                # Find the full item data
                for item in all_items:
                    if item.get('name') == match_result.exact_name:
                        return item
            
            logger.warning(f"No fuzzy match found for item: {query}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fuzzy match item {query}: {e}")
            return None
    
    def create_item(self, item_data: Dict) -> bool:
        """
        Create a new item in QuickBooks
        
        Args:
            item_data: Dictionary with item details:
                {
                    'name': str (required),
                    'type': str (default 'Service'),
                    'description': str (optional),
                    'price': float (optional),
                    'account': str (optional)
                }
        
        Returns:
            True if created successfully
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            # Determine item type and create appropriate request
            item_type = item_data.get('type', 'Service')
            
            request_set = fast_qb_connection.create_request_set()
            
            if item_type == 'Service':
                add_rq = request_set.AppendItemServiceAddRq()
                add_rq.Name.SetValue(item_data['name'])
                
                if item_data.get('description'):
                    add_rq.ORSalesPurchase.SalesOrPurchase.Desc.SetValue(item_data['description'])
                
                if item_data.get('price'):
                    add_rq.ORSalesPurchase.SalesOrPurchase.ORPrice.Price.SetValue(str(item_data['price']))
                
                if item_data.get('account'):
                    add_rq.ORSalesPurchase.SalesOrPurchase.AccountRef.FullName.SetValue(item_data['account'])
            else:
                # For now, only support Service items
                logger.error(f"Unsupported item type: {item_type}")
                return False
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Created item: {item_data['name']}")
                return True
            else:
                logger.error(f"Failed to create item: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to create item: {e}")
            return False
    
    def update_item(self, item_data: Dict) -> bool:
        """
        Update an existing item in QuickBooks
        
        Args:
            item_data: Dictionary with item details including list_id and edit_sequence
                {
                    'list_id': str (required),
                    'edit_sequence': str (required),
                    'name': str (optional),
                    'description': str (optional),
                    'price': float (optional),
                    'is_active': bool (optional)
                }
        
        Returns:
            True if updated successfully
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return False
            
            request_set = fast_qb_connection.create_request_set()
            
            # We need to determine the item type first by querying
            query_rq = request_set.AppendItemQueryRq()
            query_rq.ORListQuery.ListIDList.Add(item_data['list_id'])
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0 or not response.Detail or response.Detail.Count == 0:
                logger.error(f"Failed to find item for update: {item_data['list_id']}")
                return False
            
            # Determine item type from the response
            item_ret = response.Detail.GetAt(0)
            item_type = None
            
            if hasattr(item_ret, 'ItemServiceRet') and item_ret.ItemServiceRet:
                item_type = 'Service'
            elif hasattr(item_ret, 'ItemNonInventoryRet') and item_ret.ItemNonInventoryRet:
                item_type = 'NonInventory'
            elif hasattr(item_ret, 'ItemInventoryRet') and item_ret.ItemInventoryRet:
                item_type = 'Inventory'
            elif hasattr(item_ret, 'ItemOtherChargeRet') and item_ret.ItemOtherChargeRet:
                item_type = 'OtherCharge'
            
            if not item_type:
                logger.error(f"Could not determine item type for update")
                return False
            
            # Create the appropriate modify request based on item type
            request_set = fast_qb_connection.create_request_set()
            
            if item_type == 'Service':
                mod_rq = request_set.AppendItemServiceModRq()
            elif item_type == 'NonInventory':
                mod_rq = request_set.AppendItemNonInventoryModRq()
            elif item_type == 'Inventory':
                mod_rq = request_set.AppendItemInventoryModRq()
            elif item_type == 'OtherCharge':
                mod_rq = request_set.AppendItemOtherChargeModRq()
            else:
                logger.error(f"Unsupported item type for update: {item_type}")
                return False
            
            # Set the required fields
            mod_rq.ListID.SetValue(item_data['list_id'])
            mod_rq.EditSequence.SetValue(item_data['edit_sequence'])
            
            # Set optional fields if provided
            if item_data.get('name'):
                mod_rq.Name.SetValue(item_data['name'])
            
            if item_data.get('is_active') is not None:
                mod_rq.IsActive.SetValue(item_data['is_active'])
            
            # Set description and price for applicable item types
            if item_type in ['Service', 'NonInventory', 'OtherCharge']:
                if item_data.get('description') is not None:
                    mod_rq.ORSalesPurchase.SalesOrPurchase.Desc.SetValue(item_data['description'])
                
                if item_data.get('price') is not None:
                    mod_rq.ORSalesPurchase.SalesOrPurchase.ORPrice.Price.SetValue(str(item_data['price']))
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Updated item: {item_data.get('name', item_data['list_id'])}")
                return True
            else:
                logger.error(f"Failed to update item: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update item: {e}")
            return False
        