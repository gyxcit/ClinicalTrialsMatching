"""
Custom Tools - Tous les outils de l'agent
==========================================

Ce fichier contient tous les outils disponibles pour l'agent :
- Outils par défaut (get_time, get_date)
- Outils mathématiques
- Outils de manipulation de chaînes
- Outils utilitaires

Chaque outil est automatiquement découvert et enregistré.
"""

import json
import sys
import inspect
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, List, Any, Optional


# ==============================================================================
# Tool Manager - Gestion centralisée
# ==============================================================================

class ToolManager:
    """Gestionnaire centralisé des outils."""
    
    def __init__(self, config_path: str = None):
        """Initialize the tool manager.
        
        Args:
            config_path: Path to tools_config.json. If None, uses default.
        """
        if config_path is None:
            self.config_path = Path(__file__).parent / "tools_config.json"
        else:
            self.config_path = Path(config_path)
        
        self._tool_map: Dict[str, Callable] = {}
        self._tools: List[Dict[str, Any]] = []
    
    @property
    def tool_map(self) -> Dict[str, Callable]:
        """Get the current tool map."""
        return self._tool_map
    
    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Get the current tool definitions."""
        return self._tools
    
    def load_tools_from_json(self, json_path: str = None) -> List[Dict[str, Any]]:
        """Load tool definitions from JSON file.
        
        Args:
            json_path: Path to the JSON file. If None, uses default config_path
            
        Returns:
            List of tool definitions
        """
        path = Path(json_path) if json_path else self.config_path
        
        if not path.exists():
            print(f"⚠ Tools configuration file not found: {path}")
            return []
        
        with open(path, 'r', encoding='utf-8-sig') as f:
            config = json.load(f)
        
        # Handle nested format: {"tools": [{"type": "function", "function": {...}}]}
        tools = config.get("tools", [])
        self._tools = []
        for tool in tools:
            if isinstance(tool, dict):
                if "function" in tool:
                    # Nested format
                    self._tools.append(tool["function"])
                else:
                    # Flat format
                    self._tools.append(tool)
        
        return self._tools
    
    def save_tools_to_json(self, json_path: str = None) -> None:
        """Save tool definitions to JSON file.
        
        Args:
            json_path: Path to save to. If None, uses default config_path
        """
        path = Path(json_path) if json_path else self.config_path
        
        config = {"tools": self._tools}
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def register_tool(self, name: str, function: Callable, 
                     description: str = None, parameters: Dict = None) -> None:
        """Register a tool with its function and optional definition.
        
        Args:
            name: Tool name
            function: Tool function
            description: Tool description (optional)
            parameters: Tool parameters schema (optional)
        """
        self._tool_map[name] = function
        
        if description and parameters:
            # Format OpenAI avec "type": "function"
            tool_def = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            }
            
            # Update or add to tools list
            existing = next((t for t in self._tools if t.get("function", {}).get("name") == name), None)
            if existing:
                existing.update(tool_def)
            else:
                self._tools.append(tool_def)
    
    def discover_functions_from_module(self, module, exclude: List[str] = None) -> None:
        """Auto-discover functions from a module.
        
        Args:
            module: The module to discover functions from
            exclude: List of function names to exclude
        """
        exclude = exclude or []
        
        for name, obj in inspect.getmembers(module):
            if (inspect.isfunction(obj) and 
                not name.startswith('_') and 
                name not in exclude):
                self._tool_map[name] = obj
    
    def reload_tools(self) -> None:
        """Reload tools from JSON configuration."""
        self._tools = []
        self.load_tools_from_json()


# Global tool manager instance
_global_manager = None

def get_tool_manager() -> ToolManager:
    """Get the global tool manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ToolManager()
    return _global_manager


# ==============================================================================
# Default Tools - Outils par défaut
# ==============================================================================

def get_time() -> str:
    """Get the current server time in ISO format.
    
    Returns:
        Current datetime as ISO formatted string
    """
    return datetime.now().isoformat()


def get_date() -> str:
    """Get the current date.
    
    Returns:
        Current date as string (YYYY-MM-DD)
    """
    return datetime.now().strftime("%Y-%m-%d")


# ==============================================================================
# Mathematical Tools
# ==============================================================================

