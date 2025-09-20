# QuickBooks Connector Commands Reference

## Usage Format
```bash
python qbc.py <COMMAND> param1=value1 param2=value2
```

For complex parameters (arrays/JSON), use single quotes:
```bash
python qbc.py UPDATE_WORK_BILL vendor_name=Adrian remove_days='["friday","saturday"]'
```

---

## WORK BILL COMMANDS

### GET_WORK_BILL
Get the current work bill for a vendor
- **Parameters:**
  - `vendor_name` (required) - Name of the vendor
- **Example:**
  ```bash
  python qbc.py GET_WORK_BILL vendor_name=Jaciel
  python qbc.py GET_WORK_BILL vendor_name="Adrian Rodriguez"
  ```

### CREATE_WORK_BILL
Create a new work bill for a vendor
- **Parameters:**
  - `vendor_name` (required) - Name of the vendor
  - `days_worked` (required) - Number of days worked
  - `daily_cost` (required) - Cost per day
  - `job_name` (optional) - Customer/job name
  - `item_name` (optional) - Item for the work
  - `memo` (optional) - Bill memo
- **Example:**
  ```bash
  python qbc.py CREATE_WORK_BILL vendor_name=Jaciel days_worked=5 daily_cost=250
  python qbc.py CREATE_WORK_BILL vendor_name=Adrian days_worked=3 daily_cost=130 job_name="42 Parsons" item_name="Install Cabinets"
  ```

### UPDATE_WORK_BILL
Update an existing work bill (add/remove days, change items/jobs)
- **Parameters:**
  - `vendor_name` (required) - Name of the vendor
  - `add_days` (optional) - JSON array of days to add with details
  - `remove_days` (optional) - JSON array of days to remove
  - `update_days` (optional) - JSON array of days to update
- **Example:**
  ```bash
  # Remove days
  python qbc.py UPDATE_WORK_BILL vendor_name=Jaciel remove_days='["friday","saturday"]'

  # Add days with details
  python qbc.py UPDATE_WORK_BILL vendor_name=Adrian add_days='[{"day":"wednesday","item":"Painting","job":"42 Parsons"}]'

  # Update existing days
  python qbc.py UPDATE_WORK_BILL vendor_name=Elmer update_days='[{"day":"thursday","item":"Install Cabinets","job":"Cottage 77"}]'
  ```

### DELETE_BILL
Delete a bill by ID or reference number
- **Parameters:**
  - `bill_id` (optional) - QuickBooks transaction ID
  - `ref_number` (optional) - Bill reference number
- **Example:**
  ```bash
  python qbc.py DELETE_BILL ref_number="ja_01/12-01/18/25"
  python qbc.py DELETE_BILL bill_id="12345-1234567890"
  ```

**SDK Implementation Note (CRITICAL):**
```python
# CORRECT - Must use SetAsString for TxnDelType
delete_req.TxnDelType.SetAsString("Bill")  # Works!
delete_req.TxnID.SetValue(txn_id)

# WRONG - SetValue with enum does NOT work for deletion
delete_req.TxnDelType.SetValue(0)  # Fails with "Invalid record number"
delete_req.TxnDelType.SetValue(2)  # Fails
```
Discovered August 31, 2025: QuickBooks SDK requires string values for TxnDelType, not enum integers.

### GET_WORK_WEEK_SUMMARY
Get summary of all work bills for current or specified week
- **Parameters:**
  - `week_offset` (optional) - Number of weeks back (0=current, -1=last week)
  - `start_date` (optional) - Specific start date (YYYY-MM-DD)
  - `end_date` (optional) - Specific end date (YYYY-MM-DD)
- **Example:**
  ```bash
  python qbc.py GET_WORK_WEEK_SUMMARY
  python qbc.py GET_WORK_WEEK_SUMMARY week_offset=-1
  python qbc.py GET_WORK_WEEK_SUMMARY start_date=2025-01-13 end_date=2025-01-19
  ```

---

## VENDOR COMMANDS

### SEARCH_VENDORS
Search for vendors by name or partial name
- **Parameters:**
  - `search_term` (required) - Search text
- **Example:**
  ```bash
  python qbc.py SEARCH_VENDORS search_term=home
  python qbc.py SEARCH_VENDORS search_term="precision interior"
  ```

