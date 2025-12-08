# Guide des Outils Personnalisés (custom_tools.py)

## Vue d'ensemble

Tous les outils de l'agent sont maintenant centralisés dans **un seul fichier** : `src/custom_tools.py`

Ce fichier contient :
- ✅ Le gestionnaire d'outils (ToolManager)
- ✅ Les outils par défaut (get_time, get_date)
- ✅ Les outils personnalisés (math, string, utility)
- ✅ Le système d'auto-découverte
- ✅ La configuration et l'export

## Structure du fichier

```
src/custom_tools.py
│
├── ToolManager (classe)
│   ├── load_tools_from_json()
│   ├── save_tools_to_json()
│   ├── register_tool()
│   └── discover_functions_from_module()
│
├── Default Tools
│   ├── get_time()
│   └── get_date()
│
├── Mathematical Tools
│   ├── calculate_sum()
│   ├── calculate_multiply()
│   └── calculate_power()
│
├── String Tools
│   ├── reverse_string()
│   └── count_words()
│
├── Utility Tools
│   ├── convert_temperature()
│   └── calculate_age()
│
└── Setup & Export
    ├── setup_tools()
    ├── TOOLS (export)
    └── TOOL_MAP (export)
```

## Ajouter un nouvel outil

### Étape 1 : Définir la fonction

Ajoutez votre fonction dans la section appropriée de `custom_tools.py` :

```python
# ==============================================================================
# Vos nouveaux outils
# ==============================================================================

def mon_nouvel_outil(param1: str, param2: int) -> str:
    """Description de votre outil.
    
    Args:
        param1: Description du paramètre 1
        param2: Description du paramètre 2
        
    Returns:
        Description du résultat
    """
    return f"Résultat: {param1} x {param2}"
```

### Étape 2 : Ajouter la définition JSON

Dans la fonction `setup_tools()`, ajoutez la définition de votre outil :

```python
def setup_tools():
    """Configure and register all tools."""
    manager = get_tool_manager()
    
    # Auto-discover all functions in this module
    manager.discover_functions_from_module(
        sys.modules[__name__],
        exclude=['setup_tools', 'get_tool_manager']
    )
    
    # Load existing definitions from JSON
    manager.load_tools_from_json()
    
    # Register all tools with their definitions
    tools_definitions = [
        # ... outils existants ...
        
        # VOTRE NOUVEL OUTIL
        {
            "name": "mon_nouvel_outil",
            "description": "Description de votre outil",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Description du paramètre 1"
                    },
                    "param2": {
                        "type": "integer",
                        "description": "Description du paramètre 2"
                    }
                },
                "required": ["param1", "param2"]
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
```

### Étape 3 : Tester

Exécutez le fichier pour tester :

```bash
python src/custom_tools.py
```

Vous devriez voir :
```
✓ Registered 10 tools

✓ 10 tools loaded:
  - calculate_age
  - calculate_multiply
  - calculate_power
  - calculate_sum
  - convert_temperature
  - count_words
  - get_date
  - get_time
  - reverse_string
  - mon_nouvel_outil
```

## Utilisation avec l'Agent

L'agent charge automatiquement tous les outils :

```python
from src.Agent import Agent
from src.ModelClient import ModelClient

# Créer un agent
agent = Agent(ModelClient("groq/llama-3.3-70b-versatile"))

# Les outils sont automatiquement disponibles
print(f"{len(agent.tools)} outils disponibles")

# Utiliser l'agent
response = agent.chat("Quelle heure est-il ?")
print(response)
```

## Outils disponibles actuellement

### 🕐 Outils par défaut
- `get_time()` - Obtenir l'heure actuelle en format ISO
- `get_date()` - Obtenir la date actuelle (YYYY-MM-DD)

### ➗ Outils mathématiques
- `calculate_sum(a, b)` - Addition de deux entiers
- `calculate_multiply(a, b)` - Multiplication de deux entiers
- `calculate_power(base, exponent)` - Calcul de puissance

### 📝 Outils de manipulation de chaînes
- `reverse_string(text)` - Inverser une chaîne
- `count_words(text)` - Compter les mots

### 🛠️ Outils utilitaires
- `convert_temperature(celsius)` - Convertir Celsius en Fahrenheit
- `calculate_age(birth_year)` - Calculer l'âge depuis l'année de naissance

## Rétrocompatibilité

Le fichier `tools.py` importe simplement depuis `custom_tools.py` pour maintenir la compatibilité avec le code existant.

```python
# Dans tools.py
from src.custom_tools import TOOLS, TOOL_MAP, get_time, get_date, ...
```

## Configuration JSON

Les outils sont également définis dans `tools_config.json` pour le format OpenAI :

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_time",
        "description": "Get the current server time in ISO format",
        "parameters": {
          "type": "object",
          "properties": {},
          "required": []
        }
      }
    }
  ]
}
```

## Avantages de cette architecture

✅ **Un seul fichier** - Tout est centralisé dans `custom_tools.py`  
✅ **Auto-découverte** - Les fonctions sont automatiquement détectées  
✅ **Facile à étendre** - Ajoutez simplement une fonction et sa définition  
✅ **Testable** - Exécutez directement `python src/custom_tools.py`  
✅ **Rétrocompatible** - `tools.py` continue de fonctionner  
✅ **Documentation intégrée** - Docstrings dans le code  

## Exemples

Voir les fichiers dans le dossier `examples/` :
- `add_tools_example.py` - Comment ajouter de nouveaux outils
- `quick_tool_guide.py` - Guide rapide d'utilisation
- `specialized_agents.py` - Agents spécialisés avec des outils spécifiques

## Support

Pour plus d'informations :
- Consultez `DEVELOPER_GUIDE.md` pour la structure générale du projet
- Consultez `TOOLS_README.md` pour des détails sur l'architecture des outils
- Examinez le code de `custom_tools.py` directement (bien commenté)
