"""
Enhanced SDK Engine with comprehensive knowledge
Combines official documentation with discovered patterns and solutions
"""
import sqlite3
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import re
import logging

logger = logging.getLogger(__name__)

class EnhancedSDKEngine:
    """Enhanced SDK engine with complete documentation and discovered knowledge"""
    
    def __init__(self):
        # Use the comprehensive database
        self.db_path = Path(r"C:\Users\nando\Projects\anyQBMCP\docs\sdk docs\db\sdk_comprehensive.db")
        
        # Fallback to other databases if comprehensive doesn't exist
        if not self.db_path.exists():
            self.db_path = Path(r"C:\Users\nando\Projects\anyQBMCP\docs\sdk docs\db\sdk_complete.db")
        if not self.db_path.exists():
            self.db_path = Path(r"C:\Users\nando\Projects\anyQBMCP\docs\sdk docs\db\sdk_docs.db")
            
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Connect to the SDK database"""
        if self.db_path.exists():
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        else:
            raise FileNotFoundError(f"No SDK database found")
    
    def search_comprehensive(self, query: str, include_discovered: bool = True, 
                           limit: int = 10) -> List[Dict]:
        """
        Search comprehensive SDK knowledge including discovered patterns
        
        Args:
            query: Search query
            include_discovered: Include discovered knowledge, not just official
            limit: Maximum results
            
        Returns:
            List of comprehensive results with solutions
        """
        if not self.conn:
            self._connect()
        
        try:
            # First try FTS5 search
            if include_discovered:
                sql = '''
                    SELECT k.*, 
                           snippet(sdk_search, 1, '[', ']', '...', 50) as snippet
                    FROM sdk_knowledge k
                    JOIN sdk_search s ON k.id = s.rowid
                    WHERE sdk_search MATCH ?
                    ORDER BY 
                        CASE 
                            WHEN k.verified = 1 THEN 0
                            WHEN k.doc_type = 'solution' THEN 1
                            WHEN k.doc_type = 'pattern' THEN 2
                            WHEN k.doc_type = 'discovered' THEN 3
                            ELSE 4
                        END,
                        k.confidence DESC,
                        k.usage_count DESC
                    LIMIT ?
                '''
            else:
                sql = '''
                    SELECT k.*, 
                           snippet(sdk_search, 1, '[', ']', '...', 50) as snippet
                    FROM sdk_knowledge k
                    JOIN sdk_search s ON k.id = s.rowid
                    WHERE sdk_search MATCH ? AND k.doc_type = 'official'
                    ORDER BY k.usage_count DESC
                    LIMIT ?
                '''
            
            cursor = self.conn.execute(sql, (query, limit))
            results = [dict(row) for row in cursor.fetchall()]
            
            # Update usage count for returned results
            for result in results:
                self.conn.execute(
                    "UPDATE sdk_knowledge SET usage_count = usage_count + 1 WHERE id = ?",
                    (result['id'],)
                )
            self.conn.commit()
            
        except sqlite3.OperationalError:
            # Fallback to LIKE search if FTS5 fails
            query_pattern = f'%{query}%'
            
            if include_discovered:
                sql = '''
                    SELECT *, substr(content, 1, 200) as snippet
                    FROM sdk_knowledge
                    WHERE (title LIKE ? OR content LIKE ? OR keywords LIKE ?)
                    ORDER BY verified DESC, confidence DESC
                    LIMIT ?
                '''
            else:
                sql = '''
                    SELECT *, substr(content, 1, 200) as snippet
                    FROM sdk_knowledge
                    WHERE (title LIKE ? OR content LIKE ? OR keywords LIKE ?)
                    AND doc_type = 'official'
                    LIMIT ?
                '''
            
            cursor = self.conn.execute(sql, (query_pattern, query_pattern, query_pattern, limit))
            results = [dict(row) for row in cursor.fetchall()]
        
        return results
    
    def get_error_solution(self, error_code: int) -> Dict:
        """
        Get comprehensive error solution including discovered fixes
        
        Args:
            error_code: QuickBooks error code
            
        Returns:
            Complete error documentation with working solutions
        """
        if not self.conn:
            self._connect()
        
        # Get from error_solutions table first (has discovered solutions)
        cursor = self.conn.execute('''
            SELECT * FROM error_solutions WHERE error_code = ?
        ''', (error_code,))
        
        solution = cursor.fetchone()
        if solution:
            result = dict(solution)
            
            # Parse JSON fields
            for field in ['discovered_causes', 'working_solutions', 'mcp_fix_commands']:
                if result.get(field):
                    try:
                        result[field] = json.loads(result[field])
                    except:
                        pass
            
            # Update occurrence count
            self.conn.execute('''
                UPDATE error_solutions 
                SET occurrence_count = occurrence_count + 1,
                    last_encountered = CURRENT_TIMESTAMP
                WHERE error_code = ?
            ''', (error_code,))
            self.conn.commit()
            
            return result
        
        # Fallback to knowledge base
        cursor = self.conn.execute('''
            SELECT * FROM sdk_knowledge 
            WHERE error_codes LIKE ? OR title LIKE ?
            ORDER BY verified DESC, confidence DESC
            LIMIT 1
        ''', (f'%{error_code}%', f'%{error_code}%'))
        
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def get_method_details(self, object_name: str, method_name: str) -> Dict:
        """
        Get complete method details including discovered patterns
        
        Args:
            object_name: QuickBooks object (e.g., 'Bill')
            method_name: Method name (e.g., 'Add')
            
        Returns:
            Complete method documentation with examples and patterns
        """
        if not self.conn:
            self._connect()
        
        # Try exact match first
        search_term = f"{object_name}{method_name}"
        
        # Get from sdk_messages
        cursor = self.conn.execute('''
            SELECT * FROM sdk_messages WHERE message_type LIKE ?
        ''', (f'%{search_term}%',))
        
        message = cursor.fetchone()
        if message:
            result = dict(message)
            
            # Get fields for this message
            cursor = self.conn.execute('''
                SELECT * FROM sdk_fields 
                WHERE message_type = ?
                ORDER BY is_required DESC, field_name
            ''', (result['message_type'],))
            
            result['fields'] = [dict(row) for row in cursor.fetchall()]
            
            # Get related patterns
            cursor = self.conn.execute('''
                SELECT * FROM working_patterns 
                WHERE pattern_code LIKE ? OR mcp_implementation LIKE ?
                LIMIT 3
            ''', (f'%{object_name}%', f'%{object_name}%'))
            
            result['patterns'] = [dict(row) for row in cursor.fetchall()]
            
            return result
        
        # Fallback to knowledge search
        results = self.search_comprehensive(f"{object_name} {method_name}", limit=1)
        return results[0] if results else None
    
    def get_working_pattern(self, pattern_name: str) -> Optional[Dict]:
        """Get a specific working pattern by name"""
        if not self.conn:
            self._connect()
        
        cursor = self.conn.execute('''
            SELECT * FROM working_patterns WHERE pattern_name = ?
        ''', (pattern_name,))
        
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def ask_sdk(self, question: str) -> Dict:
        """
        Answer natural language questions using comprehensive knowledge
        
        Args:
            question: Natural language question
            
        Returns:
            Comprehensive answer with examples and solutions
        """
        question_lower = question.lower()
        
        # Determine question type and search accordingly
        response = {
            'question': question,
            'answer': '',
            'confidence': 0.0,
            'sources': [],
            'examples': [],
            'solutions': []
        }
        
        # Check for error code questions
        error_match = re.search(r'\b(3\d{3}|4\d{3}|5\d{3})\b', question)
        if error_match:
            error_code = int(error_match.group(1))
            error_solution = self.get_error_solution(error_code)
            if error_solution:
                response['answer'] = f"Error {error_code}: {error_solution.get('error_message', 'Unknown')}\n\n"
                response['answer'] += f"Official: {error_solution.get('official_description', 'No official description')}\n\n"
                
                if error_solution.get('working_solutions'):
                    response['answer'] += "Working Solutions:\n"
                    for solution in error_solution.get('working_solutions', []):
                        response['answer'] += f"- {solution}\n"
                
                if error_solution.get('mcp_fix_commands'):
                    response['answer'] += "\nMCP Commands to fix:\n"
                    response['answer'] += error_solution.get('mcp_fix_commands', '')
                
                response['confidence'] = 0.95
                response['sources'].append('error_solutions')
                return response
        
        # Check for method questions
        if any(word in question_lower for word in ['how to', 'create', 'add', 'modify', 'delete']):
            # Extract object and operation
            objects = re.findall(r'\b(bill|invoice|customer|vendor|item|check|payment)\b', 
                               question_lower)
            operations = re.findall(r'\b(add|create|modify|update|delete|query)\b', 
                                  question_lower)
            
            if objects and operations:
                obj = objects[0].title()
                op = operations[0].title()
                if op == 'Create':
                    op = 'Add'
                
                method_details = self.get_method_details(obj, op)
                if method_details:
                    response['answer'] = f"{obj}.{op} Method\n\n"
                    
                    if method_details.get('description'):
                        response['answer'] += f"Description: {method_details['description']}\n\n"
                    
                    if method_details.get('fields'):
                        response['answer'] += "Required Fields:\n"
                        for field in method_details['fields']:
                            if field.get('is_required'):
                                response['answer'] += f"- {field['field_name']} ({field.get('field_type', 'Unknown')})\n"
                    
                    if method_details.get('patterns'):
                        response['answer'] += "\nWorking Patterns:\n"
                        for pattern in method_details['patterns']:
                            response['answer'] += f"\n{pattern.get('description', '')}\n"
                            response['answer'] += f"```python\n{pattern.get('pattern_code', '')}\n```\n"
                    
                    response['confidence'] = 0.9
                    response['sources'].append('sdk_messages')
                    return response
        
        # General search
        results = self.search_comprehensive(question, include_discovered=True, limit=5)
        
        if results:
            # Prioritize verified and high-confidence results
            best_result = results[0]
            
            response['answer'] = best_result.get('content', '')[:1000]
            
            if best_result.get('solution_code'):
                response['answer'] += "\n\nWorking Code:\n```python\n"
                response['answer'] += best_result['solution_code'][:500]
                response['answer'] += "\n```\n"
            
            response['confidence'] = best_result.get('confidence', 0.5)
            response['sources'] = [best_result.get('source', 'unknown')]
            
            # Add related results
            if len(results) > 1:
                response['answer'] += "\n\nRelated Information:\n"
                for result in results[1:3]:
                    response['answer'] += f"- {result.get('title', 'Untitled')}\n"
        else:
            response['answer'] = "No relevant documentation found. Try rephrasing your question."
            response['confidence'] = 0.0
        
        return response
    
    def add_discovery(self, discovery_type: str, title: str, description: str, 
                     solution: str = None, verified: bool = False):
        """
        Add a new discovery to the knowledge base
        
        Args:
            discovery_type: Type of discovery (bug, workaround, pattern, limitation)
            title: Brief title
            description: Full description
            solution: Solution if applicable
            verified: Whether this has been tested
        """
        if not self.conn:
            self._connect()
        
        cursor = self.conn.cursor()
        
        # Add to discovery log
        cursor.execute('''
            INSERT INTO discovery_log 
            (discovery_type, title, description, solution, verified)
            VALUES (?, ?, ?, ?, ?)
        ''', (discovery_type, title, description, solution, verified))
        
        # Add to knowledge base
        doc_type = 'solution' if solution else 'discovered'
        confidence = 0.9 if verified else 0.6
        
        cursor.execute('''
            INSERT INTO sdk_knowledge 
            (doc_type, category, title, content, solution_code, keywords, 
             source, confidence, verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (doc_type, discovery_type, title, description, solution,
              title.lower(), 'runtime_discovery', confidence, verified))
        
        self.conn.commit()
        
        logger.info(f"Added discovery: {title}")
    
    def get_all_patterns(self) -> List[Dict]:
        """Get all working patterns"""
        if not self.conn:
            self._connect()
        
        cursor = self.conn.execute('''
            SELECT * FROM working_patterns 
            ORDER BY success_rate DESC, pattern_name
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None