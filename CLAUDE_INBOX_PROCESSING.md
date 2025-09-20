# Claude Inbox Processing - Step-by-Step Procedure

## Trigger Command
When user says: "process inbox" or "process new documents"

## CLAUDE'S EXACT PROCESSING STEPS

### STEP 1: List Inbox Documents
```bash
ls "//vmware-host/Shared Folders/D/OneDrive/Inbox"
```
- Show user what documents are found
- Group by potential transaction (invoices + payment receipts)

### STEP 2: Read ALL Documents First
- Use Read tool on each image/PDF
- Extract ALL data in one pass per document:
  - Vendor name/logo
  - Date
  - Total amount
  - ALL line items with descriptions
  - Payment method details
  - Check numbers
  - Reference numbers

### STEP 3: Pair Related Documents
Match documents that belong together:
- Invoice/receipt + payment document
- Same vendor name
- Same/similar amount
- Payment date on/after invoice date
- Show user the proposed pairings

### STEP 4: DUPLICATE CHECK (CRITICAL - DO FIRST)
For each transaction:

1. Check processed folder:
```bash
ls "upload/processed_transactions/[vendor]/"
```
Look for files with same amount/date

2. Search QuickBooks:
```bash
python qbc.py SEARCH_TRANSACTION_BY_AMOUNT amount=[amount]
```

3. If duplicate found:
- Show user the existing transaction
- Ask: "Possible duplicate found. Continue anyway? (y/n)"
- STOP if user says no

### STEP 5: Vendor Identification & Matching
1. First check vendor-specific rules:
   - Read `upload/processing_instructions/vendors/[VENDOR].txt` if exists
2. Search QuickBooks for vendor:
```bash
python qbc.py SEARCH_VENDORS search_term=[vendor]
```
3. If no match, ask user:
   - "Is this vendor [closest match] or new vendor?"

### STEP 6: Extract & Display Line Items
Show user what was found:
```
Line Items from receipt:
1. 2x4x8 Stud Lumber - Qty: 10 - $4.28 each
2. Deck Screws 3" - Qty: 2 boxes - $12.99 each
3. Liquid Nails - Qty: 3 - $5.49 each
```

### STEP 7: REQUIRED Information (ASK USER)
MUST ask for these (NO DEFAULTS):

1. **Job/Customer**:
   - "What job/customer is this for?"
   - Use `SEARCH_CUSTOMERS` to verify

2. **QuickBooks Items**:
   - "What QB item(s) should be used?"
   - "Should I use 'Lumber' for the wood products?"
   - Use `SEARCH_ITEMS` to verify

3. **Payment Details** (if not found):
   - "How was this paid?"
   - "Which bank account?"

### STEP 8: Stage Transaction Summary
Display COMPLETE details:
```
=========================
READY TO POST:
Type: CHECK
Vendor: Home Depot
Date: 2025-01-15
Amount: $125.43
Bank: Operating Account
Check #: Debit6664
Job/Customer: 123 Main St
QB Item: Lumber
Line Items: [2x4 studs, deck screws, liquid nails]
Memo: HD Receipt #203537 - Building materials
=========================
Post to QuickBooks? (y/n):
```

### STEP 9: Post to QuickBooks
ONLY after user approves:

For amounts < $100:
```bash
python qbc.py CREATE_CHECK vendor_name="[vendor]" customer_name="[job]" amount=[amount] ...
```

For amounts $100-500:
```bash
python qbc.py CREATE_BILL vendor_name="[vendor]" customer_name="[job]" amount=[amount] ...
```

### STEP 10: Save Metadata
Create searchable item database:
```bash
# Save to: upload/processed_transactions/[vendor]/01-15-2025_HD_receipt_203537_125.43_items.json
```

Include:
- Complete line item details
- SKUs, quantities, prices
- For future "what did I pay for lumber" searches

### STEP 11: Move Processed Files
After successful posting:
```bash
mv "//vmware-host/Shared Folders/D/OneDrive/Inbox/[file]" "upload/processed_transactions/[vendor]/[timestamp]_[file]"
```

### STEP 12: Handle Errors
If posting fails:
- Show exact error
- Ask user: "How would you like to proceed?"
- Do NOT try alternatives automatically

## SPECIAL RULES BY VENDOR

### Home Depot / Lowe's
- Always extract complete line items
- Pro desk purchases may have special handling
- Look for Pro rewards number

### Office Depot
- Create as "Other Name" not Vendor
- Printer ink → use specific ink items
- Usually overhead, no job required

### Overhead Vendors (Brannen's Inc, etc.)
- No job/customer required
- Mark as overhead expense

## REMEMBER
1. DUPLICATE CHECK FIRST - Always
2. NO DEFAULTS - Ask user for job/customer/items
3. ALWAYS USE ITEMS - Never expense accounts
4. EXTRACT ALL LINE ITEMS - Store in description and JSON
5. REQUIRE APPROVAL - Never auto-post
6. PAIR DOCUMENTS - Match invoices with payments