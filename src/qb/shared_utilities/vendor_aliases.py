"""
Vendor name aliasing for voice-to-text and common misspellings
Handles mapping of common variations to actual vendor names in QuickBooks
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Common vendor aliases and voice-to-text mistakes
VENDOR_ALIASES = {
    # Jaciel variations (voice-to-text often hears "Hacienda")
    'hacienda': 'Jaciel',
    'hacienda j': 'Jaciel',
    'hacienda jaciel': 'Jaciel',
    'acienda': 'Jaciel',
    'assienda': 'Jaciel',
    'hassienda': 'Jaciel',
    'hasienda': 'Jaciel',
    'hacienda joe': 'Jaciel',
    'hacienda joel': 'Jaciel',
    'jaciel': 'Jaciel',  # Correct spelling
    'jasiel': 'Jaciel',
    'haciel': 'Jaciel',
    
    # Bryan variations
    'brian': 'Bryan',
    'bryant': 'Bryan',
    'brayan': 'Bryan',
    
    # Elmer variations
    'elmar': 'Elmer',
    'almer': 'Elmer',
    
    # Selvin variations
    'selbin': 'Selvin',
    'salvin': 'Selvin',
    'calvin': 'Selvin',
    'seven': 'Selvin',  # Voice-to-text mistake
    
    # Adrian variations (maps to full vendor name in QB)
    'adrian': 'Zelle payment to Adrian Carpente',
    'adrina': 'Zelle payment to Adrian Carpente',  # Common typo/mishearing
    'adriano': 'Zelle payment to Adrian Carpente',
    'adrean': 'Zelle payment to Adrian Carpente',
    'adrian carpente': 'Zelle payment to Adrian Carpente',
    'adrian carpenter': 'Zelle payment to Adrian Carpente',
    
    # Add more aliases as needed
}

def resolve_vendor_alias(vendor_name: str) -> str:
    """
    Resolve a vendor name that might be an alias or misspelling
    
    Args:
        vendor_name: The input vendor name (possibly an alias)
    
    Returns:
        The actual vendor name to use in QuickBooks
    """
    if not vendor_name:
        return vendor_name
    
    # Check for exact alias match (case-insensitive)
    vendor_lower = vendor_name.lower().strip()
    
    if vendor_lower in VENDOR_ALIASES:
        resolved = VENDOR_ALIASES[vendor_lower]
        logger.info(f"Resolved vendor alias '{vendor_name}' -> '{resolved}'")
        return resolved
    
    # Check for partial matches (for variations like "Hacienda something")
    for alias, actual in VENDOR_ALIASES.items():
        if alias in vendor_lower:
            logger.info(f"Resolved vendor alias '{vendor_name}' -> '{actual}' (partial match)")
            return actual
    
    # No alias found, return original
    return vendor_name

def add_vendor_alias(alias: str, actual_vendor: str) -> None:
    """
    Add a new vendor alias mapping at runtime
    
    Args:
        alias: The alias/misspelling
        actual_vendor: The actual vendor name
    """
    VENDOR_ALIASES[alias.lower().strip()] = actual_vendor
    logger.info(f"Added vendor alias '{alias}' -> '{actual_vendor}'")