### CREATE_VENDOR
Create a new vendor
- **Parameters:**
  - `name` (required) - Vendor name
  - `company_name` (optional) - Company name
  - `phone` (optional) - Phone number
  - `email` (optional) - Email address
  - `address` (optional) - Street address
  - `city` (optional) - City
  - `state` (optional) - State
  - `zip` (optional) - ZIP code
- **Example:**
  ```bash
  python qbc.py CREATE_VENDOR name="TEST-New Vendor" phone="555-1234"
  python qbc.py CREATE_VENDOR name="TEST-Supplier" company_name="Test Supply Co" email="test@example.com"
  ```

### UPDATE_VENDOR
Update vendor information
- **Parameters:**
  - `vendor_name` (required) - Current vendor name
  - `new_name` (optional) - New name
  - `phone` (optional) - New phone
  - `email` (optional) - New email
  - `address` (optional) - New address
- **Example:**
  ```bash
  python qbc.py UPDATE_VENDOR vendor_name="TEST-Vendor" phone="555-5678"
  python qbc.py UPDATE_VENDOR vendor_name="TEST-Old Name" new_name="TEST-New Name"
  ```

### SET_VENDOR_DAILY_COST
Set default daily cost for a vendor
- **Parameters:**
  - `vendor_name` (required) - Vendor name
  - `daily_cost` (required) - Daily cost amount
- **Example:**
  ```bash
  python qbc.py SET_VENDOR_DAILY_COST vendor_name=Jaciel daily_cost=250
  python qbc.py SET_VENDOR_DAILY_COST vendor_name=Adrian daily_cost=130
  ```

---

## PAYEE/OTHER NAME COMMANDS

### SEARCH_PAYEES
Search all payee types (vendors, customers, employees, other names)
- **Parameters:**
  - `search_term` (required) - Search text
- **Example:**
  ```bash
  python qbc.py SEARCH_PAYEES search_term=office
  python qbc.py SEARCH_PAYEES search_term="home depot"
  ```

### CREATE_OTHER_NAME
Create a new "Other Name" type payee (for misc payees like stores)
- **Parameters:**
  - `name` (required) - Payee name
  - `company_name` (optional) - Company name
  - `phone` (optional) - Phone number
- **Example:**
  ```bash
  python qbc.py CREATE_OTHER_NAME name="Office Depot"
  python qbc.py CREATE_OTHER_NAME name="Gas Station" company_name="Shell"
  ```

### SEARCH_OTHER_NAMES
Search only "Other Names" type payees
- **Parameters:**
  - `search_term` (required) - Search text
- **Example:**
  ```bash
  python qbc.py SEARCH_OTHER_NAMES search_term=office
  python qbc.py SEARCH_OTHER_NAMES search_term=depot
  ```

---

## CUSTOMER COMMANDS

### SEARCH_CUSTOMERS
Search for customers/jobs
- **Parameters:**
  - `search_term` (required) - Search text
- **Example:**
  ```bash
  python qbc.py SEARCH_CUSTOMERS search_term=parsons
  python qbc.py SEARCH_CUSTOMERS search_term="cottage 77"
  ```

### CREATE_CUSTOMER
Create a new customer
- **Parameters:**
  - `name` (required) - Customer name
  - `company_name` (optional) - Company name
  - `phone` (optional) - Phone number
  - `email` (optional) - Email address
  - `address` (optional) - Street address
  - `city` (optional) - City
  - `state` (optional) - State
  - `zip` (optional) - ZIP code
- **Example:**
  ```bash
  python qbc.py CREATE_CUSTOMER name="TEST-Customer" phone="555-1234"
  python qbc.py CREATE_CUSTOMER name="42 Parsons" address="42 Parsons Ave"
  ```

### UPDATE_CUSTOMER
Update customer information
- **Parameters:**
  - `customer_name` (required) - Current customer name
  - `new_name` (optional) - New name
  - `phone` (optional) - New phone
  - `email` (optional) - New email
  - `address` (optional) - New address
- **Example:**
  ```bash
  python qbc.py UPDATE_CUSTOMER customer_name="TEST-Customer" phone="555-5678"
  python qbc.py UPDATE_CUSTOMER customer_name="Old Job" new_name="New Job Name"
  ```

