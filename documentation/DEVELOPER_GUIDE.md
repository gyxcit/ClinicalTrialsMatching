# 🛠️ Guide du Développeur

## Introduction

Ce guide vous aidera à étendre et personnaliser le framework Agent AI pour vos besoins spécifiques.

## 🏗️ Architecture du Framework

### Composants Principaux

```
┌─────────────────────────────────────────────────────────┐
│                     Application                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐        ┌────────────────┐             │
│  │    Agent     │──────▶ │  ModelClient   │            │
│  │              │        │                │             │
│  │ - chat()     │        │ - generate_    │             │
│  │ - memory     │        │   response()   │             │
│  │ - tools      │        └────────────────┘             │
│  └──────────────┘                 │                     │
│         │                          │                    │
│         │                          ▼                    │
│         │                  ┌──────────────┐             │
│         │                  │   LiteLLM    │             │
│         │                  └──────────────┘             │
│         │                                               │
│         ▼                                               │
│  ┌──────────────┐        ┌────────────────┐             │
│  │   Memory     │        │     Tools      │             │
│  │              │        │                │             │
│  │ - add()      │        │ - TOOLS list   │             │
│  │ - get()      │        │ - TOOL_MAP     │             │
│  │ - clear()    │        │ - register()   │             │
│  └──────────────┘        └────────────────┘             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 📝 Créer un Nouvel Outil

Les outils sont maintenant définis dans un fichier JSON (`src/tools_config.json`) pour plus de flexibilité.

### Méthode 1 : Ajouter dans tools_config.json

```json
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
            "param1": {
              "type": "string",
              "description": "Premier paramètre obligatoire"
            },
            "param2": {
              "type": "integer",
              "description": "Second paramètre optionnel",
              "default": 10
            }
          },
          "required": ["param1"]
        }
      }
    }
  ]
}
```

Ensuite, implémentez la fonction dans `tools.py` :

```python
# Dans src/tools.py

def my_custom_tool(param1: str, param2: int = 10) -> str:
    """Implementation de l'outil."""
    result = f"Processing {param1} with value {param2}"
    return result

# Ajouter au TOOL_MAP
TOOL_MAP["my_custom_tool"] = my_custom_tool
```

### Méthode 2 : Enregistrement Dynamique

```python
from src.tools import register_tool, save_tools_to_json

def my_tool(param1: str, param2: int = 10) -> str:
    """Description de l'outil."""
    result = f"Processing {param1} with value {param2}"
    return result

# Enregistrer l'outil
register_tool(
    name="my_tool",
    function=my_tool,
    description="Description courte de ce que fait l'outil",
    parameters={
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Premier paramètre obligatoire"
            },
            "param2": {
                "type": "integer",
                "description": "Second paramètre optionnel",
                "default": 10
            }
        },
        "required": ["param1"]
    }
)

