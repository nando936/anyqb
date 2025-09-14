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
User Input → Mobile UI → FastAPI → Claude API → QB MCP → QuickBooks → Response
```

## File Organization
- `src/api/` - FastAPI server and Claude integration
- `src/ui/` - Mobile web interface
- `src/qb/` - QuickBooks connection logic
- `src/utils/` - Shared utilities
- `src/config/` - Configuration files

## Development Workflow
1. Always test on mobile viewport (390x844)
2. Use existing QB command definitions from anyQBMCP
3. Keep Claude API responses under 200 tokens
4. Log all QB command executions
5. Handle errors gracefully with user-friendly messages

## QB Integration
- **IMPORTANT**: MCP server and anyQBMCP projects are now ARCHIVED
- **ARCHIVED LOCATION**: `C:\Users\nando\Projects\archived_projects\anyQBMCP`
- **USE QBConnector directly** via `python qbc.py` command
- **Simple command format**: `python qbc.py <COMMAND> param1=value1 param2=value2`
- **Example**: `python qbc.py GET_WORK_BILL vendor_name=Adrian`
- **For complex params**: Use JSON format like `remove_days='["friday"]'`
- All commands are in src/qb/connector.py lines 71-122
- Archived project has full QB SDK implementations for reference

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

## QB Command Output Display Rules
**CRITICAL: When showing QB command results in this chat:**
1. **Execute QB commands using QBConnector directly** (e.g., `python get_bill.py Adrian`)
2. **ALWAYS manually copy the actual command output to chat**
3. **NEVER summarize or paraphrase the output**
4. **Show the complete raw output as returned by QBConnector**
5. **Do not provide your own formatted summary**
6. **The user wants to see exactly what the system returns**

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