---

## CHECK COMMANDS

### CREATE_CHECK
Create a new check
- **Parameters:**
  - `payee_name` (required) - Who to pay
  - `amount` (required) - Check amount
  - `account_name` (optional) - Bank account to use
  - `check_number` (optional) - Check number (or "ATM", "Zelle", etc.)
  - `memo` (optional) - Check memo
  - `date` (optional) - Check date (YYYY-MM-DD)
- **Example:**
  ```bash
  python qbc.py CREATE_CHECK payee_name="TEST-Vendor" amount=500 check_number=1234
  python qbc.py CREATE_CHECK payee_name=Jaciel amount=650 check_number=ATM memo="Weekly payment"
  ```

### SEARCH_CHECKS
Search checks by various criteria
- **Parameters:**
  - `search_term` (optional) - Search in payee/memo
  - `check_number` (optional) - Specific check number
  - `start_date` (optional) - Date range start (YYYY-MM-DD)
  - `end_date` (optional) - Date range end (YYYY-MM-DD)
  - `payee_name` (optional) - Specific payee
- **Example:**
  ```bash
  python qbc.py SEARCH_CHECKS payee_name=Jaciel
  python qbc.py SEARCH_CHECKS check_number=1234
  python qbc.py SEARCH_CHECKS start_date=2025-01-01 end_date=2025-01-31
  ```

### GET_CHECK
Get details of a specific check
- **Parameters:**
  - `check_id` (optional) - QuickBooks transaction ID
  - `check_number` (optional) - Check number
- **Example:**
  ```bash
  python qbc.py GET_CHECK check_number=1234
  python qbc.py GET_CHECK check_id="12345-1234567890"
  ```

### GET_CHECKS_THIS_WEEK
Get all checks from current week
- **Parameters:** None
- **Example:**
  ```bash
  python qbc.py GET_CHECKS_THIS_WEEK
  ```

### UPDATE_CHECK
Update check information
- **Parameters:**
  - `check_id` (required) - QuickBooks transaction ID
  - `amount` (optional) - New amount
  - `memo` (optional) - New memo
  - `date` (optional) - New date
- **Example:**
  ```bash
  python qbc.py UPDATE_CHECK check_id="12345-1234567890" memo="Updated memo"
  python qbc.py UPDATE_CHECK check_id="12345-1234567890" amount=750
  ```

### DELETE_CHECK
Delete a check
- **Parameters:**
  - `check_id` (optional) - QuickBooks transaction ID
  - `check_number` (optional) - Check number
- **Example:**
  ```bash
  python qbc.py DELETE_CHECK check_number=1234
  python qbc.py DELETE_CHECK check_id="12345-1234567890"
  ```

---

## INVOICE COMMANDS

### SEARCH_INVOICES
Search invoices by various criteria
- **Parameters:**
  - `search_term` (optional) - Search in customer/memo
  - `customer_name` (optional) - Specific customer (finds ALL invoices for this customer across all jobs)
  - `ref_number` (optional) - Specific invoice number
  - `date_from` (optional) - Date range start YYYY-MM-DD (defaults to current quarter start)
  - `date_to` (optional) - Date range end YYYY-MM-DD (defaults to current quarter end)
  - `paid_status` (optional) - Filter by payment status: "paid", "unpaid", or "all" (default: "all")
  - `amount` (optional) - Exact amount match
  - `amount_min` (optional) - Minimum amount
  - `amount_max` (optional) - Maximum amount
- **Example:**
  ```bash
  # Search all invoices in current quarter
  python qbc.py SEARCH_INVOICES

  # Search unpaid invoices in current quarter
  python qbc.py SEARCH_INVOICES paid_status=unpaid

  # Search by customer
  python qbc.py SEARCH_INVOICES customer_name="raised panel door"

  # Search by invoice number
  python qbc.py SEARCH_INVOICES ref_number=285639

  # Search with custom date range
  python qbc.py SEARCH_INVOICES date_from=2025-01-01 date_to=2025-03-31

  # Complex search
  python qbc.py SEARCH_INVOICES amount_min=500 amount_max=1000 paid_status=unpaid
  ```
