"""
Guide Rapide: Comment Ajouter un Outil
========================================
"""

from src.tools import register_tool, save_tools_to_json, TOOL_MAP

print("="*60)
print("GUIDE: Ajouter un Nouvel Outil")
print("="*60)

# ============================================================================
# ÉTAPE 1: Définir la fonction
# ============================================================================
print("\n1️⃣  Définir la fonction de l'outil\n")

def convert_temperature(celsius: float) -> str:
    """Convertit Celsius en Fahrenheit."""
    fahrenheit = (celsius * 9/5) + 32
    return f"{celsius}°C = {fahrenheit}°F"

print("✓ Fonction convert_temperature créée")


# ============================================================================
# ÉTAPE 2: Enregistrer l'outil
# ============================================================================
print("\n2️⃣  Enregistrer l'outil\n")

register_tool(
    name="convert_temperature",
    function=convert_temperature,
    description="Convert temperature from Celsius to Fahrenheit",
    parameters={
        "type": "object",
        "properties": {
            "celsius": {
                "type": "number",
                "description": "Temperature in Celsius"
            }
        },
        "required": ["celsius"]
    }
)

print("✓ Outil enregistré dans TOOL_MAP")


# ============================================================================
# ÉTAPE 3: Tester l'outil
# ============================================================================
print("\n3️⃣  Tester l'outil\n")

# L'outil est maintenant disponible dans TOOL_MAP
result = TOOL_MAP["convert_temperature"](25)
print(f"Test: convert_temperature(25) = {result}")


# ============================================================================
# ÉTAPE 4: Sauvegarder (optionnel)
# ============================================================================
print("\n4️⃣  Sauvegarder dans JSON (optionnel)\n")

save_tools_to_json()
print("✓ Configuration sauvegardée dans src/tools_config.json")


# ============================================================================
# RÉSUMÉ
# ============================================================================
print("\n" + "="*60)
print("✅ RÉSUMÉ")
print("="*60)
print("""
Votre outil est prêt ! Il peut maintenant être utilisé par l'agent.

Outils disponibles:
""")
for tool_name in TOOL_MAP.keys():
    print(f"  • {tool_name}")

print("""
Pour utiliser avec un agent:
    
    from src.Agent import Agent
    
    agent = Agent(
        model="groq/llama-3.3-70b-versatile",
        api_key="your_key"
    )
    
    response = agent.chat("Convert 25 degrees Celsius to Fahrenheit")
    
""")

print("="*60)