def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of a and b
    """
    return a + b


def calculate_multiply(a: int, b: int) -> int:
    """Calculate the product of two integers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Product of a * b
    """
    return a * b


def calculate_power(base: int, exponent: int) -> int:
    """Calculate base raised to the power of exponent.
    
    Args:
        base: The base number
        exponent: The exponent
        
    Returns:
        base^exponent
    """
    return base ** exponent


# ==============================================================================
# String Tools
# ==============================================================================

def reverse_string(text: str) -> str:
    """Reverse a string.
    
    Args:
        text: The string to reverse
        
    Returns:
        Reversed string
    """
    return text[::-1]


def count_words(text: str) -> int:
    """Count words in a text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Number of words
    """
    return len(text.split())


# ==============================================================================
# Utility Tools
# ==============================================================================

def convert_temperature(celsius: float) -> str:
    """Convert Celsius to Fahrenheit.
    
    Args:
        celsius: Temperature in Celsius
        
    Returns:
        Temperature in both Celsius and Fahrenheit
    """
    fahrenheit = (celsius * 9/5) + 32
    return f"{celsius}°C = {fahrenheit:.1f}°F"


def calculate_age(birth_year: int) -> int:
    """Calculate age from birth year.
    
    Args:
        birth_year: Year of birth
        
    Returns:
        Current age
    """
    current_year = datetime.now().year
    return current_year - birth_year


# ==============================================================================
# Setup and Registration - Configuration
# ==============================================================================

def setup_tools():
    """Configure and register all tools."""
    manager = get_tool_manager()
    
    # Auto-discover all functions in this module
    manager.discover_functions_from_module(
        sys.modules[__name__],
        exclude=['setup_tools', 'get_tool_manager']
    )
    
    # Ne pas charger depuis JSON ici, on va tout configurer en code
    
    # Register all tools with their definitions
    tools_definitions = [
        {
            "name": "get_time",
            "description": "Get the current server time in ISO format",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_date",
            "description": "Get the current date (YYYY-MM-DD)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "calculate_sum",
            "description": "Calculate the sum of two integers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First number"},
                    "b": {"type": "integer", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        },
        {
            "name": "calculate_multiply",
            "description": "Calculate the product of two integers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First number"},
                    "b": {"type": "integer", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        },
        {
            "name": "calculate_power",
            "description": "Calculate base raised to the power of exponent",
            "parameters": {
                "type": "object",
                "properties": {
                    "base": {"type": "integer", "description": "The base number"},
                    "exponent": {"type": "integer", "description": "The exponent"}
                },
                "required": ["base", "exponent"]
            }
        },
        {
            "name": "reverse_string",
            "description": "Reverse a string",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The string to reverse"}
                },
                "required": ["text"]
            }
        },
        {
            "name": "count_words",
            "description": "Count words in a text",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to analyze"}
                },
                "required": ["text"]
            }
        },
        {
            "name": "convert_temperature",
            "description": "Convert Celsius to Fahrenheit",
            "parameters": {
                "type": "object",
                "properties": {
                    "celsius": {"type": "number", "description": "Temperature in Celsius"}
                },
                "required": ["celsius"]
            }
        },
        {
            "name": "calculate_age",
            "description": "Calculate age from birth year",
            "parameters": {
                "type": "object",
                "properties": {
                    "birth_year": {"type": "integer", "description": "Year of birth"}
                },
                "required": ["birth_year"]
            }
        }
    ]
    
    # Register each tool
    for tool_def in tools_definitions:
        func = manager.tool_map.get(tool_def["name"])
        if func:
            manager.register_tool(
                name=tool_def["name"],
                function=func,
                description=tool_def["description"],
                parameters=tool_def["parameters"]
            )
    
    print(f"✓ Registered {len(tools_definitions)} tools")
    return manager


# Initialize and export for backward compatibility
_manager = setup_tools()
TOOLS = _manager.tools
TOOL_MAP = _manager.tool_map


if __name__ == "__main__":
    # Test all tools
    print(f"\n✓ {len(TOOL_MAP)} tools loaded:")
    for name in TOOL_MAP.keys():
        print(f"  - {name}")
    
    print("\nTesting tools:")
    print(f"  Current time: {TOOL_MAP['get_time']()}")
    print(f"  Current date: {TOOL_MAP['get_date']()}")
    print(f"  5 + 3 = {TOOL_MAP['calculate_sum'](5, 3)}")
    print(f"  4 * 7 = {TOOL_MAP['calculate_multiply'](4, 7)}")
    print(f"  2^8 = {TOOL_MAP['calculate_power'](2, 8)}")
    print(f"  Reverse 'hello' = {TOOL_MAP['reverse_string']('hello')}")
    print(f"  Words in 'hello world' = {TOOL_MAP['count_words']('hello world')}")
    print(f"  25°C = {TOOL_MAP['convert_temperature'](25)}")
    print(f"  Age from 1990 = {TOOL_MAP['calculate_age'](1990)}")