- **Note:** Automatically defaults to current quarter (Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec) if no dates specified

**Note:** When searching by customer_name, this returns ALL invoices for that customer across all their jobs. To see only open (unpaid) invoices, add `paid_status=unpaid`.

### GET_INVOICE
Get details of a specific invoice
- **Parameters:**
  - `invoice_id` (required) - QuickBooks transaction ID or invoice number
- **Example:**
  ```bash
  python qbc.py GET_INVOICE invoice_id=285639
  python qbc.py GET_INVOICE invoice_id="12345-1234567890"
  ```

### GET_INVOICES_THIS_WEEK
Get all invoices from current week
- **Parameters:** None
- **Example:**
  ```bash
  python qbc.py GET_INVOICES_THIS_WEEK
  ```

### CREATE_INVOICE
Create a new invoice
- **Parameters:**
  - `customer_name` (required) - Customer name
  - `items` (required) - JSON array of line items
  - `invoice_date` (optional) - Invoice date (YYYY-MM-DD)
  - `due_date` (optional) - Due date
  - `memo` (optional) - Invoice memo
- **Example:**
  ```bash
  python qbc.py CREATE_INVOICE customer_name="TEST-Customer" items='[{"item":"Consulting","quantity":1,"rate":100}]'
  python qbc.py CREATE_INVOICE customer_name="42 Parsons" items='[{"item":"Labor","quantity":8,"rate":50}]' memo="Installation work"
  ```

---

## BILL PAYMENT COMMANDS

### PAY_BILLS
Pay vendor bills (automatically applies vendor payment settings)
- **Parameters:**
  - `vendor_name` (required) - Vendor name
  - `amount` (required) - Payment amount
  - `payment_date` (optional) - Date of payment (YYYY-MM-DD)
  - `ref_number` (optional) - Specific bill reference to pay
  - `check_number` (optional) - Check/payment number (overrides default)
  - `account_name` (optional) - Bank account to use
  - `memo` (optional) - Payment memo
- **Example:**
  ```bash
  python qbc.py PAY_BILLS vendor_name=Jaciel amount=750
  python qbc.py PAY_BILLS vendor_name=Adrian amount=650 payment_date=2025-01-15
  python qbc.py PAY_BILLS vendor_name=Elmer amount=520 check_number=Zelle account_name=8631
  ```

### CREATE_BILL_PAYMENT
Create a payment for a specific bill
- **Parameters:**
  - `vendor_name` (required) - Vendor name
  - `bill_id` (required) - Bill transaction ID
  - `amount` (required) - Payment amount
  - `payment_date` (optional) - Payment date
  - `check_number` (optional) - Check number
  - `memo` (optional) - Payment memo
- **Example:**
  ```bash
  python qbc.py CREATE_BILL_PAYMENT vendor_name="TEST-Vendor" bill_id="12345-1234567890" amount=500
  ```

### SEARCH_BILL_PAYMENTS
Search for bill payments
- **Parameters:**
  - `vendor_name` (optional) - Vendor name
  - `start_date` (optional) - Date range start
  - `end_date` (optional) - Date range end
- **Example:**
  ```bash
  python qbc.py SEARCH_BILL_PAYMENTS vendor_name=Jaciel
  python qbc.py SEARCH_BILL_PAYMENTS start_date=2025-01-01 end_date=2025-01-31
  ```

### DELETE_BILL_PAYMENT
Delete a bill payment
- **Parameters:**
  - `payment_id` (required) - Payment transaction ID
- **Example:**
  ```bash
  python qbc.py DELETE_BILL_PAYMENT payment_id="12345-1234567890"
  ```

**SDK Implementation Note (CRITICAL):**
```python
# CORRECT - Must use SetAsString for TxnDelType
delete_req.TxnDelType.SetAsString("BillPaymentCheck")  # Works!
delete_req.TxnID.SetValue(txn_id)

# WRONG - SetValue with enum does NOT work for deletion
delete_req.TxnDelType.SetValue(13)  # Fails with "Invalid record number"
```
QuickBooks SDK requires string values for TxnDelType in deletion requests. This applies to all transaction deletions.

