# 🔧 Système de Gestion des Outils

## Vue d'ensemble

Les outils de l'agent sont maintenant configurés via un fichier JSON (`tools_config.json`) pour une gestion plus flexible et une séparation claire entre la définition des outils et leur implémentation.

## Structure

```
src/
├── tools.py              # Implémentation des outils et gestionnaire
└── tools_config.json     # Configuration JSON des outils
```

## Format du JSON

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "nom_de_l_outil",
        "description": "Description de ce que fait l'outil",
        "parameters": {
          "type": "object",
          "properties": {
            "param_name": {
              "type": "string|integer|boolean|etc",
              "description": "Description du paramètre"
            }
          },
          "required": ["param_name"]
        }
      }
    }
  ]
}
```

## Ajouter un Nouvel Outil

### Étape 1 : Définir dans JSON

Ajoutez la définition dans `tools_config.json` :

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "calculate_distance",
        "description": "Calculate distance between two points",
        "parameters": {
          "type": "object",
          "properties": {
            "lat1": {"type": "number", "description": "Latitude point 1"},
            "lon1": {"type": "number", "description": "Longitude point 1"},
            "lat2": {"type": "number", "description": "Latitude point 2"},
            "lon2": {"type": "number", "description": "Longitude point 2"}
          },
          "required": ["lat1", "lon1", "lat2", "lon2"]
        }
      }
    }
  ]
}
```

### Étape 2 : Implémenter dans tools.py

Ajoutez l'implémentation et enregistrez-la :

```python
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two GPS coordinates."""
    from math import radians, cos, sin, asin, sqrt
    
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c

# Ajouter au TOOL_MAP
TOOL_MAP["calculate_distance"] = calculate_distance
```

### Étape 3 : Recharger

```python
from src.tools import reload_tools

# Recharger les outils depuis JSON
reload_tools()
```

## Utilisation Programmatique

### Charger les Outils

```python
from src.tools import TOOLS, TOOL_MAP, load_tools_from_json

# Outils par défaut (chargés automatiquement)
print(f"Nombre d'outils : {len(TOOLS)}")

# Charger depuis un fichier custom
custom_tools = load_tools_from_json("my_tools.json")
```

### Enregistrer un Outil Dynamiquement

```python
from src.tools import register_tool, save_tools_to_json

def my_tool(param: str) -> str:
    return f"Result: {param}"

# Enregistrer en mémoire
register_tool(
    name="my_tool",
    function=my_tool,
    description="My custom tool",
    parameters={
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "Input parameter"}
        },
        "required": ["param"]
    }
)

# Optionnel : Sauvegarder dans JSON
save_tools_to_json()
```

### Recharger les Outils

```python
from src.tools import reload_tools

# Après avoir modifié tools_config.json
reload_tools()
```

## Outils Disponibles

### get_time
- **Description** : Get the current server time in ISO format
- **Paramètres** : Aucun
- **Retour** : String (ISO 8601 format)

### get_date
- **Description** : Get the current date (YYYY-MM-DD format)
- **Paramètres** : Aucun
- **Retour** : String (YYYY-MM-DD)

## Exemples

Voir `examples/tools_management.py` pour des exemples complets :

```bash
python examples/tools_management.py
```

## Avantages de l'Approche JSON

### ✅ Séparation des Préoccupations
- Configuration séparée du code
- Facile à modifier sans toucher au code Python

### ✅ Portabilité
- Configuration partageable entre projets
- Versionnable indépendamment

### ✅ Validation
- Structure claire et validable
- Compatible avec JSON Schema

### ✅ Gestion Dynamique
- Rechargement à chaud possible
- Ajout/suppression sans redémarrage

### ✅ Collaboration
- Non-développeurs peuvent ajouter des outils
- Format standard et lisible

## Migration depuis l'Ancien Format

Si vous aviez des outils définis directement en Python :

```python
# Ancien format (tools.py)
TOOLS = [
    {
        "type": "function",
        "function": {...}
    }
]
```

Pour migrer :

1. Copiez les définitions dans `tools_config.json`
2. Gardez les implémentations dans `tools.py`
3. Ajoutez au `TOOL_MAP`

## Bonnes Pratiques

1. **Toujours documenter** : Description claire de chaque outil
2. **Typer correctement** : Utilisez les bons types JSON (string, integer, etc.)
3. **Required fields** : Spécifiez les paramètres obligatoires
4. **Nommage** : Utilisez snake_case pour les noms d'outils
5. **Sauvegarder** : Committez le JSON avec votre code

## Dépannage

### Outil non trouvé
```
KeyError: 'my_tool'
```
→ Vérifiez que l'outil est dans `TOOL_MAP`

### Erreur de chargement JSON
```
FileNotFoundError: tools_config.json
```
→ Vérifiez le chemin du fichier JSON

### Outil défini mais pas d'implémentation
```
Tool 'my_tool' not found in tool_map
```
→ Ajoutez la fonction à `TOOL_MAP` dans `tools.py`

## API Reference

### Functions

#### `load_tools_from_json(json_path=None)`
Charge les définitions d'outils depuis JSON

#### `register_tool(name, function, description, parameters=None)`
Enregistre un nouvel outil dynamiquement

#### `save_tools_to_json(json_path=None)`
Sauvegarde les outils actuels dans JSON

#### `reload_tools()`
Recharge les outils depuis JSON

### Variables

#### `TOOLS: List[Dict[str, Any]]`
Liste des définitions d'outils (format OpenAI)

#### `TOOL_MAP: Dict[str, Callable]`
Map des noms d'outils vers leurs implémentations
