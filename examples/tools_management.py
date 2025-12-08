"""Example: Managing tools with JSON configuration."""
import json
from pathlib import Path
from src.tools import (
    TOOLS,
    TOOL_MAP,
    register_tool,
    save_tools_to_json,
    reload_tools,
    load_tools_from_json
)


def demo_list_tools():
    """List all available tools."""
    print("\n=== Available Tools ===")
    print(f"Number of tools: {len(TOOLS)}")
    
    for tool in TOOLS:
        name = tool['function']['name']
        description = tool['function']['description']
        print(f"\n- {name}")
        print(f"  Description: {description}")
        
        # Show if function is implemented
        if name in TOOL_MAP:
            print(f"  ✓ Implementation available")
        else:
            print(f"  ✗ Implementation missing")


def demo_add_custom_tool():
    """Add a custom tool dynamically."""
    print("\n=== Adding Custom Tool ===")
    
    def calculate_sum(a: int, b: int) -> int:
        """Calculate sum of two numbers."""
        return a + b
    
    # Register the tool
    register_tool(
        name="calculate_sum",
        function=calculate_sum,
        description="Calculate the sum of two numbers",
        parameters={
            "type": "object",
            "properties": {
                "a": {
                    "type": "integer",
                    "description": "First number"
                },
                "b": {
                    "type": "integer",
                    "description": "Second number"
                }
            },
            "required": ["a", "b"]
        }
    )
    
    print(f"Tool 'calculate_sum' registered")
    print(f"Testing: 5 + 3 = {TOOL_MAP['calculate_sum'](5, 3)}")
    
    # Save to JSON (optional)
    print("\nSaving tools configuration to JSON...")
    save_tools_to_json()
    print("✓ Saved to src/tools_config.json")


def demo_load_custom_config():
    """Load tools from a custom JSON file."""
    print("\n=== Loading Custom Configuration ===")
    
    # Create a custom config
    custom_config = {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "greet",
                    "description": "Greet a person by name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name of the person to greet"
                            }
                        },
                        "required": ["name"]
                    }
                }
            }
        ]
    }
    
    # Save to a custom file
    custom_path = Path("custom_tools.json")
    with open(custom_path, 'w', encoding='utf-8') as f:
        json.dump(custom_config, f, indent=2)
    
    print(f"✓ Created {custom_path}")
    
    # Load from custom file
    custom_tools = load_tools_from_json(str(custom_path))
    print(f"✓ Loaded {len(custom_tools)} tool(s) from custom config")
    
    for tool in custom_tools:
        print(f"  - {tool['function']['name']}")
    
    # Clean up
    custom_path.unlink()


def demo_reload_tools():
    """Demonstrate reloading tools from JSON."""
    print("\n=== Reloading Tools ===")
    
    # Modify the JSON file (in a real scenario)
    print("In a real scenario, you would edit src/tools_config.json")
    print("Then call reload_tools() to refresh the configuration")
    
    # Reload
    reload_tools()
    print(f"✓ Tools reloaded: {len(TOOLS)} tool(s)")


def demo_view_json_config():
    """View the current JSON configuration."""
    print("\n=== Current JSON Configuration ===")
    
    config_path = Path(__file__).parent.parent / "src" / "tools_config.json"
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(json.dumps(config, indent=2))
    else:
        print(f"Configuration file not found: {config_path}")


def main():
    """Run all demos."""
    print("=" * 60)
    print("Tools Management Demo")
    print("=" * 60)
    
    demo_list_tools()
    demo_add_custom_tool()
    demo_load_custom_config()
    demo_reload_tools()
    demo_view_json_config()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