### UPDATE_BILL_PAYMENT
Update bill payment information
- **Parameters:**
  - `payment_id` (required) - Payment transaction ID
  - `amount` (optional) - New amount
  - `date` (optional) - New date
  - `memo` (optional) - New memo
- **Example:**
  ```bash
  python qbc.py UPDATE_BILL_PAYMENT payment_id="12345-1234567890" memo="Corrected payment"
  ```

---

## ITEM COMMANDS

### SEARCH_ITEMS
Search for items/services
- **Parameters:**
  - `search_term` (required) - Search text
- **Example:**
  ```bash
  python qbc.py SEARCH_ITEMS search_term=cabinet
  python qbc.py SEARCH_ITEMS search_term=paint
  python qbc.py SEARCH_ITEMS search_term=install
  ```

### CREATE_ITEM
Create a new item
- **Parameters:**
  - `name` (required) - Item name
  - `type` (required) - Item type (Service, Non-Inventory, etc.)
  - `description` (optional) - Item description
  - `price` (optional) - Sales price
  - `cost` (optional) - Purchase cost
  - `account` (optional) - Income account
- **Example:**
  ```bash
  python qbc.py CREATE_ITEM name="TEST-Item" type=Service price=100
  python qbc.py CREATE_ITEM name="Cabinet Install" type=Service description="Install kitchen cabinets" price=500
  ```

### UPDATE_ITEM
Update item information
- **Parameters:**
  - `item_name` (required) - Current item name
  - `new_name` (optional) - New name
  - `description` (optional) - New description
  - `price` (optional) - New price
  - `cost` (optional) - New cost
- **Example:**
  ```bash
  python qbc.py UPDATE_ITEM item_name="TEST-Item" price=150
  python qbc.py UPDATE_ITEM item_name="Old Item" new_name="New Item Name"
  ```

---

## ACCOUNT COMMANDS

### SEARCH_ACCOUNTS
Search for accounts
- **Parameters:**
  - `search_term` (required) - Search text
  - `account_type` (optional) - Filter by type (Bank, CreditCard, etc.)
- **Example:**
  ```bash
  python qbc.py SEARCH_ACCOUNTS search_term=checking
  python qbc.py SEARCH_ACCOUNTS search_term=8631
  python qbc.py SEARCH_ACCOUNTS search_term=credit account_type=CreditCard
  ```

### CREATE_ACCOUNT
Create a new account
- **Parameters:**
  - `name` (required) - Account name
  - `account_type` (required) - Type (Bank, CreditCard, Income, Expense, etc.)
  - `account_number` (optional) - Account number
  - `description` (optional) - Account description
  - `opening_balance` (optional) - Opening balance
- **Example:**
  ```bash
  python qbc.py CREATE_ACCOUNT name="TEST-Bank Account" account_type=Bank
  python qbc.py CREATE_ACCOUNT name="TEST-Credit Card" account_type=CreditCard account_number=1234
  ```

### UPDATE_ACCOUNT
Update account information
- **Parameters:**
  - `account_name` (required) - Current account name
  - `new_name` (optional) - New name
  - `account_number` (optional) - New account number
  - `description` (optional) - New description
- **Example:**
  ```bash
  python qbc.py UPDATE_ACCOUNT account_name="TEST-Account" description="Updated description"
  python qbc.py UPDATE_ACCOUNT account_name="Old Account" new_name="New Account Name"
  ```

---

## CUSTOMER PAYMENT COMMANDS

### RECEIVE_PAYMENT
Receive payment for an invoice (creates a ReceivePayment transaction in QuickBooks)
- **Parameters:**
  - `invoice_id` (required) - Invoice number or transaction ID
  - `amount` (required) - Payment amount
  - `payment_method` (optional) - Payment method (Check, Cash, Credit Card, etc.) - default: "Check"
  - `check_number` (optional) - Check number or reference
  - `deposit_to_account` (optional) - Bank account name/number to deposit to (e.g., "8824") - if not specified, goes to Undeposited Funds
  - `payment_date` (optional) - Date of payment (YYYY-MM-DD) - default: today
  - `memo` (optional) - Payment memo
