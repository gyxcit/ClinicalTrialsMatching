"""
Exemple d'Ajout de Nouveaux Outils
===================================

Ce fichier montre comment ajouter de nouveaux outils au système.
"""

import os
from dotenv import load_dotenv
from src.Agent import Agent
from src.tools import register_tool, save_tools_to_json

load_dotenv()


# =============================================================================
# Étape 1: Créer les fonctions d'outils
# =============================================================================

def calculate_sum(a: int, b: int) -> int:
    """Calcule la somme de deux nombres.
    
    Args:
        a: Premier nombre
        b: Second nombre
        
    Returns:
        La somme a + b
    """
    return a + b


def calculate_multiply(a: int, b: int) -> int:
    """Calcule le produit de deux nombres.
    
    Args:
        a: Premier nombre
        b: Second nombre
        
    Returns:
        Le produit a * b
    """
    return a * b


def search_web(query: str) -> str:
    """Recherche sur le web (simulation).
    
    Args:
        query: Terme de recherche
        
    Returns:
        Résultats de recherche simulés
    """
    # En production, vous utiliseriez une vraie API de recherche
    return f"Résultats de recherche pour '{query}':\n" \
           f"1. Article sur {query}\n" \
           f"2. Documentation {query}\n" \
           f"3. Tutoriel {query}"


def get_weather(city: str) -> str:
    """Obtient la météo d'une ville (simulation).
    
    Args:
        city: Nom de la ville
        
    Returns:
        Informations météo
    """
    # En production, vous utiliseriez une API météo réelle
    return f"Météo à {city}: Ensoleillé, 22°C"


# =============================================================================
# Étape 2: Enregistrer les outils
# =============================================================================

def setup_custom_tools():
    """Enregistre tous les outils personnalisés."""
    
    print("🔧 Enregistrement des outils personnalisés...\n")
    
    # Important: register_tool() ajoute automatiquement au TOOL_MAP
    
    # Outil 1: Addition
    register_tool(
        name="calculate_sum",
        function=calculate_sum,
        description="Calculate the sum of two integers",
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
    print("✓ calculate_sum enregistré")
    
    # Outil 2: Multiplication
    register_tool(
        name="calculate_multiply",
        function=calculate_multiply,
        description="Calculate the product of two integers",
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
    print("✓ calculate_multiply enregistré")
    
    # Outil 3: Recherche web
    register_tool(
        name="search_web",
        function=search_web,
        description="Search the web for information",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    )
    print("✓ search_web enregistré")
    
    # Outil 4: Météo
    register_tool(
        name="get_weather",
        function=get_weather,
        description="Get current weather for a city",
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Name of the city"
                }
            },
            "required": ["city"]
        }
    )
    print("✓ get_weather enregistré")
    
    # Optionnel: Sauvegarder dans le JSON
    print("\n💾 Sauvegarde dans tools_config.json...")
    save_tools_to_json()
    print("✓ Configuration sauvegardée")


# =============================================================================
# Étape 3: Tester les outils avec l'Agent
# =============================================================================

def demo_with_agent():
    """Démontre l'utilisation des nouveaux outils avec un agent."""
    
    print("\n" + "="*60)
    print("DÉMO: Agent avec Outils Personnalisés")
    print("="*60 + "\n")
    
    # Créer l'agent
    agent = Agent(
        name="MathAssistant",
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        system_prompt="You are a helpful assistant with mathematical and information retrieval capabilities."
    )
    
    # Test 1: Addition
    print("\n--- Test 1: Addition ---")
    response = agent.chat("Calcule 25 + 37")
    print(f"User: Calcule 25 + 37")
    print(f"Agent: {response}")
    
    # Test 2: Multiplication
    print("\n--- Test 2: Multiplication ---")
    response = agent.chat("Multiplie 12 par 8")
    print(f"User: Multiplie 12 par 8")
    print(f"Agent: {response}")
    
    # Test 3: Recherche
    print("\n--- Test 3: Recherche Web ---")
    response = agent.chat("Recherche des informations sur Python programming")
    print(f"User: Recherche des informations sur Python programming")
    print(f"Agent: {response}")
    
    # Test 4: Météo
    print("\n--- Test 4: Météo ---")
    response = agent.chat("Quelle est la météo à Paris ?")
    print(f"User: Quelle est la météo à Paris ?")
    print(f"Agent: {response}")


# =============================================================================
# Étape 4: Exemple d'ajout direct dans tools.py
# =============================================================================

def add_tool_to_tools_py():
    """
    MÉTHODE ALTERNATIVE: Ajouter directement dans src/tools.py
    
    1. Ouvrir src/tools.py
    2. Ajouter votre fonction:
    
    def my_custom_tool(param: str) -> str:
        '''Description de l'outil.'''
        return f"Result: {param}"
    
    3. La fonction sera automatiquement découverte et ajoutée au TOOL_MAP !
    
    4. Ajouter la définition dans tools_config.json:
    
    {
      "tools": [
        {
          "type": "function",
          "function": {
            "name": "my_custom_tool",
            "description": "Description de ce que fait l'outil",
            "parameters": {
              "type": "object",
              "properties": {
                "param": {
                  "type": "string",
                  "description": "Description du paramètre"
                }
              },
              "required": ["param"]
            }
          }
        }
      ]
    }
    """
    print("\n📝 Méthode alternative documentée ci-dessus")


# =============================================================================
# Exécution
# =============================================================================

def main():
    """Point d'entrée principal."""
    
    # Étape 1: Enregistrer les outils
    setup_custom_tools()
    
    # Étape 2: Tester avec l'agent
    if os.getenv("GROQ_API_KEY"):
        demo_with_agent()
    else:
        print("\n⚠️  GROQ_API_KEY non définie. Demo avec agent ignorée.")
        print("Définissez GROQ_API_KEY dans .env pour tester l'agent.")
    
    # Étape 3: Montrer la méthode alternative
    add_tool_to_tools_py()
    
    print("\n" + "="*60)
    print("✅ Exemple terminé !")
    print("="*60)
    print("\n📚 Pour plus d'infos, consultez:")
    print("  - src/TOOLS_README.md")
    print("  - DEVELOPER_GUIDE.md")


if __name__ == "__main__":
    main()
