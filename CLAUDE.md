# AnyQB Project - Claude Instructions

## Project Overview
AnyQB is a mobile-first web application that provides a natural language interface to QuickBooks using Claude API. It's built on the proven architecture from the "claude chat" project but with enhanced structure for production use.

## Critical Rules
1. **Mobile First Development**: ALL development must be mobile-first
2. **ASCII Only**: Use ASCII characters only - no Unicode symbols
3. **Fast Response**: Target < 1 second response time
4. **QB Commands Only**: Claude API is restricted to executing QB commands

## Architecture Flow
```
User Input → Mobile UI → FastAPI → Claude API → QBConnector → QuickBooks → Response
```

## Layered Architecture
The project follows a clean layered architecture pattern:

1. **Commands Layer** (connector.py)
   - Entry point for all QB operations
   - Routes commands to appropriate services
   - Handles parameter validation and vendor resolution

2. **Service Layer** (custom_systems/*/service.py)
   - Business logic and workflow orchestration
   - Coordinates between repositories and formatters
   - Manages complex operations (e.g., work week calculations)

3. **Repository Layer** (quickbooks_standard/entities/*/repository.py)
   - Direct QuickBooks SDK interactions via QBFC
   - Data access and CRUD operations
   - Returns raw data from QuickBooks

4. **Formatter Layer** (shared_utilities/*_formatter.py)
   - ALL output formatting happens here
   - Consistent display across commands
   - Text formatting for CLI display

**IMPORTANT**: The formatter layer is responsible for ALL formatting. Services should pass data to formatters, not format directly.

## Quick Commands
- `*` - Check comments.txt in the AnyQB project folder (C:\Users\nando\Projects\anyqb\comments.txt)
- "show checks" or "sho checks" - Run GET_CHECKS_THIS_WEEK (not SEARCH_CHECKS)

## File Organization
- `src/api/` - FastAPI server and Claude integration
- `src/ui/` - Mobile web interface
- `src/qb/` - QuickBooks connection logic
  - `connector.py` - Command router (Commands Layer)
  - `custom_systems/` - Business logic (Service Layer)
  - `quickbooks_standard/` - QB SDK operations (Repository Layer)
  - `shared_utilities/` - Formatters and utilities
- `src/utils/` - Shared utilities
- `src/config/` - Configuration files

## Development Workflow
1. Always test on mobile viewport (390x844)
2. Keep Claude API responses under 200 tokens
3. Log all QB command executions
4. Handle errors gracefully with user-friendly messages

## QB Integration
- **USE QBConnector directly** via `python qbc.py` command
- **Simple command format**: `python qbc.py <COMMAND> param1=value1 param2=value2`
- **Example**: `python qbc.py GET_WORK_BILL vendor_name=Adrian`
- **For complex params**: Use JSON format like `remove_days='["friday"]'`
- All commands are in src/qb/connector.py lines 71-122

### Archived MCP Reference
- **MCP/anyQBMCP projects are ARCHIVED** - Do not use for active development
- **ARCHIVED LOCATION**: `C:\Users\nando\Projects\archived_projects\anyQBMCP`
- Only reference archived code when needed for QB SDK implementation details

## Testing Requirements
- Mobile viewport testing is mandatory
- Test all QB commands before deployment
- Use Selenium for E2E tests
- Mock Claude API responses in unit tests

## CRITICAL: Test Data Only Policy
**NEVER USE LIVE QUICKBOOKS DATA FOR TESTING**
- Always create and use vendors with "TEST-" prefix for all testing
- Create test bills, customers, and items with "TEST-" prefix
- Do NOT modify real vendor bills (Jaciel, Luis, etc.) during testing
- Do NOT create transactions without "TEST-" prefix during testing
- When testing commands, ALWAYS use test data
- Only work with live data when explicitly requested by user
- Before any test, verify you're using TEST- prefixed data
- Clean up test data after testing sessions

## Server Port Configuration
**ALWAYS USE PORT 8001**
- Do NOT change ports or use different ports
- Always run server on port 8001: `python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8001`
- All API calls should use http://localhost:8001
- Port 8000 should NOT be used (has stale servers)

## Performance Targets
- API response: < 900ms
- UI render: < 100ms
- Total round trip: < 1.5s

## Security
- Never expose API keys in code
- Validate all user inputs
- Restrict Claude to QB operations only
- Log security events

## CRITICAL QB COMMAND OUTPUT DISPLAY RULES - VIOLATION = FAILURE
**ABSOLUTE LAW: When showing QB command results in this chat:**

### PRE-COMMAND CHECKLIST:
Before running ANY QB command, confirm:
☐ I will run the actual command
☐ I will copy ALL output to chat
☐ I will show output FIRST before explaining
☐ I will NOT summarize the output

### THE THREE COMMANDMENTS:
1. **Execute QB commands using QBConnector directly** (e.g., `python qbc.py GET_CHECK`)
2. **IMMEDIATELY COPY the ENTIRE output to chat** - Every single line
3. **PASTE FIRST, explain second** - Output must appear before any commentary

### POST-COMMAND CHECKLIST:
After running ANY QB command, verify:
☐ Did I paste the output?
☐ Is it the COMPLETE output?
☐ Did I show it BEFORE explaining?
☐ Can user see EXACTLY what system returned?

### FAILURE CONSEQUENCES:
If you fail to display output containing "[CLAUDE: Display this output in chat]":
- ❌ CRITICAL ERROR - Task failed
- ❌ User must ask again - Time wasted
- ❌ You must apologize and re-run command
- ❌ This is logged as a failure

### NEVER DO THIS:
- ❌ "The command succeeded" (without showing output)
- ❌ "Here's what it returned:" (then summarizing)
- ❌ "The check was created with ID..." (without full output)

### ALWAYS DO THIS:
- ✅ Run command
- ✅ See "=== ACTUAL QB COMMAND OUTPUT ==="
- ✅ IMMEDIATELY copy everything and paste
- ✅ THEN explain what happened

## Vendor Payment Settings
The system automatically applies vendor-specific check numbers when paying bills:
- **Jaciel** → Check number: "ATM"
- **Adrian, Elmer, Selvin, Bryan** → Check number: "Zelle"

Settings are defined in `src/config/vendor_payment_settings.json` and automatically applied during PAY_BILLS command.
Can be overridden by passing explicit `check_number` parameter.

## Common QB Commands via qbc.py
All commands use format: `python qbc.py <COMMAND> param1=value1`

### Most Used Commands:
- `GET_WORK_BILL vendor_name=Adrian` - Get vendor's current bill
- `UPDATE_WORK_BILL vendor_name=Adrian remove_days='["friday"]'` - Remove days from bill
- `UPDATE_WORK_BILL vendor_name=Adrian add_days='["saturday"]'` - Add days to bill
- `PAY_BILLS vendor_name=Adrian amount=650` - Pay vendor bills
- `GET_WORK_WEEK_SUMMARY` - Get weekly summary
- `SEARCH_VENDORS search_term=adrian` - Find vendors
- `CREATE_WORK_BILL vendor_name=Adrian days_worked=5 daily_cost=250` - Create new bill

### Full Command List:
Check src/qb/connector.py lines 71-122 for all 40+ available commands including:
- Work Bills: GET_WORK_BILL, CREATE_WORK_BILL, UPDATE_WORK_BILL, DELETE_BILL
- Vendors: SEARCH_VENDORS, CREATE_VENDOR, UPDATE_VENDOR
- Customers: SEARCH_CUSTOMERS, CREATE_CUSTOMER
- Checks: CREATE_CHECK, SEARCH_CHECKS, GET_CHECK, DELETE_CHECK
- Invoices: SEARCH_INVOICES, CREATE_INVOICE, GET_INVOICE
- Payments: PAY_BILLS, CREATE_BILL_PAYMENT, SEARCH_BILL_PAYMENTS
- Items/Accounts/Deposits: Various search and create commands

## Error Handling
- Use [OK], [ERROR], [WARNING] instead of Unicode
- Provide clear error messages
- Log all errors with context
- Never crash the server

## Deployment Notes
- Use environment variables for configuration
- Test on actual mobile devices
- Monitor API usage and costs
- Keep logs for debugging