- **Example:**
  ```bash
  # Basic payment to Undeposited Funds
  python qbc.py RECEIVE_PAYMENT invoice_id=532159 amount=2000

  # Payment with direct deposit to bank account (PREFERRED)
  python qbc.py RECEIVE_PAYMENT invoice_id=532159 amount=2000 deposit_to_account=8824

  # Payment with all details
  python qbc.py RECEIVE_PAYMENT invoice_id=532159 amount=2000 payment_method="Check" check_number=1234 deposit_to_account=8824 payment_date=2025-09-19
  ```

**IMPORTANT:** When `deposit_to_account` is not specified, ASK the user which bank account to deposit to. Direct deposit is preferred over Undeposited Funds as it eliminates the need for a separate deposit step.

### DELETE_CUSTOMER_PAYMENT
Delete a customer payment (ReceivePayment) from QuickBooks
- **Parameters:**
  - `payment_id` (required) - Transaction ID of the payment to delete
- **Example:**
  ```bash
  python qbc.py DELETE_CUSTOMER_PAYMENT payment_id=51CC7-1758372968
  ```
- **Note:** Payment must not be deposited or locked. If payment is applied to an invoice, it will automatically be unapplied before deletion.

**SDK Implementation Note (CRITICAL):**
```python
# CORRECT - Must use SetAsString for TxnDelType
delete_req.TxnDelType.SetAsString("ReceivePayment")  # Works!
delete_req.TxnID.SetValue(txn_id)

# WRONG - SetValue with enum does NOT work for deletion
delete_req.TxnDelType.SetValue(7)  # Fails with "Invalid record number"
delete_req.TxnDelType.SetValue(18)  # Fails
delete_req.TxnDelType.SetValue(20)  # Fails with "Feature not enabled"
```
This was discovered through extensive testing. QuickBooks SDK requires string values for TxnDelType, not enum integers.

### SEARCH_CUSTOMER_PAYMENTS
Search for customer payments by various criteria
- **Parameters:**
  - `customer_name` (optional) - Search payments for specific customer
  - `date_from` (optional) - Start date MM-DD-YYYY (defaults to current quarter start)
  - `date_to` (optional) - End date MM-DD-YYYY (defaults to current quarter end)
- **Example:**
  ```bash
  # Search all payments in current quarter
  python qbc.py SEARCH_CUSTOMER_PAYMENTS

  # Search all payments for a customer (uses current quarter by default)
  python qbc.py SEARCH_CUSTOMER_PAYMENTS customer_name="Merrily Thompson"

  # Search payments with custom date range
  python qbc.py SEARCH_CUSTOMER_PAYMENTS date_from=09-01-2025 date_to=09-30-2025

  # Search specific customer in date range
  python qbc.py SEARCH_CUSTOMER_PAYMENTS customer_name="raised panel door:3408" date_from=09-20-2025
  ```
- **Note:** Automatically defaults to current quarter (Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec) if no dates specified

---

## DEPOSIT COMMANDS

### SEARCH_DEPOSITS
Search for deposits
- **Parameters:**
  - `search_term` (optional) - Search text
  - `start_date` (optional) - Date range start
  - `end_date` (optional) - Date range end
  - `account_name` (optional) - Bank account
- **Example:**
  ```bash
  python qbc.py SEARCH_DEPOSITS account_name=8631
  python qbc.py SEARCH_DEPOSITS start_date=2025-01-01 end_date=2025-01-31
  ```

### DEPOSIT_CUSTOMER_PAYMENT
Deposit customer payments to bank
- **Parameters:**
  - `payment_ids` (required) - JSON array of payment transaction IDs
  - `account_name` (required) - Bank account name
  - `deposit_date` (optional) - Deposit date
  - `memo` (optional) - Deposit memo
- **Example:**
  ```bash
  python qbc.py DEPOSIT_CUSTOMER_PAYMENT payment_ids='["12345-1234567890"]' account_name=8631
  python qbc.py DEPOSIT_CUSTOMER_PAYMENT payment_ids='["id1","id2"]' account_name="Operating Account" memo="Daily deposit"
  ```

---

## TRANSACTION SEARCH COMMANDS

### SEARCH_TRANSACTION_BY_AMOUNT
Search ALL transaction types by amount (bills, checks, invoices, deposits, etc.)
- **Parameters:**
  - `amount` (required) - Transaction amount
  - `date_from` (optional) - Start date MM-DD-YYYY (defaults to current quarter start)
  - `date_to` (optional) - End date MM-DD-YYYY (defaults to current quarter end)
  - `tolerance` (optional) - Amount tolerance (default 0.01)
