#!/usr/bin/env python
"""
Calculate job profitability for Jeff's trailer
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qb.connector import QBConnector

def calculate_job_profit():
    """Calculate profit for Jeff's trailer job"""
    qb = QBConnector()
    
    if not qb.connected:
        print("[ERROR] QuickBooks not connected")
        return
    
    print("\n=== JOB PROFITABILITY: Jeff's Trailer ===\n")
    
    # Get all vendor bills to find costs for this job
    vendors = ["Adrian", "Jaciel", "Luis", "Chelo", "Selvin"]
    total_costs = 0
    job_name = "jeck:Jeff trailer"
    
    print("COSTS (from vendor bills):")
    print("-" * 40)
    
    for vendor in vendors:
        try:
            result = qb.execute_command("GET_WORK_BILL", {"vendor_name": vendor})
            if result['success']:
                output = result['output']
                # Look for Jeff trailer costs in the output
                if job_name in output or "Jeff trailer" in output:
                    # Extract the job cost from the job summary section
                    lines = output.split('\n')
                    for i, line in enumerate(lines):
                        if 'Jeff trailer' in line and '$' in line:
                            # Get the amount
                            amount_str = line.split('$')[-1].strip()
                            try:
                                amount = float(amount_str.replace(',', ''))
                                if amount > 0:
                                    print(f"  {vendor}: ${amount:.2f}")
                                    total_costs += amount
                                    break
                            except:
                                pass
        except Exception as e:
            pass
    
    print("-" * 40)
    print(f"TOTAL COSTS: ${total_costs:.2f}")
    
    # Get invoice for Jeff to find revenue
    print("\nREVENUE (from customer invoice):")
    print("-" * 40)
    
    # Search for Jeff's invoices
    invoices = qb.invoice_repo.search_invoices()
    jeff_revenue = 0
    
    for invoice in invoices:
        customer = invoice.get('customer', '')
        if 'Jeff' in customer or 'jeff' in customer:
            # Check if this invoice is for the trailer job
            memo = invoice.get('memo', '')
            items = invoice.get('line_items', [])
            
            # Look through line items for trailer-related work
            for item in items:
                desc = item.get('description', '')
                if 'trailer' in desc.lower() or 'cabinet' in desc.lower() or 'door' in desc.lower():
                    amount = item.get('amount', 0)
                    jeff_revenue += amount
    
    if jeff_revenue == 0:
        # If no invoice found, estimate based on typical markup
        print("  [No invoice found - estimating based on typical 50% markup]")
        jeff_revenue = total_costs * 1.5
        print(f"  Estimated Revenue: ${jeff_revenue:.2f}")
    else:
        print(f"  Invoice Total: ${jeff_revenue:.2f}")
    
    print("-" * 40)
    print(f"TOTAL REVENUE: ${jeff_revenue:.2f}")
    
    # Calculate profit
    print("\n" + "=" * 40)
    profit = jeff_revenue - total_costs
    margin = (profit / jeff_revenue * 100) if jeff_revenue > 0 else 0
    
    print(f"GROSS PROFIT: ${profit:.2f}")
    print(f"PROFIT MARGIN: {margin:.1f}%")
    print("=" * 40)

if __name__ == "__main__":
    calculate_job_profit()