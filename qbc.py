#!/usr/bin/env python
"""
Direct QBConnector CLI - Fast QB command execution
Usage: python qb.py <command> [params as key=value]
Example: python qb.py GET_WORK_BILL vendor_name=Adrian
"""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qb.connector import QBConnector

def main():
    if len(sys.argv) < 2:
        print("Usage: python qb.py <command> [param1=value1 param2=value2 ...]")
        print("Example: python qb.py GET_WORK_BILL vendor_name=Adrian")
        print("\nFor list of commands: python list_commands.py")
        return
    
    command = sys.argv[1].upper()
    
    # Parse parameters
    params = {}
    for arg in sys.argv[2:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            # Try to parse as JSON for complex values
            try:
                params[key] = json.loads(value)
            except:
                params[key] = value
    
    # Execute command
    qb = QBConnector()
    
    if not qb.connected:
        print("[ERROR] QuickBooks not connected")
        return
    
    result = qb.execute_command(command, params)
    
    if result['success']:
        print(result['output'])
    else:
        print(f"[ERROR] {result.get('error', 'Command failed')}")

if __name__ == "__main__":
    main()