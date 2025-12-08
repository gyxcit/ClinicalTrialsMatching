"""
Tools - Import depuis custom_tools
===================================

Ce module importe simplement les outils depuis custom_tools.py
pour la rétrocompatibilité.

Tous les outils sont maintenant définis dans custom_tools.py
"""

# Import everything from custom_tools
from src.custom_tools import (
    # Tool Manager
    ToolManager,
    get_tool_manager,
    
    # Default tools
    get_time,
    get_date,
    
    # Math tools
    calculate_sum,
    calculate_multiply,
    calculate_power,
    
    # String tools
    reverse_string,
    count_words,
    
    # Utility tools
    convert_temperature,
    calculate_age,
    
    # Setup
    setup_tools,
    
    # Exports
    TOOLS,
    TOOL_MAP
)

# For backward compatibility
__all__ = [
    'ToolManager',
    'get_tool_manager',
    'get_time',
    'get_date',
    'calculate_sum',
    'calculate_multiply',
    'calculate_power',
    'reverse_string',
    'count_words',
    'convert_temperature',
    'calculate_age',
    'setup_tools',
    'TOOLS',
    'TOOL_MAP'
]