"""
Gas Station Consolidator - Consolidates gas station payee variations
Maps all variations of gas stations to their main payee names
"""

import logging
import re
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

class GasStationConsolidator:
    """Consolidates gas station payee variations to standard names"""
    
    # Main gas station mappings
    # Key: Keywords to search for (lowercase)
    # Value: (Standard Name, Priority) - higher priority wins in conflicts
    GAS_STATION_MAPPINGS = [
        # Higher priority (more specific) first
        (['kay mart valero'], 'Kay Mart Valero', 90),
        (['speedy stop', 'speedystop'], 'Speedy Stop', 80),
        (['valero'], 'Valero', 70),
        (['shell'], 'Shell', 70),
        (['chevron'], 'Chevron', 70),
        (['exxon'], 'Exxon', 70),
        (['mobil'], 'Mobil', 70),
        (['texaco'], 'Texaco', 70),
        (['conoco'], 'Conoco', 70),
        (['phillips 66', 'phillips66'], 'Phillips 66', 70),
        (['marathon'], 'Marathon', 70),
        (['citgo'], 'Citgo', 70),
        (['sunoco'], 'Sunoco', 70),
        (['bp', 'british petroleum'], 'BP', 70),
        (['gulf'], 'Gulf', 70),
        (['sinclair'], 'Sinclair', 70),
        (['arco'], 'Arco', 70),
        (['76', 'seventy six'], '76', 60),
        (['circle k'], 'Circle K', 60),
        (['7-eleven', '7 eleven', 'seven eleven'], '7-Eleven', 60),
        (['wawa'], 'Wawa', 60),
        (['sheetz'], 'Sheetz', 60),
        (['quiktrip', 'quik trip', 'qt'], 'QuikTrip', 60),
        (['racetrac', 'race trac'], 'RaceTrac', 60),
        (['loves', "love's"], "Love's", 60),
        (['pilot'], 'Pilot', 60),
        (['flying j'], 'Flying J', 60),
        (['ta travel', 'ta truck'], 'TA Travel Centers', 60),
        (['petro'], 'Petro', 60),
        (['costco gas'], 'Costco Gas', 60),
        (['sams club gas', "sam's club gas"], "Sam's Club Gas", 60),
        (['kroger fuel'], 'Kroger Fuel', 60),
        (['heb gas'], 'HEB Gas', 60),
    ]
    
    # Patterns to remove from payee names
    CLEANUP_PATTERNS = [
        r'CHECKCARD\s+\d+',  # CHECKCARD 0917
        r'#\d{9}',           # #000213600
        r'\d{2}/\d{2}',      # 05/06
        r'PURCHASE\s+CO',    # PURCHASE CO
        r'DESREVERSAL',      # DESREVERSAL
        r'\s+\d{2}\s+\d{2}/\d{2}',  # 87 02/06
        r'\s+#\d+',          # #000010700
    ]
    
    def __init__(self):
        """Initialize the consolidator"""
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.CLEANUP_PATTERNS]
    
    def is_gas_station(self, payee_name: str) -> bool:
        """
        Check if a payee name is a gas station
        
        Args:
            payee_name: The payee name to check
            
        Returns:
            True if it's a gas station, False otherwise
        """
        if not payee_name:
            return False
            
        payee_lower = payee_name.lower()
        
        # Check if any gas station keywords are in the name
        for keywords, _, _ in self.GAS_STATION_MAPPINGS:
            for keyword in keywords:
                if keyword in payee_lower:
                    return True
        
        # Additional gas-related keywords
        gas_keywords = ['gas station', 'fuel', 'gasoline', 'petroleum']
        for keyword in gas_keywords:
            if keyword in payee_lower:
                return True
                
        return False
    
    def consolidate(self, payee_name: str) -> str:
        """
        Consolidate a gas station payee name to its standard form
        
        Args:
            payee_name: The original payee name
            
        Returns:
            The consolidated standard name, or original if not a gas station
        """
        if not payee_name:
            return payee_name
        
        # Check if it's a gas station
        if not self.is_gas_station(payee_name):
            return payee_name
        
        payee_lower = payee_name.lower()
        
        # Find the best match based on priority
        best_match = None
        best_priority = -1
        
        for keywords, standard_name, priority in self.GAS_STATION_MAPPINGS:
            for keyword in keywords:
                if keyword in payee_lower:
                    if priority > best_priority:
                        best_match = standard_name
                        best_priority = priority
                    break
        
        if best_match:
            logger.info(f"Consolidated '{payee_name}' to '{best_match}'")
            return best_match
        
        # If no specific match, try to clean up the name
        cleaned = self.clean_payee_name(payee_name)
        if cleaned != payee_name:
            logger.info(f"Cleaned '{payee_name}' to '{cleaned}'")
            return cleaned
            
        return payee_name
    
    def clean_payee_name(self, payee_name: str) -> str:
        """
        Clean up a payee name by removing transaction-specific information
        
        Args:
            payee_name: The original payee name
            
        Returns:
            Cleaned payee name
        """
        cleaned = payee_name
        
        # Apply all cleanup patterns
        for pattern in self.compiled_patterns:
            cleaned = pattern.sub('', cleaned)
        
        # Clean up extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def find_best_gas_station_match(self, search_term: str, payee_list: List[str]) -> Optional[str]:
        """
        Find the best gas station match from a list of payees
        
        Args:
            search_term: What the user searched for
            payee_list: List of available payees
            
        Returns:
            Best matching payee name, or None if no good match
        """
        if not search_term or not payee_list:
            return None
        
        search_lower = search_term.lower()
        
        # First, try to find the consolidated name in the list
        consolidated_search = self.consolidate(search_term)
        for payee in payee_list:
            if payee == consolidated_search:
                return payee
        
        # If searching for a gas station, find all gas station matches and consolidate
        gas_stations = []
        for payee in payee_list:
            if self.is_gas_station(payee):
                consolidated = self.consolidate(payee)
                # Check if the consolidated name matches what we're looking for
                if search_lower in consolidated.lower() or consolidated.lower() in search_lower:
                    gas_stations.append((payee, consolidated))
        
        if gas_stations:
            # Prefer exact consolidated matches
            for original, consolidated in gas_stations:
                if consolidated.lower() == search_lower:
                    return original
            
            # Otherwise return the first match
            return gas_stations[0][0]
        
        return None