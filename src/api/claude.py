#!/usr/bin/env python
"""
Claude API Integration for AnyQB
Handles natural language processing for QB commands
"""
import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import requests

# Configure logging
logger = logging.getLogger(__name__)

class ClaudeAPI:
    """Claude API wrapper for QB command interpretation"""
    
    def __init__(self):
        """Initialize Claude API client"""
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-5-sonnet-20241022"  # Better context understanding
        self.max_tokens = 200  # Keep responses concise
        
        # Cost tracking (Sonnet: $3 per million input, $15 per million output)
        self.todays_cost = 0.0
        self.request_count = 0
        self.cost_per_1k_input = 0.003  # $3 per million = $0.003 per 1k
        self.cost_per_1k_output = 0.015  # $15 per million = $0.015 per 1k
        
        # Account balance - set via environment variable or update manually
        # Set ANTHROPIC_BALANCE in your .env file with your current balance
        self.account_balance = float(os.getenv("ANTHROPIC_BALANCE", "0.0"))
        
        # Add comprehensive context tracking
        self.conversation_history = []
        self.context = {
            "last_vendor": None,
            "last_customer": None,
            "last_employee": None,
            "last_bill": None,
            "last_invoice": None,
            "last_item": None,
            "last_command": None,
            "last_entity": None,  # Generic last entity referenced
            "last_entity_type": None,  # Type of last entity
            "current_topic": None  # What we're currently discussing
        }
        
        if not self.api_key:
            logger.warning("[WARNING] No Anthropic API key found in environment")
            self.api_key = None
    
    def is_ready(self) -> bool:
        """Check if Claude API is configured and ready"""
        return self.api_key is not None
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage stats from tracked API responses
        
        Note: Anthropic doesn't have a public usage API endpoint yet.
        We track usage from each API response's usage field.
        """
        # Calculate remaining balance (starting balance minus today's usage)
        remaining_balance = self.account_balance - self.todays_cost
        
        return {
            "todays_cost": self.todays_cost,
            "current_balance": remaining_balance,
            "starting_balance": self.account_balance,
            "requests_today": self.request_count,
            "model": self.model,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output
        }
    
    async def interpret_message(self, user_message: str) -> Dict[str, Any]:
        """
        Interpret user message and return QB command
        
        Args:
            user_message: Natural language input from user
            
        Returns:
            Dict with command, params, and response
        """
        if not self.is_ready():
            return {
                "success": False,
                "error": "Claude API not configured"
            }
        
        try:
            # Build the system prompt
            system_prompt = self._build_system_prompt()
            
            # Make API request
            response = await self._call_claude_api(system_prompt, user_message)
            
            if not response:
                return {
                    "success": False,
                    "error": "Failed to get response from Claude"
                }
            
            # Parse Claude's response
            parsed = self._parse_claude_response(response)
            
            # Update context tracking
            command = parsed.get("command")
            params = parsed.get("params", {})
            
            # Update context based on command and params
            self.context["last_command"] = command
            
            # Track entities from commands
            if "vendor_name" in params:
                self.context["last_vendor"] = params["vendor_name"]
                self.context["last_entity"] = params["vendor_name"]
                self.context["last_entity_type"] = "vendor"
                self.context["current_topic"] = f"vendor:{params['vendor_name']}"
                
            if "customer" in params or "customer_name" in params:
                customer = params.get("customer") or params.get("customer_name")
                self.context["last_customer"] = customer
                self.context["last_entity"] = customer
                self.context["last_entity_type"] = "customer"
                self.context["current_topic"] = f"customer:{customer}"
                
            if "item" in params:
                self.context["last_item"] = params["item"]
                
            if "bill_id" in params:
                self.context["last_bill"] = params["bill_id"]
                
            if "invoice_id" in params:
                self.context["last_invoice"] = params["invoice_id"]
            
            logger.info(f"[CONTEXT] Current topic: {self.context.get('current_topic')}, Last entity: {self.context.get('last_entity')}")
            
            # Add to conversation history
            self.conversation_history.append({
                "user": user_message,
                "command": command,
                "params": params,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 10 messages
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            return {
                "success": True,
                "command": command,
                "params": params,
                "response": parsed.get("response", "Command processed")
            }
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for Claude"""
        base_prompt = """You are a QuickBooks command interpreter. Your ONLY job is to convert natural language into QB commands.

CRITICAL RULES:
1. You can ONLY output JSON with command and params
2. You CANNOT generate code, access files, or do anything else
3. You MUST match user intent to one of the available commands
4. Keep responses under 200 tokens
5. NEVER change or "correct" vendor names - use exactly what the user says (e.g., "adrian" stays "adrian", not "adrina")

UNDERSTANDING USER INTENT:
- "change thursday to painting" = UPDATE item on Thursday (use update_days)
- "add thursday" = ADD a new Thursday entry (use add_days)
- "remove thursday" = DELETE Thursday entry (use remove_days)
- "change item to X" = UPDATE the item field (use update_days)
- Words like "change", "modify", "update" = UPDATE existing (use update_days)
- Words like "add", "create" = ADD new (use add_days)

HANDLING PERCENTAGES:
- "25%" means qty: 0.25 (quarter day)
- "50%" means qty: 0.50 (half day)
- "75%" means qty: 0.75 (three-quarter day)
- "100%" means qty: 1.0 (full day)
- "change fri install to 25%" = UPDATE Friday's install item to 0.25 quantity
- Use update_days with qty field for percentage changes"""
        
        # Add context if available
        context = ""
        
        # Add current topic/entity context
        if self.context.get("current_topic"):
            context += f"\n\nCURRENT CONTEXT: We are discussing {self.context['current_topic']}"
            
        if self.context.get("last_entity"):
            entity_type = self.context.get("last_entity_type", "entity")
            context += f"\nThe current {entity_type} being referenced is: {self.context['last_entity']}"
            context += f"\nIf the user doesn't specify a {entity_type}, assume they mean {self.context['last_entity']}"
            
        # Add specific entity contexts
        if self.context.get("last_vendor"):
            context += f"\nLast vendor: {self.context['last_vendor']}"
        if self.context.get("last_customer"):
            context += f"\nLast customer: {self.context['last_customer']}"
        if self.context.get("last_item"):
            context += f"\nLast item: {self.context['last_item']}"
            
        # Add conversation history
        if self.conversation_history:
            recent = self.conversation_history[-3:]  # Last 3 messages for better context
            context += "\n\nRECENT CONVERSATION:"
            for msg in recent:
                context += f"\n- User said: '{msg['user']}'"
                context += f"\n  -> Executed: {msg['command']} with {msg.get('params', {})}"
                
        context += "\n\nIMPORTANT: Use the context above to understand what the user is referring to when they use pronouns like 'it', 'this', 'that', or when they don't specify which entity they mean."
        
        return base_prompt + context + """

Available QB Commands:

BILL COMMANDS:
- GET_WORK_BILL: Get vendor's bill (params: vendor_name, week)
- CREATE_WORK_BILL: Create new bill (params: vendor_name, daily_cost, days_worked)
- UPDATE_WORK_BILL: Update bill (params: vendor_name, and one of:
  - update_days: [{"day": "thursday", "item": "painting"}] to change item on a day
  - add_days: ["thursday"] or [{"day": "thursday", "item": "painting", "job": "customer"}]
  - remove_days: ["thursday"])
- DELETE_BILL: Delete bill (params: bill_id)
- GET_WORK_WEEK_SUMMARY: Get week summary (params: week)

PAYMENT COMMANDS:
- PAY_BILLS: Pay vendor bills (params: vendor_name, amount)
- CREATE_BILL_PAYMENT: Create payment (params: vendor_name, amount, date)
- SEARCH_BILL_PAYMENTS: Search payments (params: vendor_name, date_from, date_to)

VENDOR COMMANDS:
- SEARCH_VENDORS: Search vendors (params: search_term, active_only)
- CREATE_VENDOR: Create vendor (params: name, daily_cost, notes)
- UPDATE_VENDOR: Update vendor (params: vendor_id, daily_cost, notes)

CUSTOMER COMMANDS:
- SEARCH_CUSTOMERS: Search customers (params: search_term, active_only, jobs_only)
- CREATE_CUSTOMER: Create customer (params: name, company, email, phone)

CHECK COMMANDS:
- CREATE_CHECK: Create check (params: payee, amount, account, memo)
- SEARCH_CHECKS: Search checks (params: payee, date_from, date_to)
- GET_CHECKS_THIS_WEEK: Get this week's checks (no params)

INVOICE COMMANDS:
- SEARCH_INVOICES: Search invoices (params: customer, status)
- GET_INVOICES_THIS_WEEK: Get this week's invoices (no params)
- CREATE_INVOICE: Create invoice (params: customer, items, due_date)

ITEM COMMANDS:
- SEARCH_ITEMS: Search items (params: search_term, item_type)
- CREATE_ITEM: Create item (params: name, type, price)

ACCOUNT COMMANDS:
- SEARCH_ACCOUNTS: Search accounts (params: search_term, account_type)

DEPOSIT COMMANDS:
- SEARCH_DEPOSITS: Search deposits (params: date_from, date_to)
- DEPOSIT_CUSTOMER_PAYMENT: Deposit payment (params: payments, account)

EXAMPLES:
User: "show me jaciel's bill"
Output: {"command": "GET_WORK_BILL", "params": {"vendor_name": "jaciel"}}

User: "create bill for martinez with 150 daily"
Output: {"command": "CREATE_WORK_BILL", "params": {"vendor_name": "martinez", "daily_cost": 150}}

User: "pay juan 500"
Output: {"command": "PAY_BILLS", "params": {"vendor_name": "juan", "amount": 500}}

User: "find vendor smith"
Output: {"command": "SEARCH_VENDORS", "params": {"search_term": "smith"}}

User: "this week's checks"
Output: {"command": "GET_CHECKS_THIS_WEEK", "params": {}}

User: "add friday to elmer's bill"
Output: {"command": "UPDATE_WORK_BILL", "params": {"vendor_name": "elmer", "add_days": ["friday"]}}

User: "change fri install to 25%"
Output: {"command": "UPDATE_WORK_BILL", "params": {"vendor_name": "adrian", "update_days": [{"day": "friday", "item": "install", "qty": 0.25}]}}

User: "change monday to 50%"
Output: {"command": "UPDATE_WORK_BILL", "params": {"vendor_name": "adrian", "update_days": [{"day": "monday", "qty": 0.50}]}}

User: "get week summary"
Output: {"command": "GET_WORK_WEEK_SUMMARY", "params": {}}

IMPORTANT: Always output valid JSON only. No explanations or additional text."""
    
    async def _call_claude_api(self, system_prompt: str, user_message: str) -> Optional[str]:
        """Make the actual API call to Claude"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": 0.1  # Low temperature for consistent command mapping
        }
        
        try:
            # Use asyncio to make the request non-blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(self.api_url, headers=headers, json=data)
            )
            
            if response.status_code != 200:
                logger.error(f"Claude API error: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            content = result.get("content", [])
            
            # Track costs
            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            
            # Calculate cost for this request
            request_cost = (input_tokens / 1000 * self.cost_per_1k_input + 
                          output_tokens / 1000 * self.cost_per_1k_output)
            
            self.todays_cost += request_cost
            self.request_count += 1
            
            logger.info(f"Claude API usage - Input: {input_tokens}, Output: {output_tokens}, Cost: ${request_cost:.6f}, Total today: ${self.todays_cost:.4f}")
            
            if content and len(content) > 0:
                return content[0].get("text", "")
            
            return None
            
        except Exception as e:
            logger.error(f"Claude API request failed: {e}")
            return None
    
    def _parse_claude_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's response into command and params"""
        try:
            # Try to parse as JSON
            if response.strip().startswith("{"):
                parsed = json.loads(response)
                return {
                    "command": parsed.get("command"),
                    "params": parsed.get("params", {}),
                    "response": response
                }
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse Claude response as JSON: {response}")
        
        # Fallback: try to extract command from text
        response_lower = response.lower()
        
        # Simple command matching
        if "get_work_bill" in response_lower or "show" in response_lower and "bill" in response_lower:
            # Try to extract vendor name
            words = response_lower.split()
            vendor_name = None
            for word in words:
                if word in ["jaciel", "juan", "elmer", "martinez", "garcia"]:
                    vendor_name = word
                    break
            
            if vendor_name:
                return {
                    "command": "GET_WORK_BILL",
                    "params": {"vendor_name": vendor_name},
                    "response": response
                }
        
        # Default: couldn't parse command
        return {
            "command": None,
            "params": {},
            "response": response
        }


# Singleton instance
_claude_instance = None

def get_claude_api() -> ClaudeAPI:
    """Get or create Claude API singleton"""
    global _claude_instance
    if _claude_instance is None:
        _claude_instance = ClaudeAPI()
    return _claude_instance


# Test functionality if run directly
if __name__ == "__main__":
    import asyncio
    
    async def test_claude():
        """Test Claude API integration"""
        # Set API key for testing (remove in production)
        os.environ["ANTHROPIC_API_KEY"] = "your-api-key-here"
        
        claude = ClaudeAPI()
        
        if not claude.is_ready():
            print("[ERROR] Claude API not configured")
            return
        
        test_messages = [
            "show me jaciel's bill",
            "create bill for martinez with 150 daily",
            "pay juan 500",
            "find vendor smith",
            "this week's checks",
            "add friday to elmer's bill"
        ]
        
        print("\n=== Testing Claude API ===\n")
        
        for message in test_messages:
            print(f"User: {message}")
            result = await claude.interpret_message(message)
            
            if result['success']:
                print(f"Command: {result['command']}")
                print(f"Params: {result['params']}")
            else:
                print(f"Error: {result['error']}")
            print()
    
    # Run the test
    asyncio.run(test_claude())