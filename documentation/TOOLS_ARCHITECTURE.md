# 🏗️ Architecture des Outils - Structure Séparée

## 📁 Structure des Fichiers

```
src/
├── tool_manager.py      # Gestionnaire de outils (logique)
├── tools.py             # Outils par défaut (get_time, get_date)
├── custom_tools.py      # Vos outils personnalisés
└── tools_config.json    # Configuration JSON des outils
```

## 🎯 Responsabilités

### 1. `tool_manager.py` - Gestionnaire
**Responsabilité** : Logique de gestion des outils

```python
class ToolManager:
    - load_tools_from_json()      # Charger depuis JSON
    - save_tools_to_json()         # Sauvegarder dans JSON
    - register_tool()              # Enregistrer un outil
    - discover_functions_from_module()  # Auto-découverte
    - reload_tools()               # Recharger config
```

**Quand l'utiliser** :
- ✅ Pour la logique de gestion
- ✅ Pour créer des gestionnaires personnalisés
- ✅ Pour des opérations avancées

### 2. `tools.py` - Outils Par Défaut
**Responsabilité** : Outils inclus de base

```python
def get_time() -> str:
    """Get current time"""
    
def get_date() -> str:
    """Get current date"""
```

**Quand l'utiliser** :
- ✅ Outils nécessaires pour tous les projets
- ✅ Fonctions utilitaires de base
- ❌ Ne pas ajouter d'outils spécifiques au projet ici

### 3. `custom_tools.py` - Outils Personnalisés
**Responsabilité** : Vos outils spécifiques au projet

```python
def calculate_sum(a: int, b: int) -> int:
    """Your custom tool"""
    
def search_database(query: str) -> str:
    """Another custom tool"""
```

**Quand l'utiliser** :
- ✅ Outils spécifiques à votre application
- ✅ Fonctions métier
- ✅ Intégrations avec APIs externes

### 4. `tools_config.json` - Configuration
**Responsabilité** : Définitions des outils pour l'IA

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "tool_name",
        "description": "What it does",
        "parameters": {...}
      }
    }
  ]
}
```

## 🚀 Utilisation

### Ajouter un Outil Personnalisé

#### Étape 1: Créer la fonction dans `custom_tools.py`

```python
def my_tool(param: str) -> str:
    """My custom tool."""
    return f"Result: {param}"
```

#### Étape 2: Enregistrer l'outil

```python
def register_all_custom_tools():
    from src.tool_manager import get_tool_manager
    import sys
    
    manager = get_tool_manager()
    
    # Auto-découvrir les fonctions
    manager.discover_functions_from_module(sys.modules[__name__])
    
    # Enregistrer avec définition
    manager.register_tool(
        name="my_tool",
        function=my_tool,
        description="Description for the AI",
        parameters={...}
    )
```

#### Étape 3: Utiliser avec l'Agent

```python
from src.Agent import Agent
from src.custom_tools import register_all_custom_tools

# Enregistrer les outils personnalisés
register_all_custom_tools()

# Créer l'agent
agent = Agent(model="groq/llama-3.3-70b-versatile")

# L'agent a maintenant accès à tous les outils !
response = agent.chat("Use my_tool with 'test'")
```

## 📊 Comparaison Avant/Après

### ❌ Avant (Monolithique)
```
tools.py
├── Fonctions d'outils
├── Gestion (load, save, register)
├── Auto-découverte
└── Configuration
```
**Problème** : Tout mélangé, difficile à maintenir

### ✅ Après (Séparé)
```
tool_manager.py  → Gestion
tools.py         → Outils par défaut
custom_tools.py  → Vos outils
tools_config.json → Configuration
```
**Avantages** :
- ✅ Séparation des responsabilités
- ✅ Facilité de maintenance
- ✅ Extensibilité
- ✅ Clarté du code

## 🔄 Flux de Données

```
1. custom_tools.py
   └─→ Définit les fonctions

2. register_all_custom_tools()
   └─→ Auto-découvre et enregistre

3. tool_manager.py
   └─→ Gère TOOL_MAP et TOOLS

4. tools_config.json
   └─→ Stocke les définitions

5. Agent
   └─→ Utilise TOOLS et TOOL_MAP
```

## 💡 Exemples

### Utilisation Basique

```python
from src.tools import TOOLS, TOOL_MAP

# Outils par défaut disponibles
print(list(TOOL_MAP.keys()))
# ['get_time', 'get_date']
```

### Ajouter des Outils Personnalisés

```python
from src.custom_tools import register_all_custom_tools
from src.tool_manager import get_tool_manager

# Enregistrer les outils
register_all_custom_tools()

# Accéder au manager
manager = get_tool_manager()
print(list(manager.tool_map.keys()))
# ['get_time', 'get_date', 'calculate_sum', ...]
```

### Utiliser avec un Agent

```python
from src.Agent import Agent
from src.custom_tools import register_all_custom_tools

# Optionnel : Ajouter outils personnalisés
register_all_custom_tools()

agent = Agent(model="groq/llama-3.3-70b-versatile")
response = agent.chat("What time is it?")
```

## 🛠️ API Reference

### ToolManager

```python
manager = ToolManager(config_path="path/to/config.json")

# Charger depuis JSON
tools = manager.load_tools_from_json()

# Sauvegarder dans JSON
manager.save_tools_to_json()

# Enregistrer un outil
manager.register_tool(name, function, description, parameters)

# Auto-découvrir depuis un module
manager.discover_functions_from_module(module, exclude=[])

# Recharger
manager.reload_tools()

# Accéder aux outils
tool_map = manager.tool_map
tools = manager.tools
```

### Fonctions Globales (Backward Compatibility)

```python
from src.tools import (
    TOOLS,           # Liste des définitions
    TOOL_MAP,        # Map nom → fonction
    register_tool,   # Enregistrer un outil
    save_tools_to_json,  # Sauvegarder
    load_tools_from_json, # Charger
    reload_tools     # Recharger
)
```

## 📝 Bonnes Pratiques

### ✅ DO
- Mettez les outils génériques dans `tools.py`
- Mettez vos outils spécifiques dans `custom_tools.py`
- Utilisez `tool_manager.py` pour la logique
- Documentez chaque fonction avec docstring
- Testez vos outils avant de les enregistrer

### ❌ DON'T
- Ne modifiez pas `tool_manager.py` sans raison
- N'ajoutez pas d'outils spécifiques dans `tools.py`
- Ne mélangez pas logique et outils
- N'oubliez pas d'enregistrer les outils

## 🔍 Debugging

### Lister tous les outils

```python
from src.tool_manager import get_tool_manager

manager = get_tool_manager()
print("Tools:", list(manager.tool_map.keys()))
```

### Vérifier un outil spécifique

```python
if "my_tool" in manager.tool_map:
    result = manager.tool_map["my_tool"](param="test")
    print(result)
```

### Recharger après modification

```python
manager.reload_tools()
```

## 🎓 Avantages de cette Architecture

1. **Modularité** : Chaque fichier a une responsabilité unique
2. **Maintenabilité** : Facile à comprendre et modifier
3. **Extensibilité** : Ajout d'outils sans toucher au core
4. **Testabilité** : Chaque composant testable indépendamment
5. **Clarté** : Code organisé et lisible

## 📚 Ressources

- `tool_manager.py` : Implémentation du gestionnaire
- `tools.py` : Outils par défaut
- `custom_tools.py` : Exemple d'outils personnalisés
- `examples/add_tools_example.py` : Exemple complet
- `DEVELOPER_GUIDE.md` : Guide développeur
