# QuickBooks Item Receipts and Job Costing Investigation

## Current Issue
Item Receipts with proper CustomerRef (job assignment) are being created successfully but NOT showing in Job Profitability reports' COGS. The job materials cost shows $481.94 (checks only) instead of expected $931.94 (including $450 from receipts).

## Root Cause Discovered
1. **JobReport SDK Limitation**: Always runs on Cash basis regardless of company preferences
2. **Cash vs Accrual Mismatch**:
   - Company preferences set to Accrual (AgingReportBasis=0, SummaryReportBasis=0)
   - JobReport ignores this and uses Cash basis (ReportBasis=0 in its context)
   - ReportBasis cannot be set via SDK on JobReportQueryRq
3. **Item Receipts in Cash Basis**: Not considered "paid" transactions, so excluded from COGS until converted to bills and paid

## What Was Fixed
### 1. RECEIVE_PURCHASE_ORDER Command (COMPLETED)
**File**: `src\qb\quickbooks_standard\entities\purchase_orders\purchase_order_repository.py`
- Switched from XML to QBFC connection for reliability
- Fixed CustomerRef preservation for job costing (lines 619-632)
- Key insight: When using LinkToTxn, do NOT set ItemRef - it's pulled automatically
- Successfully tested: PO #269070 shows 75 received (50 + 25 new) of 200 ordered

### 2. GET_JOB_PROFIT Command (COMPLETED)
**File**: `src\qb\connector.py` (lines 952-977)
- Added fuzzy matching for job names
- Removed invalid include_line_items parameter

## What Still Needs to Be Done

### 1. Fix Vendor Breakdown to Include Item Receipts
**File**: `src\qb\connector.py` (lines 1039-1116)
**Current**: Only queries Bills and Checks
**Needed**: Add ItemReceiptQuery to include unpaid receipts
```python
# Add after existing bill/check queries:
receipt_query = request_set.AppendItemReceiptQueryRq()
receipt_query.ORTxnQuery.TxnFilter.EntityFilter.OREntityFilter.FullNameList.Add(vendor_name)
receipt_query.ORTxnQuery.TxnFilter.ORDateRangeFilter.TxnDateRangeFilter.ORTxnDateRangeFilter.DateMacro.SetValue(14)
receipt_query.IncludeLineItems.SetValue(True)
```

### 2. Fix ItemReceiptRepository Parser
**File**: `src\qb\quickbooks_standard\entities\item_receipts\item_receipt_repository.py`
**Current**: Doesn't parse CustomerRef from line items
**Needed**: Add CustomerRef parsing in _parse_item_receipt_line method

### 3. Add Cash/Accrual Indicator to Reports
**File**: `src\qb\connector.py`
**Add**: Note in GET_JOB_PROFIT output showing report basis
```python
summary_lines.append("[NOTE] Report runs on Cash basis - unpaid receipts not included in COGS")
```

### 4. Create Bill Conversion Command (Optional)
**New Command**: CONVERT_RECEIPT_TO_BILL
- Find Item Receipt by vendor/PO
- Create corresponding Bill
- Preserve all CustomerRef assignments
- Allow immediate payment if desired

## Test Data Created
- Vendor: TEST_VENDOR_RECEIPT
- PO #269070: 200 units total, 75 received (50 + 25 in testing)
- Item Receipts: $450 total (not showing in COGS)
- Job: jeck:Jeff trailer
- Expected COGS: $931.94 (actual shows $481.94)

## Key Technical Findings

### Value Mapping Confusion
- **Company Preferences**: 0=Accrual, 1=Cash
- **JobReport Response**: 0=Cash, 1=Accrual (opposite!)
- **SDK Limitation**: Cannot override report basis programmatically

### Item Receipt Behavior
- ARE posting transactions (increase inventory asset and A/P)
- DO preserve CustomerRef when properly set
- DON'T appear in Cash basis COGS until paid
- MUST be converted to bills then paid to show in reports

### QBFC vs XML Connection
- XML had parsing errors with complex receipt creation
- QBFC more reliable for Item Receipt operations
- Both connections available in purchase_order_repository.py

## Testing Commands
```bash
# Test receipt creation with job assignment
python qbc.py RECEIVE_PURCHASE_ORDER po_number=269070 vendor_name=TEST_VENDOR_RECEIPT item_name="job materials" quantity=25

# Check job profitability (shows checks only)
python qbc.py GET_JOB_PROFIT job_name="jeck:Jeff trailer"

# Test report basis settings
python test_report_basis.py

# Check company preferences
python test_all_preferences.py
```

## Next Session Instructions
1. Start by reviewing this document
2. Check if receipts still don't show in job profitability
3. Implement vendor breakdown fix to include ItemReceiptQuery
4. Add cash/accrual indicator to report output
5. Consider implementing CONVERT_RECEIPT_TO_BILL command if needed
6. Clean up TEST_VENDOR_RECEIPT data when done testing