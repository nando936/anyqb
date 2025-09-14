"""
SDK Documentation Search Engine
Provides search capabilities for QuickBooks SDK documentation
"""
import sqlite3
from typing import List, Dict, Optional
from pathlib import Path
import re

class SDKSearchEngine:
    """Search engine for SDK documentation optimized for Claude Code CLI"""
    
    def __init__(self):
        self.db_path = Path(r"C:\Users\nando\Projects\anyQBMCP\docs\sdk docs\db\sdk_docs.db")
        self.conn = None
        self._connect()
        
    def _connect(self):
        """Connect to the SDK documentation database"""
        if self.db_path.exists():
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        else:
            raise FileNotFoundError(f"SDK database not found at {self.db_path}")
    
    def search(self, query: str, doc_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Search SDK documentation using full-text search
        
        Args:
            query: Search query string
            doc_type: Optional filter by document type (error, knowledge, method, etc.)
            limit: Maximum number of results to return
            
        Returns:
            List of matching documents with relevance ranking
        """
        if not self.conn:
            self._connect()
        
        try:
            # Try FTS5 search first
            if doc_type:
                sql = '''
                    SELECT d.*, snippet(sdk_search, 1, '[', ']', '...', 50) as snippet
                    FROM sdk_docs d
                    JOIN sdk_search s ON d.rowid = s.rowid
                    WHERE sdk_search MATCH ? AND d.doc_type = ?
                    ORDER BY rank
                    LIMIT ?
                '''
                params = (query, doc_type, limit)
            else:
                sql = '''
                    SELECT d.*, snippet(sdk_search, 1, '[', ']', '...', 50) as snippet
                    FROM sdk_docs d
                    JOIN sdk_search s ON d.rowid = s.rowid
                    WHERE sdk_search MATCH ?
                    ORDER BY rank
                    LIMIT ?
                '''
                params = (query, limit)
                
            cursor = self.conn.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.DatabaseError:
            # FTS5 is corrupted, fallback to LIKE search
            query_pattern = f'%{query}%'
            
            if doc_type:
                sql = '''
                    SELECT *, substr(content, 1, 200) as snippet
                    FROM sdk_docs
                    WHERE (title LIKE ? OR content LIKE ? OR keywords LIKE ?)
                    AND doc_type = ?
                    LIMIT ?
                '''
                params = (query_pattern, query_pattern, query_pattern, doc_type, limit)
            else:
                sql = '''
                    SELECT *, substr(content, 1, 200) as snippet
                    FROM sdk_docs
                    WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ?
                    LIMIT ?
                '''
                params = (query_pattern, query_pattern, query_pattern, limit)
            
            cursor = self.conn.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
        
        return results
    
    def get_error_documentation(self, error_code: int) -> Optional[Dict]:
        """
        Get documentation for a specific error code
        
        Args:
            error_code: QuickBooks error code
            
        Returns:
            Error documentation if found
        """
        if not self.conn:
            self._connect()
            
        cursor = self.conn.execute('''
            SELECT * FROM sdk_docs 
            WHERE error_code = ? OR title LIKE ?
            LIMIT 1
        ''', (error_code, f'%Error {error_code}%'))
        
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def get_method_documentation(self, object_name: str, method_name: str) -> Optional[Dict]:
        """
        Get documentation for a specific SDK method
        
        Args:
            object_name: QuickBooks object name (e.g., 'Bill', 'Customer')
            method_name: Method name (e.g., 'Add', 'Query', 'Mod')
            
        Returns:
            Method documentation if found
        """
        search_term = f"{object_name} {method_name}"
        results = self.search(search_term, limit=1)
        return results[0] if results else None
    
    def suggest_related(self, current_topic: str, limit: int = 5) -> List[Dict]:
        """
        Suggest related documentation based on current topic
        
        Args:
            current_topic: Current documentation topic
            limit: Maximum number of suggestions
            
        Returns:
            List of related documentation entries
        """
        # Extract key terms from current topic
        key_terms = re.findall(r'\b[A-Z][a-z]+\b', current_topic)
        if key_terms:
            query = ' OR '.join(key_terms)
            return self.search(query, limit=limit)
        return []
    
    def get_all_error_codes(self) -> List[Dict]:
        """Get all documented error codes"""
        if not self.conn:
            self._connect()
            
        cursor = self.conn.execute('''
            SELECT error_code, title, substr(content, 1, 100) as preview
            FROM sdk_docs 
            WHERE error_code IS NOT NULL
            ORDER BY error_code
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


class ClaudeFormatter:
    """Format SDK documentation for optimal Claude Code CLI consumption"""
    
    @staticmethod
    def format_search_results(results: List[Dict], query: str) -> str:
        """Format search results for Claude"""
        if not results:
            return f"No results found for '{query}'\n\nTry:\n- Different keywords\n- Checking spelling\n- Using broader terms"
        
        output = f"## Found {len(results)} results for '{query}'\n\n"
        
        for i, result in enumerate(results, 1):
            output += f"### {i}. {result.get('title', 'Untitled')}\n"
            
            # Show type and category if available
            doc_type = result.get('doc_type', result.get('type', 'unknown'))
            category = result.get('category', 'general')
            output += f"**Type**: {doc_type} | **Category**: {category}\n"
            
            # Show snippet or truncated content
            content = result.get('snippet') or result.get('content', '')[:200] + '...'
            output += f"{content}\n\n"
            
            if i >= 3 and len(results) > 3:  # Show only top 3 in initial response
                output += f"*...and {len(results) - 3} more results*\n\n"
                break
        
        output += "**Get details**: Use GET_SDK_ERROR or GET_SDK_METHOD for full documentation\n"
        return output
    
    @staticmethod
    def format_error_documentation(error_doc: Dict) -> str:
        """Format error documentation for Claude"""
        if not error_doc:
            return "Error code not found in documentation"
        
        output = f"## {error_doc['title']}\n\n"
        output += f"{error_doc['content']}\n\n"
        
        # Add actionable solutions
        if 'invalid reference' in error_doc['content'].lower():
            output += "**Quick Fix**:\n"
            output += "```\n"
            output += "# Check if the referenced item exists:\n"
            output += "SEARCH_ITEMS search_term='ItemName'\n"
            output += "# If not found, create it:\n"
            output += "CREATE_ITEM item_name='ItemName' item_type='Service'\n"
            output += "```\n"
        
        output += f"\n**Source**: {error_doc.get('source', 'SDK Documentation')}"
        return output
    
    @staticmethod
    def format_method_documentation(method_doc: Dict) -> str:
        """Format method documentation for Claude"""
        if not method_doc:
            return "Method documentation not found"
        
        output = f"## {method_doc['title']}\n\n"
        output += f"{method_doc['content']}\n\n"
        
        # Add example MCP commands if relevant
        if 'bill' in method_doc['title'].lower():
            output += "**Related MCP Commands**:\n"
            output += "- `CREATE_WORK_BILL` - Create a new bill\n"
            output += "- `UPDATE_WORK_BILL` - Modify existing bill\n"
            output += "- `GET_WORK_BILL` - View bill details\n"
        
        return output
    
    @staticmethod
    def format_progressive(content: str, depth: str = "summary") -> str:
        """
        Format content with progressive disclosure
        
        Args:
            content: Full content
            depth: 'summary', 'detailed', 'full'
        """
        if depth == "summary":
            # Return first 500 characters
            truncated = content[:500]
            if len(content) > 500:
                truncated += "...\n\n**Need more?** Ask for 'detailed' or 'full' view"
            return truncated
        elif depth == "detailed":
            # Return first 1500 characters
            truncated = content[:1500]
            if len(content) > 1500:
                truncated += "...\n\n**Need more?** Ask for 'full' view"
            return truncated
        else:  # full
            return content