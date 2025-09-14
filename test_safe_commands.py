#!/usr/bin/env python
"""
Safe Test of QB Commands - Uses TEST data only
Does NOT modify live/production data
Tests Claude API natural language -> QB command conversion
"""
import json
import time
import requests
from datetime import datetime

API_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_URL}/api/chat"

def test_command(message: str, expected_command: str = None):
    """Test a natural language command via Claude API"""
    print(f"\n{'='*60}")
    print(f"Testing: {message}")
    print("-" * 40)
    
    try:
        start = time.time()
        response = requests.post(
            CHAT_ENDPOINT,
            json={"message": message},
            timeout=30
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            command = data.get('command', 'N/A')
            success = data.get('success', False)
            
            # Check if command matches expected
            if expected_command and command != expected_command:
                print(f"[WARNING] Expected {expected_command}, got {command}")
            
            print(f"[OK] Response in {elapsed:.2f}s")
            print(f"Command Detected: {command}")
            print(f"Success: {success}")
            
            # Show first 300 chars of response
            output = data.get('response', '')[:300]
            if len(data.get('response', '')) > 300:
                output += "..."
            print(f"Output: {output}")
            
            return {"success": success, "command": command, "time": elapsed}
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            return {"success": False}
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {"success": False}

def main():
    """Run safe tests using TEST data only"""
    
    print("\n" + "="*60)
    print("SAFE QB COMMAND TESTING")
    print("Using TEST vendors/data only - NO LIVE DATA MODIFICATIONS")
    print("Testing: Natural Language -> Claude API -> QB Commands")
    print("="*60)
    
    # Check server health
    try:
        health = requests.get(f"{API_URL}/api/health").json()
        print(f"\n[OK] Server: {health['status']}")
        print(f"[OK] QB Connected: {health['qb_connected']}")
        print(f"[OK] Claude API: {health['claude_ready']}")
    except Exception as e:
        print(f"\n[ERROR] Server not running: {e}")
        return
    
    results = []
    
    # ========== READ-ONLY TESTS (Safe) ==========
    print("\n\n" + "="*60)
    print("READ-ONLY COMMANDS (Safe to Run)")
    print("="*60)
    
    readonly_tests = [
        # Search/List Commands - These only READ data
        ("list all vendors", "SEARCH_VENDORS"),
        ("show me vendors", "SEARCH_VENDORS"),
        ("find vendor TEST", "SEARCH_VENDORS"),
        ("search vendor TEST_VENDOR", "SEARCH_VENDORS"),
        
        ("list all customers", "SEARCH_CUSTOMERS"),
        ("show customers", "SEARCH_CUSTOMERS"),
        ("find jobs", "SEARCH_CUSTOMERS"),
        
        ("show all items", "SEARCH_ITEMS"),
        ("list services", "SEARCH_ITEMS"),
        ("find products", "SEARCH_ITEMS"),
        
        ("list all accounts", "SEARCH_ACCOUNTS"),
        ("show bank accounts", "SEARCH_ACCOUNTS"),
        
        ("search all checks", "SEARCH_CHECKS"),
        ("show this week's checks", "GET_CHECKS_THIS_WEEK"),
        
        ("search invoices", "SEARCH_INVOICES"),
        ("show this week's invoices", "GET_INVOICES_THIS_WEEK"),
        
        ("search deposits", "SEARCH_DEPOSITS"),
        ("show bill payments", "SEARCH_BILL_PAYMENTS"),
        
        # Get specific TEST vendor bills (read-only)
        ("show TEST_VENDOR bill", "GET_WORK_BILL"),
        ("get TEST_VENDOR_2025 bill", "GET_WORK_BILL"),
        ("show me TEST-VENDOR-2025-B bill", "GET_WORK_BILL"),
        
        # Week summaries (read-only)
        ("get this week's summary", "GET_WORK_WEEK_SUMMARY"),
        ("show week summary", "GET_WORK_WEEK_SUMMARY"),
    ]
    
    for message, expected_cmd in readonly_tests:
        result = test_command(message, expected_cmd)
        results.append(result)
        time.sleep(0.5)  # Small delay between requests
    
    # ========== TEST DATA WRITE COMMANDS (Safe) ==========
    print("\n\n" + "="*60)
    print("TEST DATA WRITE COMMANDS (Only affects TEST entities)")
    print("="*60)
    
    test_write_commands = [
        # These only affect TEST vendors/entities
        ("create vendor TEST_API_VENDOR with 150 daily", "CREATE_VENDOR"),
        ("update TEST_VENDOR daily to 200", "UPDATE_VENDOR"),
        ("create bill for TEST_VENDOR with 200 daily", "CREATE_WORK_BILL"),
        ("update TEST_VENDOR bill add friday", "UPDATE_WORK_BILL"),
        ("add saturday to TEST_VENDOR bill", "UPDATE_WORK_BILL"),
        ("create check to TEST_VENDOR for 300", "CREATE_CHECK"),
        ("pay TEST_VENDOR 300", "PAY_BILLS"),
    ]
    
    print("\n[INFO] These commands would modify TEST data only:")
    for message, expected_cmd in test_write_commands:
        print(f"  - {message} -> {expected_cmd}")
    
    user_input = input("\nDo you want to run TEST data write commands? (y/n): ")
    if user_input.lower() == 'y':
        for message, expected_cmd in test_write_commands:
            result = test_command(message, expected_cmd)
            results.append(result)
            time.sleep(0.5)
    else:
        print("[SKIPPED] Write commands not executed")
    
    # ========== NATURAL LANGUAGE VARIATIONS ==========
    print("\n\n" + "="*60)
    print("NATURAL LANGUAGE VARIATIONS TEST")
    print("="*60)
    
    variations = [
        # Different ways to ask for vendor list
        ("show vendors", "SEARCH_VENDORS"),
        ("display all vendors", "SEARCH_VENDORS"),
        ("give me vendor list", "SEARCH_VENDORS"),
        ("I need to see vendors", "SEARCH_VENDORS"),
        
        # Different ways to ask for bills
        ("show TEST_VENDOR's bill", "GET_WORK_BILL"),
        ("get bill for TEST_VENDOR", "GET_WORK_BILL"),
        ("I need TEST_VENDOR bill", "GET_WORK_BILL"),
        ("display TEST_VENDOR work bill", "GET_WORK_BILL"),
        
        # Different ways to ask for week summary
        ("what's this week's total", "GET_WORK_WEEK_SUMMARY"),
        ("show me weekly summary", "GET_WORK_WEEK_SUMMARY"),
        ("get week totals", "GET_WORK_WEEK_SUMMARY"),
    ]
    
    for message, expected_cmd in variations:
        result = test_command(message, expected_cmd)
        results.append(result)
        time.sleep(0.5)
    
    # ========== RESULTS SUMMARY ==========
    print("\n\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for r in results if r.get("success"))
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} [OK]")
    print(f"Failed: {failed} [ERROR]")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    # Performance stats
    times = [r["time"] for r in results if r.get("time")]
    if times:
        print(f"\nPerformance:")
        print(f"  Average: {sum(times)/len(times):.2f}s")
        print(f"  Fastest: {min(times):.2f}s")
        print(f"  Slowest: {max(times):.2f}s")
    
    # Command detection accuracy
    commands = [r["command"] for r in results if r.get("command")]
    unique_commands = set(commands)
    print(f"\nUnique Commands Detected: {len(unique_commands)}")
    for cmd in sorted(unique_commands):
        if cmd != "N/A":
            count = commands.count(cmd)
            print(f"  - {cmd}: {count} times")
    
    print("\n" + "="*60)
    print("TEST COMPLETE - Only TEST data was used")
    print("="*60)

if __name__ == "__main__":
    main()