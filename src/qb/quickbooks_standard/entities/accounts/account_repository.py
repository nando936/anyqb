"""
Account Repository - Standard QuickBooks account operations using QBFC SDK
NO custom business logic - only pure QB operations
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import pywintypes
from shared_utilities.fast_qb_connection import fast_qb_connection

logger = logging.getLogger(__name__)

class AccountRepository:
    """Handles standard QuickBooks account operations using QBFC SDK"""
    
    def __init__(self):
        """Initialize account repository"""
        pass  # Using singleton fast_qb_connection
    
    def search_accounts(self, search_term: Optional[str] = None, account_type: Optional[str] = None, active_only: bool = True) -> List[Dict]:
        """
        Search accounts with optional filters
        
        Args:
            search_term: Optional search term for fuzzy matching
            account_type: Filter by account type (Bank, Income, Expense, Asset, Liability, etc.)
            active_only: Only return active accounts
            
        Returns:
            List of matching accounts
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return []
            
            request_set = fast_qb_connection.create_request_set()
            account_query = request_set.AppendAccountQueryRq()
            
            # Note: ActiveStatus may not be supported in all QB versions
            # We'll filter active status in post-processing instead
            # if active_only:
            #     account_query.ActiveStatus.SetValue(1)  # Active only
            
            # Note: SDK doesn't support direct account type filter in query
            # We'll filter in post-processing
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            logger.info(f"Account query response StatusCode: {response.StatusCode}")
            
            if response.StatusCode != 0:
                logger.error(f"Account query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return []
            
            # Check different response formats
            accounts = []
            
            # Try Detail first (most common)
            if hasattr(response, 'Detail') and response.Detail:
                logger.info(f"Found Detail with Count: {response.Detail.Count}")
                for i in range(response.Detail.Count):
                    account_ret = response.Detail.GetAt(i)
                    account_data = self._parse_account_from_sdk(account_ret)
                    
                    if account_data:
                        # Apply active filter
                        if active_only and not account_data.get('is_active', True):
                            continue
                            
                        # Apply search filter if provided
                        if search_term:
                            search_lower = search_term.lower()
                            if not (search_lower in account_data['name'].lower() or
                                    (account_data.get('description') and search_lower in account_data['description'].lower()) or
                                    (account_data.get('account_type') and search_lower in account_data['account_type'].lower())):
                                continue
                        
                        # Apply type filter if provided
                        if account_type and account_data.get('account_type') and account_data['account_type'].lower() != account_type.lower():
                            continue
                        
                        accounts.append(account_data)
            # If no Detail, try other response formats
            elif hasattr(response, 'AccountRet'):
                logger.info("Found AccountRet in response (single account)")
                account_data = self._parse_account_from_sdk(response.AccountRet)
                if account_data:
                    accounts.append(account_data)
            else:
                logger.warning("No recognized account data format in response")
            
            # Sort by name
            accounts.sort(key=lambda x: x.get('name', ''))
            
            return accounts
            
        except Exception as e:
            logger.error(f"Failed to search accounts: {e}")
            return []
    
    def get_account(self, account_name: str) -> Optional[Dict]:
        """Get a specific account by name"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            account_query = request_set.AppendAccountQueryRq()
            
            # Query by name
            account_query.ORListQuery.FullNameList.Add(account_name)
            
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                logger.error(f"Account query failed: {response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown'}")
                return None
            
            if not response.Detail or response.Detail.Count == 0:
                logger.error(f"Account {account_name} not found")
                return None
            
            account_ret = response.Detail.GetAt(0)
            return self._parse_account_from_sdk(account_ret)
            
        except Exception as e:
            logger.error(f"Failed to get account {account_name}: {e}")
            return None
    
    def create_account(self, account_data: Dict) -> Optional[Dict]:
        """Create a new account in QuickBooks"""
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            account_add = request_set.AppendAccountAddRq()
            
            # Required: Account name
            if 'name' not in account_data:
                logger.error("Account name is required")
                return None
            account_add.Name.SetValue(account_data['name'])
            
            # Required: Account type
            if 'account_type' not in account_data:
                logger.error("Account type is required")
                return None
            
            # Map account type string to SDK enum value
            type_mapping = {
                'BANK': 0,
                'ACCOUNTSRECEIVABLE': 1,
                'OTHERASSET': 2,
                'FIXEDASSET': 3,
                'OTHERCURRENTASSET': 4,
                'ACCOUNTSPAYABLE': 5,
                'CREDITCARD': 6,
                'OTHERCURRENTLIABILITY': 7,
                'LONGTERMLIABILITY': 8,
                'EQUITY': 9,
                'INCOME': 10,
                'COSTOFGOODSSOLD': 11,
                'EXPENSE': 12,
                'OTHEREXPENSE': 13,
                'OTHERINCOME': 14,
                'NONPOSTING': 15
            }
            
            account_type_upper = account_data['account_type'].upper().replace(' ', '').replace('_', '')
            if account_type_upper in type_mapping:
                account_add.AccountType.SetValue(type_mapping[account_type_upper])
            else:
                logger.error(f"Invalid account type: {account_data['account_type']}")
                return None
            
            # Optional: Description
            if 'description' in account_data:
                account_add.Desc.SetValue(account_data['description'])
            
            # Optional: Account number
            if 'account_number' in account_data:
                account_add.AccountNumber.SetValue(str(account_data['account_number']))
            
            # Optional: Bank account number (for bank accounts)
            if 'bank_number' in account_data:
                account_add.BankNumber.SetValue(str(account_data['bank_number']))
            
            # Optional: Opening balance (requires date)
            if 'opening_balance' in account_data and 'opening_balance_date' in account_data:
                account_add.OpenBalance.SetValue(account_data['opening_balance'])
                account_add.OpenBalanceDate.SetValue(account_data['opening_balance_date'])
            
            # Optional: Parent account (for sub-accounts)
            if 'parent_account' in account_data:
                account_add.ParentRef.FullName.SetValue(account_data['parent_account'])
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to create account: {error_msg}")
                return None
            
            if not response.Detail:
                logger.error("No account data returned after creation")
                return None
            
            account_ret = response.Detail
            return self._parse_account_from_sdk(account_ret)
            
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            return None
    
    def update_account(self, account_name: str, updates: Dict) -> Optional[Dict]:
        """Update an existing account"""
        try:
            # First get the existing account with ListID and EditSequence
            existing_account = self.get_account(account_name)
            if not existing_account:
                logger.error(f"Account {account_name} not found for update")
                return None
            
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return None
            
            request_set = fast_qb_connection.create_request_set()
            account_mod = request_set.AppendAccountModRq()
            
            # Required: ListID and EditSequence
            account_mod.ListID.SetValue(existing_account['list_id'])
            account_mod.EditSequence.SetValue(existing_account['edit_sequence'])
            
            # Apply updates
            if 'name' in updates:
                account_mod.Name.SetValue(updates['name'])
            
            if 'description' in updates:
                account_mod.Desc.SetValue(updates['description'])
            
            if 'account_number' in updates:
                account_mod.AccountNumber.SetValue(str(updates['account_number']))
            
            if 'bank_number' in updates:
                account_mod.BankNumber.SetValue(str(updates['bank_number']))
            
            if 'is_active' in updates:
                account_mod.IsActive.SetValue(updates['is_active'])
            
            # Note: Account type cannot be changed after creation
            
            # Process the request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode != 0:
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else 'Unknown error'
                logger.error(f"Failed to update account: {error_msg}")
                return None
            
            if not response.Detail:
                logger.error("No account data returned after update")
                return None
            
            account_ret = response.Detail
            return self._parse_account_from_sdk(account_ret)
            
        except Exception as e:
            logger.error(f"Failed to update account {account_name}: {e}")
            return None
    
    def _parse_account_from_sdk(self, account_ret) -> Optional[Dict]:
        """Parse account data from SDK response"""
        try:
            # Map account type enum values to string names
            # NOTE: These mappings are based on actual QuickBooks data, not QBFC docs
            # The enum values differ from standard QBFC documentation
            type_enum_to_string = {
                0: 'AccountsPayable',         # Accounts Payable (system account)
                1: 'AccountsReceivable',      # Accounts Receivable
                2: 'Bank',                    # Bank accounts (1887 b, Cuenta de Cash, etc.)
                3: 'CostOfGoodsSold',         # Cost of Goods Sold, Job Materials Purchased
                4: 'OtherCurrentAsset',       # boa cs credit card
                5: 'Equity',                  # Capital Stock
                6: 'Expense',                 # Auto and Truck Expenses, fuel, Gas accounts
                7: 'OtherCurrentLiability',   # Accumulated Depreciation
                8: 'Income',                  # Job Income
                9: 'OtherIncome',             # (not confirmed)
                10: 'NonPosting',             # Estimates, Purchase Orders
                11: 'LongTermLiability',      # Cuotas autos nuevos
                12: 'OtherCurrentAsset',      # Inventory Asset
                13: 'OtherLiability',         # Loan From CS
                14: 'OtherExpense',           # Ask My Accountant
                15: 'FixedAsset'              # (not confirmed)
            }
            
            # Safe getter function
            def safe_get(obj, attr_name, default=None):
                """Safely get attribute value from SDK object"""
                if obj is None:
                    return default
                if hasattr(obj, attr_name):
                    attr = getattr(obj, attr_name)
                    if attr is not None and hasattr(attr, 'GetValue'):
                        return attr.GetValue()
                return default
            
            # Get account type as string
            account_type_value = None
            if hasattr(account_ret, 'AccountType') and account_ret.AccountType:
                type_enum = safe_get(account_ret, 'AccountType')
                if type_enum is not None:
                    account_type_value = type_enum_to_string.get(type_enum, f'Unknown_{type_enum}')
            
            # Build account data with safe access
            account_data = {
                'list_id': safe_get(account_ret, 'ListID'),
                'edit_sequence': safe_get(account_ret, 'EditSequence'),
                'name': safe_get(account_ret, 'Name'),
                'full_name': safe_get(account_ret, 'FullName'),
                'is_active': safe_get(account_ret, 'IsActive', True),
                'sublevel': safe_get(account_ret, 'Sublevel', 0),
                'account_type': account_type_value,
                'account_number': safe_get(account_ret, 'AccountNumber'),
                'bank_number': safe_get(account_ret, 'BankNumber'),
                'description': safe_get(account_ret, 'Desc'),
                'balance': 0.0,
                'total_balance': 0.0,
            }
            
            # Handle balance fields separately with float conversion
            balance_val = safe_get(account_ret, 'Balance')
            if balance_val is not None:
                try:
                    account_data['balance'] = float(balance_val)
                except (ValueError, TypeError):
                    pass
            
            total_balance_val = safe_get(account_ret, 'TotalBalance')
            if total_balance_val is not None:
                try:
                    account_data['total_balance'] = float(total_balance_val)
                except (ValueError, TypeError):
                    pass
            
            # Parent account reference
            if hasattr(account_ret, 'ParentRef') and account_ret.ParentRef:
                if hasattr(account_ret.ParentRef, 'FullName') and account_ret.ParentRef.FullName:
                    account_data['parent_account'] = safe_get(account_ret.ParentRef, 'FullName')
            
            # Cash flow classification (for reports)
            account_data['cash_flow_classification'] = safe_get(account_ret, 'CashFlowClassification')
            
            return account_data
            
        except Exception as e:
            logger.error(f"Failed to parse account data: {e}")
            return None