# Optionnel : Sauvegarder dans le JSON
save_tools_to_json()
```

### Méthode 3 : Ajout Direct dans tools.py

```python
# Dans src/tools.py

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates."""
    from math import radians, cos, sin, asin, sqrt
    
    # Haversine formula
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km

# Ajouter à TOOLS
TOOLS.append({
    "type": "function",
    "function": {
        "name": "calculate_distance",
        "description": "Calculate distance in km between two GPS coordinates",
        "parameters": {
            "type": "object",
            "properties": {
                "lat1": {"type": "number", "description": "Latitude of point 1"},
                "lon1": {"type": "number", "description": "Longitude of point 1"},
                "lat2": {"type": "number", "description": "Latitude of point 2"},
                "lon2": {"type": "number", "description": "Longitude of point 2"}
            },
            "required": ["lat1", "lon1", "lat2", "lon2"]
        }
    }
})

# Ajouter à TOOL_MAP
TOOL_MAP["calculate_distance"] = calculate_distance
```

## 🤖 Créer un Agent Personnalisé

### Template de Base

```python
from typing import Optional
from src.Agent import Agent

class CustomAgent(Agent):
    """Votre agent personnalisé."""
    
    def __init__(
        self,
        name: str = "CustomAgent",
        model: str = "groq/llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        **kwargs
    ):
        # Définir un system prompt personnalisé
        system_prompt = """
        Vous êtes un agent spécialisé en [DOMAINE].
        Vous aidez les utilisateurs à [OBJECTIF].
        Toujours [RÈGLES SPÉCIFIQUES].
        """
        
        super().__init__(
            name=name,
            system_prompt=system_prompt,
            model=model,
            api_key=api_key,
            api_base=api_base,
            **kwargs
        )
    
    def custom_method(self, param: str) -> str:
        """Méthode personnalisée spécifique à votre agent."""
        # Votre logique
        result = self.chat(f"Process this: {param}")
        return result
```

### Exemple Concret : Agent Traducteur

```python
from src.Agent import Agent
from typing import Optional, List

class TranslatorAgent(Agent):
    """Agent spécialisé en traduction."""
    
    SUPPORTED_LANGUAGES = ["fr", "en", "es", "de", "it", "pt"]
    
    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "en",
        api_key: Optional[str] = None,
    ):
        system_prompt = f"""You are a professional translator.
        Source language: {source_lang}
        Target language: {target_lang}
        
        Rules:
        - Translate accurately while preserving meaning
        - Maintain the tone and style of the original
        - Explain cultural nuances when relevant
        - If source language is 'auto', detect it first
        """
        
        self.source_lang = source_lang
        self.target_lang = target_lang
        
        super().__init__(
            name=f"Translator_{source_lang}_to_{target_lang}",
            system_prompt=system_prompt,
            model="groq/llama-3.3-70b-versatile",
            api_key=api_key
        )
    
    def translate(self, text: str) -> str:
        """Translate text from source to target language."""
        prompt = f"Translate the following text to {self.target_lang}:\n\n{text}"
        return self.chat(prompt)
    
    def translate_batch(self, texts: List[str]) -> List[str]:
        """Translate multiple texts."""
        return [self.translate(text) for text in texts]
```

## 💾 Personnaliser la Mémoire

### Mémoire Persistante

```python
import json
from pathlib import Path
from typing import List, Dict, Optional
from src.memory import Memory

class PersistentMemory(Memory):
    """Memory that persists to disk."""
    
    def __init__(
        self,
        max_history: Optional[int] = None,
        save_path: str = "memory.json"
    ):
        super().__init__(max_history=max_history)
        self.save_path = Path(save_path)
        self.load()
    
    def add(self, role: str, content: str) -> None:
        """Add message and save to disk."""
        super().add(role, content)
        self.save()
    
    def save(self) -> None:
        """Save memory to disk."""
        with open(self.save_path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def load(self) -> None:
        """Load memory from disk."""
        if self.save_path.exists():
            with open(self.save_path, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
```

### Mémoire avec Recherche Sémantique

```python
from src.memory import Memory
from typing import List, Dict

class SemanticMemory(Memory):
    """Memory with semantic search capabilities."""
    
    def __init__(self, max_history: Optional[int] = None):
        super().__init__(max_history=max_history)
        # Vous pourriez ajouter un modèle d'embeddings ici
        # self.embedder = SentenceTransformer('model-name')
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        """Search memory for relevant messages."""
        # Placeholder - implémentation avec embeddings
        # query_embedding = self.embedder.encode(query)
        # Calculate similarity with all messages
        # Return top_k most similar
        
        # Simple keyword search pour l'exemple
        results = [
            msg for msg in self.history 
            if query.lower() in msg['content'].lower()
        ]
        return results[:top_k]
```

## 🔧 Personnaliser ModelClient

### Client avec Retry Logic

```python
from src.ModelClient import ModelClient
import time
from typing import List, Dict, Any, Optional

class ResilientModelClient(ModelClient):
    """ModelClient with automatic retry on failure."""
    
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        super().__init__(model=model, api_key=api_key, api_base=api_base)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return super().generate_response(messages, tools, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise last_error
```

## 🧪 Tests

### Template de Test

```python
import pytest
from src.Agent import Agent
import os

@pytest.fixture
def agent():
    """Create agent for testing."""
    return Agent(
        name="TestAgent",
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY")
    )

def test_agent_initialization(agent):
    """Test agent is properly initialized."""
    assert agent.name == "TestAgent"
    assert agent.memory is not None
    assert agent.tools is not None

def test_agent_chat(agent):
    """Test basic chat functionality."""
    response = agent.chat("Hello")
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0

def test_agent_memory(agent):
    """Test memory persistence."""
    agent.chat("My name is Alice")
    response = agent.chat("What's my name?")
    assert "Alice" in response or "alice" in response.lower()
```

## 📊 Monitoring et Logging

### Logger Personnalisé

```python
import logging
from datetime import datetime

class AgentLogger:
    """Custom logger for agent activities."""
    
    def __init__(self, agent_name: str):
        self.logger = logging.getLogger(f"Agent.{agent_name}")
        self.agent_name = agent_name
    
    def log_conversation(self, user_input: str, agent_response: str):
        """Log a conversation turn."""
        timestamp = datetime.now().isoformat()
        self.logger.info(
            f"[{timestamp}] User: {user_input[:100]}... "
            f"| Agent: {agent_response[:100]}..."
        )
    
    def log_tool_call(self, tool_name: str, args: dict, result: str):
        """Log a tool invocation."""
        self.logger.debug(
            f"Tool called: {tool_name} "
            f"with args: {args} "
            f"result: {result[:50]}..."
        )
```

## 🚀 Déploiement

### API REST avec FastAPI

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.Agent import Agent
import os

app = FastAPI()

# Initialize agent
agent = Agent(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint."""
    try:
        response = agent.chat(request.message)
        return ChatResponse(
            response=response,
            session_id=request.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

# Run with: uvicorn api:app --reload
```

## 📚 Ressources

### Documentation Utile
- [LiteLLM Docs](https://docs.litellm.ai/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

### Best Practices
1. **Toujours ajouter des type hints**
2. **Documenter avec docstrings**
3. **Gérer les erreurs avec try/except**
4. **Logger les actions importantes**
5. **Tester votre code**

### Exemples de Projets
Consultez le dossier `examples/` pour :
- `example_usage.py` : Usage basique
- `specialized_agents.py` : Agents personnalisés
- Plus à venir...

## 💡 Idées d'Extensions

1. **Agents Multi-Modèles** : Switch entre modèles selon le contexte
2. **Mémoire Vectorielle** : Utiliser embeddings pour recherche sémantique
3. **Outils Avancés** : Intégration avec APIs externes
4. **Interface UI** : Streamlit ou Gradio
5. **Multi-Agent System** : Agents qui collaborent

## 🤝 Contribution

Pour contribuer :
1. Fork le projet
2. Créer une branche feature
3. Coder avec tests et docs
4. Submit pull request

## 📞 Support

Questions ? Consultez :
- README.md pour usage de base
- OPTIMIZATIONS.md pour détails techniques
- Ce guide pour développement avancé
