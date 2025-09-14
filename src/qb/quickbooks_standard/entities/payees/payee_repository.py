"""
Payee Repository - Search across all entity types that can be payees
Searches vendors, customers, employees, and other names
"""

import logging
import time
from typing import Dict, List, Optional
from shared_utilities.fast_qb_connection import fast_qb_connection
from shared_utilities.payee_cache import payee_cache

logger = logging.getLogger(__name__)

class PayeeRepository:
    """Handles searching for payees across all entity types"""
    
    def __init__(self):
        """Initialize payee repository"""
        self.cache = payee_cache
    
    def get_cached_payees(self, search_term: Optional[str] = None) -> Optional[List[Dict]]:
        """Get payees from cache only (no QB query)"""
        if not search_term:
            return self.cache.get_full_search()
        
        cache_key = f"payees_{search_term}_True_None"
        return self.cache.get(cache_key)
    
    def preload_all_payees(self) -> List[Dict]:
        """Preload all payees into cache (run this periodically)"""
        logger.info("Preloading payees into cache...")
        
        # Check if already cached
        cached = self.cache.get_full_search()
        if cached:
            logger.info(f"Found {len(cached)} payees in cache")
            return cached
        
        # Load from QuickBooks (vendors and other names for checks)
        all_payees = []
        
        try:
            # Vendors (most common for checks)
            vendors = self._search_vendors(None, True)
            for vendor in vendors:
                vendor['payee_type'] = 'Vendor'
            all_payees.extend(vendors)
            logger.info(f"Loaded {len(vendors)} vendors")
            
            # Other Names (one-time payees, also common for checks)
            other_names = self._search_other_names(None, True)
            for other in other_names:
                other['payee_type'] = 'Other Name'
            all_payees.extend(other_names)
            logger.info(f"Loaded {len(other_names)} other names")
            
            # Skip customers and employees (not typical for checks)
            
        except Exception as e:
            logger.error(f"Failed to load payees: {e}")
        
        # Cache the results
        if all_payees:
            self.cache.set_full_search(all_payees)
            logger.info(f"Cached {len(all_payees)} total payees")
        
        return all_payees
    
    def search_all_payees(self, search_term: Optional[str] = None, active_only: bool = True, limit: Optional[int] = None) -> List[Dict]:
        """
        Search for payees across all entity types (vendors, customers, employees, other names)
        
        Args:
            search_term: Optional search term for fuzzy matching
            active_only: Only return active entities
            limit: Maximum number of results to return (optional)
            
        Returns:
            List of payees with their type and details
        """
        logger.info(f"search_all_payees called with search_term='{search_term}', active_only={active_only}, limit={limit}")
        
        # Start timeout timer (30 seconds max)
        start_time = time.time()
        timeout_seconds = 30
        
        # Check cache first
        cache_key = f"payees_{search_term}_{active_only}_{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info(f"Returning {len(cached)} cached payees")
            return cached
        
        # For searches with a term, try to use cached full list and filter
        if search_term:
            cached_full = self.cache.get_full_search()
            if cached_full:
                # Filter cached results
                from shared_utilities.fuzzy_matcher import FuzzyMatcher
                matcher = FuzzyMatcher()
                filtered = []
                for payee in cached_full:
                    if matcher.fuzzy_match(search_term, payee.get('name', '')):
                        filtered.append(payee)
                
                # Apply limit
                if limit:
                    filtered = filtered[:limit]
                
                # Cache the filtered results
                self.cache.set(cache_key, filtered)
                logger.info(f"Returning {len(filtered)} filtered payees from cache")
                return filtered
        
        all_payees = []
        
        # For check payees, prioritize vendors and other names (skip customers/employees)
        # This speeds up searches dramatically since checks are rarely written to customers/employees
        
        # Search vendors (most common for checks)
        if time.time() - start_time < timeout_seconds:
            vendors = self._search_vendors_with_timeout(search_term, active_only, timeout_seconds - (time.time() - start_time))
            logger.info(f"Found {len(vendors)} vendors")
            for vendor in vendors:
                vendor['payee_type'] = 'Vendor'
            all_payees.extend(vendors)
        else:
            logger.warning("Timeout reached before searching vendors")
        
        # Search other names (second most common for checks)
        if time.time() - start_time < timeout_seconds:
            other_names = self._search_other_names_with_timeout(search_term, active_only, timeout_seconds - (time.time() - start_time))
            logger.info(f"Found {len(other_names)} other names")
            for other in other_names:
                other['payee_type'] = 'Other Name'
            all_payees.extend(other_names)
        else:
            logger.warning("Timeout reached before searching other names")
        
        # Only search customers if we have time left and need more results
        if (not limit or len(all_payees) < limit) and time.time() - start_time < timeout_seconds:
            customers = self._search_customers_with_timeout(search_term, active_only, timeout_seconds - (time.time() - start_time))
            logger.info(f"Found {len(customers)} customers")
            for customer in customers:
                customer['payee_type'] = 'Customer'
            all_payees.extend(customers)
        
        # Only search employees if we have time left and need more results
        if (not limit or len(all_payees) < limit) and time.time() - start_time < timeout_seconds:
            employees = self._search_employees_with_timeout(search_term, active_only, timeout_seconds - (time.time() - start_time))
            logger.info(f"Found {len(employees)} employees")
            for employee in employees:
                employee['payee_type'] = 'Employee'
            all_payees.extend(employees)
        
        # Sort by name
        all_payees.sort(key=lambda x: x.get('name', '').lower())
        
        # Apply limit if specified
        if limit and limit > 0:
            all_payees = all_payees[:limit]
            logger.info(f"Applied limit of {limit}, returning {len(all_payees)} payees")
        
        # Cache the results
        self.cache.set(cache_key, all_payees)
        if not search_term and not limit:
            # Cache as full search for quick access
            self.cache.set_full_search(all_payees)
        
        elapsed = time.time() - start_time
        logger.info(f"Total payees found: {len(all_payees)} in {elapsed:.2f} seconds")
        return all_payees
    
    def _search_vendors(self, search_term: Optional[str], active_only: bool) -> List[Dict]:
        """Search vendors"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            vendor_query = request_set.AppendVendorQueryRq()
            # Don't set ActiveStatus - will filter later
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Vendor query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            if not response.Detail:
                return []
            
            vendors = []
            for i in range(response.Detail.Count):
                vendor_ret = response.Detail.GetAt(i)
                vendor_name = vendor_ret.Name.GetValue() if vendor_ret.Name else None
                
                if vendor_name:
                    vendor_data = {
                        'name': vendor_name,
                        'list_id': vendor_ret.ListID.GetValue() if vendor_ret.ListID else None,
                        'is_active': vendor_ret.IsActive.GetValue() if vendor_ret.IsActive else True,
                        'company_name': vendor_ret.CompanyName.GetValue() if vendor_ret.CompanyName else None,
                        'phone': vendor_ret.Phone.GetValue() if vendor_ret.Phone else None,
                        'email': vendor_ret.Email.GetValue() if vendor_ret.Email else None,
                        'notes': vendor_ret.Notes.GetValue() if vendor_ret.Notes else None,
                    }
                    
                    # Filter by active status if requested
                    if active_only and not vendor_data.get('is_active', True):
                        continue
                    
                    # Apply search filter across ALL fields if provided
                    if search_term:
                        search_lower = search_term.lower()
                        searchable_fields = [
                            str(vendor_data.get('name', '')),
                            str(vendor_data.get('list_id', '')),
                            str(vendor_data.get('company_name', '')),
                            str(vendor_data.get('phone', '')),
                            str(vendor_data.get('email', '')),
                            str(vendor_data.get('notes', ''))
                        ]
                        
                        # Check if search term matches any field
                        match_found = False
                        for field in searchable_fields:
                            if search_lower in field.lower():
                                match_found = True
                                break
                        
                        if not match_found:
                            continue
                    
                    vendors.append(vendor_data)
            
            return vendors
            
        except Exception as e:
            logger.error(f"Failed to search vendors: {e}")
            return []
    
    def _search_customers(self, search_term: Optional[str], active_only: bool) -> List[Dict]:
        """Search customers"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            customer_query = request_set.AppendCustomerQueryRq()
            # Don't set ActiveStatus - will filter later
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Customer query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            if not response.Detail:
                return []
            
            customers = []
            for i in range(response.Detail.Count):
                customer_ret = response.Detail.GetAt(i)
                customer_name = customer_ret.Name.GetValue() if customer_ret.Name else None
                
                if customer_name:
                    customer_data = {
                        'name': customer_name,
                        'list_id': customer_ret.ListID.GetValue() if customer_ret.ListID else None,
                        'is_active': customer_ret.IsActive.GetValue() if customer_ret.IsActive else True,
                        'company_name': customer_ret.CompanyName.GetValue() if customer_ret.CompanyName else None,
                        'phone': customer_ret.Phone.GetValue() if customer_ret.Phone else None,
                        'email': customer_ret.Email.GetValue() if customer_ret.Email else None,
                        'notes': customer_ret.Notes.GetValue() if customer_ret.Notes else None,
                    }
                    
                    # Filter by active status if requested
                    if active_only and not customer_data.get('is_active', True):
                        continue
                    
                    # Apply search filter across ALL fields if provided
                    if search_term:
                        search_lower = search_term.lower()
                        searchable_fields = [
                            str(customer_data.get('name', '')),
                            str(customer_data.get('list_id', '')),
                            str(customer_data.get('company_name', '')),
                            str(customer_data.get('phone', '')),
                            str(customer_data.get('email', '')),
                            str(customer_data.get('notes', ''))
                        ]
                        
                        # Check if search term matches any field
                        match_found = False
                        for field in searchable_fields:
                            if search_lower in field.lower():
                                match_found = True
                                break
                        
                        if not match_found:
                            continue
                    
                    customers.append(customer_data)
            
            return customers
            
        except Exception as e:
            logger.error(f"Failed to search customers: {e}")
            return []
    
    def _search_employees(self, search_term: Optional[str], active_only: bool) -> List[Dict]:
        """Search employees"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            employee_query = request_set.AppendEmployeeQueryRq()
            # Don't set ActiveStatus - will filter later
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Employee query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            if not response.Detail:
                return []
            
            employees = []
            for i in range(response.Detail.Count):
                employee_ret = response.Detail.GetAt(i)
                
                # Build employee name from first and last name
                first_name = employee_ret.FirstName.GetValue() if employee_ret.FirstName else ''
                last_name = employee_ret.LastName.GetValue() if employee_ret.LastName else ''
                employee_name = f"{first_name} {last_name}".strip()
                
                if not employee_name:
                    employee_name = employee_ret.Name.GetValue() if employee_ret.Name else None
                
                if employee_name:
                    employee_data = {
                        'name': employee_name,
                        'list_id': employee_ret.ListID.GetValue() if employee_ret.ListID else None,
                        'is_active': employee_ret.IsActive.GetValue() if employee_ret.IsActive else True,
                        'phone': employee_ret.Phone.GetValue() if employee_ret.Phone else None,
                        'mobile': employee_ret.Mobile.GetValue() if employee_ret.Mobile else None,
                        'email': employee_ret.Email.GetValue() if employee_ret.Email else None,
                    }
                    
                    # Filter by active status if requested
                    if active_only and not employee_data.get('is_active', True):
                        continue
                    
                    # Apply search filter across ALL fields if provided
                    if search_term:
                        search_lower = search_term.lower()
                        searchable_fields = [
                            str(employee_data.get('name', '')),
                            str(employee_data.get('list_id', '')),
                            str(employee_data.get('phone', '')),
                            str(employee_data.get('mobile', '')),
                            str(employee_data.get('email', ''))
                        ]
                        
                        # Check if search term matches any field
                        match_found = False
                        for field in searchable_fields:
                            if search_lower in field.lower():
                                match_found = True
                                break
                        
                        if not match_found:
                            continue
                    
                    employees.append(employee_data)
            
            return employees
            
        except Exception as e:
            logger.error(f"Failed to search employees: {e}")
            return []
    
    def _search_other_names(self, search_term: Optional[str], active_only: bool) -> List[Dict]:
        """Search other names"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            other_name_query = request_set.AppendOtherNameQueryRq()
            # Don't set ActiveStatus - will filter later
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Other name query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            if not response.Detail:
                return []
            
            other_names = []
            for i in range(response.Detail.Count):
                other_ret = response.Detail.GetAt(i)
                other_name = other_ret.Name.GetValue() if other_ret.Name else None
                
                if other_name:
                    other_data = {
                        'name': other_name,
                        'list_id': other_ret.ListID.GetValue() if other_ret.ListID else None,
                        'is_active': other_ret.IsActive.GetValue() if other_ret.IsActive else True,
                        'company_name': other_ret.CompanyName.GetValue() if other_ret.CompanyName else None,
                        'phone': other_ret.Phone.GetValue() if other_ret.Phone else None,
                        'email': other_ret.Email.GetValue() if other_ret.Email else None,
                    }
                    
                    # Filter by active status if requested
                    if active_only and not other_data.get('is_active', True):
                        continue
                    
                    # Apply search filter across ALL fields if provided
                    if search_term:
                        search_lower = search_term.lower()
                        searchable_fields = [
                            str(other_data.get('name', '')),
                            str(other_data.get('list_id', '')),
                            str(other_data.get('company_name', '')),
                            str(other_data.get('phone', '')),
                            str(other_data.get('email', ''))
                        ]
                        
                        # Check if search term matches any field
                        match_found = False
                        for field in searchable_fields:
                            if search_lower in field.lower():
                                match_found = True
                                break
                        
                        if not match_found:
                            continue
                    
                    other_names.append(other_data)
            
            return other_names
            
        except Exception as e:
            logger.error(f"Failed to search other names: {e}")
            return []
    
    # Timeout wrapper methods
    def _search_vendors_with_timeout(self, search_term: Optional[str], active_only: bool, timeout: float) -> List[Dict]:
        """Search vendors with timeout"""
        try:
            import threading
            result = []
            exception = None
            
            def search():
                nonlocal result, exception
                try:
                    result = self._search_vendors(search_term, active_only)
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=search)
            thread.start()
            thread.join(timeout)
            
            if thread.is_alive():
                logger.warning(f"Vendor search timed out after {timeout:.1f} seconds")
                return []
            
            if exception:
                raise exception
            
            return result
        except Exception as e:
            logger.error(f"Failed to search vendors with timeout: {e}")
            return []
    
    def _search_customers_with_timeout(self, search_term: Optional[str], active_only: bool, timeout: float) -> List[Dict]:
        """Search customers with timeout"""
        try:
            import threading
            result = []
            exception = None
            
            def search():
                nonlocal result, exception
                try:
                    result = self._search_customers(search_term, active_only)
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=search)
            thread.start()
            thread.join(timeout)
            
            if thread.is_alive():
                logger.warning(f"Customer search timed out after {timeout:.1f} seconds")
                return []
            
            if exception:
                raise exception
            
            return result
        except Exception as e:
            logger.error(f"Failed to search customers with timeout: {e}")
            return []
    
    def _search_employees_with_timeout(self, search_term: Optional[str], active_only: bool, timeout: float) -> List[Dict]:
        """Search employees with timeout"""
        try:
            import threading
            result = []
            exception = None
            
            def search():
                nonlocal result, exception
                try:
                    result = self._search_employees(search_term, active_only)
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=search)
            thread.start()
            thread.join(timeout)
            
            if thread.is_alive():
                logger.warning(f"Employee search timed out after {timeout:.1f} seconds")
                return []
            
            if exception:
                raise exception
            
            return result
        except Exception as e:
            logger.error(f"Failed to search employees with timeout: {e}")
            return []
    
    def _search_other_names_with_timeout(self, search_term: Optional[str], active_only: bool, timeout: float) -> List[Dict]:
        """Search other names with timeout"""
        try:
            import threading
            result = []
            exception = None
            
            def search():
                nonlocal result, exception
                try:
                    result = self._search_other_names(search_term, active_only)
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=search)
            thread.start()
            thread.join(timeout)
            
            if thread.is_alive():
                logger.warning(f"Other names search timed out after {timeout:.1f} seconds")
                return []
            
            if exception:
                raise exception
            
            return result
        except Exception as e:
            logger.error(f"Failed to search other names with timeout: {e}")
            return []