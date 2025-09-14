"""
Fuzzy Matcher - Intelligent entity matching for QuickBooks data
Provides fuzzy matching capabilities for vendors, items, customers, and jobs
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

@dataclass
class MatchResult:
    """Result of a fuzzy match operation"""
    found: bool
    exact_name: str = ""
    confidence: float = 0.0
    match_type: str = ""  # 'exact', 'fuzzy', 'partial', 'number'
    original_query: str = ""
    
    def __str__(self):
        if not self.found:
            return f"No match found for '{self.original_query}'"
        return f"Found '{self.exact_name}' ({self.match_type} match, {self.confidence:.1%} confidence)"


class FuzzyMatcher:
    """Provides fuzzy matching capabilities for QuickBooks entities"""
    
    def __init__(self, min_confidence: float = 0.7):
        """
        Initialize fuzzy matcher
        
        Args:
            min_confidence: Minimum confidence score for fuzzy matches (0.0 to 1.0)
        """
        self.min_confidence = min_confidence
    
    def find_best_match(self, query: str, candidates: List[str], 
                       entity_type: str = "generic") -> MatchResult:
        """
        Find the best match for a query from a list of candidates
        
        Args:
            query: The search term
            candidates: List of possible matches
            entity_type: Type of entity for specialized matching ('vendor', 'item', 'customer', 'job')
        
        Returns:
            MatchResult with the best match found
        """
        if not query or candidates is None or not candidates:
            return MatchResult(found=False, original_query=query if query else "")
        
        query_lower = query.lower().strip()
        
        # Check for exact match first
        for candidate in candidates:
            if candidate.lower() == query_lower:
                return MatchResult(
                    found=True,
                    exact_name=candidate,
                    confidence=1.0,
                    match_type="exact",
                    original_query=query
                )
        
        # Apply entity-specific matching
        if entity_type == "vendor":
            return self._match_vendor(query, candidates)
        elif entity_type == "item":
            return self._match_item(query, candidates)
        elif entity_type == "customer":
            return self._match_customer(query, candidates)
        elif entity_type == "job":
            return self._match_job(query, candidates)
        else:
            return self._generic_fuzzy_match(query, candidates)
    
    def _match_vendor(self, query: str, candidates: List[str]) -> MatchResult:
        """
        Match vendor with special rules:
        - First name only matching (e.g., "selvin" -> "Selvin Lopez")
        - Substring matching (e.g., "adrian" -> "Zelle payment to Adrian Carpente")
        - Case insensitive
        """
        if not candidates:
            return MatchResult(found=False, original_query=query)
            
        query_lower = query.lower().strip()
        
        # SIMPLE SUBSTRING MATCH - if query is IN the vendor name, match it!
        for candidate in candidates:
            if not candidate:  # Skip None or empty candidates
                continue
            if query_lower in candidate.lower():
                return MatchResult(
                    found=True,
                    exact_name=candidate,
                    confidence=0.9,
                    match_type="partial",
                    original_query=query
                )
        
        # First name matching
        for candidate in candidates:
            if not candidate:  # Skip None or empty candidates
                continue
            candidate_first = candidate.split()[0].lower() if candidate else ""
            if candidate_first == query_lower:
                return MatchResult(
                    found=True,
                    exact_name=candidate,
                    confidence=0.95,
                    match_type="partial",
                    original_query=query
                )
        
        # Fuzzy match on full name
        return self._generic_fuzzy_match(query, candidates)
    
    def _match_item(self, query: str, candidates: List[str]) -> MatchResult:
        """
        Match item with special rules:
        - Number matching (e.g., "30" -> "30 deliver and install")
        - Partial word matching (e.g., "deliver" -> "30 deliver and install")
        """
        if not candidates:
            return MatchResult(found=False, original_query=query)
            
        query_lower = query.lower().strip()
        
        # Number prefix matching
        if query_lower.isdigit():
            for candidate in candidates:
                if not candidate:  # Skip None or empty candidates
                    continue
                if candidate.lower().startswith(query_lower + " "):
                    return MatchResult(
                        found=True,
                        exact_name=candidate,
                        confidence=0.9,
                        match_type="number",
                        original_query=query
                    )
        
        # Partial word matching
        for candidate in candidates:
            if not candidate:  # Skip None or empty candidates
                continue
            candidate_lower = candidate.lower()
            if query_lower in candidate_lower:
                # Calculate confidence based on how much of the string matches
                confidence = len(query_lower) / len(candidate_lower)
                if confidence >= 0.3:  # At least 30% of the string
                    return MatchResult(
                        found=True,
                        exact_name=candidate,
                        confidence=min(0.85, confidence + 0.3),
                        match_type="partial",
                        original_query=query
                    )
        
        # Fuzzy match
        return self._generic_fuzzy_match(query, candidates)
    
    def _match_customer(self, query: str, candidates: List[str]) -> MatchResult:
        """
        Match customer with special rules:
        - Handle customer:job format
        - Match on customer prefix
        """
        query_lower = query.lower().strip()
        
        # Direct customer matching (no job)
        for candidate in candidates:
            candidate_lower = candidate.lower()
            # Remove job portion if present
            customer_part = candidate_lower.split(':')[0] if ':' in candidate_lower else candidate_lower
            
            if customer_part == query_lower:
                return MatchResult(
                    found=True,
                    exact_name=candidate,
                    confidence=0.95,
                    match_type="partial",
                    original_query=query
                )
        
        return self._generic_fuzzy_match(query, candidates)
    
    def _match_job(self, query: str, candidates: List[str]) -> MatchResult:
        """
        Match job with special rules:
        - Match "customer:job" format
        - Allow matching on customer prefix (e.g., "rws" -> "rws:Retreat 24")
        - Allow matching on job suffix (e.g., "retreat" -> "rws:Retreat 24")
        """
        query_lower = query.lower().strip()
        
        # Check if query contains colon (full format)
        if ':' in query_lower:
            # Try exact match on full format
            for candidate in candidates:
                if candidate.lower() == query_lower:
                    return MatchResult(
                        found=True,
                        exact_name=candidate,
                        confidence=1.0,
                        match_type="exact",
                        original_query=query
                    )
        
        # Match on customer prefix
        for candidate in candidates:
            if ':' in candidate:
                customer_part, job_part = candidate.split(':', 1)
                customer_lower = customer_part.lower()
                job_lower = job_part.lower()
                
                # Match customer prefix
                if customer_lower == query_lower:
                    return MatchResult(
                        found=True,
                        exact_name=candidate,
                        confidence=0.9,
                        match_type="partial",
                        original_query=query
                    )
                
                # Match job suffix
                if query_lower in job_lower:
                    return MatchResult(
                        found=True,
                        exact_name=candidate,
                        confidence=0.85,
                        match_type="partial",
                        original_query=query
                    )
        
        return self._generic_fuzzy_match(query, candidates)
    
    def _generic_fuzzy_match(self, query: str, candidates: List[str]) -> MatchResult:
        """
        Generic fuzzy matching using SequenceMatcher
        
        Args:
            query: Search term
            candidates: List of possible matches
        
        Returns:
            Best match found or no match
        """
        if not candidates:
            return MatchResult(found=False, original_query=query)
            
        query_lower = query.lower().strip()
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            if not candidate:  # Skip None or empty candidates
                continue
            candidate_lower = candidate.lower()
            
            # Calculate similarity score
            score = SequenceMatcher(None, query_lower, candidate_lower).ratio()
            
            # Check various containment relationships
            if query_lower in candidate_lower:
                # Query is contained in candidate (e.g., "paint" in "24 paint")
                score = max(score, 0.75)
            elif candidate_lower in query_lower:
                # Candidate is contained in query (e.g., "paint" in "painting")
                score = max(score, 0.8)
            else:
                # Check if they share common words (e.g., "painting" and "24 paint" both have "paint")
                query_words = query_lower.replace('24', '').strip().split()
                candidate_words = candidate_lower.replace('24', '').strip().split()
                for q_word in query_words:
                    for c_word in candidate_words:
                        if q_word in c_word or c_word in q_word:
                            score = max(score, 0.75)
                            break
            
            if score > best_score and score >= self.min_confidence:
                best_score = score
                best_match = candidate
        
        if best_match:
            return MatchResult(
                found=True,
                exact_name=best_match,
                confidence=best_score,
                match_type="fuzzy",
                original_query=query
            )
        
        return MatchResult(found=False, original_query=query)
    
    def match_vendor(self, query: str, vendors: List[str]) -> MatchResult:
        """Convenience method for vendor matching"""
        return self.find_best_match(query, vendors, entity_type="vendor")
    
    def match_item(self, query: str, items: List[str]) -> MatchResult:
        """Convenience method for item matching"""
        return self.find_best_match(query, items, entity_type="item")
    
    def match_customer(self, query: str, customers: List[str]) -> MatchResult:
        """Convenience method for customer matching"""
        return self.find_best_match(query, customers, entity_type="customer")
    
    def match_job(self, query: str, jobs: List[str]) -> MatchResult:
        """Convenience method for job matching"""
        return self.find_best_match(query, jobs, entity_type="job")