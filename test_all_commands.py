#!/usr/bin/env python
"""
Test ALL QuickBooks Commands via Claude API
Uses real QB test data, not demo/fake data
Tests direct Claude API -> QB integration (no MCP)
"""
import asyncio
import json
import time
from typing import Dict, List
import requests
from datetime import datetime

# Test configuration
API_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_URL}/api/chat"
EXECUTE_ENDPOINT = f"{API_URL}/api/execute"

def test_chat_command(message: str, test_name: str) -> Dict:
    """Test a command via chat endpoint (uses Claude API)"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"Message: {message}")
    print("-" * 40)
    
    try:
        start = time.time()
        response = requests.post(
            CHAT_ENDPOINT,
            json={"message": message},
            timeout=45
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Success in {elapsed:.2f}s")
            print(f"Command: {data.get('command', 'N/A')}")
            
            # Show first 500 chars of response
            output = data.get('response', '')[:500]
            if len(data.get('response', '')) > 500:
                output += "..."
            print(f"Output: {output}")
            
            return {"success": True, "time": elapsed, "data": data}
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        return {"success": False, "error": str(e)}

def test_direct_command(command: str, params: Dict, test_name: str) -> Dict:
    """Test a command via direct execute endpoint (bypasses Claude)"""
    print(f"\n{'='*60}")
    print(f"Testing Direct: {test_name}")
    print(f"Command: {command}")
    print(f"Params: {json.dumps(params)[:100]}")
    print("-" * 40)
    
    try:
        start = time.time()
        response = requests.post(
            EXECUTE_ENDPOINT,
            json={"command": command, "params": params},
            timeout=30
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Success in {elapsed:.2f}s")
            
            # Show first 500 chars of output
            output = data.get('output', '')[:500]
            if len(data.get('output', '')) > 500:
                output += "..."
            print(f"Output: {output}")
            
            return {"success": True, "time": elapsed, "data": data}
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        return {"success": False, "error": str(e)}

def main():
    """Test all QB commands with real test data"""
    
    print("\n" + "="*60)
    print("ANYQB COMPREHENSIVE COMMAND TEST")
    print("Testing Claude API -> QB Direct Integration")
    print("Using REAL QuickBooks Test Data")
    print("="*60)
    
    # Check server health first
    try:
        health = requests.get(f"{API_URL}/api/health").json()
        print(f"\n[OK] Server Status: {health['status']}")
        print(f"[OK] QB Connected: {health['qb_connected']}")
        print(f"[OK] Claude Ready: {health['claude_ready']}")
    except Exception as e:
        print(f"\n[ERROR] Server not running: {e}")
        return
    
    results = {"passed": 0, "failed": 0, "commands": {}}
    
    # ========== BILL COMMANDS ==========
    print("\n\n" + "="*60)
    print("BILL COMMANDS")
    print("="*60)
    
    bill_tests = [
        ("show me jaciel's bill", "GET_WORK_BILL - Jaciel"),
        ("get juan's bill", "GET_WORK_BILL - Juan"),
        ("show elmer's work bill", "GET_WORK_BILL - Elmer"),
        ("create bill for TEST_VENDOR with 200 daily", "CREATE_WORK_BILL"),
        ("update jaciel's bill add friday", "UPDATE_WORK_BILL - Add Day"),
        ("get this week's summary", "GET_WORK_WEEK_SUMMARY"),
        ("show me last week's summary", "GET_WORK_WEEK_SUMMARY - Last Week"),
    ]
    
    for message, test_name in bill_tests:
        result = test_chat_command(message, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== VENDOR COMMANDS ==========
    print("\n\n" + "="*60)
    print("VENDOR COMMANDS")
    print("="*60)
    
    vendor_tests = [
        ("list all vendors", "SEARCH_VENDORS - All"),
        ("find vendor martinez", "SEARCH_VENDORS - Martinez"),
        ("search vendor jaciel", "SEARCH_VENDORS - Jaciel"),
        ("show vendors with daily cost", "SEARCH_VENDORS - With Cost"),
        ("create vendor TEST_AUTO_2025 with 250 daily", "CREATE_VENDOR"),
        ("update vendor TEST_VENDOR daily to 300", "UPDATE_VENDOR"),
    ]
    
    for message, test_name in vendor_tests:
        result = test_chat_command(message, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== CUSTOMER COMMANDS ==========
    print("\n\n" + "="*60)
    print("CUSTOMER COMMANDS")
    print("="*60)
    
    customer_tests = [
        ("list all customers", "SEARCH_CUSTOMERS - All"),
        ("find customer fox", "SEARCH_CUSTOMERS - Fox"),
        ("search jobs", "SEARCH_CUSTOMERS - Jobs Only"),
        ("show all jobs", "SEARCH_CUSTOMERS - All Jobs"),
    ]
    
    for message, test_name in customer_tests:
        result = test_chat_command(message, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== CHECK COMMANDS ==========
    print("\n\n" + "="*60)
    print("CHECK COMMANDS")
    print("="*60)
    
    check_tests = [
        ("show this week's checks", "GET_CHECKS_THIS_WEEK"),
        ("search all checks", "SEARCH_CHECKS - All"),
        ("find checks to juan", "SEARCH_CHECKS - Juan"),
        ("find checks to elmer", "SEARCH_CHECKS - Elmer"),
        ("create check to TEST_VENDOR for 500", "CREATE_CHECK"),
    ]
    
    for message, test_name in check_tests:
        result = test_chat_command(message, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== PAYMENT COMMANDS ==========
    print("\n\n" + "="*60)
    print("PAYMENT COMMANDS")
    print("="*60)
    
    payment_tests = [
        ("pay jaciel 450", "PAY_BILLS - Jaciel"),
        ("search bill payments", "SEARCH_BILL_PAYMENTS"),
        ("show all bill payments", "SEARCH_BILL_PAYMENTS - All"),
        ("create payment for TEST_VENDOR", "CREATE_BILL_PAYMENT"),
    ]
    
    for message, test_name in payment_tests:
        result = test_chat_command(message, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== INVOICE COMMANDS ==========
    print("\n\n" + "="*60)
    print("INVOICE COMMANDS")
    print("="*60)
    
    invoice_tests = [
        ("show this week's invoices", "GET_INVOICES_THIS_WEEK"),
        ("search all invoices", "SEARCH_INVOICES - All"),
        ("find unpaid invoices", "SEARCH_INVOICES - Unpaid"),
        ("get invoice 1001", "GET_INVOICE"),
    ]
    
    for message, test_name in invoice_tests:
        result = test_chat_command(message, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== ITEM COMMANDS ==========
    print("\n\n" + "="*60)
    print("ITEM COMMANDS")
    print("="*60)
    
    item_tests = [
        ("search all items", "SEARCH_ITEMS - All"),
        ("find service items", "SEARCH_ITEMS - Services"),
        ("list products", "SEARCH_ITEMS - Products"),
    ]
    
    for message, test_name in item_tests:
        result = test_chat_command(message, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== ACCOUNT COMMANDS ==========
    print("\n\n" + "="*60)
    print("ACCOUNT COMMANDS")
    print("="*60)
    
    account_tests = [
        ("list all accounts", "SEARCH_ACCOUNTS - All"),
        ("show bank accounts", "SEARCH_ACCOUNTS - Bank"),
        ("find expense accounts", "SEARCH_ACCOUNTS - Expense"),
    ]
    
    for message, test_name in account_tests:
        result = test_chat_command(message, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== DEPOSIT COMMANDS ==========
    print("\n\n" + "="*60)
    print("DEPOSIT COMMANDS")
    print("="*60)
    
    deposit_tests = [
        ("search all deposits", "SEARCH_DEPOSITS - All"),
        ("show this week's deposits", "SEARCH_DEPOSITS - This Week"),
    ]
    
    for message, test_name in deposit_tests:
        result = test_chat_command(message, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== DIRECT EXECUTE TESTS (Bypass Claude) ==========
    print("\n\n" + "="*60)
    print("DIRECT EXECUTE TESTS (Bypassing Claude API)")
    print("="*60)
    
    direct_tests = [
        ("GET_WORK_BILL", {"vendor_name": "jaciel"}, "Direct: Jaciel Bill"),
        ("SEARCH_VENDORS", {"search_term": "martinez"}, "Direct: Search Martinez"),
        ("SEARCH_CUSTOMERS", {"active_only": True}, "Direct: Active Customers"),
        ("GET_CHECKS_THIS_WEEK", {}, "Direct: This Week Checks"),
        ("SEARCH_ITEMS", {"item_type": "Service"}, "Direct: Service Items"),
    ]
    
    for command, params, test_name in direct_tests:
        result = test_direct_command(command, params, test_name)
        results["commands"][test_name] = result
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # ========== FINAL REPORT ==========
    print("\n\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    total = results["passed"] + results["failed"]
    success_rate = (results["passed"] / total * 100) if total > 0 else 0
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {results['passed']} [OK]")
    print(f"Failed: {results['failed']} [ERROR]")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Show failed tests
    if results["failed"] > 0:
        print("\n" + "-"*40)
        print("FAILED TESTS:")
        for cmd_name, result in results["commands"].items():
            if not result["success"]:
                print(f"  [ERROR] {cmd_name}: {result.get('error', 'Unknown error')}")
    
    # Performance stats
    print("\n" + "-"*40)
    print("PERFORMANCE STATS:")
    times = [r["time"] for r in results["commands"].values() if r.get("time")]
    if times:
        print(f"  Average Response Time: {sum(times)/len(times):.2f}s")
        print(f"  Fastest: {min(times):.2f}s")
        print(f"  Slowest: {max(times):.2f}s")
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test_results_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    results = main()
    
    # Exit with error code if tests failed
    import sys
    sys.exit(0 if results["failed"] == 0 else 1)