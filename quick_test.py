#!/usr/bin/env python
"""Quick test of all major QB commands via Claude API"""
import requests
import json
import time

API = "http://localhost:8000/api/chat"

def test(msg):
    """Test a natural language command"""
    print(f"\nTest: {msg}")
    try:
        r = requests.post(API, json={"message": msg}, timeout=10)
        d = r.json()
        cmd = d.get('command', 'NONE')
        success = "OK" if d.get('success') else "FAIL"
        output = d.get('response', '')[:150]
        print(f"  [{success}] Command: {cmd}")
        print(f"  Output: {output}...")
        return d.get('success', False)
    except Exception as e:
        print(f"  [ERROR] {str(e)[:50]}")
        return False

print("="*60)
print("QUICK QB COMMAND TEST - Via Claude API")
print("="*60)

tests = [
    # VENDOR Commands
    "list all vendors",
    "find vendor TEST",
    "show TEST_VENDOR details",
    
    # BILL Commands
    "show TEST_VENDOR bill",
    "get week summary",
    
    # CUSTOMER Commands
    "list customers",
    "search jobs",
    
    # CHECK Commands
    "show this week's checks",
    "search all checks",
    
    # INVOICE Commands
    "show invoices",
    "this week's invoices",
    
    # PAYMENT Commands
    "search bill payments",
    
    # ITEM Commands
    "list all items",
    "show services",
    
    # ACCOUNT Commands
    "list accounts",
    "show bank accounts",
    
    # DEPOSIT Commands
    "search deposits",
]

passed = 0
failed = 0

for msg in tests:
    if test(msg):
        passed += 1
    else:
        failed += 1
    time.sleep(0.5)  # Small delay

print("\n" + "="*60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("="*60)