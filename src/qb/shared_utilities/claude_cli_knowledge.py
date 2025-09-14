"""
Claude Code CLI Knowledge Base
Stores discovered facts about Claude Code CLI limitations and workarounds
"""
from typing import Dict, List, Optional
import json
from pathlib import Path

class ClaudeCLIKnowledge:
    """Knowledge base for Claude Code CLI quirks and solutions"""
    
    def __init__(self):
        """Initialize with hardcoded knowledge"""
        self.knowledge = self._load_knowledge()
    
    def _load_knowledge(self) -> Dict:
        """Load all Claude CLI knowledge"""
        return {
            "module_caching": {
                "issue": "Claude Code CLI caches Python modules and doesn't reload on file changes",
                "github_issue": "#7174",
                "symptoms": [
                    "Changes to Python files don't take effect",
                    "Old code continues to run after edits",
                    "MCP server uses stale module versions"
                ],
                "solutions": [
                    "Use /mcp command twice to disconnect and reconnect",
                    "Create direct testing tools like test_mcp_direct.py",
                    "Import modules dynamically with importlib.reload()",
                    "Test functions directly without going through MCP"
                ],
                "workarounds": [
                    "Build development tools that bypass MCP server",
                    "Use subprocess calls instead of imports when possible",
                    "Test with standalone scripts before MCP integration"
                ]
            },
            "mcp_slash_command": {
                "issue": "/mcp command sometimes stops working",
                "symptoms": [
                    "Typing /mcp does nothing",
                    "MCP connection appears stuck",
                    "Commands timeout or fail silently"
                ],
                "solutions": [
                    "Type /mcp directly in Claude's response (not in code block)",
                    "Use /mcp twice: once to disconnect, once to reconnect",
                    "Never use 'claude mcp remove' followed by 'claude mcp add' - corrupts config",
                    "If /mcp fails, restart Claude Code CLI session"
                ],
                "best_practice": "Always test with a simple command like health_check after reconnect"
            },
            "mcp_configuration": {
                "issue": "MCP configuration can become corrupted",
                "symptoms": [
                    "MCP servers fail to start",
                    ".claude-mcp.json becomes malformed",
                    "Servers listed but not responding"
                ],
                "solutions": [
                    "Never use 'claude mcp remove' then 'claude mcp add' repeatedly",
                    "Always use /mcp for reconnection instead",
                    "Backup .claude-mcp.json before changes",
                    "Use stdio transport for reliability"
                ],
                "config_location": ".claude-mcp.json in project root"
            },
            "stdio_transport": {
                "issue": "MCP servers must not output to stdout",
                "symptoms": [
                    "MCP server fails to connect",
                    "Commands fail with parsing errors",
                    "Server appears to start but doesn't respond"
                ],
                "solutions": [
                    "Never use print() statements in MCP server",
                    "Use logging module with FileHandler only",
                    "No StreamHandler in logging config",
                    "All output must go through MCP protocol"
                ],
                "correct_logging": "logging.FileHandler('logs/mcp_server.log')"
            },
            "windows_unicode": {
                "issue": "Windows terminals have Unicode encoding issues",
                "symptoms": [
                    "UnicodeEncodeError in terminal output",
                    "'charmap' codec can't encode character",
                    "Unicode symbols display incorrectly"
                ],
                "solutions": [
                    "Use ASCII characters only in output",
                    "Replace ✓ with [OK], ✗ with [X]",
                    "Set sys.stdout.reconfigure(encoding='utf-8')",
                    "Specify encoding='utf-8' for file operations"
                ]
            },
            "async_timeout": {
                "issue": "Long-running operations timeout in MCP",
                "symptoms": [
                    "Operations fail after 30 seconds",
                    "Large queries timeout",
                    "Complex operations never complete"
                ],
                "solutions": [
                    "Wrap blocking calls with asyncio.wait_for()",
                    "Use run_in_executor() for sync code",
                    "Set appropriate timeout values",
                    "Break large operations into smaller chunks"
                ],
                "example": "await asyncio.wait_for(run_in_executor(None, func), timeout=30)"
            },
            "development_workflow": {
                "issue": "Slow development due to restart requirements",
                "symptoms": [
                    "Every code change requires MCP restart",
                    "Testing is slow and cumbersome",
                    "Can't iterate quickly on fixes"
                ],
                "solutions": [
                    "Create test_mcp_direct.py for direct testing",
                    "Build standalone test scripts first",
                    "Use Python scripts instead of going through MCP",
                    "Test repository functions directly"
                ],
                "best_tools": [
                    "test_mcp_direct.py - Test without restart",
                    "sdk_field_explorer.py - Discover SDK structure",
                    "Direct repository testing scripts"
                ]
            },
            "mcp_error_handling": {
                "issue": "MCP errors are often cryptic",
                "symptoms": [
                    "Generic error messages",
                    "No stack traces in responses",
                    "Hard to debug failures"
                ],
                "solutions": [
                    "Always log full exceptions with exc_info=True",
                    "Return detailed error information in responses",
                    "Check logs/mcp_server.log for details",
                    "Use try/except with specific error messages"
                ]
            }
        }
    
    def search_issues(self, query: str) -> List[Dict]:
        """Search for Claude CLI issues by keyword"""
        results = []
        query_lower = query.lower()
        
        for key, info in self.knowledge.items():
            # Check if query matches issue, symptoms, or solutions
            if (query_lower in key.lower() or
                query_lower in info.get('issue', '').lower() or
                any(query_lower in s.lower() for s in info.get('symptoms', [])) or
                any(query_lower in s.lower() for s in info.get('solutions', []))):
                
                results.append({
                    'topic': key.replace('_', ' ').title(),
                    'issue': info.get('issue'),
                    'symptoms': info.get('symptoms', []),
                    'solutions': info.get('solutions', [])
                })
        
        return results
    
    def get_all_topics(self) -> List[str]:
        """Get all knowledge topics"""
        return [key.replace('_', ' ').title() for key in self.knowledge.keys()]
    
    def get_topic(self, topic: str) -> Optional[Dict]:
        """Get detailed info about a specific topic"""
        # Convert topic to key format
        key = topic.lower().replace(' ', '_')
        
        # Try exact match first
        if key in self.knowledge:
            return {
                'topic': topic,
                **self.knowledge[key]
            }
        
        # Try partial match
        for k, v in self.knowledge.items():
            if key in k or k in key:
                return {
                    'topic': k.replace('_', ' ').title(),
                    **v
                }
        
        return None
    
    def get_quick_fixes(self) -> Dict[str, str]:
        """Get quick reference for common issues"""
        return {
            "Module not reloading": "Use /mcp twice to reconnect",
            "MCP not responding": "Check logs/mcp_server.log",
            "Unicode errors": "Use ASCII characters only",
            "Timeout errors": "Increase timeout or break into chunks",
            "Config corrupted": "Never use remove/add, only /mcp",
            "Development slow": "Use test_mcp_direct.py"
        }
    
    def format_knowledge(self, topic_data: Dict) -> str:
        """Format knowledge for display"""
        output = []
        
        output.append(f"## {topic_data.get('topic', 'Unknown Topic')}")
        output.append("")
        
        if topic_data.get('issue'):
            output.append(f"### Issue")
            output.append(topic_data['issue'])
            output.append("")
        
        if topic_data.get('github_issue'):
            output.append(f"**GitHub Issue**: {topic_data['github_issue']}")
            output.append("")
        
        if topic_data.get('symptoms'):
            output.append("### Symptoms")
            for symptom in topic_data['symptoms']:
                output.append(f"- {symptom}")
            output.append("")
        
        if topic_data.get('solutions'):
            output.append("### Solutions")
            for idx, solution in enumerate(topic_data['solutions'], 1):
                output.append(f"{idx}. {solution}")
            output.append("")
        
        if topic_data.get('workarounds'):
            output.append("### Workarounds")
            for workaround in topic_data['workarounds']:
                output.append(f"- {workaround}")
            output.append("")
        
        if topic_data.get('best_practice'):
            output.append(f"**Best Practice**: {topic_data['best_practice']}")
            output.append("")
        
        if topic_data.get('example'):
            output.append("### Example")
            output.append(f"```python\n{topic_data['example']}\n```")
            output.append("")
        
        return "\n".join(output)