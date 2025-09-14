#!/usr/bin/env python
"""
List all available QBConnector commands
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qb.connector import QBConnector

def list_commands():
    """List all available commands"""
    qb = QBConnector()
    
    # Get command map from the execute_command method
    command_map = {
        # Work Bill Commands
        "GET_WORK_BILL": "Get vendor's current work bill",
        "CREATE_WORK_BILL": "Create new work bill", 
        "UPDATE_WORK_BILL": "Update existing work bill (add/remove days)",
        "DELETE_BILL": "Delete a bill",
        "GET_WORK_WEEK_SUMMARY": "Get weekly summary",
        
        # Vendor Commands
        "SEARCH_VENDORS": "Search for vendors",
        "CREATE_VENDOR": "Create new vendor",
        "UPDATE_VENDOR": "Update vendor info",
        
        # Customer Commands
        "SEARCH_CUSTOMERS": "Search for customers",
        "CREATE_CUSTOMER": "Create new customer",
        
        # Check Commands
        "CREATE_CHECK": "Create a check",
        "SEARCH_CHECKS": "Search for checks",
        "UPDATE_CHECK": "Update a check",
        "DELETE_CHECK": "Delete a check",
        "GET_CHECK": "Get specific check",
        "GET_CHECKS_THIS_WEEK": "Get this week's checks",
        
        # Invoice Commands
        "SEARCH_INVOICES": "Search for invoices",
        "GET_INVOICES_THIS_WEEK": "Get this week's invoices",
        "GET_INVOICE": "Get specific invoice",
        "CREATE_INVOICE": "Create new invoice",
        
        # Bill Payment Commands
        "PAY_BILLS": "Pay vendor bills",
        "CREATE_BILL_PAYMENT": "Create bill payment",
        "SEARCH_BILL_PAYMENTS": "Search bill payments",
        "DELETE_BILL_PAYMENT": "Delete bill payment",
        "UPDATE_BILL_PAYMENT": "Update bill payment",
        
        # Item Commands
        "SEARCH_ITEMS": "Search for items",
        "CREATE_ITEM": "Create new item",
        "UPDATE_ITEM": "Update item",
        
        # Account Commands
        "SEARCH_ACCOUNTS": "Search for accounts",
        "CREATE_ACCOUNT": "Create new account",
        "UPDATE_ACCOUNT": "Update account",
        
        # Deposit Commands
        "SEARCH_DEPOSITS": "Search for deposits",
        "DEPOSIT_CUSTOMER_PAYMENT": "Deposit customer payment",
    }
    
    print("\n=== QBConnector Available Commands ===\n")
    
    for category in ["Work Bill", "Vendor", "Customer", "Check", "Invoice", "Bill Payment", "Item", "Account", "Deposit"]:
        print(f"\n{category} Commands:")
        print("-" * 40)
        for cmd, desc in command_map.items():
            if category.upper().replace(" ", "_") in cmd or category.upper().replace(" ", "") in cmd:
                print(f"  {cmd}: {desc}")
    
    print(f"\n\nTotal commands available: {len(command_map)}")
    print("\nUsage: qb.execute_command('COMMAND_NAME', {'param1': value1, ...})")

if __name__ == "__main__":
    list_commands()