- **Example:**
  ```bash
  # Search with default current quarter date range
  python qbc.py SEARCH_TRANSACTION_BY_AMOUNT amount=125.43

  # Search with custom date range
  python qbc.py SEARCH_TRANSACTION_BY_AMOUNT amount=2000 date_from=01-01-2025 date_to=03-31-2025

  # Search with tolerance
  python qbc.py SEARCH_TRANSACTION_BY_AMOUNT amount=500 tolerance=10
  ```
- **Note:** Automatically defaults to current quarter (Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec) if no dates specified

---

## SPECIAL NOTES

### Vendor Payment Settings
The system automatically applies these payment methods:
- **Jaciel** → Check number: "ATM"
- **Adrian, Elmer, Selvin, Bryan** → Check number: "Zelle"

### Work Bill Day Format
When adding/updating days in work bills:
- Days should be lowercase: "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
- Each day can have different item and job assignments

### Date Formats
All dates use YYYY-MM-DD format:
- `2025-01-15` (correct)
- `01/15/2025` (incorrect)

### Testing
Always prefix test data with "TEST-":
- Vendors: `TEST-Vendor Name`
- Customers: `TEST-Customer Name`
- Items: `TEST-Item Name`

### Account References
Bank accounts can be referenced by:
- Last 4 digits: `8631`, `3841`
- Full name: `Operating Account`
- Partial name that uniquely identifies it

---

## COMMON WORKFLOWS

### Finding Open Invoices for a Customer
When you want to see open invoices for any customer:
```bash
# 1. First find the exact customer name
python qbc.py SEARCH_CUSTOMERS search_term="[customer name or partial name]"

# 2. Then search for their invoices (shows ALL invoices across all jobs)
python qbc.py SEARCH_INVOICES customer_name="[exact customer name from search]"

# 3. Or search for ONLY open/unpaid invoices
python qbc.py SEARCH_INVOICES customer_name="[exact customer name]" paid_status=unpaid
```

**Examples with different customers:**
```bash
# For "raised panel" customer:
python qbc.py SEARCH_CUSTOMERS search_term="raised panel"
python qbc.py SEARCH_INVOICES customer_name="raised panel door" paid_status=unpaid

# For "cottage" customer:
python qbc.py SEARCH_CUSTOMERS search_term="cottage"
python qbc.py SEARCH_INVOICES customer_name="cottage 77" paid_status=unpaid

# For "parsons" customer:
python qbc.py SEARCH_CUSTOMERS search_term="parsons"
python qbc.py SEARCH_INVOICES customer_name="42 Parsons" paid_status=unpaid
```

**Important:** This searches ALL jobs/invoices under that customer, not just one specific job.

### Daily Worker Payment Workflow
```bash
# 1. Check current bill
python qbc.py GET_WORK_BILL vendor_name=Jaciel

# 2. Update if needed
python qbc.py UPDATE_WORK_BILL vendor_name=Jaciel add_days='[{"day":"friday","item":"Painting","job":"42 Parsons"}]'

# 3. Pay the bill
python qbc.py PAY_BILLS vendor_name=Jaciel amount=750 payment_date=2025-01-15

# 4. Check week summary
python qbc.py GET_WORK_WEEK_SUMMARY
```

### Vendor Bill Processing
```bash
# 1. Check for duplicates first
python qbc.py SEARCH_TRANSACTION_BY_AMOUNT amount=125.43

# 2. Search for vendor
python qbc.py SEARCH_VENDORS search_term="home depot"

# 3. Create check or bill payment
python qbc.py CREATE_CHECK payee_name="Home Depot" amount=125.43 check_number=1234 memo="PIP Receipt 203537"
```

### Weekly Summary Review
```bash
# Current week
python qbc.py GET_WORK_WEEK_SUMMARY

# Last week
python qbc.py GET_WORK_WEEK_SUMMARY week_offset=-1

# Specific date range
python qbc.py GET_WORK_WEEK_SUMMARY start_date=2025-01-13 end_date=2025-01-19
```