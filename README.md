# Agent AI Framework

Un framework d'agent IA modulaire et extensible avec support des outils et gestion de la mémoire, basé sur LiteLLM.

## 📋 Fonctionnalités

- **Agent intelligent** avec support multi-tours de conversation
- **Système d'outils** extensible avec appels de fonctions
- **Gestion de la mémoire** pour contexte conversationnel
- **Support multi-modèles** via LiteLLM (Groq, OpenAI, Ollama, etc.)
- **Gestion d'erreurs** robuste avec logging
- **Type hints** complets pour meilleure IDE support

## 🏗️ Architecture

```
code/
├── src/
│   ├── Agent.py          # Agent principal avec boucle de réflexion
│   ├── ModelClient.py    # Client LLM via LiteLLM
│   ├── memory.py         # Gestion de l'historique
│   ├── tools.py          # Définition et registry des outils
│   ├── get_trials.py     # Récupération données clinicaltrials.gov
│   └── config.py         # Configuration centralisée
├── test/
│   └── agent_test.py     # Tests de l'agent
├── examples/
│   └── example_usage.py  # Exemples d'utilisation
└── requirements.txt      # Dépendances
```

## 🚀 Installation

1. Cloner le repository
2. Installer les dépendances :

```powershell
pip install -r requirements.txt
```

3. Créer un fichier `.env` avec vos clés API :

```env
GROQ_API_KEY=your_groq_api_key_here
```

## 📖 Utilisation

### Agent Basique

```python
from src.Agent import Agent
import os

# Initialiser l'agent
agent = Agent(
    name="assistant",
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# Envoyer un message
response = agent.chat("Quelle heure est-il ?")
print(response)
```

### ModelClient Direct

```python
from src.ModelClient import ModelClient
import os

# Client pour appels directs au LLM
client = ModelClient(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]

response = client.generate_response(messages)
print(response["choices"][0]["message"]["content"])
```

### Ajouter des Outils Personnalisés

```python
from src.tools import register_tool

def my_custom_tool(param1: str, param2: int) -> str:
    """Ma fonction personnalisée."""
    return f"Résultat: {param1} x {param2}"

# Enregistrer l'outil
register_tool(
    name="my_tool",
    function=my_custom_tool,
    description="Description de mon outil",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Premier paramètre"},
            "param2": {"type": "integer", "description": "Second paramètre"}
        },
        "required": ["param1", "param2"]
    }
)
```

### Gestion de la Mémoire

```python
from src.memory import Memory

# Créer une mémoire avec limite
memory = Memory(max_history=10)

# Ajouter des messages
memory.add("user", "Bonjour")
memory.add("assistant", "Salut! Comment puis-je vous aider?")

# Récupérer l'historique
history = memory.get()
last_5 = memory.get(last_n=5)

# Vider la mémoire
memory.clear()
```

## 🔧 Configuration

### Modèles Supportés

- **Groq**: `groq/llama-3.3-70b-versatile`, `groq/mixtral-8x7b-32768`
- **OpenAI**: `openai/gpt-4o`, `openai/gpt-4-turbo`
- **Ollama**: `ollama/mistral:latest`, `ollama/llama2:latest`
- Et tous les modèles supportés par [LiteLLM](https://docs.litellm.ai/docs/providers)

### Options de l'Agent

```python
agent = Agent(
    name="assistant",                           # Nom de l'agent
    system_prompt="You are a helpful AI.",      # Prompt système
    model="groq/llama-3.3-70b-versatile",      # Modèle à utiliser
    api_key="your_key",                         # Clé API
    api_base=None,                              # URL de base (optionnel)
    max_tool_iterations=5                       # Max d'itérations d'outils
)
```

## 📊 Récupération de Données Cliniques

```python
from src.get_trials import fetch_trials

# Récupérer des essais cliniques
trials = fetch_trials(
    condition="diabetes",
    max_studies=100,
    return_status=True
)

# Sauvegarder en JSON
fetch_trials(
    condition="diabetes",
    max_studies=100,
    return_status=False,
    json_output=True,
    output_name="diabetes_trials"
)
```

## 🧪 Tests

```powershell
python -m test.agent_test
```

## 📝 Logging

Le framework utilise le module `logging` standard de Python. Pour configurer :

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🛠️ Développement

### Structure des Outils

Les outils suivent le schéma OpenAI Function Calling :

```python
{
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "What the tool does",
        "parameters": {
            "type": "object",
            "properties": {
                "param_name": {
                    "type": "string",
                    "description": "Parameter description"
                }
            },
            "required": ["param_name"]
        }
    }
}
```

## 📄 Licence

Ce projet est sous licence MIT.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📚 Documentation Complémentaire

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [ClinicalTrials.gov API](https://clinicaltrials.gov/api/gui)
