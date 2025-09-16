"""
Customer Repository - Standard QuickBooks customer and job operations
Part of the quickbooks_standard layer - handles all direct QB SDK interactions for customers/jobs
"""

import logging
from typing import List, Dict, Optional
from shared_utilities.fast_qb_connection import fast_qb_connection
from shared_utilities.fuzzy_matcher import FuzzyMatcher, MatchResult

logger = logging.getLogger(__name__)

class CustomerRepository:
    """Repository for QuickBooks Customer and Job operations"""
    
    def __init__(self):
        """Initialize customer repository"""
        self.fuzzy_matcher = FuzzyMatcher()
    
    def get_all_customers(self, include_jobs: bool = True) -> List[Dict]:
        """
        Get all customers and optionally their jobs from QuickBooks
        
        Args:
            include_jobs: Whether to include customer jobs
        
        Returns:
            List of customer/job dictionaries with structure:
            {
                'list_id': str,
                'name': str,
                'full_name': str,
                'is_active': bool,
                'parent_name': str (for jobs),
                'is_job': bool,
                'company_name': str,
                'bill_address': str
            }
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            query_rq = request_set.AppendCustomerQueryRq()
            
            # Don't set ActiveStatus - it may not be valid
            # query_rq.ActiveStatus.SetValue(2)  # All customers
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            customers = []
            
            if response.StatusCode == 0 and response.Detail:
                for i in range(response.Detail.Count):
                    customer_ret = response.Detail.GetAt(i)
                    
                    # Determine if this is a job (has parent) or customer
                    sublevel = 0
                    if hasattr(customer_ret, 'Sublevel') and customer_ret.Sublevel:
                        try:
                            sublevel = customer_ret.Sublevel.GetValue()
                        except:
                            sublevel = 0
                    is_job = sublevel > 0
                    
                    customer_data = {
                        'list_id': customer_ret.ListID.GetValue() if (hasattr(customer_ret, 'ListID') and customer_ret.ListID) else None,
                        'name': customer_ret.Name.GetValue() if (hasattr(customer_ret, 'Name') and customer_ret.Name) else None,
                        'full_name': customer_ret.FullName.GetValue() if (hasattr(customer_ret, 'FullName') and customer_ret.FullName) else None,
                        'is_active': customer_ret.IsActive.GetValue() if (hasattr(customer_ret, 'IsActive') and customer_ret.IsActive) else True,
                        'is_job': is_job,
                        'parent_name': None,
                        'company_name': customer_ret.CompanyName.GetValue() if (hasattr(customer_ret, 'CompanyName') and customer_ret.CompanyName) else None,
                        'bill_address': None
                    }
                    
                    # Get parent reference for jobs
                    if hasattr(customer_ret, 'ParentRef') and customer_ret.ParentRef:
                        customer_data['parent_name'] = customer_ret.ParentRef.FullName.GetValue()
                    
                    # Get billing address
                    if hasattr(customer_ret, 'BillAddress') and customer_ret.BillAddress:
                        addr_lines = []
                        for j in range(1, 6):  # QB supports up to 5 address lines
                            line_attr = getattr(customer_ret.BillAddress, f'Addr{j}', None)
                            if line_attr:
                                line_value = line_attr.GetValue()
                                if line_value:
                                    addr_lines.append(line_value)
                        customer_data['bill_address'] = '\n'.join(addr_lines)
                    
                    customers.append(customer_data)
            
            return customers
            
        except Exception as e:
            logger.error(f"Failed to get customers: {e}")
            return []
    
    def get_all_jobs(self) -> List[Dict]:
        """
        Get all jobs (customers with parents) from QuickBooks
        
        Returns:
            List of job dictionaries
        """
        all_customers = self.get_all_customers(include_jobs=True)
        return [c for c in all_customers if c.get('is_job')]
    
    def resolve_customer_or_job(self, name: str) -> Optional[str]:
        """
        Resolve a customer/job name to the correct QuickBooks reference.
        Returns the proper string to use in QuickBooks (full_name for jobs, name for customers).
        
        This method handles the complexity of:
        - Standalone customers like "shop" should return "shop"
        - Jobs like "Retreat 24" should return "rws:Retreat 24"
        - Already qualified names like "Fox:prestegard" should return as-is
        
        Args:
            name: The customer or job name to resolve
            
        Returns:
            The correct QuickBooks reference string, or None if not found
        """
        try:
            # If it already has a colon, assume it's already qualified
            if ':' in name:
                # Verify it exists
                job = self.find_job_fuzzy(name)
                if job:
                    return job['full_name']
                return None
            
            # Try exact match first
            exact = self.find_customer_by_exact_name(name)
            if exact:
                # Return full_name for jobs, name for standalone customers
                if exact.get('is_job') and exact.get('full_name'):
                    return exact['full_name']
                else:
                    return exact['name']
            
            # Fall back to fuzzy job search
            job = self.find_job_fuzzy(name)
            if job:
                return job['full_name']
            
            # Fall back to fuzzy customer search
            customer = self.find_customer_fuzzy(name)
            if customer:
                return customer['name']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to resolve customer/job '{name}': {e}")
            return None
    
    def find_customer_by_exact_name(self, name: str) -> Optional[Dict]:
        """
        Find a customer or job by exact name match
        
        Args:
            name: Exact customer/job name
        
        Returns:
            Customer/job dictionary if found, None otherwise
        """
        try:
            # Get all customers and jobs
            all_customers = self.get_all_customers(include_jobs=True)
            if not all_customers:
                return None
            
            # Look for exact name match (case-insensitive)
            name_lower = name.lower()
            for customer in all_customers:
                if customer.get('name') and customer['name'].lower() == name_lower:
                    return customer
                # Also check full_name for jobs
                if customer.get('full_name') and customer['full_name'].lower() == name_lower:
                    return customer
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find customer by exact name {name}: {e}")
            return None
    
    def find_customer_by_name(self, name: str) -> Optional[Dict]:
        """
        Find a customer by exact name (deprecated - use find_customer_by_exact_name)
        
        Args:
            name: Exact customer name
        
        Returns:
            Customer dictionary if found, None otherwise
        """
        return self.find_customer_by_exact_name(name)
    
    def find_customer_fuzzy(self, query: str) -> Optional[Dict]:
        """
        Find a customer using fuzzy matching

        Args:
            query: Search term

        Returns:
            Best matching customer dictionary if found
        """
        try:
            # Get all customers AND jobs for fuzzy matching
            all_customers = self.get_all_customers(include_jobs=True)
            if not all_customers:
                logger.warning("No customers found in QuickBooks")
                return None

            # Include both customers and jobs in fuzzy matching
            customer_names = [c['name'] for c in all_customers if c.get('name')]

            # Find best match
            match_result = self.fuzzy_matcher.match_customer(query, customer_names)

            if match_result.found:
                logger.info(f"Customer fuzzy match: {match_result}")
                # Find the full customer data
                for customer in all_customers:
                    if customer.get('name') == match_result.exact_name:
                        return customer

            logger.warning(f"No fuzzy match found for customer: {query}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fuzzy match customer {query}: {e}")
            return None
    
    def get_customer_details(self, name: str) -> Optional[Dict]:
        """
        Get full customer details by name

        Args:
            name: Customer name to lookup

        Returns:
            Customer dictionary with ListID and EditSequence, or None
        """
        try:
            if not fast_qb_connection.connect():
                return None

            request_set = fast_qb_connection.create_request_set()
            query_rq = request_set.AppendCustomerQueryRq()
            query_rq.ORCustomerListQuery.FullNameList.Add(name)

            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)

            if response.StatusCode != 0 or not response.Detail or response.Detail.Count == 0:
                return None

            customer_ret = response.Detail.GetAt(0)
            return {
                'list_id': customer_ret.ListID.GetValue(),
                'edit_sequence': customer_ret.EditSequence.GetValue(),
                'name': customer_ret.Name.GetValue() if hasattr(customer_ret, 'Name') else customer_ret.FullName.GetValue(),
                'full_name': customer_ret.FullName.GetValue() if hasattr(customer_ret, 'FullName') else None,
                'is_job': hasattr(customer_ret, 'ParentRef') and customer_ret.ParentRef is not None,
                'parent_name': customer_ret.ParentRef.FullName.GetValue() if hasattr(customer_ret, 'ParentRef') and customer_ret.ParentRef else None
            }

        except Exception as e:
            logger.error(f"Failed to get customer details: {e}")
            return None

    def update_customer(self, customer_id: str, edit_sequence: str, updates: Dict) -> Dict:
        """
        Update an existing customer

        Args:
            customer_id: ListID of customer to update
            edit_sequence: Edit sequence for the customer
            updates: Dictionary of fields to update (parent_ref, name, etc)

        Returns:
            Success/failure dictionary
        """
        try:
            if not fast_qb_connection.connect():
                return {
                    'success': False,
                    'error': 'Failed to connect to QuickBooks'
                }

            request_set = fast_qb_connection.create_request_set()
            mod_rq = request_set.AppendCustomerModRq()

            # Required fields
            mod_rq.ListID.SetValue(customer_id)
            mod_rq.EditSequence.SetValue(edit_sequence)

            # Set parent if converting to job
            if 'parent_ref' in updates:
                parent_name = updates['parent_ref']
                # Find parent customer
                parent = self.find_customer_fuzzy(parent_name)
                if not parent:
                    return {
                        'success': False,
                        'error': f"Parent customer '{parent_name}' not found"
                    }
                mod_rq.ParentRef.ListID.SetValue(parent['list_id'])
                logger.info(f"Setting ParentRef to {parent['name']} (ID: {parent['list_id']})")

            # Update other fields if provided
            if 'name' in updates:
                mod_rq.Name.SetValue(updates['name'])

            if 'is_active' in updates:
                mod_rq.IsActive.SetValue(updates['is_active'])

            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)

            if response.StatusCode == 0:
                logger.info(f"Successfully updated customer")
                return {'success': True}
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                return {
                    'success': False,
                    'error': f"QB Error {response.StatusCode}: {error_msg}"
                }

        except Exception as e:
            logger.error(f"Failed to update customer: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def search_jobs(self, search_term: Optional[str] = None, active_only: bool = True) -> List[Dict]:
        """
        Search for jobs using fuzzy matching or list all jobs
        
        Args:
            search_term: Optional search term for fuzzy matching
            active_only: Whether to return only active jobs (default: True)
        
        Returns:
            List of matching jobs with their details
        """
        try:
            # Get all jobs
            all_jobs = self.get_all_jobs()
            if not all_jobs:
                return []
            
            # Filter by active status if requested
            if active_only:
                jobs = [j for j in all_jobs if j.get('is_active', True)]
            else:
                jobs = all_jobs
            
            # If no search term, return all (filtered) jobs
            if not search_term:
                return jobs
            
            # Perform fuzzy search
            search_lower = search_term.lower()
            matching_jobs = []
            
            for job in jobs:
                # Check various fields for matches - handle None values
                full_name = (job.get('full_name') or '').lower()
                name = (job.get('name') or '').lower()
                parent = (job.get('parent_name') or '').lower()
                
                # Calculate match score
                score = 0
                if search_lower in full_name:
                    score = 100  # Exact substring match in full name
                elif search_lower in name:
                    score = 80  # Match in job name
                elif search_lower in parent:
                    score = 60  # Match in customer name
                else:
                    # Fuzzy match
                    from difflib import SequenceMatcher
                    score = max(
                        SequenceMatcher(None, search_lower, full_name).ratio() * 100,
                        SequenceMatcher(None, search_lower, name).ratio() * 80,
                        SequenceMatcher(None, search_lower, parent).ratio() * 60
                    )
                
                if score > 40:  # Threshold for fuzzy matches
                    job['match_score'] = score
                    matching_jobs.append(job)
            
            # Sort by match score
            matching_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            
            # Remove match_score from results
            for job in matching_jobs:
                job.pop('match_score', None)
            
            return matching_jobs
            
        except Exception as e:
            logger.error(f"Failed to search jobs: {e}")
            return []
    
    def find_job_fuzzy(self, query: str) -> Optional[Dict]:
        """
        Find a job using fuzzy matching
        Handles both "customer:job" format and partial matches
        
        Args:
            query: Search term (can be customer prefix, job name, etc.)
        
        Returns:
            Best matching job dictionary if found
        """
        try:
            # Get all jobs
            all_jobs = self.get_all_jobs()
            if not all_jobs:
                logger.warning("No jobs found in QuickBooks")
                return None
            
            # Use full_name for job matching (includes customer:job format)
            job_names = [j['full_name'] for j in all_jobs if j.get('full_name')]
            
            # Find best match
            match_result = self.fuzzy_matcher.match_job(query, job_names)
            
            if match_result.found:
                logger.info(f"Job fuzzy match: {match_result}")
                # Find the full job data
                for job in all_jobs:
                    if job.get('full_name') == match_result.exact_name:
                        return job
            
            logger.warning(f"No fuzzy match found for job: {query}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fuzzy match job {query}: {e}")
            return None
    
    def create_customer(self, customer_data: Dict) -> Dict:
        """
        Create a new customer in QuickBooks
        
        Args:
            customer_data: Dictionary with customer details:
                {
                    'name': str (required),
                    'company_name': str (optional),
                    'address': str (optional),
                    'phone': str (optional),
                    'email': str (optional)
                }
        
        Returns:
            Result dictionary with success status and error details
        """
        try:
            if not fast_qb_connection.connect():
                error_msg = "[CustomerRepository.create_customer] Failed to connect to QuickBooks"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'error_source': 'CustomerRepository.create_customer',
                    'explanation': 'QuickBooks is not open or connection failed'
                }
            
            request_set = fast_qb_connection.create_request_set()
            add_rq = request_set.AppendCustomerAddRq()
            
            add_rq.Name.SetValue(customer_data['name'])
            
            if customer_data.get('company_name'):
                add_rq.CompanyName.SetValue(customer_data['company_name'])
            
            if customer_data.get('address'):
                # Parse address into lines (up to 5)
                addr_lines = customer_data['address'].split('\n')[:5]
                addr = add_rq.BillAddress
                for i, line in enumerate(addr_lines):
                    if i == 0 and line: addr.Addr1.SetValue(line)
                    elif i == 1 and line: addr.Addr2.SetValue(line)
                    elif i == 2 and line: addr.Addr3.SetValue(line)
                    elif i == 3 and line: addr.Addr4.SetValue(line)
                    elif i == 4 and line: addr.Addr5.SetValue(line)
            
            if customer_data.get('phone'):
                add_rq.Phone.SetValue(customer_data['phone'])
            
            if customer_data.get('email'):
                add_rq.Email.SetValue(customer_data['email'])
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Created customer: {customer_data['name']}")
                return {'success': True, 'message': f"Customer '{customer_data['name']}' created"}
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                error_code = response.StatusCode
                
                # Provide helpful error explanations
                explanation = ""
                if "already in use" in error_msg.lower():
                    explanation = f"A customer named '{customer_data['name']}' already exists"
                elif "permission" in error_msg.lower():
                    explanation = "QuickBooks user doesn't have permission to create customers"
                else:
                    explanation = "QuickBooks rejected the customer creation"
                
                full_error = f"[CustomerRepository.create_customer] QB Error {error_code}: {error_msg}"
                logger.error(full_error)
                
                return {
                    'success': False,
                    'error': full_error,
                    'error_code': error_code,
                    'error_message': error_msg,
                    'error_source': 'CustomerRepository.create_customer',
                    'explanation': explanation
                }
            
        except Exception as e:
            error_msg = f"[CustomerRepository.create_customer] Exception: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'error_source': 'CustomerRepository.create_customer',
                'explanation': 'Unexpected error while creating customer'
            }
    
    def create_job(self, job_data: Dict) -> Dict:
        """
        Create a new job under a customer in QuickBooks
        
        Args:
            job_data: Dictionary with job details:
                {
                    'name': str (required - job name),
                    'parent_name': str (required - customer name),
                    'description': str (optional)
                }
        
        Returns:
            Result dictionary with success status and error details
        """
        try:
            # First find the parent customer
            parent = self.find_customer_by_name(job_data['parent_name'])
            if not parent:
                # Try fuzzy match
                parent = self.find_customer_fuzzy(job_data['parent_name'])
                if not parent:
                    error_msg = f"[CustomerRepository.create_job] Parent customer not found: '{job_data['parent_name']}'"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'error_source': 'CustomerRepository.create_job',
                        'explanation': f"No customer named '{job_data['parent_name']}' exists. Create the customer first."
                    }
            
            if not fast_qb_connection.connect():
                error_msg = "[CustomerRepository.create_job] Failed to connect to QuickBooks"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'error_source': 'CustomerRepository.create_job',
                    'explanation': 'QuickBooks is not open or connection failed'
                }
            
            request_set = fast_qb_connection.create_request_set()
            add_rq = request_set.AppendCustomerAddRq()
            
            # Set job name
            add_rq.Name.SetValue(job_data['name'])
            
            # Set parent reference
            add_rq.ParentRef.ListID.SetValue(parent['list_id'])
            
            # Set job status (optional)
            if job_data.get('description'):
                add_rq.Notes.SetValue(job_data['description'])
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Created job: {parent['name']}:{job_data['name']}")
                return {
                    'success': True,
                    'message': f"Job '{job_data['name']}' created under customer '{parent['name']}'"
                }
            else:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                error_code = response.StatusCode
                
                # Provide helpful error explanations
                explanation = ""
                if "already in use" in error_msg.lower():
                    explanation = f"A job named '{job_data['name']}' already exists under '{parent['name']}'"
                elif "permission" in error_msg.lower():
                    explanation = "QuickBooks user doesn't have permission to create jobs"
                else:
                    explanation = "QuickBooks rejected the job creation"
                
                full_error = f"[CustomerRepository.create_job] QB Error {error_code}: {error_msg}"
                logger.error(full_error)
                
                return {
                    'success': False,
                    'error': full_error,
                    'error_code': error_code,
                    'error_message': error_msg,
                    'error_source': 'CustomerRepository.create_job',
                    'explanation': explanation
                }
            
        except Exception as e:
            error_msg = f"[CustomerRepository.create_job] Exception: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'error_source': 'CustomerRepository.create_job',
                'explanation': 'Unexpected error while creating job'
            }