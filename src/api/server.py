#!/usr/bin/env python
"""
AnyQB FastAPI Server - Mobile QuickBooks Chat Interface
Direct Claude API integration for natural language QB commands
"""
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys
import os
import io

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import QB connector and Claude integration
from qb.connector import QBConnector
from api.claude import ClaudeAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Custom log handler to capture logs
class LogCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = []
    
    def emit(self, record):
        self.logs.append(self.format(record))
    
    def get_logs(self):
        return self.logs.copy()
    
    def clear(self):
        self.logs = []

# Initialize FastAPI app
app = FastAPI(
    title="AnyQB - Mobile QuickBooks Chat",
    description="Natural language interface for QuickBooks using Claude API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
qb_connector = QBConnector()
claude_api = ClaudeAPI()

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    command: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    success: bool
    timestamp: str
    logs: Optional[List[str]] = None  # Add verbose logging

class CommandRequest(BaseModel):
    command: str
    params: Dict[str, Any] = {}

# Load command definitions
def load_commands():
    """Load QB command definitions from config"""
    try:
        config_path = Path(__file__).parent.parent / "config" / "commands.json"
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load commands: {e}")
        return {"commands": {}}

COMMANDS = load_commands()

# API Routes
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the mobile web interface"""
    ui_path = Path(__file__).parent.parent / "ui" / "index.html"
    
    if not ui_path.exists():
        # Return a simple default UI if file doesn't exist yet
        return HTMLResponse(content=DEFAULT_UI, status_code=200)
    
    with open(ui_path, 'r') as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/api/chat", response_model=ChatResponse)
async def process_chat(request: ChatRequest):
    """Process natural language chat messages"""
    start_time = time.time()
    
    try:
        # Get Claude to interpret the command
        claude_response = await claude_api.interpret_message(request.message)
        
        if not claude_response['success']:
            return ChatResponse(
                response=claude_response.get('error', 'Failed to process message'),
                success=False,
                timestamp=datetime.now().isoformat()
            )
        
        command = claude_response.get('command')
        params = claude_response.get('params', {})
        
        # Log what Claude returned
        logger.info(f"Claude returned: command={command}, params={params}")
        
        # Execute the QB command with log capture
        captured_logs = []
        if command:
            # Set up log capture
            log_capture = LogCapture()
            log_capture.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
            
            # Add to root logger to capture all logs
            root_logger = logging.getLogger()
            root_logger.addHandler(log_capture)
            
            try:
                qb_result = qb_connector.execute_command(command, params)
                response_text = qb_result.get('output', 'Command executed')
                captured_logs = log_capture.get_logs()
            finally:
                # Remove the handler
                root_logger.removeHandler(log_capture)
        else:
            response_text = claude_response.get('response', 'No command identified')
        
        # Log performance
        elapsed = time.time() - start_time
        logger.info(f"Chat processed in {elapsed:.2f}s - Command: {command}")
        
        return ChatResponse(
            response=response_text,
            command=command,
            params=params,
            success=True,
            timestamp=datetime.now().isoformat(),
            logs=captured_logs if captured_logs else None
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            response=f"[ERROR] {str(e)}",
            success=False,
            timestamp=datetime.now().isoformat()
        )

@app.post("/api/execute")
async def execute_command(request: CommandRequest):
    """Execute a QB command directly with verbose logging"""
    try:
        # Set up log capture
        log_capture = LogCapture()
        log_capture.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        
        # Add to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(log_capture)
        
        try:
            result = qb_connector.execute_command(request.command, request.params)
            
            # Add captured logs to result
            result['logs'] = log_capture.get_logs()
            
            return JSONResponse(content=result)
        finally:
            # Remove the handler
            root_logger.removeHandler(log_capture)
            
    except Exception as e:
        logger.error(f"Execute error: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

@app.get("/api/commands")
async def list_commands():
    """List all available QB commands"""
    return JSONResponse(content=COMMANDS)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "qb_connected": qb_connector.connected,
        "claude_ready": claude_api.is_ready(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/stats")
async def get_stats():
    """Get usage statistics tracked from API responses"""
    try:
        # Get stats tracked from actual API responses
        anthropic_stats = claude_api.get_usage_stats()
        
        return {
            "todays_cost": anthropic_stats.get('todays_cost', 0.0),
            "current_balance": anthropic_stats.get('current_balance', 0.0),
            "requests_today": anthropic_stats.get('requests_today', 0),
            "model": anthropic_stats.get('model', ''),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {
            "todays_cost": 0.0,
            "current_balance": 0.0,
            "requests_today": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Default UI if index.html doesn't exist yet
DEFAULT_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AnyQB - Mobile QuickBooks Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: #000;
            color: #fff;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        #header {
            background: #111;
            padding: 10px;
            display: flex;
            justify-content: space-around;
            align-items: center;
            border-bottom: 1px solid #333;
            font-size: 14px;
        }
        .header-stat {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .stat-label {
            color: #666;
            font-size: 12px;
        }
        .stat-value {
            color: #fff;
            font-size: 16px;
            font-weight: bold;
        }
        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            max-width: 600px;
            margin: 0 auto;
            width: 100%;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border: 1px solid #333;
            border-radius: 5px;
            word-wrap: break-word;
        }
        .user-message {
            background: #1a1a1a;
            text-align: right;
            margin-left: 20%;
        }
        .assistant-message {
            background: #0a0a0a;
            margin-right: 20%;
            white-space: pre-wrap;
        }
        #input-container {
            padding: 10px;
            background: #111;
            border-top: 1px solid #333;
        }
        #message-input {
            width: 100%;
            padding: 10px;
            background: #222;
            border: 1px solid #444;
            color: #fff;
            font-family: inherit;
            font-size: 14px;
            border-radius: 5px;
        }
        #send-button {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            background: #1a1a1a;
            color: #fff;
            border: 1px solid #333;
            cursor: pointer;
            font-family: inherit;
            border-radius: 5px;
        }
        #send-button:hover {
            background: #2a2a2a;
        }
        .loading {
            color: #666;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div id="header">
        <div class="header-stat">
            <span class="stat-label">Today's Cost</span>
            <span class="stat-value" id="todays-cost">$0.00</span>
        </div>
        <div class="header-stat">
            <span class="stat-label">Balance</span>
            <span class="stat-value" id="current-balance">$0.00</span>
        </div>
    </div>
    
    <div id="chat-container"></div>
    
    <div id="input-container">
        <input type="text" id="message-input" placeholder="Type a command... (e.g., 'show jaciel's bill')" />
        <button id="send-button">Send</button>
    </div>

    <script>
        const chatContainer = document.getElementById('chat-container');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        
        function addMessage(text, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
            messageDiv.textContent = text;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;
            
            addMessage(message, true);
            messageInput.value = '';
            
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message assistant-message loading';
            loadingDiv.textContent = 'Processing...';
            chatContainer.appendChild(loadingDiv);
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message })
                });
                
                const data = await response.json();
                chatContainer.removeChild(loadingDiv);
                addMessage(data.response, false);
                
            } catch (error) {
                chatContainer.removeChild(loadingDiv);
                addMessage('[ERROR] Failed to send message', false);
            }
        }
        
        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        // Focus input on load
        messageInput.focus();
    </script>
</body>
</html>
"""

# Run the server
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("SERVER_PORT", 8000))
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    
    logger.info(f"Starting AnyQB server on {host}:{port}")
    logger.info(f"QB Connected: {qb_connector.connected}")
    logger.info(f"Claude API Ready: {claude_api.is_ready()}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=True  # Enable auto-reload in development
    )